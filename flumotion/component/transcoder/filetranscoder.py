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
import traceback

from StringIO import StringIO
from twisted.internet import reactor

from flumotion.component import component
from flumotion.component.component import moods
from flumotion.common.common import ensureDir
from flumotion.common import errors, messages

from flumotion.component.transcoder import job, compconsts
from flumotion.transcoder import properties, log
from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.enums import TranscoderStatusEnum
from flumotion.transcoder.enums import JobStateEnum
from flumotion.transcoder.transconfig import TranscodingConfig
from flumotion.transcoder.transreport import TranscodingReport
from flumotion.transcoder.inifile import IniFile
from flumotion.transcoder.virtualpath import VirtualPath
from flumotion.transcoder.local import Local

from flumotion.common.messages import N_
T_ = messages.gettexter('flumotion-transcoder')


class FileTranscoderMedium(component.BaseComponentMedium):
    
    def remote_acknowledge(self):
        self.comp.do_acknowledge()
        
    def remote_getReportPath(self):
        path = self.comp._getReportPath()
        if path:
            return str(path)
        return None
        

class FileTranscoder(component.BaseComponent, job.JobEventSink):
    
    componentMediumClass = FileTranscoderMedium
    logCategory = compconsts.TRANSCODER_LOG_CATEGORY


    ## Public Methods ##
    
    def do_acknowledge(self):
        self.onAcknowledged()
        d = self._job.acknowledge()
        d.addCallback(self.__cbJobTerminated)
        d.addErrback(self.__ebAcknowledgeError)
        return d

        
    ## Overriden Methods ##

    def init(self):
        log.setDefaultCategory(compconsts.TRANSCODER_LOG_CATEGORY)
        self.logName = None
        self._diagnoseMode = False
        self._waitAcknowledge = False
        self._job = job.TranscoderJob(self, self)
        self._report = None
        self._reportPath = None
        self._config = None
        self._local = None
        self.status = TranscoderStatusEnum.pending
        self.uiState.addDictKey('job-data', {})
        self.uiState.addDictKey('source-data', {})
        self.uiState.addDictKey('targets-data', {})
        self.uiState.setitem('job-data', "progress", 0.0)
        self.uiState.setitem('job-data', "job-state", JobStateEnum.pending)
        self.uiState.setitem('job-data', "acknowledged", False)
        self.uiState.setitem('job-data', "status", self.status)
        
    def do_setup(self):
        try:
            self._fireStatusChanged(TranscoderStatusEnum.setting_up)
            loader = IniFile()
            props = self.config["properties"]
            self._waitAcknowledge = props.get("wait-acknowledge", False)
            niceLevel = props.get("nice-level", None)
            #FIXME: Better checks for path roots
            self._local = Local.createFromComponentProperties(props)
            if props.has_key("config"):
                if props.has_key("report"):
                    raise Exception("Component properties 'config' "
                                    + "and 'report' should not be "
                                    + "specified at the same time")
                configPath = VirtualPath(props["config"])
                localConfigPath = configPath.localize(self._local)
                if not os.path.exists(localConfigPath):
                    raise Exception("Config file not found ('%s')" 
                                    % localConfigPath)
                self.debug("Loading configuration from '%s'", localConfigPath)
                self._config = TranscodingConfig()
                loader.loadFromFile(self._config, localConfigPath)
                self._report = TranscodingReport()
                self._report.init(self._config)
                self._report.configPath = configPath
                self._diagnoseMode = False
                self._job.setup(self._local, self._config, self._report, 
                                niceLevel=niceLevel)
            else:
                if props.has_key("report"):
                    reportPath = VirtualPath(props["report"])
                    localReportPath = reportPath.localize(self._local)
                    if not os.path.exists(localReportPath):
                        raise Exception("Report file not found ('%s')" 
                                        % localReportPath)
                    self.debug("Loading report from '%s'", localReportPath)
                    baseReport = TranscodingReport()
                    loader.loadFromFile(baseReport, reportPath)
                    configPath = baseReport.configPath
                    localConfigPath = configPath.localize(self._local)
                    if not os.path.exists(localConfigPath):
                        raise Exception("Config file not found ('%s')" 
                                        % localConfigPath)
                    self.debug("Loading configuration from '%s'", 
                               localConfigPath)
                    self._config = TranscodingConfig()
                    loader.loadFromFile(self._config, localConfigPath)
                    virtRepFilePath = baseReport.source.filePath
                    repFilePath = virtRepFilePath.localize(self._local)
                    virtConfInputFile = self._config.source.inputFile
                    confInputFile = virtConfInputFile.localize(self._local)
                    if not repFilePath.endswith(confInputFile):
                        raise Exception("The report source file-path property "
                                        + "doesn't match the configuration "
                                        + "source input-file property")
                    altInputDir = repFilePath[:-len(confInputFile)]
                    self._report = TranscodingReport()
                    self._report.init(self._config)
                    self._report.configPath = configPath
                    self.info("Entering diagnose mode")
                    self._diagnoseMode = True
                    self._job.setup(self._local, self._config, self._report,
                                    moveInputFile=False,
                                    altInputDir=altInputDir,
                                    niceLevel=niceLevel)
                else:
                    raise Exception("One of the component properties "
                                    + "'config' and 'report' "
                                    + "should be specified")
            return component.BaseComponent.do_setup(self)
        except Exception, e:
            self.warning("File transcoder component setup failed")
            self._logCurrentException()
            self.__abortTranscoding(e)
            raise errors.ComponentSetupHandledError(e)

    def do_start(self, *args, **kwargs):
        try:
            self._fireStatusChanged(TranscoderStatusEnum.working)
            d = self._job.start()
            d.addCallbacks(self.__cbJobDone, self.__ebJobFailed)
            return component.BaseComponent.do_start(self)
        except Exception, e:
            self.warning("File transcoder component startup failed")
            self._logCurrentException()
            self.__abortTranscoding(e)
            raise errors.ComponentStartHandledError(e)
            
    def do_stop(self, *args, **kwargs):
        try:            
            return self._job.stop()
        except Exception, e:
            self.warning("File transcoder component stopping failed")
            self._logCurrentException()
            self.__abortTranscoding(e)
            return component.BaseComponent.do_stop(self)

    
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
        if self._reportPath:
            virtPath = VirtualPath.virtualize(self._reportPath, self._local)
            return virtPath
        return None

    def _logCurrentException(self):
        if log.getCategoryLevel(self.logCategory) < log.DEBUG:
            return
        tb = StringIO()
        traceback.print_exc(file=tb)
        self.debug("Traceback with filenames cleaned up:\n%s", 
                   log.cleanTraceback(tb.getvalue()))
    
    def _fireStatusChanged(self, status):
        self.status = status
        self.uiState.setitem('job-data', "status", status)
        
    def _fireTranscodingReport(self, reportPath):
        virtPath = VirtualPath.virtualize(reportPath, self._local)
        self.uiState.setitem('job-data', "transcoding-report", str(virtPath))
        
    
    ## Private Methods ##
    
    def __abortTranscoding(self, e=None):
        self._fireStatusChanged(TranscoderStatusEnum.failed)
        if e:
            m = messages.Error(T_(str(e)), 
                               debug=log.getExceptionMessage(e))
            self.addMessage(m)
        else:
            self.setMood(moods.sad)
    
    def __cbJobDone(self, report):
        try:
            assert report == self._report, ("Job creates it's own report "
                                            + "instance. It's Baaaaad.")
            config = self._config
            # FIXME: Very ugly, should not ask the job for this
            self._reportPath = self._job.getDoneReportPath()
            self.__writeReport(report, self._reportPath)
            self._fireTranscodingReport(self._reportPath)
            self._fireStatusChanged(TranscoderStatusEnum.done)
            self.__finalize(report, True)
        except Exception, e:
            self.warning("Unexpected exception: %s", str(e))
            self._logCurrentException()
            self.__abortTranscoding(e)
        
    
    def __ebJobFailed(self, failure):
        try:
            config = self._config
            report = self._report
            if not failure.check(TranscoderError):
                m = messages.Error(T_(failure.getErrorMessage()),
                                   debug=log.getFailureMessage(failure))
                self.addMessage(m)
            # FIXME: Very ugly, should not ask the job for this
            self._reportPath = self._job.getFailedReportPath()
            self.__writeReport(report, self._reportPath)
            self._fireTranscodingReport(self._reportPath)
            self._fireStatusChanged(TranscoderStatusEnum.failed)
            self.__finalize(report, False)
        except Exception, e:
            self.warning("Unexpected exception: %s", str(e))
            self._logCurrentException()
            self.__abortTranscoding(e)

    def __cbJobTerminated(self, result):
        try:
            self.__writeReport(self._report, self._reportPath)
            return
        except Exception, e:
            self.warning("Unexpected exception: %s", str(e))
            self._logCurrentException()
            self.__abortTranscoding(e)

    def __ebAcknowledgeError(self, failure):
        try:
            self.warning("Transcoding acknowledge Error: %s",
                         log.getFailureMessage(failure))
            self._fireStatusChanged(TranscoderStatusEnum.failed)
            self.setMood(moods.sad)
            # FIXME: Very ugly, should not ask the job for this
            newReportPath = self._job.getFailedReportPath()
            if newReportPath != self._reportPath:
                self._reportPath = newReportPath
                self._fireTranscodingReport(self._reportPath)
            self.__writeReport(self._report, self._reportPath)
            return
        except Exception, e:
            self.warning("Unexpected exception: %s", str(e))
            self._logCurrentException()
            self.__abortTranscoding(e)

    def __writeReport(self, report, path):
        localPath = path # Already localized
        #if running in diagnose mode, don't overrite it
        if self._diagnoseMode:
            localPath = localPath + ".diag"
        self.debug("Writing report file '%s'", localPath)
        report.status = self.status
        ensureDir(os.path.dirname(localPath), "report")
        saver = IniFile()
        saver.saveToFile(report, localPath)
    
    def __finalize(self, report, succeed):
        if self._diagnoseMode:
            self.__finalizeDiagnoseMode(report, succeed)
        else:
            self.__finalizeStandardMode(report, succeed)
            
    def __finalizeDiagnoseMode(self, report, succeed):
        msg = ""
        if succeed:
            msg += "DONE"
        else:
            msg += "FAILED"
        fatal = 0
        if report.fatalError:
            fatal += 1
        total = len(report.errors)
        for t in report.targets:
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
        d = self.do_acknowledge()
        d.addBoth(lambda r: reactor.stop())
        
    def __finalizeStandardMode(self, report, succeed):
        if not succeed:
            self.setMood(moods.sad)
        if not self._waitAcknowledge:
            self.do_acknowledge()
