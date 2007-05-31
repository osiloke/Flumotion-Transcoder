# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.
# Headers in this file shall remain intact.

from flumotion.transcoder import properties
from flumotion.transcoder.enums import TargetTypeEnum
from flumotion.transcoder.enums import PeriodUnitEnum
from flumotion.transcoder.enums import ThumbOutputTypeEnum
from flumotion.transcoder.enums import VideoScaleMethodEnum
from flumotion.transcoder.admin.datasource import datasource


class AudioData(properties.PropertyBag):

    type = TargetTypeEnum.audio
    muxer = properties.String('muxer', None, True)
    audioEncoder = properties.String('audio-encoder', None, True)
    audioRate = properties.String('audio-rate', None)
    audioChannels = properties.String('audio-channels', None)

    
class VideoData(properties.PropertyBag):

    type = TargetTypeEnum.video
    muxer = properties.String('muxer', None, True)
    videoEncoder = properties.String('video-encoder', None, True)
    videoWidth = properties.Integer('video-width', None, False, True)
    videoHeight = properties.Integer('video-height', None, False, True)
    videoMaxWidth = properties.Integer('video-max-width', None, False, True)
    videoMaxHeight = properties.Integer('video-max-height', None, False, True)
    videoPAR = properties.Fraction('video-par', None, False, True)
    videoFramerate = properties.Fraction('video-framerate', None, False, True)
    scaleMethod = properties.Enum('preferred-method', 
                                   VideoScaleMethodEnum,
                                   VideoScaleMethodEnum.height)
    
    
class AudioVideoData(AudioData, VideoData):
    
    type = TargetTypeEnum.audiovideo
    
    
class ThumbnailsData(properties.PropertyBag):

    type = TargetTypeEnum.thumbnails
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
    

class TargetData(properties.PropertyBag):
    
    type = properties.Enum('type', TargetTypeEnum, None, True)
    name = properties.String('name', None, True)
    extension = properties.String('extension', None)
    subdir = properties.String('subdir', None)
    outputFileTemplate = properties.String('output-file-template', None)
    linkFileTemplate = properties.String('link-file-template', None)
    linkTemplate = properties.String('link-template', None)
    linkURLPrefix = properties.String('link-url-prefix', None)
    enablePostprocessing = properties.Boolean('post-processing-enabled', None)
    enableLinkFiles = properties.Boolean('link-files-enabled', None)
    postprocessCommand = properties.String('post-process-command', None)
    postprocessTimeout = properties.Integer('post-process-timeout', None, False, True)
    config = properties.DynEnumChild('config', 'type', 
                                     {TargetTypeEnum.audio: AudioData,
                                      TargetTypeEnum.video: VideoData,
                                      TargetTypeEnum.audiovideo: AudioVideoData,
                                      TargetTypeEnum.thumbnails: ThumbnailsData})


class ProfileData(properties.PropertyBag):

    name = properties.String('name', None, True)
    subdir = properties.String('subdir', None)
    inputDir = properties.String('input-dir', None)
    outputDir = properties.String('output-dir', None)
    failedDir = properties.String('failed-dir', None)
    doneDir = properties.String('done-dir', None)
    linkDir = properties.String('link-dir', None)
    workDir = properties.String('work-dir', None)
    configDir = properties.String('config-dir', None)
    failedRepDir = properties.String('failed-report-dir', None)
    doneRepDir = properties.String('done-report-dir', None)
    outputFileTemplate = properties.String('output-file-template', None)
    linkFileTemplate = properties.String('link-file-template', None)
    configFileTemplate = properties.String('config-file-template', None)
    reportFileTemplate = properties.String('report-file-template', None)
    linkTemplate = properties.String('link-template', None)
    linkURLPrefix = properties.String('link-url-prefix', None)
    enablePostprocessing = properties.Boolean('post-processing-enabled', None)
    enablePreprocessing = properties.Boolean('pre-processing-enabled', None)
    enableLinkFiles = properties.Boolean('link-files-enabled', None)
    transcodingPriority = properties.Integer('transcoding-priority', None, False, True)
    processPriority = properties.Integer('process-priority', None, False, True)
    preprocessCommand = properties.String('pre-process-command', None)
    postprocessCommand = properties.String('post-process-command', None)
    preprocesstimeout = properties.Integer('pre-process-timeout', None, False, True)
    postprocessTimeout = properties.Integer('post-process-timeout', None, False, True)
    transcodingTimeout = properties.Integer('transcoding-timeout', None, False, True)
    monitoringPeriod = properties.Integer('monitoring-period', 2, False, True)
    targets = properties.ChildList('targets', TargetData)


class CustomerInfoData(properties.PropertyBag):
    
    name = properties.String('name', None)
    contact = properties.String('contact', None)
    addresses = properties.List(properties.String('addresses', None))
    phone = properties.String('phone', None)
    email = properties.String('email', None)


class CustomerData(properties.PropertyBag):
    
    name = properties.String('name', None, True)
    subdir = properties.String('subdir', None)
    inputDir = properties.String('input-dir', None)
    outputDir = properties.String('output-dir', None)
    failedDir = properties.String('failed-dir', None)
    doneDir = properties.String('done-dir', None)
    linkDir = properties.String('link-dir', None)
    workDir = properties.String('work-dir', None)
    configDir = properties.String('config-dir', None)
    failedRepDir = properties.String('failed-report-dir', None)
    doneRepDir = properties.String('done-report-dir', None)
    outputFileTemplate = properties.String('output-file-template', None)
    linkFileTemplate = properties.String('link-file-template', None)
    configFileTemplate = properties.String('config-file-template', None)
    reportFileTemplate = properties.String('report-file-template', None)
    linkTemplate = properties.String('link-template', None)
    linkURLPrefix = properties.String('link-url-prefix', None)
    enablePostprocessing = properties.Boolean('post-processing-enabled', None)
    enablePreprocessing = properties.Boolean('pre-processing-enabled', None)
    enableLinkFiles = properties.Boolean('link-files-enabled', None)
    transcodingPriority = properties.Integer('transcoding-priority', None, False, True)
    processPriority = properties.Integer('process-priority', None, False, True)
    preprocessCommand = properties.String('pre-process-command', None)
    postprocessCommand = properties.String('post-process-command', None)
    preprocesstimeout = properties.Integer('pre-process-timeout', None, False, True)
    postprocessTimeout = properties.Integer('post-process-timeout', None, False, True)    
    transcodingTimeout = properties.Integer('transcoding-timeout', None, False, True)
    monitoringPeriod = properties.Integer('monitoring-period', 2, False, True)
    info = properties.Child('info', CustomerInfoData)
    profiles = properties.ChildList('profiles', ProfileData)


class AdminData(properties. RootPropertyBag):
    monitoringPeriod = properties.Integer('monitoring-period', 2, False, True)
    transcodingTimeout = properties.Integer('transcoding-timeout', 4, False, True)
    postprocessTimeout = properties.Integer('post-process-timeout', 60, False, True)
    preprocessTimeout = properties.Integer('pre-process-timeout', 60, False, True)
    outputFileTemplate = properties.String('output-file-template', "%(inputFileBase)s.%(outputFileExt)")
    linkFileTemplate = properties.String('link-file-template', "%(inputFile)s.link")
    configFileTemplate = properties.String('config-file-template', "%(inputFile)s.ini")
    reportFileTemplate = properties.String('report-file-template', "%(inputFile)s.rep")
    mailSubjectTemplate = properties.String('mail-subject-template', "Transcoding Error")
    mailBodyTemplate = properties.String('mail-body-template', "Errorrrrr")
    GETRequestTimeout = properties.Integer('get-request-timeout', 60, False, True)
    GETRequestRetryCount = properties.Integer('get-request-retry-count', 3, False, True)
    GETRequestRetrySleep = properties.Integer('get-request-retry-sleep', 60, False, True)
    customers = properties.ChildList('customers', CustomerData)
