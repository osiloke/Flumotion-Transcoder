# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007,2008,2009 Fluendo, S.L.
# Copyright (C) 2010,2011 Flumotion Services, S.A.
# All rights reserved.
#
# This file may be distributed and/or modified under the terms of
# the GNU Lesser General Public License version 2.1 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.LGPL" in the source distribution for more information.
#
# Headers in this file shall remain intact.

from flumotion.inhouse import properties

from flumotion.transcoder import local, virtualpath
from flumotion.transcoder.enums import JobStateEnum
from flumotion.transcoder.enums import TargetStateEnum
from flumotion.transcoder.enums import TranscoderStatusEnum


class UsageProperty(properties.ValueProperty):

    def __init__(self, descriptor, default=None, required=False):
        properties.ValueProperty.__init__(self, descriptor, default, required)

    def checkValue(self, value):
        return (isinstance(value, tuple)
                and (len(value) == 3)
                and isinstance(value[0], (float, int, long))
                and isinstance(value[1], (float, int, long))
                and isinstance(value[2], (float, int, long)))

    def str2val(self, strval):
        ratio, percent = strval.split(' ~ ')
        cpuTime, realTime = ratio.split(' / ')
        return (float(cpuTime), float(realTime), float(percent))

    def val2str(self, value):
        return "%.2f / %.2f ~ %.2f" % value


class TaskReport(properties.PropertyBag):

    fatalError = properties.String('fatal-error')
    errors = properties.List(properties.String('errors'))


class AnalysisReport(properties.PropertyBag):
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

    prognosis = properties.String('prognosis')


class SourceReport(properties.PropertyBag):

    lastPath = virtualpath.VirtualPathProperty('last-path')
    inputPath = virtualpath.VirtualPathProperty('input-path')
    donePath = virtualpath.VirtualPathProperty('done-path')
    failedPath = virtualpath.VirtualPathProperty('failed-path')
    analysis = properties.Child('analysis', AnalysisReport)
    pipelineAudit = properties.Dict(properties.String("pipeline-audit"))
    fileType = properties.String("file-type")
    fileHeader = properties.List(properties.String("file-header"))
    fileSize = properties.Integer('file-size')
    machineName = properties.String("machine-name")


class TargetReport(TaskReport):

    state = properties.Enum('state', TargetStateEnum, TargetStateEnum.pending)
    workFiles = properties.List(virtualpath.VirtualPathProperty('files-work'))
    outputFiles = properties.List(virtualpath.VirtualPathProperty('files-output'))
    analysis = properties.Child('analysis', AnalysisReport)
    pipelineAudit = properties.Dict(properties.String("pipeline-audit"))
    pipelineInfo = properties.Dict(properties.String("pipeline-info"))
    cpuUsagePostprocess = UsageProperty('cpu-usage-postprocess')
    cpuUsageAnalysis = UsageProperty('cpu-usage-analysis')
    fileSize = properties.Integer('file-size')


class LocalReport(properties.PropertyBag):

    roots = properties.Dict(properties.String('roots'))
    name = properties.String('name')

    def loadFromLocal(self, local):
        # PyChecker doesn't like dynamic attributes
        __pychecker__ = "no-classattr"
        self.name = local.getName()
        for name, value in local.iterVirtualRoots():
            self.roots[name] = value

    def getLocal(self):
        # PyChecker doesn't like dynamic attributes
        __pychecker__ = "no-classattr"
        return local.Local(self.name, self.roots)


class TranscodingReport(properties.RootPropertyBag, TaskReport):

    VERSION = (1,0)

    state = properties.Enum('state', JobStateEnum, JobStateEnum.pending)
    status = properties.Enum('status', TranscoderStatusEnum,
                             TranscoderStatusEnum.pending)
    startTime = properties.DateTime('time-start')
    doneTime = properties.DateTime('time-done')
    ackTime = properties.DateTime('time-ack')
    terminateTime = properties.DateTime('time-terminate')
    configPath = virtualpath.VirtualPathProperty('config-path', None, True)
    niceLevel = properties.Integer('nice-level')
    local = properties.Child('local', LocalReport)
    source = properties.Child('source', SourceReport)
    targets = properties.ChildDict('targets', TargetReport)
    cpuUsageTotal = UsageProperty('cpu-usage-total')
    cpuUsagePreprocess = UsageProperty('cpu-usage-preprocess')
    cpuUsageTranscoding = UsageProperty('cpu-usage-transcoding')
    reportPath = virtualpath.VirtualPathProperty('report-path', None, True)

    def init(self, config):
        # PyChecker doesn't like dynamic attributes
        __pychecker__ = "no-classattr"
        for key in config.targets:
            self.targets[key] = TargetReport()
