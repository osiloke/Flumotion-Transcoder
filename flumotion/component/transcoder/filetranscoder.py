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
from flumotion.common.common import ensureDir
from flumotion.common import errors, messages
from flumotion.common import log as flog
from flumotion.component.component import moods
from flumotion.component.transcoder import job
from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.enums import TranscoderStatusEnum
from flumotion.transcoder import properties, log, enums
from flumotion.transcoder.jobconfig import JobConfig
from flumotion.transcoder.jobreport import JobReport
from flumotion.transcoder.inifile import IniFile


from flumotion.common.messages import N_
T_ = messages.gettexter('flumotion-transcoder')


class FileTranscoderMedium(component.BaseComponentMedium):
    pass


class FileTranscoder(component.BaseComponent, job.JobEventSink):
    
    componentMediumClass = FileTranscoderMedium
    logCategory = 'file-trans'


    ## Public Methods ##
    
    def do_acknowledge(self):
        d = self._job.acknowledge()
        d.addCallback(self.__jobTerminated)
        d.addErrback(self.__acknowledgeError)
        return d

        
    ## Overriden Methods ##

    def init(self):
        self.logName = None
        self._diagnoseMode = False
        self._job = job.TranscoderJob(self, self)
        self._report = None
        self._reportPath = None
        self._config = None
        self.uiState.addDictKey('job-data', {})
        self.uiState.addDictKey('source-data', {})
        self.uiState.addDictKey('targets-data', {})
        self.uiState.setitem('job-data', "progress", 0.0)
        self.uiState.setitem('job-data', "state", "initializing")
        
    def do_setup(self):
        try:
            self._fireStatusChanged(TranscoderStatusEnum.setting_up)
            loader = IniFile()
            props = self.config["properties"]
            niceLevel = props.get("nice-level", None)
            if props.has_key("config"):
                if props.has_key("report"):
                    raise Exception("Component properties 'config' "
                                    + "and 'report' should not be "
                                    + "specified at the same time")
                configPath = props["config"]
                if not os.path.exists(configPath):
                    raise Exception("Config file not found ('%s')" % configPath)
                self.debug("Loading configuration from '%s'", configPath)
                self._config = JobConfig()
                loader.loadFromFile(self._config, configPath)
                self._report = JobReport()
                self._report.init(self._config)
                self._report.configPath = configPath
                self._diagnoseMode = False
                self._job.setup(self._config, self._report, 
                                niceLevel=niceLevel)
            else:
                if props.has_key("report"):
                    reportPath = props["report"]
                    if not os.path.exists(reportPath):
                        raise Exception("Report file not found ('%s')" % reportPath)
                    self.debug("Loading report from '%s'", reportPath)
                    baseReport = JobReport()
                    loader.loadFromFile(baseReport, reportPath)
                    configPath = baseReport.configPath
                    if not os.path.exists(configPath):
                        raise Exception("Config file not found ('%s')" % configPath)
                    self.debug("Loading configuration from '%s'", configPath)
                    self._config = JobConfig()
                    loader.loadFromFile(self._config, configPath)
                    repFilePath = baseReport.source.filePath
                    confInputFile = self._config.source.inputFile
                    if not repFilePath.endswith(confInputFile):
                        raise Exception("The report source file-path property "
                                        + "doesn't match the configuration "
                                        + "source input-file property")
                    altInputDir = repFilePath[:-len(confInputFile)]
                    self._report = JobReport()
                    self._report.init(self._config)
                    self._report.configPath = configPath
                    self.info("Entering diagnose mode")
                    self._diagnoseMode = True
                    self._job.setup(self._config, self._report,
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
            m = messages.Error(T_(str(e)), 
                               debug=log.getExceptionMessage(e))
            self.addMessage(m)
            self.setMood(moods.sad)
            raise errors.ComponentSetupHandledError(e)

    def do_start(self, *args, **kwargs):
        try:
            self._fireStatusChanged(TranscoderStatusEnum.working)
            d = self._job.start()
            d.addCallbacks(self.__jobDone, self.__jobFailed)
            return component.BaseComponent.do_start(self)
        except Exception, e:
            self.warning("File transcoder component startup failed")
            self._logCurrentException()
            m = messages.Error(T_(str(e)), 
                               debug=log.getExceptionMessage(e))
            self.addMessage(m)
            self.setMood(moods.sad)
            raise errors.ComponentStartHandledError(e)
            
    def do_stop(self, *args, **kwargs):
        try:            
            return self._job.stop()
        except Exception, e:
            self.warning("File transcoder component stopping failed")
            self._logCurrentException()
            m = messages.Error(T_(str(e)), 
                               debug=log.getExceptionMessage(e))
            self.addMessage(m)
            return component.BaseComponent.do_stop(self)

    
    ## Overriden Methods ##
    
    def onJobInfo(self, info):
        for key, value in info.iteritems():
            self.uiState.setitem('job-data', key, value)

    def onJobError(self, error):
        self.uiState.setitem('job-data', "job-error", error)
    
    def onJobWarning(self, warning):
        self.uiState.setitem('job-data', "job-warning", warning)

    def onProgress(self, percent):
        self.uiState.setitem('job-data', "progress", percent)
    
    def onJobStateChanged(self, state):
        self.uiState.setitem('job-data', "job-state", state)
    
    def onSourceInfo(self, info):
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

    def _logCurrentException(self):
        if flog.getCategoryLevel(self.logCategory) < flog.DEBUG:
            return
        tb = StringIO()
        traceback.print_exc(file=tb)
        self.debug("Traceback with filenames cleaned up:\n%s" 
                   % log.cleanTraceback(tb.getvalue()))
    
    def _fireStatusChanged(self, status):
        self.uiState.setitem('job-data', "status", status)
        
    def _fireTranscodingReport(self, reportPath):
        self.uiState.setitem('job-data', "transcoding-report", reportPath)
        
    
    ## Private Methods ##
    
    def __jobDone(self, report):
        try:
            assert report == self._report, ("Job creates it's own report "
                                            + "instance. It's Baaaaad.")
            config = self._config
            self._reportPath = self._job.getDoneReportPath()
            self.__writeReport(report, self._reportPath)
            self._fireTranscodingReport(self._reportPath)
            self._fireStatusChanged(TranscoderStatusEnum.done)
            self.__finalize(report, True)
        except Exception, e:
            self.warning("Unexpected exception: %s", str(e))
            self._logCurrentException()
            m = messages.Error(T_(str(e)), 
                               debug=log.getExceptionMessage(e))
            self.addMessage(m)
        
    
    def __jobFailed(self, failure):
        try:
            config = self._config
            report = self._report
            if not failure.check(TranscoderError):
                m = messages.Error(T_(failure.getErrorMessage()),
                                   debug=log.getFailureMessage(failure))
                self.addMessage(m)
            self._reportPath = self._job.getFailedReportPath()
            self.__writeReport(report, self._reportPath)
            self._fireTranscodingReport(self._reportPath)
            self._fireStatusChanged(TranscoderStatusEnum.failed)
            self.__finalize(report, False)
        except Exception, e:
            self.warning("Unexpected exception: %s", str(e))
            self._logCurrentException()
            m = messages.Error(T_(str(e)), 
                               debug=log.getExceptionMessage(e))

    def __jobTerminated(self, result):
        try:
            self.__writeReport(self._report, self._reportPath)
            return
        except Exception, e:
            self.warning("Unexpected exception: %s", str(e))
            self._logCurrentException()
            m = messages.Error(T_(str(e)), 
                               debug=log.getExceptionMessage(e))
            self.addMessage(m)

    def __acknowledgeError(self, failure):
        try:
            self.warning("Transcoding Acknowledge Error: %s",
                         log.getFailureMessage(failure))
            newReportPath = self._job.getFailedReportPath()
            if newReportPath != self._reportPath:
                self._reportPath = newReportPath
                self._fireTranscodingReport(self._reportPath)
            self.__writeReport(self._report, self._reportPath)
            return
        except Exception, e:
            self.warning("Unexpected exception: %s", str(e))
            self._logCurrentException()
            m = messages.Error(T_(str(e)), 
                               debug=log.getExceptionMessage(e))
            self.addMessage(m)

    def __writeReport(self, report, path):
        #if running in diagnose mode, don't overrite it
        if self._diagnoseMode:
            path = path + ".diag"
        self.debug("Writing report file '%s'", path)
        try:
            ensureDir(os.path.dirname(path), "report")
            saver = IniFile()
            saver.saveToFile(report, path)
        except properties.PropertyError, e:
            self.warning("Failed to write report; %s"
                         % log.getExceptionMessage(e))

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
        pass


