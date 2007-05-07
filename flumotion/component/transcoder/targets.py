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
from flumotion.common import common
from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.enums import IntervalUnitEnum
from flumotion.transcoder.enums import ThumbOutputTypeEnum
from flumotion.component.transcoder.binmaker import makeEncodeBin
from flumotion.component.transcoder.binmaker import makeAudioEncodeBin
from flumotion.component.transcoder.binmaker import makeVideoEncodeBin
from flumotion.component.transcoder.thumbsink import ThumbnailSink


class TranscodingTarget(object):
    
    def __init__(self, config, tag, logger, data=None):
        self._config = config
        self._logger = logger
        self._data = data
        self._tag = tag
        self._bins = {}

    def getData(self):
        return self._data

    def getBins(self):
        return self._bins
    
    def log(self, *args, **kwargs):
        self._logger.log(*args, **kwargs)
        
    def debug(self, *args, **kwargs):
        self._logger.debug(*args, **kwargs)

    def info(self, *args, **kwargs):
        self._logger.info(*args, **kwargs)

    def warning(self, *args, **kwargs):
        self._logger.warning(*args, **kwargs)

    def error(self, *args, **kwargs):
        self._logger.error(*args, **kwargs)

    def _raiseError(self, msg, *args):
        raise TranscoderError(msg % args, data=self._data)        
    
    def _sourceDiscovered(self, discoverer):
        pass
    
    def _pushExpectedOutputs(self, outputs):
        pass

    def _hasTargetFile(self, filePath):
        pass

    def _updatePipeline(self, pipeline, discoverer, tees):
        pass


class FileTarget(TranscodingTarget):

    def __init__(self, outputPath, config, tag, logger, data=None):
        TranscodingTarget.__init__(self, config, tag, logger, data)
        self._outputPath = outputPath
        common.ensureDir(os.path.dirname(outputPath), "transcoding output")

    def getOutputPath(self):
        return self._outputPath

    def getOutputs(self):
        return (self.getOutputPath(),)
    
    def _pushExpectedOutputs(self, outputs):
        outputs.append(self.getOutputPath())

    def _hasTargetFile(self, filePath):
        return self._outputPath == filePath
    
class AudioTarget(FileTarget):
    def __init__(self, outputPath, config, tag, logger, data=None):
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
        FileTarget.__init__(self, outputPath, config, tag, logger, data)

    def _sourceDiscovered(self, discoverer):
        if not discoverer.is_audio:
            self._raiseError("Source media doesn't have audio stream")

    def _updatePipeline(self, pipeline, discoverer, tees):
        audioEncBin = makeAudioEncodeBin(self._config, discoverer, self._tag)
        encBin = makeEncodeBin(self.getOutputPath(), self._config, 
                                     discoverer, self._tag, audioEncBin, None)
        pipeline.add(encBin)
        tees['audiosink'].get_pad('src%d').link(encBin.get_pad('audiosink'))
        self._bins["audio-encoder"] = audioEncBin

        
class VideoTarget(FileTarget):
    def __init__(self, outputPath, config, tag, logger, data=None):
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
        FileTarget.__init__(self, outputPath, config, tag, logger, data)

    def _sourceDiscovered(self, discoverer):
        if not discoverer.is_video:
            self._raiseError("Source media doesn't have video stream")

    def _updatePipeline(self, pipeline, discoverer, tees):
        videoEncBin = makeVideoEncodeBin(self._config, discoverer, self._tag)
        encBin = makeEncodeBin(self.getOutputPath(), self._config, 
                                      discoverer, self._tag, None, videoEncBin)
        pipeline.add(encBin)
        tees['videosink'].get_pad('src%d').link(encBin.get_pad('videosink'))
        self._bins["video-encoder"] = videoEncBin
        

class AudioVideoTarget(FileTarget):
    def __init__(self, outputPath, config, tag, logger, data=None):
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
        """
        FileTarget.__init__(self, outputPath, config, tag, logger, data)

    def _sourceDiscovered(self, discoverer):
        if not discoverer.is_audio:
            self._raiseError("Source media doesn't have audio stream")
        if not discoverer.is_video:
            self._raiseError("Source media doesn't have video stream")

    def _updatePipeline(self, pipeline, discoverer, tees):
        tag = self._tag
        audioEncBin = makeAudioEncodeBin(self._config, discoverer, tag)
        videoEncBin = makeVideoEncodeBin(self._config, discoverer, tag)
        encBin = makeEncodeBin(self.getOutputPath(), self._config, 
                                      discoverer, tag, audioEncBin, videoEncBin)
        pipeline.add(encBin)
        tees['videosink'].get_pad('src%d').link(encBin.get_pad('videosink'))
        tees['audiosink'].get_pad('src%d').link(encBin.get_pad('audiosink'))
        self._bins["video-encoder"] = videoEncBin
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
            self.videoPreferredMethod = "upscale"
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

    def __init__(self, template, config, tag, logger, data=None):
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
            intervalValue
            intervalUnit (seconds, frames or percent)
            maxCount
            outputFormat Enum(jpg, png)
            smartThumbs
        """
        TranscodingTarget.__init__(self, config, tag, logger, data)
        self._sink = None
        self._template = template

    def getOutputs(self):
        if self._sink:
            return self._sink.getFiles()
        return None
    
    def _sourceDiscovered(self, discoverer):
        if not discoverer.is_video:
            self._raiseError("Source media doesn't have video stream")

    def _updatePipeline(self, pipeline, discoverer, tees):
        setupMethods = {IntervalUnitEnum.seconds: self._setupThumbnailBySeconds,
                        IntervalUnitEnum.frames: self._setupThumbnailByFrames,
                        IntervalUnitEnum.keyframes: self._setupThumbnailByKeyFrames,
                        IntervalUnitEnum.percent: self._setupThumbnailByPercent}
        probMethods = {IntervalUnitEnum.seconds: self._thumbnail_prob_by_seconds,
                       IntervalUnitEnum.frames: self._thumbnail_prob_by_frames,
                       IntervalUnitEnum.keyframes: self._thumbnail_prob_by_keyframes,
                       IntervalUnitEnum.percent: self._thumbnail_prob_by_percent}
        unit = self._config.intervalUnit
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
        self._nextFrame = self._config.intervalValue
    
    def _thumbnail_prob_by_frames(self, pad, buffer):
        self._frame += 1
        if (not self._max) or (self._count < self._max):
            if self._frame >= self._nextFrame:
                self._count += 1
                self._nextFrame += self._config.intervalValue
                return True
        return False

    def _setupThumbnailByKeyFrames(self, discoverer):
        self._keyframe = 0
        self._count = 0
        self._max = self._config.maxCount
        self._nextKeyFrame = self._config.intervalValue
    
    def _thumbnail_prob_by_keyframes(self, pad, buffer):
        if not buffer.flag_is_set(gst.BUFFER_FLAG_DELTA_UNIT):
            self._keyframe += 1
            if (not self._max) or (self._count < self._max):
                if self._keyframe >= self._nextKeyFrame:
                    self._count += 1
                    self._nextKeyFrame += self._config.intervalValue
                    return True
        return False

    def _setupThumbnailByPercent(self, discoverer):
        self._count = 0
        self._length = discoverer.videolength
        self._max = self._config.maxCount
        percent = self._config.intervalValue
        self._nextTimestamp = (self._length * percent) / 100
    
    def _thumbnail_prob_by_percent(self, pad, buffer):
        if (not self._max) or (self._count < self._max):
            if buffer.timestamp >= self._nextTimestamp:
                self._count += 1
                percent = self._config.intervalValue                
                self._nextTimestamp = (((self._count + 1) 
                                        * self._length
                                        * percent) / 100)
                return True
        return False
    
    def _setupThumbnailBySeconds(self, discoverer):
        self._count = 0
        self._nextTimestamp = self._config.intervalValue * gst.SECOND
    
    def _thumbnail_prob_by_seconds(self, pad, buffer):
        if self._count < self._config.maxCount:
            if buffer.timestamp >= self._nextTimestamp:
                self._count += 1
                self._nextTimestamp += self._config.intervalValue * gst.SECOND
                return True
        return False
    
