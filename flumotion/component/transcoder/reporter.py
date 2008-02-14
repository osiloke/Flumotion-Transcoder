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

import time
import datetime
import gobject

from twisted.python.failure import Failure

from flumotion.inhouse import log

from flumotion.transcoder import pipelinecrawler
from flumotion.transcoder.virtualpath import VirtualPath


class ReportVisitor(pipelinecrawler.PipelineVisitor):
    """
    Can be used more than one time with diffrent chunk of
    a pipeline. For example, It should be used with all
    the encoder bin of a target to have the complete commands.
    To use it again with a diffrent target it must be cleaned.
    """
    
    _hiddenElements = set(["typefind", "identity"])
    _hiddenProperties = set(["name", "fd", "copyright", "qos", "buffer-size", "sync"])
    _hiddenCompProps = {"queue":           set(["current-level-buffers",
                                                 "current-level-bytes",
                                                 "current-level-time",
                                                 "max-size-buffers",
                                                 "max-size-bytes",
                                                 "max-size-time"]),
                        "filesink":         set(["last-buffer"]),
                        "audiorate":        set(["in", "out", "drop", "add"]),
                        "videorate":        set(["in", "out", "drop", "add", "duplicate"]),
                        "vorbisenc":        set(["last-message"]),
                        "mp3parse":         set(["bitrate"]),
                        "lame":             set(["mode", "force-ms", "free-format",
                                                 "error-protection", "padding-type",
                                                 "extension", "strict-iso",
                                                 "disable-reservoir", "vbr-mean-bitrate",
                                                 "ath-only", "ath-short", "no-ath",
                                                 "cwlimit", "allow-diff-short", "emphasis"])}

    _genericTypes = {True:  {True: None, False: "audio"},
                     False: {True: "video", False: None}}

    _separator = " ! "

    def __init__(self):
        pipelinecrawler.PipelineVisitor.__init__(self)
        self.commands = {}
        self._pending = []
        self._lastType = None
        self.clean()

    def clean(self):
        self.commands.clear()
        del self._pending[:]
        self._lastType = None
    
    def getCommands(self):
        result = dict(self.commands)
        # If there is pending element,
        # Add them to the last command type        
        if len(self._pending) > 0:
            type = self._lastType
            if type == None:
                type = "unknown"
            if type in result:
                cmd = result[type] + self._separator
            else:
                cmd = ""
            cmd += self._separator.join(self._pending)
            result[type] = cmd
        return result
    
    def _elem2str(self, element):
        desc = ""
        factory = element.get_factory()
        if factory:
            name = factory.get_name()
        else:
            name = element.__class__.__name__
        desc += name
        if desc == "capsfilter":
            caps = str(element.get_property("caps"))
            if caps == "ANY":
                return "capsfilter"
            return "'%s'" % caps.replace("; ", ";")
        compProps = self._hiddenCompProps.get(name, set())
        hiddenProps = self._hiddenProperties | compProps
        for p in gobject.list_properties(element):
            if (p.name in hiddenProps):
                continue
            if p.name == "location":
                desc += " location=$FILE_PATH"
                continue
            defVal = p.default_value            
            currVal = element.get_property(p.name)
            if currVal != defVal:
                #For enums
                if hasattr(currVal, "value_name"):
                    currVal = currVal.value_name
                try:
                    float(currVal)
                except:
                    currVal = "'%s'" % currVal
                desc += " %s=%s" % (p.name, currVal)
        return desc

    def _getElementType(self, element):
        factory = element.get_factory()
        if not factory:
            return None
        klass = factory.get_klass()
        if "Demuxer" in klass:
            return "demuxer"
        if "Muxer" in klass:
            return "muxer"
        if "Video" in klass:
            return "video"
        if "Audio" in klass:
            return "audio"
        if "Generic" in klass:
            audio, video = False, False
            for pad in element.sink_pads():
                caps = str(pad.get_negotiated_caps())
                audio = audio or ("audio/" in caps)
                video = video or ("video/" in caps)
            return self._genericTypes[audio][video]
        return None
            
    def enterElement(self, branch, previous, element, next):
        # When crawling the whole pipeline, we should stop at the tee elements 
        # to not crawl the target parts of the pipeline
        factory = element.get_factory()
        if factory and (factory.get_name() == "tee"):
            return False
        # And we may ignore some elements
        if factory and (factory.get_name() in self._hiddenElements):
            return True
        
        # Find the element type. 
        # If the type is not found, store it for later triage
        type = self._getElementType(element)
        if type == None:
            self._pending.append(self._elem2str(element))
            return True
        self._lastType = type
        
        # retrieve the command for the current type
        if type in self.commands:
            cmd = self.commands[type] + self._separator
        else:
            cmd = ""
            
        # If there is pending element, add them to the command
        if len(self._pending) > 0:
            cmd += self._separator.join(self._pending) + self._separator
            del self._pending[:]
            
        # Add the current element command
        cmd += self._elem2str(element)
        
        # And store back the command
        self.commands[type] = cmd
        return True


def _addTaskError(task, error=None):
    if error == None:
        task.errors.append(log.getFailureMessage(Failure()))
    elif isinstance(error, Failure):
        task.errors.append(log.getFailureMessage(error))
    elif isinstance(error, Exception):
        task.errors.append(log.getFailureMessage(Failure(error)))
    else:
        task.errors.append(error)

def _getMediaLength(analysis):
    if analysis.videoLength and analysis.audioLength:
        return max(analysis.videoLength, analysis.audioLength)
    if analysis.videoLength:
        return analysis.videoLength
    if analysis.audioLength:
        return analysis.audioLength
    return -1

def _getMediaDuration(analysis):
    if (analysis.videoDuration == None) and (analysis.audioDuration == None):
        return None
    if analysis.videoDuration and analysis.audioDuration:
        return max(analysis.videoDuration, analysis.audioDuration)
    if analysis.videoDuration:
        return analysis.videoDuration
    if analysis.audioDuration:
        return analysis.audioDuration
    return -1

def _loadAnalysis(report, analysis):
    report.reset()
    report.mimeType = analysis.mimeType
    report.hasAudio = analysis.hasAudio
    if report.hasAudio:
        report.audioCaps = analysis.getAudioCapsAsString()
        report.audioFloat = analysis.audioFloat
        report.audioRate = analysis.audioRate
        report.audioDepth = analysis.audioDepth
        report.audioWidth = analysis.audioWidth
        report.audioChannels = analysis.audioChannels
        report.audioLength = analysis.audioLength
        report.audioDuration = analysis.getAudioDuration()
        
    report.hasVideo = analysis.hasVideo
    if report.hasVideo:
        report.videoCaps = analysis.getVideoCapsAsString()
        report.videoWidth = analysis.videoWidth
        report.videoHeight = analysis.videoHeight
        report.videoRate = (analysis.videoRate.num, 
                            analysis.videoRate.denom)
        report.videoLength = analysis.videoLength
        report.videoDuration = analysis.getVideoDuration()
        
    for s in analysis.otherStreams:
        report.otherStreams.append(str(s))
    for t, v in analysis.audioTags.iteritems():
        report.audioTags[str(t)] = str(v)
    for t, v in analysis.videoTags.iteritems():
        report.videoTags[str(t)] = str(v)
    for t, v in analysis.otherTags.iteritems():
        report.otherTags[str(t)] = str(v)


class CPUUsageMixin(object):
    
    def __init__(self, report, measures):
        self._measures = dict(measures)
        self._startTimes = dict()
        self._report = report
    
    def startUsageMeasure(self, measureName):
        if not measureName in self._measures:
            raise Exception("Unknown mesure '%s'" % measureName)
        self._startTimes[measureName] = (time.clock(), time.time())
    
    def stopUsageMeasure(self, measureName):
        if not measureName in self._measures:
            raise Exception("Unknown mesure '%s'" % measureName)
        cpu, real = self._startTimes[measureName]
        deltaCPU, deltaReal = time.clock() - cpu, time.time() - real
        if deltaReal > 0:
            percent = deltaCPU * 100 / deltaReal
        else:
            percent = -1
        usage = (deltaCPU, deltaReal, percent)
        setattr(self._report, self._measures[measureName], usage)
    

class SourceReporter(object):
    
    def __init__(self, rootReport):
        self.report = rootReport.source
        
    def getMediaLength(self):
        return _getMediaLength(self.report.analysis)
    
    def getMediaDuration(self):
        return _getMediaDuration(self.report.analysis)
    
    def setMediaAnalysis(self, analysis):
        _loadAnalysis(self.report.analysis, analysis)
        

class TargetReporter(CPUUsageMixin):
    
    def __init__(self, local, rootReport, targetKey):
        report = rootReport.targets[targetKey]
        CPUUsageMixin.__init__(self, report, 
                               {"postprocess": "cpuUsagePostprocess",
                                "analysis": "cpuUsageAnalysis"})
        self.local = local
        self.report = report
        self._postprocessStartTime = None
    
    def addError(self, error=None):
        _addTaskError(self.report, error)
        
    def setFatalError(self, error):
        self.report.fatalError = error
        
    def hasFatalError(self, targetKey=None):
        return self.report.fatalError != None
    
    def getMediaLength(self):
        return _getMediaLength(self.report.analysis)
    
    def getMediaDuration(self):
        return _getMediaDuration(self.report.analysis)

    def setMediaAnalysis(self, analysis):
        _loadAnalysis(self.report.analysis, analysis)

    def updatePipelineInfo(self, pipelineInfo):
        self.report.pipelineInfo.update(pipelineInfo)

    def addFile(self, work, output):
        if len(self.report.workFiles) != len(self.report.outputFiles):
            raise Exception("Report's file list invalid")
        virtWork = VirtualPath.virtualize(work, self.local)
        virtOutput = VirtualPath.virtualize(output, self.local)
        self.report.workFiles.append(virtWork)
        self.report.outputFiles.append(virtOutput)
        
    def getFiles(self):
        return [(work.localize(self.local), output.localize(self.local))
                for work, output in zip(self.report.workFiles,
                                        self.report.outputFiles)]


class Reporter(CPUUsageMixin):
    
    def __init__(self, local, report):
        CPUUsageMixin.__init__(self, report, 
                               {"job": "cpuUsageTotal",                                
                                "preprocess": "cpuUsagePreprocess",
                                "transcoding": "cpuUsageTranscoding"})        
        self.local = local
        self.report = report

    def init(self, context):
        sourceCtx = context.getSourceContext()
        self.setCurrentPath(sourceCtx.getInputPath())
        self.report.local.loadFromLocal(context.local)
        virtInput = VirtualPath.virtualize(sourceCtx.getInputPath(), self.local)
        virtDone = VirtualPath.virtualize(sourceCtx.getDoneInputPath(), self.local)
        virtFailed = VirtualPath.virtualize(sourceCtx.getFailedInputPath(), self.local)
        self.report.source.inputPath = virtInput
        self.report.source.donePath = virtDone
        self.report.source.failedPath = virtFailed

    _timeLookup = {"start": "startTime",
                   "done": "doneTime",
                   "acknowledge": "ackTime",
                   "terminated": "terminateTime"}

    def setCurrentPath(self, path):
        self.report.source.lastPath = VirtualPath.virtualize(path, self.local)

    def time(self, name):
        setattr(self.report, self._timeLookup[name], datetime.datetime.now())

    def getSourceReporter(self):
        return SourceReporter(self.report)
    
    def getTargetReporter(self, targetKey):
        return TargetReporter(self.local, self.report, targetKey)

    def addError(self, error=None):
        _addTaskError(self.report, error)
        
    def setFatalError(self, error):
        self.report.fatalError = error
        
    def hasFatalError(self, targetKey=None):
        return self.report.fatalError != None
        
    def crawlPipeline(self, pipeline, targetBins):
        visitor = ReportVisitor()
        crawler = pipelinecrawler.PipelineCrawler(visitor)
        crawler.crawlPipeline(pipeline)
        for c, v in visitor.getCommands().iteritems():
            self.report.source.pipelineAudit[c] = v
        for targetKey, bins in targetBins.iteritems():
            visitor.clean()
            crawler.clean()
            for name, bin in bins.iteritems():
                crawler.crawlBin(bin)
            for c, v in visitor.getCommands().iteritems():
                self.report.targets[targetKey].pipelineAudit[c] = v
    
        
