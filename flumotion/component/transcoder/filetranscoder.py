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

from twisted.internet import reactor
from twisted.python.failure import Failure

from flumotion.component import component
from flumotion.component.component import moods
from flumotion.common import errors, messages

from flumotion.component.transcoder import job, compconsts
from flumotion.transcoder import log, defer, constants, properties, utils
from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.errors import TranscoderConfigError
from flumotion.transcoder.enums import TranscoderStatusEnum
from flumotion.transcoder.enums import JobStateEnum
from flumotion.transcoder.transconfig import TranscodingConfig
from flumotion.transcoder.transreport import TranscodingReport
from flumotion.transcoder.properties import PropertyError
from flumotion.transcoder.inifile import IniFile
from flumotion.transcoder.virtualpath import VirtualPath
from flumotion.transcoder.local import Local

from flumotion.common.messages import N_
T_ = messages.gettexter('flumotion-transcoder')


class FileTranscoderMedium(component.BaseComponentMedium):
    
    def remote_getStatus(self):
        return self.comp.getStatus()
    
    def remote_acknowledge(self):
        return self.comp.do_acknowledge()
        
    def remote_getReportPath(self):
        return self.comp._getReportPath()
        

class FileTranscoder(component.BaseComponent, job.JobEventSink):
    
    componentMediumClass = FileTranscoderMedium
    logCategory = compconsts.TRANSCODER_LOG_CATEGORY


    ## Public Methods ##
    
    def getStatus(self):
        return self._status
    
    def do_acknowledge(self):
        self.onAcknowledged()
        d = self._job.acknowledge()
        d.addCallback(self.__cbJobTerminated)
        d.addErrback(self.__ebAcknowledgeError)
        return d

        
    ## Overriden Methods ##

    def init(self):
        log.setDefaultCategory(compconsts.TRANSCODER_LOG_CATEGORY)
        log.setDebugNotifier(self.__notifyDebug)
        self.logName = None
        self._diagnoseMode = False
        self._waitAcknowledge = False
        self._moveInputFile = True
        self._niceLevel = None
        self._job = None
        self._report = None
        self._reportDefaultPath = None
        self._reportForcedPath = None
        self._configPath = None
        self._config = None
        self._inputPath = None
        self._local = None
        self._status = TranscoderStatusEnum.pending
        self.uiState.addDictKey('job-data', {})
        self.uiState.addDictKey('source-data', {})
        self.uiState.addDictKey('targets-data', {})
        self.uiState.setitem('job-data', "progress", 0.0)
        self.uiState.setitem('job-data', "job-state", JobStateEnum.pending)
        self.uiState.setitem('job-data', "acknowledged", False)
        self.uiState.setitem('job-data', "status", self._status)
        
    def check_properties(self, props, addMessage):
        #TODO: Add directories/files right checks
        if props.has_key("config"):
            if props.has_key("diagnose"):
                msg = ("Component properties 'config' "
                       + "and 'diagnose' should not be "
                       + "specified at the same time")
                raise TranscoderConfigError(msg)
            local = Local.createFromComponentProperties(props)
            configPath = VirtualPath(props["config"])
            localConfigPath = configPath.localize(local)
            if not os.path.exists(localConfigPath):
                msg = "Config file '%s' not found" % localConfigPath
                raise TranscoderConfigError(msg)
        elif props.has_key("diagnose"):
            localReportPath = props["diagnose"]
            if not os.path.exists(localReportPath):
                msg = "Report file '%s' not found" % localReportPath
                raise TranscoderConfigError(msg)
        else:
            msg = ("One of the component properties "
                   + "'config' and 'diagnose' "
                   + "should be specified")
            raise TranscoderConfigError(msg)
        if props.has_key("report"):
            localRealPath = os.path.realpath(props["report"])
            localReportDir = os.path.dirname(localRealPath)
            if not os.path.exists(localReportDir):
                msg = "Output report directory '%s' not found" % localReportDir
                raise TranscoderConfigError(msg)
            
        
    def do_check(self):
        
        def transcoder_checks(result):
            # PyChecker doesn't like dynamic attributes
            __pychecker__ = "no-objattrs"
            props = self.config["properties"]
            #FIXME: Better checks for path roots
            self._waitAcknowledge = props.get("wait-acknowledge", False)
            self._moveInputFile = props.get("move-input-file", True)
            self._niceLevel = props.get("nice-level", None)
            localRepPath = props.get("report", None)
            self._reportForcedPath = localRepPath and os.path.realpath(localRepPath)
            if props.has_key("config"):
                self._local = Local.createFromComponentProperties(props)
                configPath = VirtualPath(props["config"])
                localConfigPath = configPath.localize(self._local)
                self.debug("Loading configuration from '%s'", 
                           localConfigPath)
                self._configPath = localConfigPath
                self._inputPath = None
                self._diagnoseMode = False
            else:
                localReportPath = props["diagnose"]
                self.debug("Loading report from '%s'", localReportPath)
                baseReport = TranscodingReport()
                loader = IniFile()
                loader.loadFromFile(baseReport, localReportPath)
                self.info("Using local '%s' from report file", 
                          baseReport.local.name)
                self._local = baseReport.local.getLocal()
                self._local.updateFromComponentProperties(props)
                configPath = baseReport.configPath
                localConfigPath = configPath.localize(self._local)
                if not os.path.exists(localConfigPath):
                    msg = "Config file not found ('%s')" % localConfigPath
                    raise TranscoderConfigError(msg)
                self._configPath = localConfigPath
                virtAltPath = baseReport.source.filePath
                self._inputPath = virtAltPath.localize(self._local)
                self._diagnoseMode = True
            return result
        
        try:
            self._fireStatusChanged(TranscoderStatusEnum.checking)
            d = component.BaseComponent.do_check(self)
            d.addCallback(transcoder_checks)
            d.addErrback(self.__ebErrorFilter, "component checking")
            return d
        except:
            self.__unexpectedError(task="component checks")
        
    def do_setup(self):
        
        def transcoder_setup(result):
            localConfigPath = self._configPath
            configPath = VirtualPath.virtualize(localConfigPath, self._local)
            self.debug("Loading configuration from '%s'", localConfigPath)
            
            self._config = TranscodingConfig()
            loader = IniFile()
            loader.loadFromFile(self._config, localConfigPath)
            
            if self._inputPath:
                confInputFile = self._config.source.inputFile
                if not self._inputPath.endswith(confInputFile):
                    raise Exception("The source file path "
                                    + "doesn't match the configuration "
                                    + "source input-file property")
                altInputDir = self._inputPath[:-len(confInputFile)]
            else:
                altInputDir=None
            
            self._report = TranscodingReport()
            self._report.init(self._config)
            self._report.configPath = configPath
            
            if not self._diagnoseMode:
                moveInputFile = self._moveInputFile
            else:
                self.info("Entering diagnose mode")
                moveInputFile = False
            
            self._job = job.TranscoderJob(self, self)
            self._job.setup(self._local, self._config, self._report,
                            moveInputFile=moveInputFile, 
                            altInputDir=altInputDir,
                            niceLevel=self._niceLevel)
            return result
        
        try:
            self._fireStatusChanged(TranscoderStatusEnum.setting_up)
            d = component.BaseComponent.do_setup(self)
            d.addCallback(transcoder_setup)
            d.addErrback(self.__ebErrorFilter, "component setup")
            return d
        except:
            self.__unexpectedError(task="component setup")

    def do_start(self, *args, **kwargs):
        
        def transcoder_start(result):
            d = self._job.start()
            d.addCallbacks(self.__cbJobDone, self.__ebJobFailed)
            return result
        
        try:
            self._fireStatusChanged(TranscoderStatusEnum.working)
            d = component.BaseComponent.do_start(self)
            d.addCallback(transcoder_start)
            d.addErrback(self.__ebErrorFilter, "component startup")
            return d
        except:
            self.__unexpectedError(task="component startup")
            
    def do_stop(self, *args, **kwargs):
        
        def component_stop(result):
            return component.BaseComponent.do_stop(self)

        try:
            if self._job:
                d = self._job.stop()
            else:
                d = defer.succeed(None)
            d.addCallback(component_stop)
            d.addErrback(self.__ebStopErrorFilter)
            return d
        except:
            self.__unexpectedError(task="component stopping")
    
    ## Overriden Methods ##
    
    def onJobInfo(self, info):
        for key, value in info.iteritems():
            self.uiState.setitem('job-data', key, value)
        
    def onAcknowledged(self):
        self.uiState.setitem('job-data', "acknowledged", True)

    def onJobError(self, error):
        self.uiState.setitem('job-data', "job-error", error)
    
    def onJobWarning(self, warning):
        self.uiState.setitem('job-data', "job-warning", warning)

    def onProgress(self, percent):
        self.uiState.setitem('job-data', "progress", percent)
    
    def onJobStateChanged(self, state):
        self.uiState.setitem('job-data', "job-state", state)
    
    def onSourceInfo(self, info):
        inputFile = info["input-file"]
        virtFile = VirtualPath.virtualize(inputFile, self._local)
        info["input-file"] = str(virtFile)
        for key, value in info.iteritems():
            self.uiState.setitem('source-data', key, value)
    
    def onTargetStateChanged(self, label, state):
        self.uiState.setitem('targets-data', (label, "target-state"), state)
    
    def onTargetInfo(self, label, info):
        for key, value in info.iteritems():
            self.uiState.setitem('targets-data', (label, key), value)

    def onTargetError(self, label, error):
        self.uiState.setitem('targets-data', (label, "target-error"), error)
    
    def onTargetWarning(self, label, warning):
        self.uiState.setitem('targets-data', (label, "target-warning"), warning)


    ## Protected/Friend Methods ##

    def _getReportPath(self):
        if self._reportDefaultPath:
            virtPath = VirtualPath.virtualize(self._reportDefaultPath,
                                              self._local)
            return virtPath
        return None

    def _fireStatusChanged(self, status):
        self._status = status
        self.uiState.setitem('job-data', "status", status)
        
    def _fireTranscodingReport(self, reportPath):
        virtPath = VirtualPath.virtualize(reportPath, self._local)
        self.uiState.setitem('job-data', "transcoding-report", virtPath)
        
    
    ## Private Methods ##
    
    def __notifyDebug(self, msg, info=None, debug=None,
                      failure=None, exception=None):
        infoMsg = ["File Transcoder Debug Notification: %s" % msg]
        debugMsg = []
        if info:
            infoMsg.append("Information:\n\n%s" % info)
        if debug:
            debugMsg.append("Additional Debug Info:\n\n%s" % debug)
        if failure:
            debugMsg.append("Failure Message: %s\nFailure Traceback:\n%s"
                            % (log.getFailureMessage(failure),
                               log.getFailureTraceback(failure)))
        if exception:
            debugMsg.append("Exception Message: %s\n\nException Traceback:\n%s"
                            % (log.getExceptionMessage(exception),
                               log.getExceptionTraceback(exception)))
        m = messages.Warning(T_("\n\n".join(infoMsg)),
                             debug="\n\n".join(debugMsg))
        self.addMessage(m)
    
    def __ebErrorFilter(self, failure, task=None):
        if failure.check(TranscoderError, PropertyError):
            return self.__transcodingError(failure, task)
        return self.__unexpectedError(failure, task)

    def __ebStopErrorFilter(self, failure):
        self.__unexpectedError(failure)
        return component.BaseComponent.do_stop(self)
    
    def __transcodingError(self, failure=None, task=None):
        self._fireStatusChanged(TranscoderStatusEnum.error)
        if not failure:
            failure = Failure()
        self.onJobError(failure.getErrorMessage())
        log.notifyFailure(self, failure,
                          "Transocding error%s",
                          (task and " during %s" % task) or "", 
                          cleanTraceback=True)
        self.setMood(moods.sad)
        return failure
        
    def __unexpectedError(self, failure=None, task=None):
        self._fireStatusChanged(TranscoderStatusEnum.unexpected_error)
        if not failure:
            failure = Failure()
        self.onJobError(failure.getErrorMessage())
        log.notifyFailure(self, failure,
                          "Unexpected error%s",
                          (task and " during %s" % task) or "", 
                          cleanTraceback=True)
        m = messages.Error(T_(failure.getErrorMessage()), 
                           debug=log.getFailureMessage(failure))
        self.addMessage(m)
        return failure
    
    def __cbJobDone(self, report):
        try:
            assert report == self._report, ("Job creates it's own report "
                                            + "instance. It's Baaaaad.")
            # FIXME: Very ugly, should not ask the job for this
            self._reportDefaultPath = self._job.getDoneReportPath()
            self.__writeReport(report)
            self._fireTranscodingReport(self._reportDefaultPath)
            self._fireStatusChanged(TranscoderStatusEnum.done)
            self.__finalize(report, True)
        except Exception, e:
            log.notifyException(self, e,
                                "Unexpected exception",
                                cleanTraceback=True)
            self.__unexpectedError()
        
    
    def __ebJobFailed(self, failure):
        try:
            report = self._report
            if not failure.check(TranscoderError):
                m = messages.Error(T_(failure.getErrorMessage()),
                                   debug=log.getFailureMessage(failure))
                self.addMessage(m)
            # FIXME: Very ugly, should not ask the job for this
            self._reportDefaultPath = self._job.getFailedReportPath()
            self.__writeReport(report)
            self._fireTranscodingReport(self._reportDefaultPath)
            self._fireStatusChanged(TranscoderStatusEnum.failed)
            self.__finalize(report, False)
        except Exception, e:
            log.notifyException(self, e,
                                "Unexpected exception",
                                cleanTraceback=True)
            self.__unexpectedError()

    def __cbJobTerminated(self, result):
        try:
            self.__writeReport(self._report)
            self.__terminate(self._report, self._status)
            # Acknowledge return the transcoding status
            return self._status
        except Exception, e:
            log.notifyException(self, e,
                                "Unexpected exception",
                                cleanTraceback=True)
            self.__unexpectedError()
            # Reraise for the do_acknowledge call to return the failure
            raise e

    def __ebAcknowledgeError(self, failure):
        try:
            self.warning("Transcoding acknowledge Error: %s",
                         log.getFailureMessage(failure))
            self._fireStatusChanged(TranscoderStatusEnum.failed)
            self.setMood(moods.sad)
            # FIXME: Very ugly, should not ask the job for this
            newReportPath = self._job.getFailedReportPath()
            if newReportPath != self._reportDefaultPath:
                self._reportDefaultPath = newReportPath
                self._fireTranscodingReport(self._reportDefaultPath)
            self.__writeReport(self._report)
            self.__terminate(self._report, self._status)
            return failure
        except Exception, e:
            log.notifyException(self, e,
                                "Unexpected exception", 
                                cleanTraceback=True)
            self.__unexpectedError()
            # Reraise for the do_acknowledge call to return the failure
            raise e

    def __writeReport(self, report):
        if self._reportForcedPath:
            reportPath = self._reportForcedPath
        else:
            reportPath = self._reportDefaultPath
            #if running in diagnose mode, don't overrite it
            if self._diagnoseMode:
                reportPath = reportPath + ".diag"
        self.debug("Writing report file '%s'", reportPath)
        report.status = self._status
        utils.ensureDirExists(os.path.dirname(reportPath), "report")
        saver = IniFile()
        saver.saveToFile(report, reportPath)
    
    def __finalize(self, report, succeed):
        if self._diagnoseMode:
            self.__finalizeDiagnoseMode(report, succeed)
        else:
            self.__finalizeStandardMode(report, succeed)
            
    def __finalizeDiagnoseMode(self, report, succeed):
        self.info("Automatic acknowledgement")
        d = self.do_acknowledge()
        d.addErrback(self.__ebDiagnoseAcknowledgeFail)
        
    def __ebDiagnoseAcknowledgeFail(self, failure):
        log.notifyFailure(self, failure,
                          "Acknowledgment failed",
                          cleanTraceback=True)
        utils.callNext(reactor.stop)
        
    def __finalizeStandardMode(self, report, succeed):
        if not succeed:
            self.setMood(moods.sad)
        if not self._waitAcknowledge:
            self.do_acknowledge()

    def __terminate(self, report, status):
        if self._diagnoseMode:
            self.__terminateDiagnoseMode(report, status)
        else:
            self.__terminateStandardMode(report, status)
            
    def __terminateDiagnoseMode(self, report, status):
        msg = ""
        msg += status.nick.upper()
        fatal = 0
        if report.fatalError:
            fatal += 1
        total = len(report.errors)
        for t in report.targets.values():
            if not t:
                continue
            if t.fatalError:
                fatal += 1
            total += len(t.errors)
        if fatal > 0:
            msg += " ** %d Fatal Error(s)" % fatal
        if total > fatal:
            msg += " ** %d Recoverable Error(s)" % (total - fatal)
        self.info("*"*6 + " " + msg + " " + "*"*6)
        utils.callNext(reactor.stop)
        
    def __terminateStandardMode(self, report, succeed):
        pass
