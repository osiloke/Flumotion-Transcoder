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
import shutil

from flumotion.common import common

from flumotion.transcoder import log, defer, utils
from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.enums import PeriodUnitEnum
from flumotion.transcoder.enums import ThumbOutputTypeEnum
from flumotion.transcoder.enums import AudioVideoToleranceEnum
from flumotion.transcoder.enums import VideoScaleMethodEnum
from flumotion.component.transcoder import compconsts
from flumotion.component.transcoder.binmaker import makeEncodeBin
from flumotion.component.transcoder.binmaker import makeAudioEncodeBin
from flumotion.component.transcoder.binmaker import makeVideoEncodeBin
from flumotion.component.transcoder.thumbsink import ThumbnailSink

__all__ = ['ProcessingTarget', 'TranscodingTarget', 'IdentityTarget',
           'AudioTarget', 'VideoTarget', 'AudioVideoTarget',
           'ThumbnailsTarget']

class BaseTarget(log.LoggerProxy):
    
    def __init__(self, logger, data=None):
        log.LoggerProxy.__init__(self, logger)
        self._data = data

    ## Public Methods ##

    def getData(self):
        return self._data

    def getOutputs(self):
        return []


class ProcessingTarget(BaseTarget):

    def __init__(self, logger, data=None):
        BaseTarget.__init__(self, logger, data)
        self._outputs = []


    ## Public Methods ##

    def getOutputs(self):
        return list(self._outputs)

    def process(self, context, targetCtx):
        return defer.succeed(self)
    
        
class IdentityTarget(ProcessingTarget):
    
    def __init__(self, logger, data=None):
        """
        This target only copy the source file to the target file.
        """
        ProcessingTarget.__init__(self, logger, data)
        
    def process(self, context, targCtx):
        try:
            srcCtx = context.getSourceContext()
            sourcePath = srcCtx.getInputPath()
            destPath = targCtx.getOutputWorkPath()
            utils.ensureDirExists(os.path.dirname(destPath), "identity output")
            shutil.copy(sourcePath, destPath)
            self._outputs.append(destPath)
            return defer.succeed(self)
        except:
            return defer.fail()


class TranscodingTarget(BaseTarget):
    
    def __init__(self, logger, config, tag, data=None):
        BaseTarget.__init__(self, logger, data)
        self._config = config
        self._tag = tag
        self._bins = {}


    ## Public Methods ##

    def getBins(self):
        return self._bins

    ## Protected Methods ##
    
    def _raiseError(self, msg, *args):
        raise TranscoderError(msg % args, data=self._data)        
    
    def _setup(self, transcoder):
        pass
    
    def _sourceDiscovered(self, discoverer):
        pass
    
    def _pushMonitoredOutputs(self, outputs):
        pass

    def _hasTargetFile(self, filePath):
        pass

    def _updatePipeline(self, pipeline, discoverer, tees):
        pass


class FileTarget(TranscodingTarget):

    def __init__(self, logger, config, outputPath, tag, data=None):
        TranscodingTarget.__init__(self, logger, config, tag, data)
        self._outputPath = outputPath
        utils.ensureDirExists(os.path.dirname(outputPath),
                              "transcoding output")

    def getOutputPath(self):
        return self._outputPath

    def getOutputs(self):
        return (self.getOutputPath(),)
    
    def _pushMonitoredOutputs(self, outputs):
        outputs.append(self.getOutputPath())

    def _hasTargetFile(self, filePath):
        return self._outputPath == filePath


class AudioTarget(FileTarget):

    def __init__(self, logger, config, outputPath, tag, data=None):
        """
        Some abstract data can be specified to be able to track the target,
        the data will be embedded in the TranscoderError if the error
        is raised by this target.
        The config argument should contains the attributes:
            audioEncoder
            audioRate
            audioChannels
            muxer
        """
        FileTarget.__init__(self, logger, config, outputPath, tag, data)

    def _sourceDiscovered(self, discoverer):
        if not discoverer.is_audio:
            self._raiseError("Source media doesn't have audio stream")
        return True

    def _updatePipeline(self, pipeline, discoverer, tees):
        audioEncBin = makeAudioEncodeBin(self._config, discoverer, self._tag)
        encBin = makeEncodeBin(self.getOutputPath(), self._config, 
                                     discoverer, self._tag, audioEncBin, None)
        pipeline.add(encBin)
        tees['audiosink'].get_pad('src%d').link(encBin.get_pad('audiosink'))
        self._bins["audio-encoder"] = audioEncBin

        
class VideoTarget(FileTarget):
 
    def __init__(self, logger, config, outputPath, tag, data=None):
        """
        Some abstract data can be specified to be able to track the target,
        the data will be embedded in the TranscoderError if the error
        is raised by this target.
        The config argument should contains the attributes:
            videoEncoder
            videoFramerate
            videoPAR
            videoWidth
            videoHeight
            muxer
        """
        FileTarget.__init__(self, logger, config, outputPath, tag, data)

    def _sourceDiscovered(self, discoverer):
        if not discoverer.is_video:
            self._raiseError("Source media doesn't have video stream")
        return True

    def _updatePipeline(self, pipeline, discoverer, tees):
        videoEncBin = makeVideoEncodeBin(self._config, discoverer, self._tag)
        encBin = makeEncodeBin(self.getOutputPath(), self._config, 
                                      discoverer, self._tag, None, videoEncBin)
        pipeline.add(encBin)
        tees['videosink'].get_pad('src%d').link(encBin.get_pad('videosink'))
        self._bins["video-encoder"] = videoEncBin
        

class AudioVideoTarget(FileTarget):
 
    def __init__(self, logger, config, outputPath, tag, data=None):
        """
        Some abstract data can be specified to be able to track the target,
        the data will be embedded in the TranscoderError if the error
        is raised by this target.
        The config argument should contains the attributes:
            audioEncoder
            audioRate
            audioChannels
            videoEncoder
            videoFramerate
            videoPAR
            videoWidth
            videoHeight
            muxer
            tolerance
        """
        FileTarget.__init__(self, logger, config, outputPath, tag, data)

    def _sourceDiscovered(self, discoverer):
        tolerance = self._config.tolerance
        if not discoverer.is_audio:
            if tolerance == AudioVideoToleranceEnum.allow_without_audio:
                self.info("Source media doesn't have audio stream, "
                          "but we tolerate it")
            else:
                self._raiseError("Source media doesn't have audio stream")
        if not discoverer.is_video:
            if tolerance == AudioVideoToleranceEnum.allow_without_video:
                self.info("Source media doesn't have video stream, "
                          "but we tolerate it")
            else:
                self._raiseError("Source media doesn't have video stream")
        return True

    def _updatePipeline(self, pipeline, discoverer, tees):
        tag = self._tag
        if discoverer.is_audio:
            audioEncBin = makeAudioEncodeBin(self._config, discoverer, tag)
        else:
            audioEncBin = None
        if discoverer.is_video:
            videoEncBin = makeVideoEncodeBin(self._config, discoverer, tag)
        else:
            videoEncBin = None
        encBin = makeEncodeBin(self.getOutputPath(), self._config, 
                                      discoverer, tag, audioEncBin, videoEncBin)
        pipeline.add(encBin)
        if videoEncBin:
            tees['videosink'].get_pad('src%d').link(encBin.get_pad('videosink'))
            self._bins["video-encoder"] = videoEncBin
        if audioEncBin:
            tees['audiosink'].get_pad('src%d').link(encBin.get_pad('audiosink'))
            self._bins["audio-encoder"] = audioEncBin


class ThumbnailsTarget(TranscodingTarget):
    """
    The image encoders used for thumbnailing must use 
    one buffer by encoded frames.
    """
    
    class EncoderConfig(object):
        def __init__(self, config):
            self.videoWidth = config.thumbsWidth
            self.videoHeight = config.thumbsHeight
            self.videoMaxWidth = None
            self.videoMaxHeight = None
            self.videoScaleMethod = VideoScaleMethodEnum.upscale
            self.videoFramerate = None
            self.videoPAR = (1, 1)            
            format = config.outputFormat
            if format == ThumbOutputTypeEnum.png:
                self.videoEncoder = "ffmpegcolorspace ! pngenc snapshot=false"
            elif format == ThumbOutputTypeEnum.jpg:
                self.videoEncoder = "ffmpegcolorspace ! jpegenc"
            else:
                raise TranscoderError("Unknown thumbnails output format '%s'"
                                      % format)        

    def __init__(self, logger, config, template, tag, data=None):
        """
        Some abstract data can be specified to be able to track the target,
        the data will be embedded in the TranscoderError if the error
        is raised by this target.
        The root argument is the base path of the output files.
        template is the path template of the output files 
        relative to the secified root.
        It may contain template variables:
            %(index)d  => index of the thumbnail (starting at 1)
            %(timestamp)d => timestamp of the thumbnail
            %(time)s => composed time of the thumbnail, 
                        like %(hours)02d:%(minutes)02d:%(seconds)02d
            %(hours)d => hours from start
            %(minutes)d => minutes from start
            %(seconds)d => seconds from start
        config should contains the attributes:
            periodValue
            periodUnit (seconds, frames or percent)
            maxCount
            outputFormat Enum(jpg, png)
            smartThumbs
        """
        TranscodingTarget.__init__(self, logger, config, tag, data)
        self._sink = None
        self._template = template

    def getOutputs(self):
        if self._sink:
            return self._sink.getFiles()
        return None
    
    def _sourceDiscovered(self, discoverer):
        if not discoverer.is_video:
            self._raiseError("Source media doesn't have video stream")
        if ((self._config.periodUnit == PeriodUnitEnum.percent)
            and not (discoverer.videolength and (discoverer.videolength > 0))
            and not (discoverer.audiolength and (discoverer.audiolength > 0))):
            self.warning("Cannot generate percent-based thumbnails with a "
                         "source media without known duration, "
                         "falling back to second-based thumbnailing.")
            newMax = max((100 / (self._config.periodValue or 10)) - 1, 1)
            if self._config.maxCount:
                self._config.maxCount = min(self._config.maxCount, newMax)
            else:
                self._config.maxCount = newMax
            self._config.periodUnit = PeriodUnitEnum.seconds
            self._config.periodValue = compconsts.FALLING_BACK_THUMBS_PERIOD_VALUE
        return True

    def _updatePipeline(self, pipeline, discoverer, tees):
        setupMethods = {PeriodUnitEnum.seconds: self._setupThumbnailBySeconds,
                        PeriodUnitEnum.frames: self._setupThumbnailByFrames,
                        PeriodUnitEnum.keyframes: self._setupThumbnailByKeyFrames,
                        PeriodUnitEnum.percent: self._setupThumbnailByPercent}
        probMethods = {PeriodUnitEnum.seconds: self._thumbnail_prob_by_seconds,
                       PeriodUnitEnum.frames: self._thumbnail_prob_by_frames,
                       PeriodUnitEnum.keyframes: self._thumbnail_prob_by_keyframes,
                       PeriodUnitEnum.percent: self._thumbnail_prob_by_percent}
        unit = self._config.periodUnit
        self._setupThumbnail = setupMethods[unit]
        self._buffer_prob_callback = probMethods[unit]

        encoderConf = self.EncoderConfig(self._config)        
        videoEncBin = makeVideoEncodeBin(encoderConf, discoverer, self._tag, False)
        thumbsBin = gst.Bin("thumbnailing-%s" % self._tag)
        self._sink = ThumbnailSink(self._template, "thumbsink-%s" % self._tag)
        thumbsBin.add(videoEncBin, self._sink)
        videoEncBin.link(self._sink)
        encPad = videoEncBin.get_pad("sink")
        encPad.add_buffer_probe(self._buffer_prob_callback)        
        pad = gst.GhostPad("videosink", encPad)
        thumbsBin.add_pad(pad)
        pipeline.add(thumbsBin)
        tees['videosink'].get_pad('src%d').link(thumbsBin.get_pad('videosink'))
        self._bins["thumbnailer"] = videoEncBin
        self._setupThumbnail(discoverer)
    
    def _setupThumbnailByFrames(self, discoverer):
        self._frame = 0
        self._count = 0
        self._max = self._config.maxCount
        self._nextFrame = self._config.periodValue
        self.log("Setup to create a thumbnail each %s frames %s",
                 str(self._nextFrame), self._max
                 and ("to a maximum of %s thumbnails" % str(self._max))
                 or "without limitation")
    
    def _thumbnail_prob_by_frames(self, pad, buffer):
        self._frame += 1
        if (not self._max) or (self._count < self._max):
            if self._frame >= self._nextFrame:
                self._count += 1
                self._nextFrame += self._config.periodValue
                return True
        return False

    def _setupThumbnailByKeyFrames(self, discoverer):
        self._keyframe = 0
        self._count = 0
        self._max = self._config.maxCount
        self._nextKeyFrame = self._config.periodValue
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
                    self._nextKeyFrame += self._config.periodValue
                    return True
        return False

    def _setupThumbnailByPercent(self, discoverer):
        self._count = 0
        self._length = max(discoverer.videolength, discoverer.audiolength)
        self._max = self._config.maxCount
        self._percent = self._config.periodValue
        self._nextTimestamp = None
        self.log("Setup to create a thumbnail each %s percent of total "
                 "length %s sconds %s", str(self._percent), 
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
    
    def _setupThumbnailBySeconds(self, discoverer):
        self._max = self._config.maxCount
        self._count = 0
        self._interval = self._config.periodValue
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
    
