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

import gst

from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.errors import TranscoderConfigError
from flumotion.transcoder.enums import VideoScaleMethodEnum
from flumotion.transcoder.enums import PeriodUnitEnum
from flumotion.transcoder.enums import ThumbOutputTypeEnum
from flumotion.component.transcoder import compconsts
from flumotion.component.transcoder.basetargets import TranscodingTarget
from flumotion.component.transcoder.thumbsink import ThumbnailSink
from flumotion.component.transcoder.binmaker import makeMuxerEncodeBin
from flumotion.component.transcoder.binmaker import makeVideoEncodeBin



class ThumbnailTarget(TranscodingTarget):
    
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
            smartThumbs
        """
        TranscodingTarget.__init__(self, targetContext)
        self._sink = None
        self._checkConfAttr("periodValue")
        self._checkConfAttr("periodUnit")
        self._checkConfAttr("maxCount")
        self._checkConfAttr("thumbsWidth")
        self._checkConfAttr("thumbsHeight")
        self._checkConfAttr("outputFormat")


    ## Public Overriden Methods ##

    def getOutputFiles(self):
        if self._sink:
            return self._sink.getFiles()
        return None
        

    ## ITranscoderProducer Overriden Methods ##
    
    def checkSourceMedia(self, sourcePath, sourceAnalysis):
        if not sourceAnalysis.hasVideo:
            self.raiseError("Source media doesn't have video stream")
        config = self._getTranscodingConfig()
        if ((config.periodUnit == PeriodUnitEnum.percent)
            and not (sourceAnalysis.getMediaLength() > 0)):
            self.warning("Cannot generate percent-based thumbnails with a "
                         "source media without known duration, "
                         "falling back to second-based thumbnailing.")
            # PyChecker tells mi 100 / 10 may result to a float ? ?
            __pychecker__ = "no-intdivide"
            newMax = max((100 / (int(config.periodValue) or 10)) - 1, 1)
            if config.maxCount:
                config.maxCount = min(config.maxCount, newMax)
            else:
                config.maxCount = newMax
            config.periodUnit = PeriodUnitEnum.seconds
            config.periodValue = compconsts.FALLING_BACK_THUMBS_PERIOD_VALUE
        return True

    def updatePipeline(self, pipeline, analysis, tees, timeout=None):
        setupMethods = {PeriodUnitEnum.seconds: self._setupThumbnailBySeconds,
                        PeriodUnitEnum.frames: self._setupThumbnailByFrames,
                        PeriodUnitEnum.keyframes: self._setupThumbnailByKeyFrames,
                        PeriodUnitEnum.percent: self._setupThumbnailByPercent}
        probMethods = {PeriodUnitEnum.seconds: self._thumbnail_prob_by_seconds,
                       PeriodUnitEnum.frames: self._thumbnail_prob_by_frames,
                       PeriodUnitEnum.keyframes: self._thumbnail_prob_by_keyframes,
                       PeriodUnitEnum.percent: self._thumbnail_prob_by_percent}
        tag = self._getTranscodingTag()
        config = self._getTranscodingConfig()
        template = self._getOutputPath()
        unit = config.periodUnit
        self._setupThumbnail = setupMethods[unit]
        self._buffer_prob_callback = probMethods[unit]

        encoderConf = self.EncoderConfig(config)        
        videoEncBin = makeVideoEncodeBin(encoderConf, analysis, tag,
                                         withRateControl=False, 
                                         pipelineInfo=self._pipelineInfo,
                                         logger=self)
        thumbsBin = gst.Bin("thumbnailing-%s" % tag)
        self._sink = ThumbnailSink(template, "thumbsink-%s" % tag)
        thumbsBin.add(videoEncBin, self._sink)
        videoEncBin.link(self._sink)
        encPad = videoEncBin.get_pad("sink")
        encPad.add_buffer_probe(self._buffer_prob_callback)        
        pad = gst.GhostPad("videosink", encPad)
        thumbsBin.add_pad(pad)
        pipeline.add(thumbsBin)
        tees['videosink'].get_pad('src%d').link(thumbsBin.get_pad('videosink'))
        self._bins["thumbnailer"] = videoEncBin
        self._setupThumbnail(analysis)

    
    ## Private Methods ##
    
    def _setupThumbnailByFrames(self, analysis):
        config = self._getTranscodingConfig()
        self._frame = 0
        self._count = 0
        self._period = config.periodValue
        self._max = config.maxCount
        self._nextFrame = config.periodValue
        self.log("Setup to create a thumbnail each %s frames %s",
                 str(self._nextFrame), self._max
                 and ("to a maximum of %s thumbnails" % str(self._max))
                 or "without limitation")
    
    def _thumbnail_prob_by_frames(self, pad, buffer):
        self._frame += 1
        if (not self._max) or (self._count < self._max):
            if self._frame >= self._nextFrame:
                self._count += 1
                self._nextFrame += self._period
                return True
        return False

    def _setupThumbnailByKeyFrames(self, analysis):
        config = self._getTranscodingConfig()
        self._keyframe = 0
        self._count = 0
        self._period = config.periodValue
        self._max = config.maxCount
        self._nextKeyFrame = config.periodValue
        self.log("Setup to create a thumbnail each %s keyframes %s",
                 str(self._nextKeyFrame), self._max
                 and ("to a maximum of %s thumbnails" % str(self._max))
                 or "without limitation")
        
    
    def _thumbnail_prob_by_keyframes(self, pad, buffer):
        if not buffer.flag_is_set(gst.BUFFER_FLAG_DELTA_UNIT):
            self._keyframe += 1
            if (not self._max) or (self._count < self._max):
                if self._keyframe >= self._nextKeyFrame:
                    self._count += 1
                    self._nextKeyFrame += self._period
                    return True
        return False

    def _setupThumbnailByPercent(self, analysis):
        config = self._getTranscodingConfig()
        self._count = 0
        self._length = analysis.getMediaLength()
        self._max = config.maxCount
        self._percent = config.periodValue
        self._nextTimestamp = None
        self.log("Setup to create a thumbnail each %s percent of total "
                 "length %s seconds %s", str(self._percent), 
                 str(self._length / gst.SECOND), self._max
                 and ("to a maximum of %s thumbnails" % str(self._max))
                 or "without limitation")
    
    def _percent_get_next(self, timestamp):
        return timestamp + (self._length * self._percent) / 100
    
    def _thumbnail_prob_by_percent(self, pad, buffer):
        next = self._nextTimestamp
        curr = buffer.timestamp
        if next == None:
            next = self._percent_get_next(curr)
            self._nextTimestamp = next
        if (not self._max) or (self._count < self._max):
            if (curr >= next):
                self._count += 1
                next = self._percent_get_next(curr)
                self._nextTimestamp = next
                return True
        return False
    
    def _setupThumbnailBySeconds(self, analysis):
        config = self._getTranscodingConfig()
        self._max = config.maxCount
        self._count = 0
        self._interval = config.periodValue
        self._nextTimestamp = None        
        self.log("Setup to create a thumbnail each %s seconds %s",
                 str(self._interval), self._max
                 and ("to a maximum of %s thumbnails" % str(self._max))
                 or "without limitation")
    
    def _seconds_get_next(self, timestamp):
        return timestamp + self._interval * gst.SECOND
    
    def _thumbnail_prob_by_seconds(self, pad, buffer):
        next = self._nextTimestamp
        curr = buffer.timestamp
        if next == None:
            next = self._seconds_get_next(curr)
            self._nextTimestamp = next
        if (not self._max) or (self._count < self._max):
            if buffer.timestamp >= self._nextTimestamp:
                self._count += 1
                next = self._seconds_get_next(curr)
                self._nextTimestamp = next
                return True
        return False
    
