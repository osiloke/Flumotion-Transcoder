# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.
# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import os
import gst
import threading

from zope.interface import Interface, implements

from flumotion.transcoder import log, defer, utils, fileutils
from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.errors import TranscoderConfigError
from flumotion.transcoder.enums import VideoScaleMethodEnum
from flumotion.transcoder.enums import PeriodUnitEnum
from flumotion.transcoder.enums import ThumbOutputTypeEnum
from flumotion.transcoder.waiters import PassiveWaiters
from flumotion.component.transcoder import compconsts
from flumotion.component.transcoder.basetargets import TranscodingTarget
from flumotion.component.transcoder.thumbsink import ThumbSink
from flumotion.component.transcoder.thumbsrc import ThumbSrc
from flumotion.component.transcoder.thumbsamplers import IThumbnailer
from flumotion.component.transcoder.thumbsamplers import FrameSampler
from flumotion.component.transcoder.thumbsamplers import KeyFrameSampler
from flumotion.component.transcoder.thumbsamplers import TimeSampler
from flumotion.component.transcoder.thumbsamplers import PercentSampler
from flumotion.component.transcoder.binmaker import makeMuxerEncodeBin
from flumotion.component.transcoder.binmaker import makeVideoEncodeBin



class ThumbnailTarget(TranscodingTarget):
    
    implements(IThumbnailer)
    
    class EncoderConfig(object):
        def __init__(self, config):
            self.videoWidth = config.thumbsWidth
            self.videoHeight = config.thumbsHeight
            self.videoMaxWidth = None
            self.videoMaxHeight = None
            self.videoWidthMultiple = None
            self.videoHeightMultiple = None
            self.videoScaleMethod = VideoScaleMethodEnum.upscale
            self.videoFramerate = None
            self.videoPAR = (1, 1)            
            format = config.outputFormat
            if format == ThumbOutputTypeEnum.png:
                self.videoEncoder = "ffmpegcolorspace ! pngenc snapshot=false"
            elif format == ThumbOutputTypeEnum.jpg:
                self.videoEncoder = "ffmpegcolorspace ! jpegenc"
            else:
                raise TranscoderConfigError("Unknown thumbnails output "
                                            "format '%s'" % format)        

    def __init__(self, targetContext):
        """
        The filename may contain template variables:
            %(frame)d  => frame number (starting at 1)
            %(keyframe)d  => key-frame number (starting at 1)
            %(index)d  => index of the thumbnail (starting at 1)
            %(timestamp)d => timestamp of the thumbnail
            %(time)s => composed time of the thumbnail, 
                        like %(hours)02d:%(minutes)02d:%(seconds)02d
            %(hours)d => hours from start
            %(minutes)d => minutes from start
            %(seconds)d => seconds from start
        Transcoding config should contains the attributes:
            periodValue
            periodUnit (seconds, frames or percent)
            maxCount
            thumbsWidth
            thumbsHeight
            outputFormat Enum(jpg, png)
        """
        TranscodingTarget.__init__(self, targetContext)
        self._pipeline = None
        self._bus = None
        self._thumbSink = None
        self._thumbSrc = None
        self._fileSink = None
        self._working = False
        self._finalizing = False
        self._pending = [] # [(gst.Buffer, Variables)]
        self._thumbnails = {} # {filename: None}
        self._waiters = PassiveWaiters("Thumbnailer Finalization")
        self._prerollTimeout = None
        self._playErrorTimeout = None
        self._startLock = threading.Lock()
        self._checkConfAttr("periodValue")
        self._checkConfAttr("periodUnit")
        self._checkConfAttr("maxCount")
        self._checkConfAttr("thumbsWidth")
        self._checkConfAttr("thumbsHeight")
        self._checkConfAttr("outputFormat")


    ## Public Overriden Methods ##

    def getOutputFiles(self):
        return self._thumbnails.keys()
        

    ## ITranscoderProducer Overriden Methods ##
    
    def checkSourceMedia(self, sourcePath, sourceAnalysis):
        if not sourceAnalysis.hasVideo:
            self.raiseError("Source media doesn't have video stream")
        return True

    def updatePipeline(self, pipeline, analysis, tees, timeout=None):
        tag = self._getTranscodingTag()
        self.log("Updating transcoding pipeline for thumbnail target '%s'", tag)
        # First connect the custom thumbnail sink
        config = self._getTranscodingConfig()
        unit = config.periodUnit
        value = config.periodValue
        maxCount = config.maxCount
        sampler = self.__createSampler(maxCount, unit, value, analysis)
        thumbSink = ThumbSink(sampler, "ThumbSink-" + tag)
        queue = gst.element_factory_make("queue", "thumbqueue-%s" % tag)
        pipeline.add(queue, thumbSink)
        gst.element_link_many(tees['videosink'], queue, thumbSink)
        
        # Then create the thumbnailing pipeline with a custom thumnail source
        config = self._getTranscodingConfig()
        thumbPipeName = "thumbnailing-" + tag
        thumbPipeline = gst.Pipeline(thumbPipeName)
        thumbSrc = ThumbSrc("ThumbSrc-" + tag)
        encoderConf = self.EncoderConfig(config)
        videoEncBin = makeVideoEncodeBin(encoderConf, analysis, tag,
                                         withRateControl=False, 
                                         logger=self)
        fileSink = gst.element_factory_make("filesink", "filesink-%s" % tag)
        thumbPipeline.add(thumbSrc, videoEncBin, fileSink)
        gst.element_link_many(thumbSrc, videoEncBin, fileSink)
        self._thumbSink = thumbSink
        self._thumbSrc = thumbSrc
        self._pipeline = thumbPipeline
        self._fileSink = fileSink
        self._bus = self._pipeline.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect("message", self._bus_message_callback)

    def finalize(self, timeout=None):
        self._finalizing = True
        if self._working or self._pending:
            return self._waiters.wait(timeout)
        return defer.succeed(self)
    
    def abort(self, timeout=None):
        self.log("Aborting thumbnail target '%s'", self._getTranscodingTag())
        self.__shutdownPipeline()
        return defer.succeed(self)


    ## IThumbnailer Methods ##
    
    def push(self, buffer, vars):
        """
        Warning, this is not called from the main thread.
        """
        self._pending.append((buffer, vars))
        self.__startThumbnailer()

    ## Protected GObject Callback Methods ##

    def _bus_message_callback(self, bus, message):
        try:
            if message.type == gst.MESSAGE_STATE_CHANGED:
                if (message.src == self._pipeline):
                    new = message.parse_state_changed()[1]
                    if new == gst.STATE_PAUSED:
                        self.__onPipelinePrerolled()
                return
            if message.type == gst.MESSAGE_EOS:
                self.__onPipelineEOS()
                return
            if message.type == gst.MESSAGE_ERROR:
                gstgerror, debug = message.parse_error()
                self.__onPipelineError(gstgerror.message, debug)
                return            
            self.log("Unhandled GStreamer message in thumbnailing pipeline "
                     "'%s': %s", self._getTranscodingTag(), message)
        except Exception, e:
            msg = ("Error during thumbnailing pipeline "
                   "message handling: " + str(e))
            debug = log.getExceptionMessage(e)
            self.__postError(msg, debug)


    ## Private Methods ##
    
    def __shutdownPipeline(self):
        self.log("Shutting down thumbnailing pipeline '%s'",
                 self._getTranscodingTag())
        if self._bus:
            self._bus.remove_signal_watch()
        self._bus = None
        if self._pipeline:
            self._pipeline.set_state(gst.STATE_NULL)
        self._pipeline = None

    def __resetPipeline(self):
        assert self._pipeline != None
        self.log("Resetting thumbnailing pipeline '%s'",
                 self._getTranscodingTag())
        self._pipeline.set_state(gst.STATE_NULL)
        self._working = False

    def __startupPipeline(self, buffer, thumbPath):
        assert not self._working
        assert self._pipeline != None
        self.log("Starting up thumbnailing pipeline '%s'",
                 self._getTranscodingTag())
        self._thumbSrc.addBuffer(buffer)
        self._fileSink.props.location = thumbPath
        
        ret = self._pipeline.set_state(gst.STATE_PLAYING)
        if ret == gst.STATE_CHANGE_FAILURE:
            timeout = compconsts.PLAY_ERROR_TIMEOUT
            to = utils.createTimeout(timeout, self.__errorNotReceived)
            self._playErrorTimeout = to
            return
        
        timeout = compconsts.THUMBNAILER_PLAYING_TIMEOUT
        to = utils.createTimeout(timeout, self.__playPipelineTimeout)
        self._prerollTimeout = to

        self._working = True

    def __startThumbnailer(self):
        self._startLock.acquire()
        try:
            if self._working: return
            while True:
                if not self._pending:
                    if self._finalizing:
                        self._waiters.fireCallbacks(self)
                        self.__shutdownPipeline()
                    return
                buffer, vars = self._pending.pop(0)
                template = self._getOutputPath()
                thumbPath = vars.substitute(template)
                if thumbPath in self._thumbnails:
                    self.warning("Thumbnail file '%s' already created, "
                                 "keeping the first one")
                    continue
                fileutils.ensureDirExists(os.path.dirname(thumbPath), "thumbnail")
                self.__startupPipeline(buffer, thumbPath)
                return
        finally:
            self._startLock.release()

    def __postError(self, message, debug=None):
        self._thumbSink.postError(message, debug)
        self.__shutdownPipeline()
        
    def __errorNotReceived(self):
        msg = "Could not play thumbnailing pipeline"
        self.__postError(msg)

    def __playPipelineTimeout(self):
        self.log("Thumbnailing pipeline '%s' stalled at prerolling",
                 self._getTranscodingTag())        
        msg = "Thumbnailing pipeline stalled at prerolling"
        self.__postError(msg)

    def __onPipelineError(self, message, debug):
        self.log("Thumbnailing pipeline '%s' error: %s",
                 self._getTranscodingTag(), message)
        utils.cancelTimeout(self._playErrorTimeout)
        msg = "Thumbnailing pipeline error: " + message
        self.__postError(msg, debug)

    def __onPipelinePrerolled(self):
        self.log("Thumbnailing pipeline '%s' prerolled",
                 self._getTranscodingTag())   
        utils.cancelTimeout(self._prerollTimeout)

    def __onPipelineEOS(self):
        self.log("Thumbnailing pipeline '%s' reach end of stream",
                 self._getTranscodingTag())        
        self._thumbnails[self._fileSink.props.location] = None
        self.__resetPipeline()
        self.__startThumbnailer()

    def __createFrameSampler(self, maxCount, length, period):
        self.log("Sample thumbnails each %s frames %s", str(period),
                 (maxCount and ("to a maximum of %s thumbnails" % str(maxCount)))
                 or "without limitation")
        return FrameSampler(self, maxCount, length, period)
        
    def __createKeyFrameSampler(self, maxCount, length, period):
        self.log("Sample thumbnails each %s keyframes %s", str(period), 
                 (maxCount and ("to a maximum of %s thumbnails" % str(maxCount)))
                 or "without limitation")
        return KeyFrameSampler(self, maxCount, length, period)

    def __createTimeSampler(self, maxCount, length, period):
        self.log("Sample thumbnails each %d seconds %s", int(period / gst.SECOND),
                 (maxCount and ("to a maximum of %s thumbnails" % str(maxCount)))
                 or "without limitation")
        return TimeSampler(self, maxCount, length, period)

    def __createPercentSampler(self, maxCount, length, period):
        self.log("Setup to creates thumbnails each %s percent of total "
                 "length %s seconds %s", str(period), 
                 str(length / gst.SECOND), (maxCount
                 and ("to a maximum of %s thumbnails" % str(maxCount)))
                 or "without limitation")
        return PercentSampler(self, maxCount, length, period)

    def __createSampler(self, maxCount, unit, value, analysis):
        length = analysis.getMediaLength()
        if unit == PeriodUnitEnum.frames:
            return self.__createFrameSampler(maxCount, length, value)
        elif unit == PeriodUnitEnum.keyframes:
            return self.__createKeyFrameSampler(maxCount, length, value)
        elif unit == PeriodUnitEnum.seconds:
            return self.__createTimeSampler(maxCount, length, value * gst.SECOND)
        elif unit == PeriodUnitEnum.percent:
            if length and (length > 0):
                value = max(min(value, 100), 0)
                return self.__createPercentSampler(maxCount, length, value)
            self.warning("Cannot generate percent-based thumbnails with a "
                         "source media without known duration, "
                         "falling back to second-based thumbnailing.")
            # PyChecker tells mi 100 / 10 may result to a float ? ?
            __pychecker__ = "no-intdivide"
            newMax = max((100 / (int(value) or 10)) - 1, 1)
            if maxCount:
                newMax = min(maxCount, newMax)
            else:
                newMax = newMax
            newValue = compconsts.FALLING_BACK_THUMBS_PERIOD_VALUE
            return self.__createTimeSampler(newMax, length, newValue * gst.SECOND)
