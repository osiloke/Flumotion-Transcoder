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
from flumotion.transcoder.enums import AudioVideoToleranceEnum
from flumotion.transcoder.admin.enums import ActivityTypeEnum
from flumotion.transcoder.admin.enums import ActivityStateEnum
from flumotion.transcoder.admin.enums import NotificationTriggerEnum
from flumotion.transcoder.admin.enums import NotificationTypeEnum
from flumotion.transcoder.admin.enums import TranscodingTypeEnum
from flumotion.transcoder.admin.datasource import datasource


class AudioData(properties.PropertyBag):

    type = TargetTypeEnum.audio
    muxer = properties.String('muxer', None, True)
    audioEncoder = properties.String('audio-encoder', None, True)
    audioRate = properties.Integer('audio-rate', None)
    audioChannels = properties.Integer('audio-channels', None)

    
class VideoData(properties.PropertyBag):

    type = TargetTypeEnum.video
    muxer = properties.String('muxer', None, True)
    videoEncoder = properties.String('video-encoder', None, True)
    videoWidth = properties.Integer('video-width', None, False, True)
    videoHeight = properties.Integer('video-height', None, False, True)
    videoWidthMultiple = properties.Integer('video-width-multiple', None, False, True)
    videoHeightMultiple = properties.Integer('video-height-multiple', None, False, True)
    videoMaxWidth = properties.Integer('video-max-width', None, False, True)
    videoMaxHeight = properties.Integer('video-max-height', None, False, True)
    videoPAR = properties.Fraction('video-par', None, False, True)
    videoFramerate = properties.Fraction('video-framerate', None, False, True)
    videoScaleMethod = properties.Enum('video-scale-method', 
                                       VideoScaleMethodEnum,
                                       VideoScaleMethodEnum.height)
    
    
class AudioVideoData(AudioData, VideoData):
    
    type = TargetTypeEnum.audiovideo
    tolerance = properties.Enum('tolerance', 
                                AudioVideoToleranceEnum,
                                AudioVideoToleranceEnum.strict)

    
class ThumbnailsData(properties.PropertyBag):

    type = TargetTypeEnum.thumbnails
    periodValue = properties.Integer('period-value', None, True, True)
    thumbsWidth = properties.Integer('thumbs-width', 128, False, True)
    thumbsHeight = properties.Integer('thumbs-height', 128, False, True)
    periodUnit = properties.Enum('period-unit', 
                                   PeriodUnitEnum, 
                                   PeriodUnitEnum.seconds)
    maxCount = properties.Integer('max-count', 1, False, True)
    format = properties.Enum('output-format',
                             ThumbOutputTypeEnum,
                             ThumbOutputTypeEnum.jpg)
    

class TargetData(properties.PropertyBag):
    
    type = properties.Enum('type', TargetTypeEnum, None, True)
    name = properties.String('name', None)
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
    notifyDoneRequests = properties.List(properties.String('notify-done-requests', None))
    config = properties.DynEnumChild('config', 'type', 
                                     {TargetTypeEnum.audio: AudioData,
                                      TargetTypeEnum.video: VideoData,
                                      TargetTypeEnum.audiovideo: AudioVideoData,
                                      TargetTypeEnum.thumbnails: ThumbnailsData})

class ProfileData(properties.PropertyBag):

    name = properties.String('name', None)
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
    outputMediaTemplate = properties.String('output-media-template', None)
    outputThumbTemplate = properties.String('output-thumb-template', None)
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
    monitoringPeriod = properties.Integer('monitoring-period', None, False, True)
    notifyDoneRequests = properties.List(properties.String('notify-done-requests', None))
    notifyFailedRequests = properties.List(properties.String('notify-failed-requests', None))
    notifyFailedMailRecipients = properties.String('notify-failed-mail-recipients', None)
    targets = properties.ChildDict('target', TargetData)
    

class CustomerData(properties.RootPropertyBag):
    """
    File Data-Source Customer Properties File.
    
    This file define the properties of a customer.
    Following is an example of the configuration properties.
    If the specified value is the default, the line will be commented.
    For more information see the section 3-4 of the document specification.odt
    
    ------
    
    # Global Section; This section contain all the default values
    # for the defined customer; Lots of these values can be overriden
    # in the profile and target definition.
    [global]
    
    # Customer Name.
    name = Fluendo
    
    # Subdirectory; if not specified, the lowercase name is used.
    #subdir = fluendo
    
    # The various base directories can be specified directly
    # as virtual path. If the virtual path root is not specified,
    # the 'default' root will be automaticaly used 
    # (minus for the workDir where the 'temp' root will be used insteed)
    # If not specified, these value are deduced from the subdir property
    #input-dir = /fluendo/file/incoming/
    #output-dir = /fluendo/file/outgoing/
    #failed-dir = /fluendo/file/failed/
    #done-dir = /fluendo/file/done/
    #link-dir = /fluendo/file/links/
    #work-dir = /fluendo/work/
    #config-dir = /fluendo/configs/
    #failed-report-dir = /fluendo/reports/failed
    #done-report-dir = /fluendo/reports/done

    # Prefix for the generated links
    link-url-prefix = http://stream.flumotion.com/%(custName)s/ondemand/
    
    # Customer's transcoding priority (different from transcoding-priority)
    #customer-priority = 100
    
    # Default Process Priority to use for this customer tasks
    #process-priority =
    
    # Flags to enable pre-processing, post-processing and link generation
    #pre-processing-enabled = False
    post-processing-enabled = True
    link-files-enabled = True
    
    # Pre-process and post-process commands
    # For more information about variable substitution,
    # see section 4-7 and 4-8 of specification.odt
    #pre-process-command =
    post-process-command = md5sum %(workPath)s
    
    # If the following properties are not specified, the default
    # values specified in the global properties file will be used.
    # See transcoder-data.ini (section 3-3 of specification.odt)
    #output-media-template =
    #output-thumb-template =
    #link-file-template =
    #config-file-template =
    #report-file-template =
    #link-template =
    #monitoring-period =
    #transcoding-priority =
    #transcoding-timeout =
    #post-process-timeout =
    #pre-process-timeout =

    # Profile Properties
    # A customer can have multiple profiles defained by a key name:
    [profile:fluprof]

    # Profile name; if not specified, the key name will be used
    #name = fluprof
    
    # Profile subdir; if not specified the lowercase of the name will be used
    subdir = default/profile

    # The directories can be overriden like for the customer properties.
    # If not specified, these value are deduced from the parent values
    # and the subdir property.
    #input-dir = /fluendo/file/incoming/default/profile/
    #output-dir = /fluendo/file/outgoing/default/profile/
    #failed-dir = /fluendo/file/failed/default/profile/
    #done-dir = /fluendo/file/done/default/profile/
    #link-dir = /fluendo/file/links/default/profile/
    #work-dir = /fluendo/work/default/profile/
    #config-dir = /fluendo/configs/default/profile/
    #failed-report-dir = /fluendo/reports/failed/default/profile/
    #done-report-dir = /fluendo/reports/done/default/profile/
    
    # HTTP GET requests to perform when a source file has been 
    # successfully transcoded or failed with this profile.
    notify-done-requests#01 = http://backoffice.flumotion.com/cgi?file=%(outputRelFile)s&status=%(success)d
    notify-failed-requests#01 = http://backoffice.flumotion.com/cgi?file=%(outputRelFile)s&status=%(success)d
    
    # Recipients of the mail send when a transcodification fail for this profile
    notify-failed-mail-recipients = Sebastien Merle <sebastien@fluendo.com>
    
    # The following variable can be overriden,
    # if not the customer level values will be used.
    #output-media-template =
    #output-thumb-template =
    #link-file-template =
    #config-file-template =
    #report-file-template =
    #link-template =
    #link-url-prefix =
    #post-processing-enabled =
    #pre-processing-enabled =
    #link-files-enabled =
    #transcoding-priority =
    #process-priority =
    #pre-process-command =
    #post-process-command =
    #pre-process-timeout =
    #post-process-timeout =
    #transcoding-timeout =
    #monitoring-period =
    
    # Target Properties
    # Each profiles can have multiple targets defined by key names:
    [profile:fluprof:target:high]

    # Target type. Can be "Audio", "Video", "Audio/Video" or "Thumbnails"
    type = Audio/Video
    
    # Target name; if not specified, the key name will be used
    #name = high
    
    # Target output extension
    extension = hq.ogg
    
    # Target subdirectory; if not specified TARGET NAME WILL NOT BE USED.
    subdir = high

    # The HTTP GET REquests to perform when this target 
    # has been successfuly transcoded.
    notify-done-requests#01 = http://backoffice.flumotion.com/cgi?file=%(outputRelFile)s&status=%(success)d
    
    # The following variable can be overriden,
    # if not the profile level values will be used.
    link-url-prefix
    post-processing-enabled
    link-files-enabled
    post-process-command
    post-process-timeout
    
    # The templates can be overriden
    #output-file-template
    #link-file-template
    #link-template
    
    # Target Configuration Section
    # In function of the tar[profile:fluprof:target:high]get type, the configuration section
    # should set diffrent properties:
    [profile:fluprof:target:high:config]
    
    # For Audio and Audio/Video Targets:
    audio-encoder = vorbisenc bitrate=128000
    audio-rate = 44100
    audio-channels = 2
    
    # For Video and Audio/Video targets:
    video-encoder = theoraenc bitrate=500
    video-width = 320
    video-height = 240
    #video-max-width = 
    #video-max-height = 
    video-par = 1/1
    video-framerate = 25/2
    # Can be Heigh, Width, Downscale or Upscale
    #video-scale-method = Heigh
    # Not implemented yet:
    #video-width-multiple = 1
    #video-height-multiple = 1
    
    # For Audio, Video and Audio/Video targets:
    muxer = oggmux
    
    # For Audio/Video targets:
    # Extra tolerence flag, can be 'Allow without Video' or 'Allow without Audio'
    tolerance = Allow without Video
    
    # For Thumbnails targets:
    period-value = 30
    # Unit of the period value, can be seconds, frames, keyframes or percent
    period-unit = Percent
    thumbs-width = 80
    thumbs-height = 60
    max-count = 1
    # The format of the ouput file, can be png od jpg
    output-format = png

    ------------------------------------------------------------"""    
    
    VERSION = (1, 0)
    COMMENTS = __doc__.split('\n')
    
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
    outputMediaTemplate = properties.String('output-media-template', None)
    outputThumbTemplate = properties.String('output-thumb-template', None)
    linkFileTemplate = properties.String('link-file-template', None)
    configFileTemplate = properties.String('config-file-template', None)
    reportFileTemplate = properties.String('report-file-template', None)
    linkTemplate = properties.String('link-template', None)
    linkURLPrefix = properties.String('link-url-prefix', None)
    enablePostprocessing = properties.Boolean('post-processing-enabled', None)
    enablePreprocessing = properties.Boolean('pre-processing-enabled', None)
    enableLinkFiles = properties.Boolean('link-files-enabled', None)
    customerPriority = properties.Integer('customer-priority', None, False, True)
    transcodingPriority = properties.Integer('transcoding-priority', None, False, True)
    processPriority = properties.Integer('process-priority', None, False, True)
    preprocessCommand = properties.String('pre-process-command', None)
    postprocessCommand = properties.String('post-process-command', None)
    preprocesstimeout = properties.Integer('pre-process-timeout', None, False, True)
    postprocessTimeout = properties.Integer('post-process-timeout', None, False, True)    
    transcodingTimeout = properties.Integer('transcoding-timeout', None, False, True)
    monitoringPeriod = properties.Integer('monitoring-period', None, False, True)
    profiles = properties.ChildDict('profile', ProfileData, root=True)


class AdminData(properties.RootPropertyBag):
    """
    File Data-Source Global Properties File.
    
    This file set the global and default property values, and specify 
    where the activities and customers properties files are located.
    Following is an example of the configuration properties.
    If the specified value is the default, the line will be commented out.
    For more information see the section 3-3 of the document specification.odt
    
    ------
    
    # Global Section
    [global]
    
    # Path to the directory containing the customers' property files.
    # Can be absolute or relative to this file.
    customers-dir = customers
    
    # Path to the activities' property files directory.
    # Can be absolute or relative to this file.
    activities-dir = /var/cache/flumotion/transcoder/activities
    
    # Default Values; See f.t.a.adminconsts.py
    # See section 4 of specification.odt for more information 
    # about the templates variables.notifyFailedRequests = 
    #monitoring-period = 5
    #transcoding-priority = 100
    #transcoding-timeout = 60
    #post-process-timeout = 60
    #pre-process-timeout = 60
    #mail-timeout = 30
    #mail-retry-count = 3
    #mail-retry-sleep = 60
    #http-request-timeout = 30
    #http-request-retry-count = 3
    #http-request-retry-sleep = 60
    #output-media-template = "%(targetPath)s%(sourceFile)s%(targetExtension)s"
    #output-thumb-template = "%(targetPath)s%(sourceFile)s.%%(index)03d%(targetExtension)s"
    #link-file-template = "%(targetPath)s%(sourceFile)s.link"
    #config-file-template = "%(sourcePath)s.ini"
    #report-file-template = "%(sourcePath)s.%%(id)s.rep"
    #mail-subject-template = "%(custName)s/%(profName)s transcoding %(trigger)s"
    mail-body-template = 
    
    # Default Values not yet used
    #access-force-group = file
    #discoverer-max-interleave = 1.0

    ------------------------------------------------------------"""
    
    VERSION = (1, 0)
    COMMENTS = __doc__.split('\n')
    
    monitoringPeriod = properties.Integer('monitoring-period', None, False, True)
    transcodingPriority = properties.Integer('transcoding-priority', None, False, True)
    transcodingTimeout = properties.Integer('transcoding-timeout', None, False, True)
    postprocessTimeout = properties.Integer('post-process-timeout', None, False, True)
    preprocessTimeout = properties.Integer('pre-process-timeout', None, False, True)
    outputMediaTemplate = properties.String('output-media-template', None)
    outputThumbTemplate = properties.String('output-thumb-template', None)
    linkFileTemplate = properties.String('link-file-template', None)
    configFileTemplate = properties.String('config-file-template', None)
    reportFileTemplate = properties.String('report-file-template', None)
    mailSubjectTemplate = properties.String('mail-subject-template', None)
    mailBodyTemplate = properties.String('mail-body-template', None)
    mailTimeout = properties.Integer('mail-timeout', None, False, True)
    mailRetryCount = properties.Integer('mail-retry-count', None, False, True)
    mailRetrySleep = properties.Integer('mail-retry-sleep', None, False, True)
    HTTPRequestTimeout = properties.Integer('http-request-timeout', None, False, True)
    HTTPRequestRetryCount = properties.Integer('http-request-retry-count', None, False, True)
    HTTPRequestRetrySleep = properties.Integer('http-request-retry-sleep', None, False, True)
    accessForceGroup = properties.String('access-force-group', None)
    discovererMaxInterleave = properties.Float('discoverer-max-interleave', 1.0)
    customersDir = properties.String('customers-dir', None, True)
    activitiesDir = properties.String('activities-dir', None, True)


class ActivityData(properties.RootPropertyBag):

    VERSION = (1, 0)
    COMMENTS = ("This file is generated by the transcoder administration.",
                "DO NOT MODIFY BY HAND.")
    
    label = properties.String('label', None)
    state = properties.Enum('state', ActivityStateEnum,
                            ActivityStateEnum.unknown)
    startTime = properties.DateTime("start-time")
    lastTime = properties.DateTime("last-time")
    customerName = properties.String('customer-name', None)
    profileName = properties.String('profile-name', None)    
    targetName = properties.String('target-name', None)    


class TranscodingActivityData(ActivityData):

    type = ActivityTypeEnum.transcoding
    subtype = properties.Enum('subtype', TranscodingTypeEnum)
    inputRelPath = properties.String('input-rel-path', None)


class NotificationActivityData(ActivityData):

    type = ActivityTypeEnum.notification
    subtype = properties.Enum('subtype', NotificationTypeEnum)
    trigger = properties.Enum('trigger', NotificationTriggerEnum)
    timeout = properties.Integer('timeout', None, False, True)
    retryCount = properties.Integer('retry-count', None, False, True)
    retryMax = properties.Integer('retry-max', None, False, True)
    retrySleep = properties.Integer('retry-sleep', None, False, True)
    data = properties.Dict(properties.String("data"))
