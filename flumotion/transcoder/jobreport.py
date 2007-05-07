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

from flumotion.transcoder import properties
from flumotion.transcoder import jobconfig
from flumotion.transcoder.enums import JobStateEnum
from flumotion.transcoder.enums import TargetStateEnum
from flumotion.transcoder.enums import TranscoderStatusEnum

class UsageProperty(properties.ValueProperty):
    
    def __init__(self, descriptor, default=None, required=False):
        properties.ValueProperty.__init__(self, descriptor, default, required)
    
    def checkValue(self, value):
        return (isinstance(value, tuple) 
                and (len(value) == 3)
                and isinstance(value[0], float)
                and isinstance(value[1], float)
                and isinstance(value[2], float))

    def str2val(self, strval):
        ratio, percent = strval.split(' ~ ')
        cpuTime, realTime = ratio.split(' / ')
        return (float(cpuTime), float(realTime), float(percent))
    
    def val2str(self, value):
        return "%.2f / %.2f ~ %.2f" % value


class TaskReport(properties.PropertyBag):

    fatalError = properties.String('fatal-error')
    errors = properties.List(properties.String('errors'))


class DiscoverReport(properties.PropertyBag):
    mimeType = properties.String('mime-type')

    hasAudio = properties.Boolean("has-audio", False)
    audioCaps = properties.String("audio-caps")
    audioFloat = properties.Boolean("audio-float")
    audioRate = properties.Integer('audio-rate')
    audioDepth = properties.Integer('audio-depth')
    audioWidth = properties.Integer('audio-width')
    audioChannels = properties.Integer('audio-channels')
    audioLength = properties.Integer('audio-length')
    audioDuration = properties.Float('audio-duration')
    
    hasVideo = properties.Boolean("has-video", False)
    videoCaps = properties.String("video-caps")
    videoWidth = properties.Integer('video-width')
    videoHeight = properties.Integer('video-height')
    videoRate = properties.Fraction('video-rate')
    videoLength = properties.Integer('video-length')
    videoDuration = properties.Float('video-duration')

    otherStreams = properties.List(properties.String("other-streams"))
    audioTags = properties.Dict(properties.String("audio-tags"))
    videoTags = properties.Dict(properties.String("video-tags"))
    otherTags = properties.Dict(properties.String("other-tags"))


class SourceReport(properties.PropertyBag):

    filePath = properties.String('file-path')
    analyse = properties.Child('analyse', DiscoverReport)
    pipeline = properties.Dict(properties.String("pipeline"))    


class TargetReport(TaskReport):

    state = properties.Enum('state', TargetStateEnum, TargetStateEnum.pending)
    workFiles = properties.List(properties.String('files-work'))
    outputFiles = properties.List(properties.String('files-output'))
    analyse = properties.Child('analyse', DiscoverReport)
    pipeline = properties.Dict(properties.String("pipeline"))
    cpuUsagePostprocess = UsageProperty('cpu-usage-postprocess')
    cpuUsageAnalyse = UsageProperty('cpu-usage-analyse')
                            

class JobReport(properties.RootPropertyBag, TaskReport):

    state = properties.Enum('state', JobStateEnum, JobStateEnum.pending)
    startTime = properties.DateTime('time-start')
    doneTime = properties.DateTime('time-done')
    ackTime = properties.DateTime('time-ack')
    terminateTime = properties.DateTime('time-terminate')
    configPath = properties.String('config-file', None, True)
    niceLevel = properties.Integer('nice-level')
    source = properties.Child('source', SourceReport)
    targets = properties.ChildList('targets', TargetReport)
    cpuUsageTotal = UsageProperty('cpu-usage-total')
    cpuUsagePreprocess = UsageProperty('cpu-usage-preprocess')
    cpuUsageTranscoding = UsageProperty('cpu-usage-transcoding')    
    
    def init(self, config):
        for index, target in enumerate(config.targets):
            if target != None:
                self.targets.addItemAt(index)
