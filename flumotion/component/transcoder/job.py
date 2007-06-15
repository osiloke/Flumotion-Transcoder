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

import sys
import os
import re
import shutil
import urllib

import gobject
gobject.threads_init()
import gst

from twisted.internet import reactor, error, defer
from twisted.python.failure import Failure

#from gst.extend.discoverer import Discoverer

from flumotion.common import common
from flumotion.common import enum
from flumotion.common.common import ensureDir
from flumotion.transcoder import process, log
from flumotion.transcoder import enums
from flumotion.transcoder.enums import TargetTypeEnum
from flumotion.transcoder.enums import JobStateEnum
from flumotion.transcoder.enums import TargetStateEnum
from flumotion.transcoder.errors import TranscoderError
from flumotion.component.transcoder import targets
from flumotion.component.transcoder.context import Context, TaskContext
from flumotion.component.transcoder.context import TargetContext
from flumotion.component.transcoder.gstutils import Discoverer
from flumotion.component.transcoder.transcoder import MultiTranscoder


CORTADO_DEFAULT_WIDTH = 320
CORTADO_DEFAULT_HEIGHT = 40


class JobEventSink(object):
    
    def onJobInfo(self, info):
        pass
    
    def onJobError(self, error):
        pass
    
    def onJobWarning(self, warning):
        pass
    
    def onProgress(self, percent):
        pass
    
    def onJobStateChanged(self, state):
        pass
    
    def onSourceInfo(self, info):
        pass
    
    def onTargetStateChanged(self, label, state):
        pass
    
    def onTargetInfo(self, label, info):
        pass
    
    def onTargetError(self, label, error):
        pass
    
    def onTargetWarning(self, label, warning):
        pass


class HandledTranscoderError(TranscoderError):
    
    def __init__(self, *args, **kwargs):
        TranscoderError.__init__(self, *args, **kwargs)


def _stopMeasureCallback(result, reporter, measureName):
    """
    Helper callback to properly stop usage measurments.
    """
    reporter.stopUsageMeasure(measureName)
    return result

RunningState = enum.EnumClass('StopState', ('initializing', 'running', 
                                            'waiting', 'acknowledged',
                                            'terminated', 'stopped'))

class TranscoderJob(log.LoggerProxy):
    
    def __init__(self, logger, eventSink=None):
        log.LoggerProxy.__init__(self, logger)
        self._context = None
        self._moveInputFile = True
        self._unrecognizedOutputs = {}
        self._failedPostProcesses = {}
        self._processes = []
        self._eventSink = eventSink
        self._ack = None
        self._ackList = None
        self._readyForAck = None
        self._acknowledged = False
        self._transcoder = None
        self._runningState = RunningState.initializing
        self._stopping = False
        self._stoppingDefer = None

        
    ## Public Methods ##
        
    #FIXME: Should have a better way to expose context info
    def getDoneReportPath(self):
        sourceCtx = self._context.getSourceContext()
        return sourceCtx.getDoneReportPath()
    
    #FIXME: Should have a better way to expose context info
    def getFailedReportPath(self):
        sourceCtx = self._context.getSourceContext()
        return sourceCtx.getFailedReportPath()
        
    def setup(self, local, config, report, 
              altInputDir=None, moveInputFile=True, niceLevel=None):
        context = Context(self, local, config, report)
        self._context = context
        if altInputDir != None:
            context.setAltInputDir(altInputDir)        
        sourceCtx = context.getSourceContext()
        self._moveInputFile = moveInputFile
        self._setLogName(sourceCtx.getInputFile())
        if niceLevel != None:
            self.__setNiceLevel(niceLevel)
        self.__checkConfig()
        
    def start(self):
        context = self._context
        if (context == None):
            raise TranscoderError("Transcoding Job not properly setup",
                                  data=context)
        context.info("Starting transcoding job")
        context.reporter.time("start")
        
        sourceCtx = context.getSourceContext()
        
        self._unrecognizedOutputs = {}
        self._failedPostProcesses = {}
        self._processes = []
        self._setJobState(JobStateEnum.starting)
        context.reporter.startUsageMeasure("job")
        
        d = defer.Deferred()            
        if sourceCtx.config.preProcess:
            #Setup pre-processing
            d.addCallback(self.__cbPerformPreProcessing, context)
            d.addErrback(self.__ebFatalFailure, context, "pre-processing")
        #Setup transcoding
        d.addCallback(self.__cbTranscodeSource, context)
        d.addErrback(self.__ebFatalFailure, context, "transcoding")
        #Setup target processing
        d.addCallback(self.__cbProcessTargets, context)
        d.addErrback(self.__ebFatalFailure, context, "targets processing")
        #Stop Job Usage measurment
        d.addBoth(_stopMeasureCallback, context.reporter, "job")
        #Transcoding Task Terminated
        d.addCallback(self.__cbJobDone, context)
        d.addErrback(self.__ebJobFailed, context)
        
        #Only move the input file after acknowledge
        deferreds = []
        #fired when acknowledge() is called
        self._ack = defer.Deferred()
        #fired when transcoding is done
        self._readyForAck = defer.Deferred()
        deferreds.append(self._ack)
        deferreds.append(self._readyForAck)
        self._ackList = defer.DeferredList(deferreds,
                                           fireOnOneCallback=False,
                                           fireOnOneErrback=False,
                                           consumeErrors=True)
        #Wait the transcoding task
        def readyForAck(result):
            self._readyForAck.callback(defer._nothing)
            return result
        d.addBoth(readyForAck)
        self._ackList.addCallback(self.__cbDoAcknowledge, context)
        #Setup output files moving
        self._ackList.addCallback(self.__cbMoveOutputFiles, context)
        self._ackList.addErrback(self.__ebFatalFailure, 
                                 context, "output files moving")
        if self._moveInputFile:
            #Setup input file moving
            self._ackList.addBoth(self.__bbMoveInputFile, context)        
        #Handle termination
        self._ackList.addBoth(self.__bbJobTerminated, context)
        
        self._fireJobInfo(context)
        self._fireSourceInfo(sourceCtx)
        for targetCtx in context.getTargetContexts():
            self._fireTargetInfo(targetCtx)
            self._setTargetState(targetCtx, TargetStateEnum.pending)
        
        #start to work after the starting call chain terminate
        reactor.callLater(0, d.callback, defer._nothing)
        self._runningState = RunningState.running
        return d
            
    def stop(self):
        self._context.info("Stopping transcoding job")
        self._setJobState(JobStateEnum.stopping)
        self._stopping = True
        #If already tell to stop, do nothing
        if self._stoppingDefer:
            return self._stoppingDefer
        #If the job has been acknowledged, wait until completion
        if self._runningState == RunningState.acknowledged:
            self._stoppingDefer = defer.Deferred()
            self._ackList.addBoth(self._stoppingDefer.callback)
        else:
            abortDefs = []
            #if there is a transcoder, try to abort it
            if self._transcoder:
                abortDefs.append(self._transcoder.abort())
            #if there is running process, try to abort them
            for process in self._processes:
                abortDefs.append(process.abort())
            if len(abortDefs) > 0:
                self._stoppingDefer = defer.DeferredList(abortDefs,
                                                         fireOnOneCallback=False,
                                                         fireOnOneErrback=False,
                                                         consumeErrors=True)
            else:
                self._stoppingDefer = defer.succeed(self)
        #ensure the deferred result value is self
        self._stoppingDefer.addCallback(lambda r, v: v, self)
        return self._stoppingDefer
    
    def acknowledge(self):
        """
        Acknowledge the transcoding task, and wait for the task to terminate.
        Return a deferred that will be called when the task is fully 
        completed and the input file has been moved.
        This method must be call for the input file to be moved, 
        this prevent moving a file used by two instances at the same time.
        Must be called after calling start.
        """
        #When acknowleged, the job cannot be stopped util completion
        self._runningState = RunningState.acknowledged
        self._context.info("Transcoding job acknowledged")
        self._context.reporter.time("acknowledge")
        self._acknowledged = True
        self._ack.callback(defer._nothing)
        return self._ackList
        
        
    ## Overriden Methods ##
    
    def getLogPrefix(self, kwargs):
        ctx = kwargs.pop('context', None)
        if ctx:
            return ctx.getTag()
        return None


    ## Protected/Friends Methods ##
    
    def _isStopping(self):
        # The Job should not be stopped during acknoledgment
        if self._runningState == RunningState.acknowledged:
            return False
        if self._stopping:
            self.debug("IS STOPPED")
            if self._runningState != RunningState.stopped:
                self._runningState = RunningState.stopped
                #Do some stopping stuff only once ?
            return True
        return False
    
    def _setJobState(self, state):
        #FIXME: Don't reference the global context
        reporter = self._context.reporter
        reporter.report.state = state
        self._fireJobStateChanged(state)
        
    def _setTargetState(self, targetCtx, state):
        targetCtx.reporter.report.state = state
        self._fireTargetStateChanged(targetCtx, state)
        
    def _setLogName(self, name):
        if len(name) > 32:
            name = name[0:14] + "..." + name[-14:]
        self.logName = name

    def _transcoderProgressCallback(self, percent):
        self._context.log("Progress: %d %%" % int(percent))
        self._fireProgress(percent)

    def _transcoderDiscoveredCallback(self, discoverer, ismedia):
        #FIXME: Don't reference the global context
        context = self._context
        sourceCtx = context.getSourceContext()
        sourceCtx.reporter.doAnalyse(discoverer)
        for otherstream in discoverer.otherstreams:
            context.info("Source file contains unknown stream type : %s" 
                      % otherstream)
        self._fireSourceInfo(context.getSourceContext())
    
    def _transcoderPiplineCallback(self, pipeline, transcodingTargets):
        #FIXME: Don't reference the global context
        context = self._context
        targetsBins = {}
        for transTarget in transcodingTargets:
            targetCtx = transTarget.getData()
            bins = transTarget.getBins()            
            if len(bins) > 0:
                targetsBins[targetCtx.index] = bins
        context.reporter.crawlPipeline(pipeline, targetsBins)

    def _getPreProcessVars(self, context):
        reporter = context.reporter
        config = context.config
        sourceCtx = context.getSourceContext()        
        sourceAnalyse = reporter.report.source.analyse
        vars = dict()
        vars['inputFile'] = sourceCtx.getInputFile()
        vars['reportFile'] = sourceCtx.getReportFile()
        vars['inputDir'] = context.getInputDir()
        vars['outputDir'] = context.getOutputDir()
        vars['workDir'] = context.getWorkDir()
        vars['inputPath'] = sourceCtx.getInputPath()
        vars['configPath'] = reporter.report.configPath
        vars['custName'] = config.customer.name
        vars['profLabel'] = config.profile.label
        vars['targets'] = [t.label for t in config.targets if t != None]
        vars['sourceMime'] = sourceAnalyse.mimeType
        if sourceAnalyse.hasVideo:
            vars['sourceHaveVideo'] = 1
            vars['sourceVideoWidth'] = sourceAnalyse.videoWidth
            vars['sourceVideoHeight'] = sourceAnalyse.videoHeight
        else:
            vars['sourceHaveVideo'] = 0
            vars['sourceVideoWidth'] = 0
            vars['sourceVideoHeight'] = 0
        if sourceAnalyse.hasAudio:
            vars['sourceHaveAudio'] = 1
        else:
            vars['sourceHaveAudio'] = 0

        duration = sourceCtx.reporter.getMediaDuration() or -1
        length = sourceCtx.reporter.getMediaLength()
        vars['sourceDuration'] = duration
        vars['sourceLength'] = length
        s = int(round(duration))
        m = s / 60
        s -= m * 60
        h = m / 60
        m -= h * 60        
        vars['sourceHours'] = h
        vars['sourceMinutes'] = m
        vars['sourceSeconds'] = s
        return vars

    def _getPostProcessVars(self, targetCtx):
        targetConfig = targetCtx.config
        targetReporter = targetCtx.reporter
        targetAnalyse = targetCtx.reporter.report.analyse
        
        #FIXME: Don't reference the global context
        vars = self._getPreProcessVars(self._context)

        vars['outputPath'] = targetCtx.getOutputPath()
        vars['linkPath'] = targetCtx.getLinkPath()
        vars['linkWorkPath'] = targetCtx.getLinkWorkPath()
        vars['outputWorkPath'] = targetCtx.getOutputWorkPath()

        vars['targetLabel'] = targetConfig.label
        vars['targetType'] = targetConfig.type.name
        vars['targetMime'] = targetAnalyse.mimeType
        if targetAnalyse.hasVideo:
            vars['targetHaveVideo'] = 1
            vars['targetVideoWidth'] = targetAnalyse.videoWidth
            vars['targetVideoHeight'] = targetAnalyse.videoHeight
        else:
            vars['targetHaveVideo'] = 0
            vars['targetVideoWidth'] = 0
            vars['targetVideoHeight'] = 0
        if targetAnalyse.hasAudio:
            vars['targetHaveAudio'] = 1
        else:
            vars['targetHaveAudio'] = 0

        duration = targetReporter.getMediaDuration() or -1
        length = targetReporter.getMediaLength()
        vars['targetDuration'] = duration
        vars['targetLength'] = length
        s = int(round(duration))
        m = s / 60
        s -= m * 60
        h = m / 60
        m -= h * 60        
        vars['targetHours'] = h
        vars['targetMinutes'] = m
        vars['targetSeconds'] = s
        return vars

    def _getLinkTemplateVars(self, targetCtx):
        return self._getPostProcessVars(targetCtx)
        
    def _getCortadoArgs(self, targetCtx):
        targetAnalyse = targetCtx.reporter.report.analyse
        args = dict()
        duration = targetCtx.reporter.getMediaDuration()
        if duration and (duration > 0):
            # let buffer time be at least 5 seconds
            output = targetCtx.getOutputWorkPath()
            bytesPerSecond = os.stat(output).st_size / duration
            # specified in Kb
            bufferSize = int(bytesPerSecond * 5 / 1024)
        else:
            # Default if we couldn't figure out duration
            bufferSize = 128
        args['c-bufferSize'] = str(bufferSize)
        # cortado doesn't handle Theora cropping, so we need to round
        # up width and height for display
        rounder = lambda i: (i + (16 - 1)) / 16 * 16
        if targetAnalyse.videoWidth:
            args['c-width'] = str(rounder(targetAnalyse.videoWidth))
        else:
            args['c-width'] = CORTADO_DEFAULT_WIDTH
        if targetAnalyse.videoHeight:
            args['c-height'] = str(rounder(targetAnalyse.videoHeight))
        else:
            args['c-height'] = CORTADO_DEFAULT_HEIGHT
        if duration:
            args['c-duration'] = str(duration)
            args['c-seekable'] = 'true'
        if targetAnalyse.audioCaps:        
            args['c-audio'] = 'true'
        else:
            args['c-audio'] = 'false'
        if targetAnalyse.videoCaps:
            args['c-video'] = 'true'
        else:
            args['c-video'] = 'false'
        return args
    
    def _fireProgress(self, percent):
        if self._eventSink:
            self._eventSink.onProgress(percent)
    
    def _fireJobStateChanged(self, state):
        if self._eventSink:
            self._eventSink.onJobStateChanged(state)
    
    def _addAnalyseInfo(self, info, analyseData):
        if analyseData.mimeType != None:    
            info["mime-type"] = analyseData.mimeType
        if analyseData.hasVideo:
            info["video-size"] = (analyseData.videoWidth, 
                                  analyseData.videoHeight)
            info["video-rate"] = analyseData.videoRate
            info["video-encoder"] = analyseData.videoTags.get("encoder", None)
        if analyseData.hasAudio:
            info["audio-rate"] = analyseData.audioRate
            info["audio-encoder"] = analyseData.audioTags.get("encoder", None)
        return info
    
    def _addFileInfo(self, info, file):
        if os.path.exists(file):
            info["file-size"] = os.stat(file).st_size
    
    def _fireJobInfo(self, context):
        if self._eventSink:
            config = context.config
            info = {}
            info["acknowledged"] = self._acknowledged
            info["customer-name"] = config.customer.name
            info["profile-label"] = config.profile.label
            info["targets"] = [t.label for t in config.targets]
            self._eventSink.onJobInfo(info)
    
    def _fireSourceInfo(self, sourceCtx):
        if self._eventSink:
            info = {}
            duration = sourceCtx.reporter.getMediaDuration()
            if duration != None:
                info["duration"] = duration
            self._addAnalyseInfo(info, sourceCtx.reporter.report.analyse)
            self._addFileInfo(info, sourceCtx.getInputPath())
            info["input-file"] = sourceCtx.getInputPath()
            self._eventSink.onSourceInfo(info)
    
    def _fireTargetStateChanged(self, targetCtx, state):
        if self._eventSink:
            label = targetCtx.config.label
            self._eventSink.onTargetStateChanged(label, state)
    
    def _fireTargetInfo(self, targetCtx):
        if self._eventSink:
            info = {}
            duration = targetCtx.reporter.getMediaDuration()
            if duration != None:
                info["duration"] = duration
            self._addAnalyseInfo(info, targetCtx.reporter.report.analyse)            
            info["output-file"] = targetCtx.getOutputFile()
            info["type"] = targetCtx.config.type.name
            if targetCtx.config.type == TargetTypeEnum.thumbnails:
                info["file-count"] = len(targetCtx.reporter.report.workFiles)
            else:
                self._addFileInfo(info, targetCtx.getOutputWorkPath())
            self._eventSink.onTargetInfo(targetCtx.config.label, info)

    def _fireError(self, context, error):
        if self._eventSink:
            if isinstance(context, TargetContext):
                self._eventSink.onTargetError(context.config.label, error)
            else:
                self._eventSink.onJobError(error)
            
    def _fireWarning(self, context, warning):
        if self._eventSink:
            if isinstance(context, TargetContext):
                self._eventSink.onTargetWarning(context.config.label, warning)
            else:
                self._eventSink.onJobWarning(warning)
    
    
    ## Private Methods ##
        
    def __setNiceLevel(self, niceLevel):
        context = self._context
        reporter = context.reporter
        try:
            os.nice(niceLevel - os.nice(0))
            context.info("Changed the process nice level to %d", niceLevel)
            reporter.report.niceLevel = niceLevel
        except OSError, e:
            reporter.addError(e)
            context.warning("Failed to change process nice level: %s",
                            log.getExceptionMessage(e))
            reporter.report.niceLevel = os.nice(0)
            
    def __checkConfig(self):
        sourceCtx = self._context.getSourceContext()
        inputPath = sourceCtx.getInputPath()
        if not os.path.exists(inputPath):
            raise Exception("Source file not found ('%s')" % inputPath)
        if not os.path.isfile(inputPath):
            raise Exception("Invalid source file ('%s')" % inputPath)
    

    
    def __showFailure(self, context, task, failure):
        context.debug("Traceback of %s failure with filenames cleaned up:\n%s" 
                      % (task, log.cleanTraceback(failure.getTraceback())))
        
    def __lookupContext(self, defaultContext, failure):
        """
        If the error has a context, use it inplace of the default one.
        """
        if failure and failure.value and isinstance(error, TranscoderError):
            data = failure.value.data
            if data and isinstance(data, TaskContext):
                return data
        return defaultContext
        
    ### Called by Deferreds ###
    def __ebFatalFailure(self, failure, context, task):
        # If stopping don't do anything
        if self._isStopping(): return
        context = self.__lookupContext(context, failure)
        if context.reporter.hasFatalError():
            context.debug("Skipping %s because of fatal error during %s"
                          % (task, context.reporter.report.state))
            return failure
        context.reporter.addError(failure)
        errMsg = failure.getErrorMessage()
        context.reporter.setFatalError(errMsg)
        context.warning("Fatal error during %s: %s", task, errMsg)
        self.__showFailure(context, task, failure)
        self._fireError(context, errMsg)
        if not failure.check(TranscoderError):
            raise TranscoderError(errMsg, data=context, cause=failure)
        return failure

    ### Called by Deferreds ###
    def __ebRecoverableFailure(self, failure, context, task, result=defer._nothing):
        # If stopping don't do anything
        if self._isStopping(): return
        context = self.__lookupContext(context, failure)
        if context.reporter.hasFatalError():
            context.debug("Skipping %s because of fatal error during %s"
                         % (task, context.reporter.report.state))
            return failure
        context.reporter.addError(failure)
        warMsg = failure.getErrorMessage()
        context.warning("Recoverable error during %s: %s", task, warMsg)
        self.__showFailure(context, task, failure)
        self._fireWarning(context, warMsg)
        return result
        
    ### Called by Deferreds ###
    def __cbJobDone(self, result, context):
        # If stopping don't do anything
        if self._isStopping(): return
        context.info("Transcoding job done")
        context.reporter.time("done")
        self._setJobState(JobStateEnum.waiting_ack)
        self._runningState = RunningState.waiting
        return context.reporter.report
    
    ### Called by Deferreds ###
    def __ebJobFailed(self, failure, context):        
        # If stopping don't do anything
        if self._isStopping(): return
        context.warning("Transcoding job failed: %s",
                        failure.getErrorMessage())
        context.reporter.time("done")
        self._setJobState(JobStateEnum.waiting_ack)
        for targetCtx in context.getTargetContexts():
            if targetCtx.reporter.report.state == "pending":
                self._setTargetState(targetCtx, TargetStateEnum.skipped)
        self._runningState = RunningState.waiting
        return failure

    ### Called by Deferreds ###
    def __bbJobTerminated(self, result, context):
        # If stopping don't do anything
        if self._isStopping(): return
        context.info("Transcoding job terminated")
        context.reporter.time("terminated")
        self._setJobState(JobStateEnum.terminated)
        self._runningState = RunningState.terminated
        return context.reporter.report

    ### Called by Deferreds ###
    def __cbPerformPreProcessing(self, result, context):
        # If stopping don't do anything
        if self._isStopping(): return
        sourceCtx = context.getSourceContext()
        context.debug("Performing profile pre-processing")
        self._setJobState(JobStateEnum.preprocessing)
        context.debug("Performing pre-processing for '%s'",
                      sourceCtx.getInputPath())
        p = process.Process("pre-process", 
                            sourceCtx.config.preProcess, 
                            context)
        self._processes.append(p)
        vars = self._getPreProcessVars(context)
        context.reporter.startUsageMeasure("preprocess")
        d = p.execute(vars, timeout=context.config.preProcessTimeout)        
        d.addBoth(_stopMeasureCallback, context.reporter, "preprocess")
        d.addBoth(lambda r, e: self._processes.remove(e) or r, p)
        #Don't return Process result, but pass the received result
        d.addCallback(lambda state, res: res, result)
        return d

    _targetClassForType = {TargetTypeEnum.audio: targets.AudioTarget,
                           TargetTypeEnum.video: targets.VideoTarget,
                           TargetTypeEnum.audiovideo: targets.AudioVideoTarget,
                           TargetTypeEnum.thumbnails: targets.ThumbnailsTarget}
    
    ### Called by Deferreds ###
    def __cbTranscodeSource(self, result, context):
        # If stopping don't do anything
        if self._isStopping(): return
        sourceCtx = context.getSourceContext()
        context.debug("Transcoding source file '%s'", 
                      sourceCtx.getInputPath())
        self._setJobState(JobStateEnum.transcoding)
        transcoder = MultiTranscoder(self, sourceCtx.getInputPath(),
                                     context.config.transcodingTimeout,
                                     self._transcoderProgressCallback,
                                     self._transcoderDiscoveredCallback,
                                     self._transcoderPiplineCallback)
        for targetCtx in context.getTargetContexts():
            targetConfig = targetCtx.config
            TargetClass = self._targetClassForType[targetConfig.type]
            transcoder.addTarget(TargetClass(targetCtx.getOutputWorkPath(),
                                             targetConfig.config, 
                                             targetConfig.label,
                                             targetCtx, targetCtx))
        context.reporter.startUsageMeasure("transcoding")
        self._transcoder = transcoder
        d = transcoder.start()
        d.addBoth(_stopMeasureCallback, context.reporter, "transcoding")
        return d

    ### Called by Deferreds ###
    def __cbProcessTargets(self, transcodingTargets, context):
        # If stopping don't do anything
        if self._isStopping(): return
        context.debug("Transcoding done")
        self._setJobState(JobStateEnum.target_processing)
        d = defer.Deferred()
        for transTarget in transcodingTargets:
            targetCtx = transTarget.getData()
            if targetCtx == None or not isinstance(targetCtx, TargetContext):
                raise TranscoderError("The transcoder mixed-up "
                                      + "the provided context", data=context)
            for wp in transTarget.getOutputs():
                op = targetCtx.getOutputFromWork(wp)
                targetCtx.reporter.addFile(wp, op)
            d.addCallback(self.__cbProcessTarget, targetCtx)
        #Handle targets outcomes
        d.addCallback(self.__cbAllTargetsSucceed, context)
        d.addErrback(self.__ebSomeTargetsFailed, context)
        d.callback(defer._nothing)
        return d

    ### Called by Deferreds ###
    def __cbProcessTarget(self, result, targetCtx):
        # If stopping don't do anything
        if self._isStopping(): return
        targetCtx.info("Start target processing")
        d = defer.Deferred()
        if targetCtx.hasAudio() or targetCtx.hasVideo():
            #Setup target output file analysis
            d.addCallback(self.__cbTargetAnalyseOutputFile, targetCtx)
            d.addErrback(self.__ebFatalFailure, targetCtx, "target analysis")
        if targetCtx.config.postProcess:
            #Setup target post-processing
            d.addCallback(self.__cbTargetPerformPostProcessing, targetCtx)
            d.addErrback(self.__ebFatalFailure, targetCtx, "post-processing")
        if targetCtx.hasAudio() or targetCtx.hasVideo():
            if targetCtx.hasLinkConfig():
                #Setup target link file generation
                d.addCallback(self.__cbTargetGenerateLinkFile, targetCtx)
                d.addErrback(self.__ebRecoverableFailure, targetCtx,
                                 "link file generation")
        d.addCallback(self.__cbTargetDone, targetCtx)
        d.addErrback(self.__ebTargetFailed, targetCtx)
        d.callback(result)
        return d

    ### Called by Deferreds ###
    def __cbDoAcknowledge(self, results, context):
        for success, result in results:
            if not success:
                return result
        return None

    ### Called by Deferreds ###
    def __cbMoveOutputFiles(self, result, context):
        # If stopping don't do anything
        if self._isStopping(): return
        context.debug("Moving output files")
        self._setJobState(JobStateEnum.output_file_moving)
        for targetCtx in context.getTargetContexts():
            for src, dest in targetCtx.reporter.getFiles():
                context.log("Moving '%s' to '%s'", src, dest)
                ensureDir(os.path.dirname(dest), "transcoding done")
                shutil.move(src, dest)
        return result

    ### Called by Deferreds ###
    def __bbMoveInputFile(self, result, context):
        """
        Can be called as a Callback or an Errback.
        If it's called with a non-failure parameter,
        it will try to move the input file to the done folder.
        If it's called with a failure parameter, 
        it will try to move the input file to the failed folder.
        If the move operation fail when trying to move to
        the done folder, it try to move to input file to the
        failed foder and raise a new failure.
        If the move operation fail when trying to move to
        the failed folder, the error is logged and then
        the original failure is raised.
        """
        # If stopping don't do anything
        if self._isStopping(): return
        self._setJobState(JobStateEnum.input_file_moving)
        sourceCtx = context.getSourceContext()
        
        if isinstance(result, Failure):
            #We are in an Errback
            error = result
            def terminate(error):
                if error:
                    return error
                return result
        else:
            #We are in a Callback
            error = None
            def terminate(error):
                if error:
                    raise error.value
                return result
            
        def moveSource(to):
            source = sourceCtx.getInputPath()
            context.debug("Moving input file to '%s'", to)
            context.log("Moving '%s' to '%s'", source, to)
            ensureDir(os.path.dirname(to), "transcoding done")
            shutil.move(source, to)
            
        if not error:
            try:
                newFile = sourceCtx.getDoneInputPath()
                moveSource(newFile)
                context.reporter.setSourcePath(newFile)
            except Exception, e:
                context.warning("Failed to move input file: %s", 
                                log.getExceptionMessage(e))
                error = Failure()
                context.reporter.addError(error)
                context.reporter.setFatalError(error.getErrorMessage())
        
        if error:
            try:
                newFile = sourceCtx.getFailedInputPath()
                moveSource(newFile)
                context.reporter.setSourcePath(newFile)
            except Exception, e:
                context.warning("Failed to move input file: %s", 
                                log.getExceptionMessage(e))
                context.reporter.addError(e)
        
        return terminate(error)

    ### Called by Deferreds ###
    def __cbTargetAnalyseOutputFile(self, result, targetCtx):
        # If stopping don't do anything
        if self._isStopping(): return
        targetCtx.debug("Analysing target output file '%s'",
                        targetCtx.getOutputWorkPath())
        self._setTargetState(targetCtx, TargetStateEnum.analysis)
        discoverer = Discoverer(targetCtx.getOutputWorkPath())
        targetCtx.reporter.startUsageMeasure("analyse")
        d = discoverer.discover()
        d.addBoth(_stopMeasureCallback, targetCtx.reporter, "analyse")
        d.addCallbacks(self.__cbTargetIsAMedia, self.__ebTargetIsNotAMedia,
                       callbackArgs=(targetCtx,),
                       errbackArgs=(targetCtx,))
        return d
    
    ### Called by Deferreds ###
    def __cbTargetIsAMedia(self, discoverer, targetCtx, result=defer._nothing):
        # If stopping don't do anything
        if self._isStopping(): return
        targetCtx.reporter.doAnalyse(discoverer)
        self._fireTargetInfo(targetCtx)
        expa = targetCtx.hasAudio()
        expv = targetCtx.hasVideo()
        gota = discoverer.is_audio
        gotv = discoverer.is_video
        if ((gota != expa) or (gotv != expv)):
            if expa: expas = "" 
            else: expas = "no "
            if expv: expvs = "" 
            else: expvs = "no "
            if gota: gotas = "" 
            else: gotas = "no "
            if gotv: gotvs = "" 
            else: gotvs = "no "
            raise TranscoderError(("Expected %saudio and %svideo, "
                                   + "but got %saudio and %svideo")
                                   % (expas, expvs, gotas, gotvs),
                                   data=targetCtx)
        return result
        
    ### Called by Deferreds ###
    def __ebTargetIsNotAMedia(self, failure, targetCtx):
        # If stopping don't do anything
        if self._isStopping(): return
        raise TranscoderError(str(failure.value), data=targetCtx, cause=failure)
    
    ### Called by Deferreds ###
    def __cbTargetPerformPostProcessing(self, result, targetCtx):
        # If stopping don't do anything
        if self._isStopping(): return
        self._setTargetState(targetCtx, TargetStateEnum.postprocessing)
        targetCtx.debug("Performing target's post-processing for '%s'",
                        targetCtx.getOutputWorkPath())
        p = process.Process("post-process", 
                            targetCtx.config.postProcess, 
                            targetCtx)
        self._processes.append(p)
        vars = self._getPostProcessVars(targetCtx)
        #FIXME: Don't reference the global context
        timeout = self._context.config.postProcessTimeout
        targetCtx.reporter.startUsageMeasure("postprocess")
        d = p.execute(vars, timeout=timeout)
        d.addBoth(_stopMeasureCallback, targetCtx.reporter, "postprocess")
        d.addBoth(lambda r, e: self._processes.remove(e) or r, p)
        #Don't return Process result, but pass the received result
        d.addCallback(lambda state, res: res, result)
        return d

    ### Called by Deferreds ###
    def __cbTargetGenerateLinkFile(self, result, targetCtx):
        # If stopping don't do anything
        if self._isStopping(): return
        targetCtx.debug("Generating target's link file '%s'",
                        targetCtx.getLinkWorkPath())
        self._setTargetState(targetCtx, TargetStateEnum.link_file_generation)
        mimeType = targetCtx.reporter.report.analyse.mimeType
        if mimeType != 'application/ogg':
            raise TranscoderError("Target output not an ogg file, "
                                  + "not writing link", data=targetCtx)
        cortadoArgs = self._getCortadoArgs(targetCtx)
        cortadoArgString = "&".join("%s=%s" % (urllib.quote(str(k)), 
                                               urllib.quote(str(v)))
                                    for (k, v) in cortadoArgs.items())
        link = targetCtx.getLinkURL(cortadoArgString)
        templateVars = self._getLinkTemplateVars(targetCtx)
        templateVars.update(cortadoArgs)
        for k, v in templateVars.items():
            templateVars[k] = urllib.quote(str(v))
        templateVars["outputURL"] = link
        #FIXME: Don't reference the global context
        template = self._context.config.profile.linkTemplate % templateVars
        workPath = targetCtx.getLinkWorkPath()
        ensureDir(os.path.dirname(workPath), "temporary target link")
        handle = open(workPath, 'w')
        handle.write(template)
        handle.close()
        linkPath = targetCtx.getLinkFromWork(workPath)
        targetCtx.reporter.addFile(workPath, linkPath)
        return result
    
    ### Called by Deferreds ###
    def __ebTargetFailed(self, failure, targetCtx):
        # If stopping don't do anything
        if self._isStopping(): return
        targetCtx.warning("Target processing failed")
        self._fireTargetInfo(targetCtx)
        return failure
    
    ### Called by Deferreds ###
    def __cbTargetDone(self, result, targetCtx):
        # If stopping don't do anything
        if self._isStopping(): return
        targetCtx.debug("Target processing done")
        self._fireTargetInfo(targetCtx)
        self._setTargetState(targetCtx, TargetStateEnum.done)
        return result
    
    ### Called by Deferreds ###
    def __cbAllTargetsSucceed(self, result, context):
        # If stopping don't do anything
        if self._isStopping(): return
        context.debug("All Targets Processed Successfuly")
        return result
    
    ### Called by Deferreds ###
    def __ebSomeTargetsFailed(self, failure, context):
        # If stopping don't do anything
        if self._isStopping(): return
        context.debug("Some Targets Failed")
        #context.reporter.setFatalError(failure.getErrorMessage())
        return failure
