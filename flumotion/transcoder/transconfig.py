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

import datetime

from flumotion.transcoder import properties, constants
from flumotion.transcoder.enums import VideoScaleMethodEnum
from flumotion.transcoder.enums import PeriodUnitEnum
from flumotion.transcoder.enums import ThumbOutputTypeEnum
from flumotion.transcoder.enums import TargetTypeEnum
from flumotion.transcoder.enums import AudioVideoToleranceEnum


class CustomerConfig(properties.PropertyBag):
    name = properties.String('name', None, True)


class ProfileConfig(properties.PropertyBag):
    label = properties.String('label', None, True)
    inputDir = properties.VirtualPath('input-dir', None, True)
    outputDir = properties.VirtualPath('output-dir', None, True)
    linkDir = properties.VirtualPath('link-dir', None)
    workDir = properties.VirtualPath('work-dir', None, True)
    failedDir = properties.VirtualPath('failed-dir', None, True)
    failedReportsDir = properties.VirtualPath('failed-reports-dir', None, True)
    doneDir = properties.VirtualPath('done-dir', None, True)
    doneReportsDir = properties.VirtualPath('done-reports-dir', None, True)
    linkTemplate = properties.String('link-template', constants.LINK_TEMPLATE)


class SourceConfig(properties.PropertyBag):
    inputFile = properties.String('input-file', None, True)
    reportTemplate = properties.String('report-template', None, True)
    preProcess = properties.String('pre-process', None)
    
    
class AudioConfig(properties.PropertyBag):
    audioEncoder = properties.String('audio-encoder', None, True)
    audioRate = properties.Integer('audio-rate', None, False, True)
    audioChannels = properties.Integer('audio-channels', None, False, True)
    muxer = properties.String('muxer', None, True)
    

class VideoConfig(properties.PropertyBag):
    videoEncoder = properties.String('video-encoder', None, True)
    videoFramerate = properties.Fraction('video-framerate', None, False, True)
    videoPAR = properties.Fraction('video-par', None, False, True)
    videoWidth = properties.Integer('video-width', None, False, True)
    videoHeight = properties.Integer('video-height', None, False, True)
    videoMaxWidth = properties.Integer('video-maxwidth', None, False, True)
    videoMaxHeight = properties.Integer('video-maxheight', None, False, True)
    videoScaleMethod = properties.Enum('video-scale-method', 
                                       VideoScaleMethodEnum,
                                       VideoScaleMethodEnum.height)
    muxer = properties.String('muxer', None, True)
    
    
class AudioVideoConfig(AudioConfig, VideoConfig):
    tolerance = properties.Enum('tolerance', 
                                AudioVideoToleranceEnum,
                                AudioVideoToleranceEnum.strict)

class ThumbnailsConfig(properties.PropertyBag):
    periodValue = properties.Integer('period-value', None, True, True)
    thumbsWidth = properties.Integer('thumbs-width', 128, False, True)
    thumbsHeight = properties.Integer('thumbs-height', 128, False, True)
    periodUnit = properties.Enum('period-unit', 
                                   PeriodUnitEnum, 
                                   PeriodUnitEnum.seconds)
    maxCount = properties.Integer('max-count', 1, False, True)
    outputFormat = properties.Enum('output-format',
                                   ThumbOutputTypeEnum,
                                   ThumbOutputTypeEnum.jpg)
                   

class TargetConfig(properties.PropertyBag):
    label = properties.String('label', None, True)
    type = properties.Enum('type', TargetTypeEnum, None, True)
    outputFile = properties.String('output-file', None, True)
    linkFile = properties.String('link-file', None, False)
    postProcess = properties.String('post-process', None)
    linkUrlPrefix = properties.String('link-url-prefix', None)
    config = properties.DynEnumChild('config', 'type', 
                                     {TargetTypeEnum.audio: AudioConfig,
                                      TargetTypeEnum.video: VideoConfig,
                                      TargetTypeEnum.audiovideo: AudioVideoConfig,
                                      TargetTypeEnum.thumbnails: ThumbnailsConfig})
    

class TranscodingConfig(properties.RootPropertyBag):
    
    VERSION = (1,0)
    
    creationTime = properties.DateTime('creation-time')
    transcodingTimeout = properties.Integer('transcoding-timeout', 4)
    postProcessTimeout = properties.Integer('post-process-timeout', 60)
    preProcessTimeout = properties.Integer('pre-process-timeout', 60)
    customer = properties.Child('customer', CustomerConfig)
    profile = properties.Child('profile', ProfileConfig)
    source = properties.Child('source', SourceConfig)
    targets = properties.ChildList('targets', TargetConfig)

    def touch(self):
        self.creationTime = datetime.datetime.now()
        
