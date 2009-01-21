import gst

try:
    from twisted.internet import gtk2reactor
    gtk2reactor.install()
except:
    pass

from twisted.internet import reactor, defer


class AnalysisError(Exception):
    pass


class NotMediaFileError(AnalysisError):
    pass


class AnalysisTimeoutError(AnalysisError):
    pass


class MediaInfo(object):
    def __init__(self, source):
        self.source = source

        self.mimetype = None
        self.codecs = []
        self.streams = []

        self.audio = []
        self.video = []
        self.other = []

        self.tags = {}

    def add_stream(self, stream):
        self.streams.append(stream)

        scaps = stream.caps.to_string()
        if scaps.startswith('audio/x-raw'):
            self.audio.append(stream)
        elif scaps.startswith('video/x-raw'):
            self.video.append(stream)
        else:
            self.other.append(stream)

    def __repr__(self):
        return '<MediaInfo: %r>' % (self.__dict__,)


class StreamInfo(object):
    def __init__(self, caps):
        self.caps = caps
        self.length = 0

    def __repr__(self):
        d = dict(self.__dict__)
        d.pop('caps')
        return '<StreamInfo %r %r>' % (self.caps.to_string(), d)


class DiscovererAdapter(MediaInfo):
    def __init__(self, mi):
        self._obj = mi

    @property
    def mimetype(self):
        return self._obj.mimetype

    @property
    def audiocaps(self):
        if self._obj.audio:
            return self._obj.audio[0].caps
        return {}

    @property
    def videocaps(self):
        if self._obj.video:
            return self._obj.video[0].caps
        return {}

    @property
    def is_audio(self):
        return bool(self._obj.audio)

    @property
    def is_video(self):
        return bool(self._obj.video)

    @property
    def audiolength(self):
        if self._obj.audio:
            return self._obj.audio[0].length
        return 0

    @property
    def videolength(self):
        if self._obj.video:
            return self._obj.video[0].length
        return 0

    @property
    def audiowidth(self):
        if self._obj.audio:
            return self._obj.audio[0].caps[0]['width']
        return 0

    @property
    def audiorate(self):
        if self._obj.audio:
            return self._obj.audio[0].caps[0]['rate']
        return 0

    @property
    def audiochannels(self):
        if self._obj.audio:
            return self._obj.audio[0].caps[0]['channels']
        return 0

    @property
    def audiodepth(self):
        if self._obj.audio and not self.audiofloat:
            return self._obj.audio[0].caps[0]['depth']
        return 0

    @property
    def audiofloat(self):
        if self._obj.audio:
            return 'x-raw-float' in self._obj.audio[0].caps.to_string()
        return False

    @property
    def videowidth(self):
        if self._obj.video:
            return self._obj.video[0].caps[0]['width']
        return 0

    @property
    def videoheight(self):
        if self._obj.video:
            return self._obj.video[0].caps[0]['height']
        return 0

    @property
    def videorate(self):
        if self._obj.video:
            return self._obj.video[0].caps[0]['framerate']
        return 0


class PatchedDiscovererAdapter(DiscovererAdapter):
    @property
    def otherstreams(self):
        return self._obj.other

    @property
    def audiotags(self):
        return {}

    @property
    def videotags(self):
        return {}

    @property
    def othertags(self):
        return self._obj.tags


class Analyzer(object):
    timeout = 10.0
    error_details = False

    def __init__(self, fpath, timeout=None):
        self.fpath = fpath
        if timeout is not None:
            self.timeout = timeout

        self.bus = None
        self.ppl = None
        self.fakesink = None

        self.info = None

        self.streams = {} # {string => StreamInfo}
        self.pending = [] # [Pad, ...]
        self.tags = []
        self.all_pads = False
        self.done = False

        self.sids = []
        self.toid = []
        self.d = None


    def _connect(self, obj, *args):
        self.sids.append((obj, obj.connect(*args)))

    def _setup_pipeline(self, fpath):
        fpathnz = fpath.replace(' ', '_')
        gst.debug('_setup_pipeline: %r' % (fpath,))

        self.ppl = gst.Pipeline('D-%s' % fpathnz)

        src = gst.element_make_from_uri(gst.URI_SRC, fpath, 'src-%s' % fpathnz)
        if not src:
            gst.warning('No element to access: %r' % fpath)
            self._finish(AnalysisError('No element to access the URI.'))
            return False

        dbin = gst.element_factory_make('decodebin2', 'dbin')
        self._connect(dbin, 'new-decoded-pad', self._cb_new_decoded_pad)
        self._connect(dbin, 'no-more-pads', self._cb_no_more_pads)
        self._connect(dbin, 'unknown-type', self._cb_unknown_type)

        tfind = dbin.get_by_name('typefind')
        self._connect(tfind, 'have-type', self._cb_have_type)
        self._connect(tfind.get_pad('src'),
                      'notify::caps', self._cb_notify_caps_tfind)

        self.ppl.add(src, dbin)
        src.link(dbin)

        gst.debug('pipeline created')

        # adding an (unconnected!?) fakesink, as seen in PiTiVi's discoverer
        self.fakesink = gst.element_factory_make('fakesink')
        self.ppl.add(self.fakesink)

        self.bus = self.ppl.get_bus()
        self._connect(self.bus, 'message', self._cb_bus_message)

        self.bus.add_signal_watch()

        return True


    def analyze(self):
        if self.d:
            return self.d
        self.d = defer.Deferred()
        reactor.callLater(0.0, self._analyze)
        return self.d


    def _analyze(self):
        fpath = self.fpath
        self.info = MediaInfo(fpath)
        if not self._setup_pipeline(fpath):
            return

        gst.debug('setting pipeline to PAUSED')
        if self.ppl.set_state(gst.STATE_PAUSED) == gst.STATE_CHANGE_FAILURE:
            # TODO: signal error and fail
            self._finish(AnalysisError("Pipeline didn't go to PAUSED."))
            return

        self.toid = reactor.callLater(self.timeout, self._cb_timeout)

    def _maybe_finish(self):
        if self.all_pads and not self.pending:
            gst.debug('finished, calling _finish')
            reactor.callLater(0.0, self._finish)

    def _finish(self, error=None):
        if self.done:
            return
        self.done = True

        gst.debug('finishing...')

        if self.bus:
            self.bus.remove_signal_watch()
            self.bus = None

        if self.toid:
            self.toid.cancel()
            self.toid = None

        for obj, sid in self.sids:
            obj.disconnect(sid)
        self.sids = []

        if self.ppl:
            self.ppl.set_state(gst.STATE_NULL)
        if self.fakesink:
            self.fakesink.set_state(gst.STATE_NULL)

        if not error:
            # check if there's anything in the info, if so then add tags,
            # otherwise set result to the error
            if self.info.streams:
                self._set_tags()
            else:
                error = NotMediaFileError('No known media found.')

        d = self.d
        info = self.info
        self.ppl = None
        self.fakesink = None
        self.info = None
        self.streams = {}
        self.pending = []
        self.all_pads = False
        self.fpath = None
        self.d = None

        # fire callback/errback with the 'result'
        if error:
            gst.debug('RESULT (err): %r (%r)' % (error, info))
            reactor.callLater(0.0, d.errback, error)
        else:
            gst.log('RESULT  (ok): %r' % info)
            reactor.callLater(0.0, d.callback, info)

    def _add_stream(self, pad, caps):
        pid = pad.get_path_string()
        sinfo = StreamInfo(caps)
        self.streams[pid] = sinfo
        self.info.add_stream(sinfo)
        return sinfo

    def _pad_analysed(self, pad, caps):
        stream = self._add_stream(pad, caps)
        self._query_duration(pad, stream)
        self._maybe_finish()

    def _query_duration(self, pad, stream):
        try:
            length, format = pad.query_duration(gst.FORMAT_TIME)
        except:
            pad.warning("query duration failed")
        else:
            if format == gst.FORMAT_TIME:
                stream.length = length


    def _cb_new_decoded_pad(self, element, pad, is_last):
        caps = pad.get_caps()
        gst.debug('pad: %s, caps: %r, is_last: %s' %
                  (pad, caps.to_string(), is_last))

        if is_last:
            self.all_pads = True

        if caps.is_fixed():
            self._pad_analysed(pad, caps)
            return

        self._decode_some_more(pad)

    def _decode_some_more(self, pad):
        self.pending.append(pad)

        q = gst.element_factory_make('queue') # FIXME: use multique?
        sink = gst.element_factory_make('fakesink')

        self.ppl.add(q, sink)
        pad.link(q.get_pad('sink'))
        q.link(sink)

        gst.debug('caps not fixed, decoding some more... (%r)' % (sink,))

        self._connect(pad, 'notify::caps', self._cb_notify_caps_fixed)

        q.set_state(gst.STATE_PAUSED)
        sink.set_state(gst.STATE_PAUSED)

    def _cb_no_more_pads(self, element):
        gst.debug('no more pads')
        self.all_pads = True
        if self.fakesink:
            self.fakesink.set_state(gst.STATE_NULL)
            self.ppl.remove(self.fakesink)
            self.fakesink = None
        self._maybe_finish()

    def _cb_unknown_type(self, element, pad, caps):
        gst.debug('unknown type: %s, caps: %r' % (pad, caps.to_string()))

    def _cb_have_type(self, element, prob, caps):
        gst.debug('have type: %r, %r, %r' % (prob, caps, caps.to_string()))
        self.info.mimetype = caps.to_string()

    def _cb_notify_caps_fixed(self, pad, smth):
        # Try to get negotiated caps - the fakesink should have got
        # them. If they're not there, just get the caps.
        caps = pad.get_negotiated_caps() or pad.get_caps()

        gst.debug('notified caps: %r, %r, %r' % (pad, smth,
                                                   pad.get_caps().to_string()))
        self.pending.remove(pad)
        self._pad_analysed(pad, pad.get_caps())

    def _cb_notify_caps_tfind(self, pad, smth):
        gst.debug('notified caps: %r, %r, %r' % (pad, smth,
                                                 pad.get_caps().to_string()))


    def _process_tags(self, message):
        t = message.parse_tag()
        gst.debug('tags: %r (%r) (%s)' % ([(k, t[k]) for k in t.keys()],
                                          message.structure.to_string(),
                                          message.src))
        elemid = None
        if message.src:
            elemid = message.src.get_path_string()

        codec_tags = (gst.TAG_AUDIO_CODEC, gst.TAG_VIDEO_CODEC, gst.TAG_CODEC)
        for k in t.keys():
            if k in codec_tags:
                self.info.codecs.append(t[k])
            self.tags.append((elemid, (k, t[k])))

        ## f = message.src.get_factory()
        ## if f:
        ##     c = f.get_klass()
        ## gst.info('f, c: %r, %r' % (f, c))

    def _set_tags(self):
        def deseq(v):
            if len(v) == 1:
                return v[0]
            elif len(v) > 1:
                return v
            return None

        def flatten(lst):
            """Flatten a list of (key, value) tuples."""
            d = {}
            for k, v in lst:
                d.setdefault(k, []).append(v)
            return d.items()

        # we ignore the source element id of a tag for now, as there
        # doesn't seem to be a way to reliably relate tag sources to
        # decodebin2's source pads anyway...
        ftags = [(key, deseq(vals)) for (key, vals) in
                 flatten([kvs for (eid, kvs) in self.tags])]

        self.info.tags.update(ftags)

    def _cb_bus_message(self, bus, message):
        mtype = message.type
        if mtype == gst.MESSAGE_EOS:
            # forcing finish now...
            gst.debug('EOS')
            reactor.callLater(0.0, self._finish)
        elif mtype == gst.MESSAGE_ERROR:
            error, desc = message.parse_error()
            if self.error_details:
                reactor.callLater(0.0, self._finish,
                                  AnalysisError('%s (%s)' % (error.message,
                                                             desc)))
            else:
                reactor.callLater(0.0, self._finish,
                                  AnalysisError('%s' % (error.message,)))
        elif mtype == gst.MESSAGE_TAG:
            self._process_tags(message)
        ## elif mtype == gst.MESSAGE_STATE_CHANGED:
        ##     pass
        ## elif mtype == gst.MESSAGE_WARNING:
        ##     pass
        ## elif mtype == gst.MESSAGE_ELEMENT:
        ##     pass
        else:
            gst.log('bus message: %s (%s)' % (mtype, message.src))

    def _cb_timeout(self):
        self.toid = None
        gst.debug('timed out')
        self._finish(AnalysisTimeoutError('Analysis timed out after'
                                          ' %.1f seconds.' % self.timeout))


## temporary code follows...

class Lab(object):
    def __init__(self):
        self.pending = []

    def addFile(self, fpath):
        self.pending.append(fpath)
        ## self._analyze() ## ?!?


def main(fpath):
    an = Analyzer(fpath)
    d = an.analyze()

    def done(result):
        print result
        reactor.stop()

    d.addBoth(done)

    reactor.run()


if __name__ == '__main__':
    import sys
    fpath = sys.argv[1]
    if not fpath.startswith('file://'):
        import os.path
        fpath = 'file://%s' % os.path.abspath(fpath)
    main(fpath)
