import gst
import gobject
from twisted.internet import reactor

class CuePointsSeeker(gst.Element):

    __gproperties__ = {
        'cuepoints': (str,
                      'Cue points',
                      'List of cue points to read from',
                      None, gobject.PARAM_READWRITE),
        'seek-guard': (gobject.TYPE_UINT64,
                      'Seek guard',
                      'Time to seek before the real seek point',
                      0, 100 * gst.SECOND, 5 * gst.SECOND,
                      gobject.PARAM_READWRITE)
        }

    _audiosinkpadtemplate = gst.PadTemplate("audiosink",
                                        gst.PAD_SINK,
                                        gst.PAD_ALWAYS,
                                        gst.caps_from_string(
                                            "audio/x-raw-float;"
                                            "audio/x-raw-int"))

    _videosinkpadtemplate = gst.PadTemplate("videosink",
                                        gst.PAD_SINK,
                                        gst.PAD_ALWAYS,
                                        gst.caps_from_string(
                                            "video/x-raw-rgb;"
                                            "video/x-raw-yuv"))

    _audiosrcpadtemplate = gst.PadTemplate("audiosrc",
                                        gst.PAD_SRC,
                                        gst.PAD_ALWAYS,
                                        gst.caps_from_string(
                                            "audio/x-raw-float;"
                                            "audio/x-raw-int"))

    _videosrcpadtemplate = gst.PadTemplate("videosrc",
                                        gst.PAD_SRC,
                                        gst.PAD_ALWAYS,
                                        gst.caps_from_string(
                                            "video/x-raw-rgb;"
                                            "video/x-raw-yuv"))

    DEFAULT_SEEK_GUARD = 5 * gst.SECOND

    def __init__(self, delay=0):
        gst.Element.__init__(self)

        self.audio_sinkpad = gst.Pad(self._audiosinkpadtemplate, "audiosink")
        self.audio_sinkpad.set_chain_function(self.audiochainfunc)
        self.audio_sinkpad.set_event_function(self.eventfunc)
        self.add_pad(self.audio_sinkpad)

        self.video_sinkpad = gst.Pad(self._videosinkpadtemplate, "videosink")
        self.video_sinkpad.set_chain_function(self.videochainfunc)
        self.video_sinkpad.set_event_function(self.eventfunc)
        self.add_pad(self.video_sinkpad)

        self.audio_srcpad = gst.Pad(self._audiosrcpadtemplate, "audiosrc")
        self.add_pad(self.audio_srcpad)
        self.video_srcpad = gst.Pad(self._videosrcpadtemplate, "videosrc")
        self.add_pad(self.video_srcpad)

        # Properties
        self.cue_points = None
        self.cue_points_str = ""
        self.seek_guard = self.DEFAULT_SEEK_GUARD

        # Private stuff
        self._need_seek = True
        self._cur_segment = {}
        self._audio_waiting_new_segment = False
        self._video_waiting_new_segment = False
        self._audio_segment_done = False
        self._video_segment_done = False
        self._next_segment = None
        self._file_start = None
        self._last_stop = 0
        self._need_newsegment = True

    def do_get_property(self, property):
        if property.name == "cuepoints":
            return self.cue_points_str
        elif property.name == "seek-guard":
            return self.seek_guard
        raise AttributeError('unknown property %s' % property.name)

    def do_set_property(self, property, value):
        if property.name == "cuepoints":
            self.cue_points = self._parse_cue_points(value)
            if self.cue_points:
                self.cue_points_str = value
        elif property.name == "seek-guard":
            self.seek_guard = value
        else:
            raise AttributeError('unknown property %s' % property.name)

    def audiochainfunc(self, pad, buffer):
        if self._need_seek:
            return gst.FLOW_OK

        if self._clip(pad, buffer):
            if self._need_newsegment:
                self._need_newsegment = False
                self._push_new_segment(self.audio_srcpad)
            self.audio_srcpad.push(buffer)
        self._check_segment_done()
        return gst.FLOW_OK

    def videochainfunc(self, pad, buffer):
        if self._need_seek:
            self._do_seek(pad, False, True)
            return gst.FLOW_OK

        if self._clip(pad, buffer):
            if self._need_newsegment:
                self._need_newsegment = False
                self._push_new_segment(self.video_srcpad)
            self.video_srcpad.push(buffer)
        self._check_segment_done()
        return gst.FLOW_OK

    def eventfunc(self, pad, event):
        if event.type == gst.EVENT_FLUSH_START or\
            event.type == gst.EVENT_FLUSH_STOP:
            return False

        elif event.type == gst.EVENT_EOS:
            if pad == self.video_sinkpad:
                self.video_srcpad.push_event(gst.event_new_eos())
            else:
                self.audio_srcpad.push_event(gst.event_new_eos())
            return False

        elif event.type != gst.EVENT_NEWSEGMENT:
            return True

        # New Segment
        update, r, t, start, stop, position = event.parse_new_segment()
        if not self._file_start:
            # This is the first new segment, we use it to get the start time of
            # the file.
            self._file_start = start
            return False
        # if it's not a segment update, it's because it's a new segment comming
        # after the seek
        if not update:
            # A new segment is starting now after the seek has been
            # done, so update the values of the current segment to clip the
            # incomming buffers with the values of the next segment
            self._cur_segment[pad] = self._next_segment
            self.info("Start of new segment on %s pad %r" %
                      (pad.get_name(), self._cur_segment[pad]))
            if pad == self.video_sinkpad:
                self._video_waiting_new_segment = False
            else:
                self._audio_waiting_new_segment = False

        return False

    def _check_segment_done(self):
        if self._video_segment_done and self._audio_segment_done:
            self._video_segment_done = False
            self._audio_segment_done = False
            if len(self.cue_points) !=0:
                self._do_seek(self.video_sinkpad, False)

    def _push_new_segment(self, pad):
        pad.push_event(
            gst.event_new_new_segment(False, 1.0, gst.FORMAT_TIME, 0, -1, 0))

    def _parse_cue_points(self, cues_str):
        # "start-stop;start-stop;start-stop;..."
        try:
            l = map(lambda s: (long(s.split("-")[0]), long(s.split("-")[1])),\
                    cues_str.split(";"))
            return l
        except ValueError, e:
            self.warning("Could not parse cue points: %r" % e)
            return None

    def _do_seek(self, pad, flush, first=False):
        start, stop =  self.cue_points[0]
        del self.cue_points[0]

        self.info("Preparing segment:  start=%s stop=%s" %
            (gst.TIME_ARGS(start), gst.TIME_ARGS(stop)))

        flags = gst.SEEK_FLAG_ACCURATE
        if flush:
            flags = flags | gst.SEEK_FLAG_FLUSH
        if len(self.cue_points) != 0:
            flags = flags | gst.SEEK_FLAG_SEGMENT

        if start <= self.DEFAULT_SEEK_GUARD:
            seek_start = 0
        else:
            seek_start = start - self.seek_guard

        self.info("Sending seek event:  start=%s stop=%s" %
            (gst.TIME_ARGS(seek_start), gst.TIME_ARGS(stop)))
        # After a segment-done event, the seek must be non-flushing in order to
        # process properly all the remaining buffers of the current segment. The
        # start of the new segment will really happen when we'll receive a
        # new-segment event with update=False.
        self._next_segment = self._make_segment(start, stop)
        event = gst.event_new_seek(1.0, gst.FORMAT_TIME, flags,
            gst.SEEK_TYPE_SET, seek_start + self._file_start,
            gst.SEEK_TYPE_SET, stop + self._file_start)

        reactor.callInThread(pad.push_event, event)

        if first:
            self._cur_segment[self.video_sinkpad] = self._next_segment
            self._cur_segment[self.audio_sinkpad] = self._next_segment
            self._need_seek = False


    def _clip(self, pad, buf):
        '''
        Clips 'buf' to the current segment and re-timestamps it with the stream
        time in the segment plus the segment offset.
        '''
        seg = self._cur_segment.get(pad, None)
        if not seg:
            return False
        if not buf.timestamp >= seg['start'] and buf.timestamp <= seg['stop']:
            self.log("%s dropped: %s" % (pad.get_name(),
                     gst.TIME_ARGS(buf.timestamp)))
            return False

        # Check end of segment
        if seg['stop'] - buf.timestamp <= 500 * gst.MSECOND:
            if pad == self.video_sinkpad:
                if not self._video_waiting_new_segment:
                    self._video_segment_done = True
                    self._video_waiting_new_segment = True
            else:
                if not self._audio_waiting_new_segment:
                    self._audio_segment_done = True
                    self._audio_waiting_new_segment = True

        buf.timestamp = buf.timestamp - seg['start'] + seg['segment-offset']
        self.log("%s out: %s" % (pad.get_name(), gst.TIME_ARGS(buf.timestamp)))
        return True

    def _make_segment(self, start, stop):
        '''
        Makes a new segment where 'start' and 'stop' are the start and stop time
        of the segment in the stream time of the input file and 'segment-offset'
        is the time offset of this segment with respect of the output file
        stream time. For example, start=10s stop=12s segment-offset=40s means
        the segment from 10 to 12 seconds with duration 2 seconds will result in
        the output file in a segment from 40 to 42 seconds.
        '''
        d = {'start': self._file_start + start,
             'stop': self._file_start + stop,
             'segment-offset': self._last_stop}
        self._last_stop += stop - start
        return d

class CuePointsFileSrc(gst.Bin):
    '''
    Decodes segments of a file specified with the 'cuepoints' property.
    This element has a very specific target, which is decoding sources from non
    indexed formats, such as MPEG-PS, with one video stream and one audio
    stream, for transcoding them.
    In non indexed formats, the seek for a new segment must happen a few seconds
    before the real seek point, as we don't know where the keyframes are and thus,
    we need to start decoding some seconds before the real seek point, hopping to
    find a keyframe before the target seek point. This seek guard can be set
    through the property 'seek-guard'.
    '''

    logCategory = "cuepointsfilesrc"

    __gstdetails__ = ('CuePointsFilesrc', 'Source/File',
                      'Read from arbitrary chunks in a file',
                      'Flumotion Dev Team')

    __gproperties__ = {
        'location': (str,
                     'Location',
                     'Location of the file to read',
                     None, gobject.PARAM_READWRITE),
        'cuepoints': (str,
                      'Cue points',
                      'List of cue points to read from',
                      None, gobject.PARAM_READWRITE),
        'seek-guard': (gobject.TYPE_UINT64,
                      'Seek guard',
                      'Time to seek before the real seek point',
                      0, 100 * gst.SECOND, 5 * gst.SECOND,
                      gobject.PARAM_READWRITE)
        }

    _srcpadtemplate = gst.PadTemplate("src\%d",
                                         gst.PAD_SRC,
                                         gst.PAD_SOMETIMES,
                                         gst.caps_from_string("ANY"))

    DEFAULT_SEEK_GUARD = 5 * gst.SECOND

    def __init__(self):
        gst.Bin.__init__(self)

        # Create the gstreamer elements
        self._file_src = gst.element_factory_make("filesrc")
        self._decodebin = gst.element_factory_make("decodebin")
        self._deinterlacer = gst.element_factory_make("ffdeinterlace")
        self._seeker = CuePointsSeeker()

        # Add them to the Bin
        self.add(self._file_src)
        self.add(self._decodebin)
        self.add(self._deinterlacer)
        self.add(self._seeker)

        # Link the filesource to the decodebin and wait for the 'pad-added'
        # signal to link the video and audio identities
        self._file_src.link(self._decodebin)
        self._decodebin.connect("pad-added", self._on_new_pad)
        self._seeker.link(self._deinterlacer)

        # Properties
        self.cue_points_str = None
        self.location = None
        self.seek_guard = self.DEFAULT_SEEK_GUARD

    ## Class methods ##

    def do_get_property(self, property):
        if property.name == "location":
            return self.location
        elif property.name == "cuepoints":
            return self._seeker.get_property('cuepoints')
        elif property.name == "seek-guard":
            return self._seeker.get_property('seek-guard')
        raise AttributeError('unknown property %s' % property.name)

    def do_set_property(self, property, value):
        if property.name == "location":
            self.location = value
            self._file_src.set_property('location', value)
        elif property.name == "cuepoints":
            self._seeker.set_property('cuepoints', value)
        elif property.name == "seek-guard":
            self._seeker.set_property('seek-guard', value)
        else:
            raise AttributeError('unknown property %s' % property.name)


    ## Private methods ##

    def _on_new_pad(self, compbin, pad):
        caps_str = pad.get_caps().to_string()

        if 'audio' in caps_str:
            sink_pad = self._seeker.get_static_pad("audiosink")
            ghost_pad = gst.GhostPad("audiosrc",
                    self._seeker.get_static_pad("audiosrc"))
        elif 'video' in caps_str:
            sink_pad = self._seeker.get_static_pad("videosink")
            ghost_pad = gst.GhostPad("videosrc",
                    self._deinterlacer.get_pad("src"))
        else:
            return

        if not sink_pad.is_linked():
            pad.link(sink_pad)
            ghost_pad.set_active(True)
            self.add_pad(ghost_pad)


def Main(file_path, cue_points):
    import gobject
    import sys

    pipeline = gst.Pipeline("pipeline")

    filesrc = CuePointsFileSrc()
    filesrc.set_property("location", file_path)
    filesrc.set_property("cuepoints", cue_points)
    filesrc.set_property("seek-guard", 2*gst.SECOND)

    videosink = gst.parse_bin_from_description(
                    "queue max-size-time=0 name=vid_queue ! autovideosink sync=true", True)
    audiosink = gst.parse_bin_from_description(
                    "queue max-size-time=0 name=aud_queue ! autoaudiosink sync=true", True)

    def on_new_pad(element, pad):
        caps = str(pad.get_caps())
        if "video" in caps:
            pad.set_active(True)
            pad.link(videosink.get_pad("sink"))
        elif "audio" in caps:
            pad.set_active(True)
            pad.link(audiosink.get_pad("sink"))

    pipeline.add(filesrc)
    pipeline.add(audiosink)
    pipeline.add(videosink)

    def on_error(bus, message):
        _, m = message.parse_error()
        pipeline.set_state(gst.STATE_NULL)
        sys.exit(1)

    def on_eos(bus, message):
        pipeline.set_state(gst.STATE_NULL)
        sys.exit(0)

    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message::eos", on_eos)
    bus.connect("message::error", on_error)

    filesrc.connect("pad-added", on_new_pad)

    pipeline.set_state(gst.STATE_PLAYING)

    gobject.threads_init()
    gobject.MainLoop().run()
    #gtk.gdk.threads_init()
    #gtk.main()

if __name__ == "__main__":
    import sys
    try:
        file_path = sys.argv[1]
        cue_points = sys.argv[2]
    except:
        print "Usage: cuepointsfilesrc file_path cue_points"
        sys.exit(0)

    reactor.callLater(0, Main, file_path, cue_points)
    reactor.run()

