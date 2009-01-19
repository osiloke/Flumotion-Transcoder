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
import shutil
import urllib
import commands

import gobject
gobject.threads_init()
import gst

from twisted.internet import reactor, error, threads
from twisted.python.failure import Failure

from flumotion.common import common
from flumotion.common import enum

from flumotion.inhouse import process, log, defer, utils, fileutils
from flumotion.inhouse.errors import FlumotionError 

from flumotion.transcoder import enums 
from flumotion.transcoder.enums import TargetTypeEnum
from flumotion.transcoder.enums import JobStateEnum
from flumotion.transcoder.enums import TargetStateEnum
from flumotion.transcoder.errors import TranscoderError
from flumotion.component.transcoder import analyst, varsets, compconsts
from flumotion.component.transcoder import basetargets, transtargets, thumbtargets
from flumotion.component.transcoder.context import Context, TaskContext
from flumotion.component.transcoder.context import TargetContext
from flumotion.component.transcoder.transcoder import MediaTranscoder

#FIXME: get ride of having to set a TaskContext as TranscoderError data

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

    def onSyncReport(self, report):
        pass


def _stopMeasureCallback(result, reporter, measureName):
    """
    Helper callback to properly stop usage measurments.
    """
    reporter.stopUsageMeasure(measureName)
    return result


RunningState = enum.EnumClass('StopState', ('initializing', 'running', 
                                            'waiting', 'acknowledged',
                                            'terminated', 'stopped'))


class TranscodingJob(log.LoggerProxy):
    
    def __init__(self, logger, eventSink=None, pathAttr=None):
        log.LoggerProxy.__init__(self, logger)
        self._context = None
        self._moveInputFile = True
        self._processes = []
        self._eventSink = eventSink
        self._ack = None
        self._ackList = None
        self._readyForAck = None
        self._acknowledged = False
        self._analyst = analyst.MediaAnalyst()
        self._transcoder = None
        self._runningState = RunningState.initializing
        self._stopping = False
        self._stoppingDefer = None
        self._pathAttr = pathAttr

        
    ## Public Methods ##
    
    #FIXME: Should have a better way to expose context info
    def getTempReportPath(self):
        sourceCtx = self._context.getSourceContext()
        return sourceCtx.getTempReportPath()
    
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
        
        # Initialize some report data
        inputPath = sourceCtx.getInputPath()
        if os.path.exists(inputPath):
            # The input file size
            sourceCtx.reporter.report.fileSize = os.stat(inputPath).st_size
            # The input file type (with the file command)
            try:
                arg = utils.mkCmdArg(inputPath)
                fileType = commands.getoutput("file -bL" + arg)
            except Exception, e:
                fileType = "ERROR: %s" % str(e)
            sourceCtx.reporter.report.fileType = fileType

            try:
                machineName = commands.getoutput("hostname")
            except Exception, e:
                machineName = "ERROR: %s" % str(e)
            sourceCtx.reporter.report.machineName = machineName

            # The input file header
            try:
                inputFile = file(inputPath)
                try:
                    dump = fileutils.hexDump(inputFile, 8, 16)
                    for line in dump.split('\n'):
                        sourceCtx.reporter.report.fileHeader.append(line)
                finally:
                    inputFile.close()
            except:
                pass
        
        self._processes = []
        self._setJobState(JobStateEnum.starting)
        context.reporter.startUsageMeasure("job")
        
        d = defer.Deferred()
        d.addCallback(self.__cbAnalyseSourceFile, context)
        d.addErrback(self.__ebFatalFailure, context, "source analysis")
        if sourceCtx.config.preProcess:
            #Setup pre-processing
            d.addCallback(self.__cbPerformPreProcessing, context)
            d.addErrback(self.__ebFatalFailure, context, "pre-processing")
        #Setup transcoding
        d.addCallback(self.__cbInitiateTargetsProcessing, context)
        d.addErrback(self.__ebFatalFailure, context, "transcoding")
        #Setup target processing
        d.addCallback(self.__cbTargetsProcessed, context)
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
            if isinstance(result, Failure):
                self._readyForAck.errback(result)
            else:
                self._readyForAck.callback(result)
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
        utils.callNext(d.callback, None)
        self._runningState = RunningState.running
        return d
            
    def stop(self):
        self._context.info("Stopping transcoding job")
        self._setJobState(JobStateEnum.stopping)
        self._stopping = True
        # If already tell to stop, do nothing
        if self._stoppingDefer:
            return self._stoppingDefer
        # If the job has been acknowledged, wait until completion
        if self._runningState == RunningState.acknowledged:
            self._stoppingDefer = defer.Deferred()
            self._ackList.addBoth(self._stoppingDefer.callback)
        else:
            abortDefs = []
            # if there is a transcoder, try to abort it
            if self._transcoder:
                abortDefs.append(self._transcoder.abort())
            # if there is pending analysis, try to abort them
            abortDefs.append(self._analyst.abort())
            # if there is running process, try to abort them
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
        if self._acknowledged:
            self.warning("Transcoding job already acknowledged")
            return self._ackList
        #When acknowleged, the job cannot be stopped util completion
        self._acknowledged = True
        self._runningState = RunningState.acknowledged
        self._context.info("Transcoding job acknowledged")
        self._context.reporter.time("acknowledge")
        self._ack.callback(None)
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
        # The state is changed after the current processing chain terminate.
        utils.callNext(self._fireJobStateChanged, state)
        
    def _setTargetState(self, targetCtx, state):
        targetCtx.reporter.report.state = state
        self._fireTargetStateChanged(targetCtx, state)
        
    def _setLogName(self, name):
        if len(name) > 32:
            name = name[0:14] + "..." + name[-14:]
        self.logName = name

    def _transcoderProgressCallback(self, transcoder, percent):
        self._fireProgress(percent)

    def _transcoderPreparedCallback(self, transcoder, pipeline):
        try:
            #FIXME: Don't reference the global context
            context = self._context
            for transTarget in transcoder.getProducers():
                targetCtx = transTarget.getContext()
                info = transTarget.getPipelineInfo()
                targetCtx.reporter.updatePipelineInfo(info)
            self._fireSyncReport()
        except Exception, e:
            log.notifyException(context, e, "Exception during "
                                "transcoder initialization reporting")
    
    def _transcoderPlayingCallback(self, transcoder, pipeline):
        try:
            #FIXME: Don't reference the global context
            context = self._context
            targetsBins = {}
            for transTarget in transcoder.getProducers():
                targetCtx = transTarget.getContext()
                bins = transTarget.getBins()            
                if len(bins) > 0:
                    targetsBins[targetCtx.key] = bins
            context.reporter.crawlPipeline(pipeline, targetsBins)
            self._fireSyncReport()
        except Exception, e:
            log.notifyException(context, e,
                                "Exception during pipeline reporting")

    def _fireProgress(self, percent):
        if self._eventSink:
            self._eventSink.onProgress(percent)
    
    def _fireJobStateChanged(self, state):
        if self._eventSink:
            self._eventSink.onJobStateChanged(state)
    
    def _addAnalysisInfo(self, info, analysisData):
        if analysisData.mimeType != None:    
            info["mime-type"] = analysisData.mimeType
        if analysisData.hasVideo:
            info["video-size"] = (analysisData.videoWidth, 
                                  analysisData.videoHeight)
            info["video-rate"] = analysisData.videoRate
            info["video-encoder"] = analysisData.videoTags.get("encoder", None)
        if analysisData.hasAudio:
            info["audio-rate"] = analysisData.audioRate
            info["audio-encoder"] = analysisData.audioTags.get("encoder", None)
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
            info["targets"] = [t.label for t in config.targets.values()]
            self._eventSink.onJobInfo(info)
    
    def _fireSourceInfo(self, sourceCtx):
        if self._eventSink:
            info = {}
            duration = sourceCtx.reporter.getMediaDuration()
            if duration != None:
                info["duration"] = duration
            self._addAnalysisInfo(info, sourceCtx.reporter.report.analysis)
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
            self._addAnalysisInfo(info, targetCtx.reporter.report.analysis)            
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
    
    def _fireSyncReport(self):
        if self._eventSink:
            self._eventSink.onSyncReport(self._context.reporter.report)
    
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
    
    def __lookupContext(self, defaultContext, failure):
        """
        If the error has a context, use it inplace of the default one.
        """
        if failure and failure.value and isinstance(error, FlumotionError):
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
                          % (task, context.reporter.report.state.name))
            return failure
        context.reporter.addError(failure)
        errMsg = failure.getErrorMessage()
        context.reporter.setFatalError(errMsg)
        log.notifyFailure(context, failure, "Fatal error during %s", task)
        self._fireError(context, errMsg)
        if not failure.check(FlumotionError):
            raise TranscoderError(errMsg, data=context, cause=failure)
        return failure

    ### Called by Deferreds ###
    def __ebRecoverableFailure(self, failure, context, task, result=None):
        # If stopping don't do anything
        if self._isStopping(): return
        context = self.__lookupContext(context, failure)
        if context.reporter.hasFatalError():
            context.debug("Skipping %s because of fatal error during %s"
                         % (task, context.reporter.report.state.name))
            return failure
        context.reporter.addError(failure)
        warMsg = failure.getErrorMessage()
        log.notifyFailure(context, failure, "Recoverable error during %s", task)
        self._fireWarning(context, warMsg)
        # The error is resolved
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
        # If it failed, propagate the failure
        if isinstance(result, Failure):
            return result
        else:
            return context.reporter.report

    ### Called by Deferreds ###
    def __cbAnalyseSourceFile(self, result, context):
        # If stopping don't do anything
        if self._isStopping(): return
        context.debug("Analyzing source file")
        self._setJobState(JobStateEnum.analyzing)
        sourceCtx = context.getSourceContext()
        inputPath = sourceCtx.getInputPath()
        analyseTimeout = compconsts.SOURCE_ANALYSE_TIMEOUT
        d = self._analyst.analyse(inputPath, timeout=analyseTimeout)
        args = (context,)
        d.addCallbacks(self.__cbSourceFileAnalyzed,
                       self.__ebSourceFileNotAMedia,
                       callbackArgs=args, errbackArgs=args)
        return d
        
    ### Called by Deferreds ###
    def __cbSourceFileAnalyzed(self, analyse, context):
        sourceCtx = context.getSourceContext()
        sourceCtx.reporter.setMediaAnalysis(analyse)
        for desc in analyse.otherStreams:
            context.info("Source file contains unknown stream type : %s" 
                         % desc)
        self._fireSourceInfo(context.getSourceContext())
        self._fireSyncReport()
        return analyse
    
    ### Called by Deferreds ###
    def __ebSourceFileNotAMedia(self, failure, context):
        # If stopping don't do anything
        if self._isStopping(): return
        if failure.check(analyst.MediaAnalysisUnknownTypeError):
            raise TranscoderError("Source file is not a known media type",
                                  data=context, cause=failure)
        if failure.check(analyst.MediaAnalysisTimeoutError):
            raise TranscoderError("Source file analysis timeout",
                                  data=context, cause=failure)
        raise TranscoderError(str(failure.value),
                              data=context, cause=failure)


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
        vars = varsets.getPreProcessVars(context)
        context.reporter.startUsageMeasure("preprocess")
        d = p.execute(vars, timeout=context.config.preProcessTimeout)        
        d.addBoth(_stopMeasureCallback, context.reporter, "preprocess")
        d.addBoth(lambda r, e: self._processes.remove(e) or r, p)
        #Don't return Process result, but pass the received result
        d.addCallback(lambda state, res: res, result)
        return d

    _targetsLookup = {TargetTypeEnum.audio:      transtargets.AudioTarget,
                      TargetTypeEnum.video:      transtargets.VideoTarget,
                      TargetTypeEnum.audiovideo: transtargets.AudioVideoTarget,
                      TargetTypeEnum.thumbnails: thumbtargets.ThumbnailTarget,
                      TargetTypeEnum.identity:   basetargets.IdentityTarget}
    
    ### Called by Deferreds ###
    def __cbInitiateTargetsProcessing(self, sourceAnalysis, context):
        # If stopping don't do anything
        if self._isStopping(): return
        assert isinstance(sourceAnalysis, analyst.MediaAnalysis)
        sourceCtx = context.getSourceContext()
        context.debug("Transcoding source file '%s'", 
                      sourceCtx.getInputPath())
        self._setJobState(JobStateEnum.transcoding)
        transcoder = MediaTranscoder(self,
                                     preparedCB=self._transcoderPreparedCallback,
                                     playingCB=self._transcoderPlayingCallback,
                                     progressCB=self._transcoderProgressCallback)

        d = defer.succeed(None)
        targets = []
        for targetCtx in context.getTargetContexts():
            target = self._targetsLookup[targetCtx.config.type](targetCtx)
            if isinstance(target, basetargets.TranscodingTarget):
                transcoder.addProducer(target)
            elif isinstance(target, basetargets.TargetProcessing):
                # The processing targets like IdentityTarget
                # will be processed before starting the transcoder.
                d.addCallback(defer.dropResult, target.process)
            else:
                self.warning("Unknown target-processing class '%s'",
                             target.__class__.__name__)
                continue
            targets.append(target)
        
        d.addCallback(self.__cbStartupTranscoder, context, transcoder, sourceAnalysis)
        d.addCallback(defer.overrideResult, targets)
        return d
    
    ### Called by Deferreds ###
    def __cbStartupTranscoder(self, result, context, transcoder, sourceAnalysis):
        # If stopping don't do anything
        if self._isStopping(): return
        assert isinstance(sourceAnalysis, analyst.MediaAnalysis)
        sourceCtx = context.getSourceContext()
        context.reporter.startUsageMeasure("transcoding")
        stallTimeout = context.config.transcodingTimeout
        d = transcoder.start(sourceCtx.getInputPath(), sourceAnalysis,
                             timeout=stallTimeout)
        self._transcoder = transcoder
        d.addBoth(_stopMeasureCallback, context.reporter, "transcoding")
        d.addCallback(defer.overrideResult, result)
        return d
    
    ### Called by Deferreds ###
    def __cbTargetsProcessed(self, targets, context):
        # If stopping don't do anything
        if self._isStopping(): return
        context.debug("Transcoding done")
        self._setJobState(JobStateEnum.target_processing)
        d = defer.Deferred()
        for target in targets:
            targetCtx = target.getContext()
            for wp in target.getOutputFiles():
                op = targetCtx.getOutputFromWork(wp)
                targetCtx.reporter.addFile(wp, op)
            d.addCallback(self.__cbInitiateTargetPostProcessings, targetCtx)
        #Handle targets outcomes
        d.addCallback(self.__cbAllTargetsSucceed, context)
        d.addErrback(self.__ebSomeTargetsFailed, context)
        d.callback(None)
        return d

    ### Called by Deferreds ###
    def __cbInitiateTargetPostProcessings(self, result, targetCtx):
        # If stopping don't do anything
        if self._isStopping(): return
        targetCtx.info("Start target processing")
        d = defer.Deferred()
        if targetCtx.shouldBeAnalyzed():
            #Setup target output file analysis
            d.addCallback(self.__cbTargetAnalysisOutputFile, targetCtx)
            d.addErrback(self.__ebFatalFailure, targetCtx, "target analysis")
        if targetCtx.config.postProcess:
            #Setup target post-processing
            d.addCallback(self.__cbTargetPerformPostProcessing, targetCtx)
            d.addErrback(self.__ebFatalFailure, targetCtx, "post-processing")
        if targetCtx.shouldGenerateLinkFile():
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
        # The transcoding succeed if all deferred succeed
        result = True
        for success, result in results:
            result = result and success
        return result

    ### Called by Deferreds ###
    def __cbMoveOutputFiles(self, succeed, context):
        # If stopping don't do anything
        if self._isStopping(): return
        if succeed:
            context.debug("Moving output files")
            self._setJobState(JobStateEnum.output_file_moving)
            d = defer.succeed(context)
            for targetCtx in context.getTargetContexts():
                for src, dest in targetCtx.reporter.getFiles():
                    d.addCallback(self.__asyncMove, src, dest, self._pathAttr)
            d.addCallback(defer.overrideResult, succeed)
            return d
        else:
            context.debug("Skipping moving output files, "
                          "because transcoding fail")
            return succeed

    ### Called by Deferreds ###
    def __bbMoveInputFile(self, succeedOrFailure, context):
        """
        Can be called as a Callback or an Errback.
        If it's called with a non-failure parameter and its True,
        it will try to move the input file to the done folder.
        If it's called with a failure parameter or its False, 
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
        if isinstance(succeedOrFailure, Failure):
            #We are in an Errback
            error = succeedOrFailure
            succeed = False
        else:
            #We are in a Callback
            error = None
            succeed = succeedOrFailure
            
        def moveSource(dest, oldResult):
            src = sourceCtx.getInputPath()
            context.debug("Moving input file to '%s'", dest)
            d = self.__asyncMove(context, src, dest, self._pathAttr)
            d.addCallback(moveSucceed, dest, oldResult)
            return d

        def moveSucceed(_, path, oldResult):
            context.reporter.setCurrentPath(path)
            return oldResult

        def moveToDoneFailure(failure, otherDest):
            context.warning("Failed to move input file: %s", 
                            log.getFailureMessage(failure))
            context.reporter.addError(failure)
            context.reporter.setFatalError(failure.getErrorMessage())
            self._fireError(context, failure.getErrorMessage())
            d = moveSource(otherDest, failure)
            d.addErrback(totalFailure, failure)
            return d

        def totalFailure(failure, oldFailure):
            context.warning("Failed to move input file: %s", 
                            log.getFailureMessage(failure))
            context.reporter.addError(failure)
            self._fireError(context, failure.getErrorMessage())
            return oldFailure or failure

        if (not error) and succeed:
            d = defer.succeed(sourceCtx.getDoneInputPath())
            d.addCallback(moveSource, succeedOrFailure)
            d.addErrback(moveToDoneFailure, sourceCtx.getFailedInputPath())
            return d
        d = defer.succeed(sourceCtx.getFailedInputPath()) 
        d.addCallback(moveSource, succeedOrFailure)
        d.addErrback(totalFailure, error)
        return d

    ### Called by Deferreds ###
    def __cbTargetAnalysisOutputFile(self, result, targetCtx):
        # If stopping don't do anything
        if self._isStopping(): return
        targetCtx.debug("Analysing target output file '%s'",
                        targetCtx.getOutputWorkPath())
        self._setTargetState(targetCtx, TargetStateEnum.analyzing)
        
        outputPath = targetCtx.getOutputWorkPath()
        if os.path.exists(outputPath):
            targetCtx.reporter.report.fileSize = os.stat(outputPath).st_size
        self._fireSyncReport()
            
        targetCtx.reporter.startUsageMeasure("analysis")
        d = self._analyst.analyse(outputPath)
        d.addBoth(_stopMeasureCallback, targetCtx.reporter, "analysis")
        d.addCallbacks(self.__cbTargetIsAMedia, self.__ebTargetIsNotAMedia,
                       callbackArgs=(targetCtx,),
                       errbackArgs=(targetCtx,))
        return d
    
    ### Called by Deferreds ###
    def __cbTargetIsAMedia(self, analysis, targetCtx, result=None):
        # If stopping don't do anything
        if self._isStopping(): return
        targetCtx.reporter.setMediaAnalysis(analysis)
        self._fireTargetInfo(targetCtx)
        expa = targetCtx.shouldHaveAudio()
        expv = targetCtx.shouldHaveVideo()
        gota = analysis.hasAudio
        gotv = analysis.hasVideo
        
        if ((expa and (gota != expa)) or (expv and (gotv != expv))):
            expChunks = []
            gotChunks = []
            if expa != None:
                if expa: 
                    expChunks.append("audio")
                else: 
                    expChunks.append("no audio")
                if gota: 
                    gotChunks.append("audio stream")
                else: 
                    gotChunks.append("no audio stream")
            if expv != None:
                if expv: 
                    expChunks.append("video")
                else: 
                    expChunks.append("no video")
                if gotv: 
                    gotChunks.append("video stream")
                else: 
                    gotChunks.append("no video stream")
            message = ("Expected %s, and got %s" 
                       % (" and ".join(expChunks) or "nothing",
                          " and ".join(gotChunks) or "nothing"))
            raise TranscoderError(message, data=targetCtx)
        return result
        
    ### Called by Deferreds ###
    def __ebTargetIsNotAMedia(self, failure, targetCtx):
        # If stopping don't do anything
        if self._isStopping(): return
        if failure.check(analyst.MediaAnalysisUnknownTypeError):
            raise TranscoderError("Target '%s' output file is not a known "
                                  "media type"  % targetCtx.config.label,
                                  data=targetCtx, cause=failure)
        if failure.check(analyst.MediaAnalysisTimeoutError):
            raise TranscoderError("Target '%s' output file analysis timeout"
                                  % targetCtx.config.label,
                                  data=targetCtx, cause=failure)
        raise TranscoderError(str(failure.value),
                              data=targetCtx, cause=failure)
    
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
        vars = varsets.getPostProcessVars(targetCtx)
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
        mimeType = targetCtx.reporter.report.analysis.mimeType
        if mimeType != 'application/ogg':
            self.warning("Target output not an ogg file, "
                         "not writing link")
            return result
        cortadoArgs = varsets.getCortadoArgs(targetCtx)
        cortadoArgString = "&".join("%s=%s" % (urllib.quote(str(k)), 
                                               urllib.quote(str(v)))
                                    for (k, v) in cortadoArgs.items())
        link = targetCtx.getLinkURL(cortadoArgString)
        templateVars = varsets.getLinkTemplateVars(targetCtx)
        templateVars.update(cortadoArgs)
        for k, v in templateVars.items():
            templateVars[k] = urllib.quote(str(v))
        templateVars["outputURL"] = link
        #FIXME: Don't reference the global context
        template = self._context.config.profile.linkTemplate % templateVars
        workPath = targetCtx.getLinkWorkPath()
        fileutils.ensureDirExists(os.path.dirname(workPath),
                                  "temporary target link")
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
        self._fireSyncReport()
        return failure
    
    ### Called by Deferreds ###
    def __cbTargetDone(self, result, targetCtx):
        # If stopping don't do anything
        if self._isStopping(): return
        targetCtx.debug("Target processing done")
        self._fireTargetInfo(targetCtx)
        self._setTargetState(targetCtx, TargetStateEnum.done)
        self._fireSyncReport()
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

    def __asyncMove(self, logger, src, dest, pathAttr=None):
        logger.log("Moving '%s' to '%s'", src, dest)
        fileutils.ensureDirExists(os.path.dirname(dest), "", pathAttr)
        if os.path.exists(dest):
            logger.debug("Output file '%s' already exists; deleting it", dest)
        d = threads.deferToThread(shutil.move, src, dest)
        if pathAttr:
            d.addCallback(defer.dropResult, pathAttr.apply, dest)
        d.addCallback(defer.overrideResult, logger)
        return d
