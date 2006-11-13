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
#from discoverer import Discoverer

from flumotion.common import log, common

from flumotion.transcoder.watcher import FilesWatcher

def calculateOutputSize(inwidth, inheight, inpar, outwidth, 
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

def getOutputVideoCaps(discoverer, profile):
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
    if profile.videoframerate:
        rate = gst.Fraction(*profile.videoframerate)
    else:
        rate = discoverer.videorate
    gst.log('rate:%s' % rate)
    gst.log('outpar:%s , outwidth:%s, outheight:%s' % (profile.videopar,
                                                       profile.videowidth,
                                                       profile.videoheight))
    
    videopar = profile.videopar and gst.Fraction(*profile.videopar)
    if profile.maxwidth and profile.maxheight:
        dar = gst.Fraction(inwidth * inpar.num, inheight * inpar.denom)
        outpar = gst.Fraction(profile.maxwidth, profile.maxheight)
        if dar.num * outpar.denom > outpar.num * dar.denom:
            # Use width
            (width, height, par) = calculateOutputSize(inwidth, 
                inheight, inpar, profile.maxwidth, None, videopar)
        else:
            # Use height
            (width, height, par) = calculateOutputSize(inwidth, 
                inheight, inpar, None, profile.maxheight, videopar)
        
    else:
        (width, height, par) = calculateOutputSize(
            inwidth, inheight, inpar, profile.videowidth, profile.videoheight, 
            videopar)

    svtempl = "width=%d,height=%d,pixel-aspect-ratio=%d/%d," \
        "framerate=%d/%d" % (width, height, par.num, par.denom,
           rate.num, rate.denom)
    fvtempl = "video/x-raw-yuv,%s;video/x-raw-rgb,%s" % (svtempl, svtempl)
    return gst.caps_from_string(fvtempl)

                
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

        self._tees = {}

        self.timeout = 30

    def addOutput(self, outputPath, profile):
        """
        Add an output file to generate with the given profile.

        @type profile: L{flumotion.transcoder.config.Profile}
        """
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
        if discoverer.is_audio:
            self.debug("%r has audio", self.inputfile)
        if discoverer.is_video:
            self.debug("%r has video", self.inputfile)
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
        paths = list(self._outputs.keys())
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

        if self._discoverer.is_audio:
            self._tees['audiosink'] = gst.element_factory_make('tee')
        if self._discoverer.is_video:
            self._tees['videosink'] = gst.element_factory_make('tee')

        for tee in self._tees.values():
            pipeline.add(tee)
            
        encbins = []
        for outputPath, profile in self._outputs.items():
            enc = self._makeEncodingBin(outputPath, profile,
                                        self._discoverer)
            encbins.append(enc)
            pipeline.add(enc)
            for pad_name, tee in self._tees.items():
                tee.get_pad('src%d').link(enc.get_pad(pad_name))

        def pad_added(dbin, pad):
            if str(pad.get_caps()).startswith('audio/x-raw'):
                pad.link(self._tees['audiosink'].get_pad('sink'))
            elif str(pad.get_caps()).startswith('video/x-raw'):
                pad.link(self._tees['videosink'].get_pad('sink'))
            else:
                self.info('unknown pad from decodebin: %r (caps %s)',
                          pad, pad.get_caps())
        dbin.connect('pad-added', pad_added)
        
        # at this point we're ready to go, once the tees' sinks are
        # connected.
        return pipeline
        
    # FIXME: why not just use self._discoverer ?
    def _makeEncodingBin(self, outputPath, profile, discoverer):
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
            aenc = self._makeAudioEncodebin(profile, discoverer)
            bin.add(aenc)
            aenc.link(muxer)
            bin.add_pad(gst.GhostPad("audiosink", aenc.get_pad("sink")))

        if discoverer.is_video:
            venc = self._makeVideoEncodebin(profile, discoverer)
            bin.add(venc)
            venc.link(muxer)
            bin.add_pad(gst.GhostPad("videosink", venc.get_pad("sink")))

        return bin

    def _parse_bin_from_description(self, description, ghost_unconnected_pads):
        """
        Implement gst_parse_bin_from_description() in pure python, since the
        C function isn't wrapped.
        """
        # Specify the type as a bin 
        desc = "bin.( %s )" % description

        bin = gst.parse_launch(desc)

        if not bin:
            return None

        if ghost_unconnected_pads:
            pad = bin.find_unconnected_pad(gst.PAD_SRC)
            if pad:
                bin.add_pad(gst.GhostPad("src", pad))

            pad = bin.find_unconnected_pad(gst.PAD_SINK)
            if pad:
                bin.add_pad(gst.GhostPad("sink", pad))

        return bin

    def _makeAudioEncodebin(self, profile, discoverer):
        """
        Create an Encoding bin for the given output file, profile,
        and discoverer.
        """
        bin = gst.Bin()
        conv = gst.element_factory_make("audioconvert")
        res = gst.element_factory_make("audioresample")
        capsfilter = gst.element_factory_make("capsfilter")
        enc = self._parse_bin_from_description(profile.audioencoder, True)
        queue = gst.element_factory_make("queue", "audioqueue")

        if (profile.audiorate or profile.audiochannels):
            audiochannels = profile.audiochannels or discoverer.audiochannels
            astmpl = "rate=%d,channels=%d" % (profile.audiorate, audiochannels)
            atmpl = "audio/x-raw-int,%s;audio/x-raw-float,%s" % (
                astmpl, astmpl)
            self.log('filter: %s', atmpl)
            capsfilter.props.caps = gst.caps_from_string(atmpl)

        bin.add(conv, res, capsfilter, enc, queue)
        gst.element_link_many(conv, res, capsfilter, enc, queue)
        
        bin.add_pad(gst.GhostPad("sink", conv.get_pad("sink")))
        bin.add_pad(gst.GhostPad("src", queue.get_pad("src")))

        return bin

    def _makeVideoEncodebin(self, profile, discoverer):
        bin = gst.Bin()
        cspace = gst.element_factory_make("ffmpegcolorspace")
        videorate = gst.element_factory_make("videorate")
        videoscale = gst.element_factory_make("videoscale")
        capsfilter = gst.element_factory_make("capsfilter")
        enc = self._parse_bin_from_description(profile.videoencoder, True)
        queue = gst.element_factory_make("queue", "videoqueue")

        # use bilinear scaling for better image quality
        videoscale.props.method = 1
        
        caps = getOutputVideoCaps(discoverer, profile)
        if caps:
            gst.log("%s" % caps.to_string())
            capsfilter.props.caps = caps

        bin.add(cspace, videorate, videoscale, capsfilter, enc, queue)
        gst.element_link_many(cspace, videorate, videoscale, capsfilter,
                              enc, queue)
            
        bin.add_pad(gst.GhostPad("sink", cspace.get_pad("sink")))
        bin.add_pad(gst.GhostPad("src", queue.get_pad("src")))

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
