# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.
# Flumotion Transcoder

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

import os

import gobject
gobject.threads_init()
import gst

from gst.extend.discoverer import Discoverer

from flumotion.common import log, common

from flumotion.transcoder.watcher import FilesWatcher

# Transcoder
class Profile(log.Loggable):
    """
    Encoding profile, describing settings for audio and video.

    @param name:         name of the configuration, must be unique in the task
    @param audioencoder: name and parameters of the audio encoder (gst-launch
                         syntax)
    @param videoencoder: name and parameters of the video encoder (gst-launch
                         syntax)
    @param muxer:        name and parameters of the muxer (gst-launch syntax)
    
    @param videowidth:      Width of the output video
    @param videoheight:     Height of the output video
    @param videopar:        Pixel Aspect Ratio of the output video
    @type  videopar:        gst.Fraction
    @param videoframerate:  Framerate of the output video
    @type  videoframerate:  gst.Fraction
    @param audiorate:       Sampling rate of the output audio
    @param audiochannels:     Number of audio channels
    """
    def __init__(self, name, audioencoder, videoencoder, muxer,
                 videowidth=None, videoheight=None, videopar=None,
                 videoframerate=None, audiorate=None, audiochannels=None,
                 maxwidth=None,maxheight=None):
        self.log("Profile: name: %s" % name)
        self.log("Profile: audioencoder: %s, videoencoder: %s, muxer: %s" % (
            audioencoder, videoencoder, muxer))
        self.log("Profile: videowidth:%s, videoheight:%s" % (
            videowidth, videoheight))
        self.log("Profile: par:%s, framerate:%s" % (
            videopar, videoframerate))
        self.log("Profile: audiorate:%s , audiochannels:%s" % (
            audiorate, audiochannels))
        self.name = name
        self.audioencoder = audioencoder
        self.videoencoder = videoencoder
        self.muxer = muxer
        self.videowidth = videowidth
        self.videoheight = videoheight
        self.videopar = videopar
        self.videoframerate = videoframerate
        self.audiorate = audiorate
        self.audiochannels = audiochannels
        self.maxwidth = maxwidth
        self.maxheight = maxheight

        self._validateArguments()

    def _validateArguments(self):
        """ Makes sure the given arguments are valid """
        for factory in [self.audioencoder, self.videoencoder, self.muxer]:
            try:
                element = gst.parse_launch(factory)
            except Exception, e:
                self.warning('Could not parse_launch %s: %r' % (factory, e))
                raise TypeError, "Given factory [%s] cannot be parsed" % factory
            if isinstance(element, gst.Pipeline):
                raise TypeError(
                    "Given factory [%s] should be a simple element, "
                    "not a gst.Pipeline" % factory)
            # FIXME: why an explicit del ?
            del element
        if self.videowidth:
            self.videowidth = int(self.videowidth)
        if self.videoheight:
            self.videoheight = int(self.videoheight)
        if self.videopar and not isinstance(self.videopar, gst.Fraction):
            raise TypeError, "videopar should be a gst.Fraction"
        if self.videoframerate and not isinstance(
            self.videoframerate, gst.Fraction):
            raise TypeError, "videoframerate should be a gst.Fraction"
        if self.audiorate:
            self.audiorate = int(self.audiorate)
        if self.audiochannels:
            self.audiochannels = int(self.audiochannels)

    def getOutputVideoCaps(self, discoverer):
        """
        Return the output video caps, according to the information from the
        discoverer and the configuration.
        Returns None if there was an error.
        """
        if not discoverer.is_video:
            return None
        inpar = dict(discoverer.videocaps[0]).get('pixel-aspect-ratio',
            gst.Fraction(1,1))
        inwidth = discoverer.videowidth
        inheight = discoverer.videoheight

        gst.log('inpar:%s , inwidth:%d , inheight:%d' % (
            inpar, inwidth, inheight))
        
        # rate is straightforward
        rate = self.videoframerate or discoverer.videorate
        gst.log('rate:%s' % rate)
        gst.log('outpar:%s , outwidth:%s, outheight:%s' % (self.videopar,
                                                           self.videowidth,
                                                           self.videoheight))
        
        if self.maxwidth and self.maxheight:
            dar = gst.Fraction(inwidth * inpar.num, inheight * inpar.denom)
            outpar = gst.Fraction(self.maxwidth, self.maxheight)
            if dar.num * outpar.denom > outpar.num * dar.denom:
                # Use width
                (width, height, par) = self._calculateOutputSize(inwidth, 
                    inheight, inpar, self.maxwidth, None, self.videopar)
            else:
                # Use height
                (width, height, par) = self._calculateOutputSize(inwidth, 
                    inheight, inpar, None, self.maxheight, self.videopar)
            
        else:
            (width, height, par) = self._calculateOutputSize(
                inwidth, inheight, inpar, self.videowidth, self.videoheight, 
                self.videopar)

        svtempl = "width=%d,height=%d,pixel-aspect-ratio=%d/%d," \
            "framerate=%d/%d" % (width, height, par.num, par.denom,
               rate.num, rate.denom)
        fvtempl = "video/x-raw-yuv,%s;video/x-raw-rgb,%s" % (svtempl, svtempl)
        return gst.caps_from_string(fvtempl)

    def _calculateOutputSize(self, inwidth, inheight, inpar, outwidth, 
        outheight, outpar):
        """
        Return (outwidth,outheight,outpar) given the video's input width,
        height, and par, and any or all of outwidth, outheight, outpar
        """
        # if we have fixed width,height,par then it's simple too
        if outwidth and outheight and outpar:
            width = outwidth
            height = outheight
            par = outpar
        else:
            # now for the tricky part :)
            # the Display Aspect ratio is going to stay the same whatever
            # happens
            dar = gst.Fraction(inwidth * inpar.num, inheight * inpar.denom)

            gst.log('DAR is %s' % dar)
            
            if outwidth:
                width = outwidth
                if outheight:
                    height = outheight
                    # calculate PAR, from width, height and DAR
                    par = gst.Fraction(dar.num * height, dar.denom * width)
                    gst.log('outgoing par:%s , width:%d , height:%d' % (
                        par, width, height))
                else:
                    if outpar:
                        par = outpar
                    else:
                        par = inpar
                    # Calculate height from width, PAR and DAR
                    height = (par.num * width * dar.denom) / (
                        par.denom * dar.num)
                    gst.log('outgoing par:%s , width:%d , height:%d' % (
                        par, width, height))
            elif outheight:
                height = outheight
                if outpar:
                    par = outpar
                else:
                    # take input PAR
                    par = inpar
                # Calculate width from height, PAR and DAR
                width = (dar.num * par.denom * height) / (dar.denom * par.num)
                gst.log('outgoing par:%s , width:%d , height:%d' % (
                    par, width, height))
            elif outpar:
                # no width/height, just PAR
                par = outpar
                height = inheight
                width = (dar.num * par.denom * height) / (dar.denom * par.num)
                gst.log('outgoing par:%s , width:%d , height:%d' % (
                    par, width, height))
            else:
                # take everything from incoming
                par = inpar
                width = inwidth
                height = inheight
                gst.log('outgoing par:%s , width:%d , height:%d' % (
                    par, width, height))

        return (width,height,par)
                
class MultiTranscoder(gobject.GObject, log.Loggable):
    """
    I take an input file.
    I can encode this input files into multiple output files
    simultaneously.

    Signals:
    _ done : the given filename has succesfully been transcoded
    _ error: An error happened on the given filename

    @ivar timeout: time out before giving up on a file because it's not growing
    """
    __gsignals__ = {
        "done" : ( gobject.SIGNAL_RUN_LAST,
                   gobject.TYPE_NONE,
                   ()),
        "error": ( gobject.SIGNAL_RUN_LAST,
                   gobject.TYPE_NONE,
                   (gobject.TYPE_STRING, )),
        }

    def __init__(self, name, inputfile):
        gobject.GObject.__init__(self)
        self.name = name
        self.inputfile = inputfile

        self._outputs = {} # dict of output file name -> profile

        self._started = False
        self._exposed = False

        self._discoverer = None
        self._pipeline = None
        self._watcher = None
        self._bus = None

        self._queuetype = gst.element_factory_make("queue").__gtype__
        self._queues = {} # element -> Full (gboolean)

        self.timeout = 30

    def addOutput(self, outputPath, profile):
        """
        Add an output file to generate with the given profile.

        @type profile: L{Profile}
        """
        if not isinstance(profile, Profile):
            raise TypeError, "Given profile is not a Profile"

        if self._started:
            self.warning("Cannot add output, already started")
            return

        self._outputs[outputPath] = profile

    def start(self):
        """
        Start transcoding.
        Will emit done or error eventually.
        """
        assert not self._started, "MultiTranscoder already started"
        self._started = True

        if not os.path.exists(self.inputfile):
            self.emit('error', "'%s' does not exist" % self.inputfile)
            return

        # discover the media
        self._discoverer = Discoverer(self.inputfile)
        self._discoverer.connect('discovered', self._discoveredCb)
        self._discoverer.discover()

    def _discoveredCb(self, discoverer, ismedia):
        # called when the discoverer is done
        if not ismedia:
            self.info("Incoming file '%s' is not a media file, ignoring" %
                self.inputfile)
            for otherstream in discoverer.otherstreams:
                self.info("File contains unknown type : %s" % otherstream)
            self.log("not media")
            self._shutDownPipeline()
            self.emit('error', "'%s' is not a media file" % self.inputfile)
            return
        
        self.info("'%s' is a media file, transcoding" % self.inputfile)
        self._pipeline = self._makePipeline(self.inputfile)
        self._bus = self._pipeline.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect("message", self._busMessageCb)
        
        ret = self._pipeline.set_state(gst.STATE_PLAYING)
        if ret == gst.STATE_CHANGE_FAILURE:
            self._shutDownPipeline()
            self.emit('error', "Could not play pipeline for file '%s'" %
                self.inputfile)
            return
        
        # start a FilesWatcher on the expected output files
        paths = [path for path,profile in self._outputs.items()]
        self._watcher = FilesWatcher(paths, timeout=self.timeout)
        self._watcher.connect('complete-file', self._watcherCompleteFileCb)
        self._watcher.connect('file-not-present', self._watcherCompleteFileCb)
        self._watcher.start()

    ## pipeline related

    def _watcherCompleteFileCb(self, watcher, filename):
        # a file has gone unchanged in size for the past self.timeout,
        # we consider we have a timeout
        self._shutDownPipeline()
        self.emit('error', "Timed out trying to transcode '%s'" %
                  self.inputfile)

    # called after discovering
    def _makePipeline(self, filename):
        """
        Build a gst.Pipeline to decode the given file.
        """
        pipeline = gst.Pipeline("%s-%s" % (self.name, filename))

        src = gst.element_factory_make("filesrc")
        src.props.location = filename
        dbin = gst.element_factory_make("decodebin")

        pipeline.add(src, dbin)
        src.link(dbin)

        dbin.connect('no-more-pads', self._decodebinNoMorePadsCb)
        dbin.connect('element-added', self._elementAddedCb)
        
        return pipeline

    def _elementAddedCb(self, dbin, element):
        self.log("element added %s" % element.get_name())
        if element.__gtype__ == self._queuetype:
            self._queues[element] = False
            element.connect('overrun', self._queueOverrunCb, dbin)

    def _queueOverrunCb(self, queue, dbin):
        self.log("overrun in queue %s" % queue.get_name())
        if self._queues[queue]:
            return
        self.log("unique overrun")
        self._queues[queue] = True
        for queue, isfull in self._queues.items():
            if not isfull:
                return
        self._decodebinNoMorePadsCb(dbin)

    def _decodebinNoMorePadsCb(self, dbin):
        # called when decodebin has all the pads and we can start
        # encoding
        if self._exposed:
            return
        self._exposed = True
        self.log('All encoded streams found, adding encoders')
        
        # go over pads, adding encoding bins, creating tees, linking
        encbins = []
        for outputPath, profile in self._outputs.items():
            encbins.append(self._buildEncodingBin(
                outputPath, profile, self._discoverer))

        # add encoding bins to pipeline and set them to paused
        for bin in encbins:
            try:
                self._pipeline.add(bin)
                bin.set_state(gst.STATE_PLAYING)
            except gst.AddError:
                self.log("decodebin already emitted no-more-pads")
                return
        
        for srcpad in dbin.src_pads():
            if srcpad.get_caps().to_string().startswith('video/x-raw') \
                and self._discoverer.is_video:
                sinkp = "videosink"
            elif self._discoverer.is_audio:
                sinkp = "audiosink"
            else:
                self.warning("Decodebin has got a pad we didn't find "
                    "during discovery %s [caps:%s]" % (
                        srcpad, srcpad.get_caps().to_string()))
                continue

            self.debug('Connecting decodebin srcpad %r with caps %s' % (
                srcpad, srcpad.get_caps().to_string()))
            tee = gst.element_factory_make("tee")
            self._pipeline.add(tee)
            srcpad.link(tee.get_pad("sink"))
            tee.set_state(gst.STATE_PLAYING)
            try:
                for bin in encbins:
                    tee.get_pad("src%d").link(bin.get_pad(sinkp))
            except gst.LinkError:
                self.warning("Couldn't link to encoding bins, "
                    "aborting transcoding")
                # We are in the streaming thread, we have to shutdown and emit
                # messages from the main thread :(
                gobject.idle_add(self._shutDownPipeline)
                gobject.idle_add(self._asyncError,
                    "Couldn't link to encoding bins")
                return

    def _asyncError(self, message):
        """ Use this method to emit an error message in the main thread """
        self.emit('error', message)

    # FIXME: why not just use self._discoverer ?
    def _buildEncodingBin(self, outputPath, profile, discoverer):
        """
        Create an Encoding bin for the given output file, profile,
        and discoverer.
        """
        outputName = os.path.basename(outputPath)
        self.log("Creating Encoding bin for %s with profile %s" % (
            outputName, profile.name))
        bin = gst.Bin("encoding-%s-%s" % (profile.name, outputName))

        # filesink
        filesink = gst.element_factory_make("filesink")
        filesink.props.location = outputPath

        # muxer
        muxer = gst.parse_launch(profile.muxer)
        bin.add(muxer, filesink)
        muxer.link(filesink)

        if discoverer.is_audio:
            # audio
            aenc = gst.parse_launch(profile.audioencoder)
            aqueue = gst.element_factory_make("queue", "audioqueue")
            aconv = gst.element_factory_make("audioconvert")
            ares = gst.element_factory_make("audioresample")

            aqueue.props.max_size_time = 0
            
            bin.add(aqueue, ares, aconv, aenc)
            gst.element_link_many(aqueue, aconv, ares)
            
            if (profile.audiorate or profile.audiochannels):
                audiochannels = profile.audiochannels or discoverer.audiochannels
                astmpl = "rate=%d,channels=%d" % (profile.audiorate, audiochannels)
                atmpl = "audio/x-raw-int,%s;audio/x-raw-float,%s" % (
                    astmpl, astmpl)
                caps = gst.caps_from_string(atmpl)
                ares.link(aenc, caps)
            else:
                ares.link(aenc)
                
            aenc.link(muxer)
        
            bin.add_pad(gst.GhostPad("audiosink", aqueue.get_pad("sink")))

        if discoverer.is_video:
            # video
            venc = gst.parse_launch(profile.videoencoder)
            vqueue = gst.element_factory_make("queue", "videoqueue")
            cspace = gst.element_factory_make("ffmpegcolorspace")
            videorate = gst.element_factory_make("videorate")
            videoscale = gst.element_factory_make("videoscale")

            vqueue.props.max_size_time = 0
            # use bilinear scaling for better image quality
            videoscale.props.method = 1
            
            bin.add(vqueue, cspace, videorate, videoscale, venc)
            gst.element_link_many(vqueue, cspace, videorate, videoscale)
            
            caps = profile.getOutputVideoCaps(discoverer)
            if caps:
                gst.log("%s" % caps.to_string())
                videoscale.link(venc, caps)
            else:
                videoscale.link(venc)
                
            venc.link(muxer)
                
            bin.add_pad(gst.GhostPad("videosink", vqueue.get_pad("sink")))

        return bin

    def _busMessageCb(self, bus, message):
        if message.type == gst.MESSAGE_STATE_CHANGED:
            pass
        elif message.type == gst.MESSAGE_ERROR:
            gstgerror, debug = message.parse_error()
            msg = "GStreamer error while processing '%s': %s" % (
                self.inputfile, gstgerror.message)
            self.warning(msg)
            self.debug("additional debug info: %s" % debug)
            self._shutDownPipeline()
            self.emit('error', msg)
        elif message.type == gst.MESSAGE_EOS:
            self.debug('EOS, done')
            self._shutDownPipeline()
            self.emit('done')
        else:
            self.log('Unhandled message %r' % message)

    def _shutDownPipeline(self):
        if self._bus:
            self._bus.remove_signal_watch()
        self._bus = None
        if self._pipeline:
            self.log("about to set pipeline to NULL")
            self._pipeline.set_state(gst.STATE_NULL)
            self.log("pipeline set to NULL")
        self._pipeline = None
        if self._watcher:
            self._watcher.stop()
            self._watcher = None
