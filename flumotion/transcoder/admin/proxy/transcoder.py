# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import os

from zope.interface import implements

from flumotion.inhouse import utils, inifile, log, defer
from flumotion.inhouse.waiters import AssignWaiters

from flumotion.transcoder.transreport import TranscodingReport
from flumotion.transcoder.enums import TranscoderStatusEnum
from flumotion.transcoder.enums import JobStateEnum
from flumotion.transcoder.virtualpath import VirtualPath
from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.admin.enums import DocumentTypeEnum
from flumotion.transcoder.admin.document import FileDocument
from flumotion.transcoder.admin.proxy import base, component
from flumotion.transcoder.admin.property import filetrans


class ITranscoderProxy(base.IProxy):
    pass


class TranscoderProxy(component.ComponentProxy):
    implements(ITranscoderProxy)

    properties_factory = filetrans.TranscoderProperties
    
    @classmethod
    def loadTo(cls, workerPxy, name, label, properties, timeout=None):
        managerPxy = workerPxy.getManagerProxy()
        atmoPxy = managerPxy.getAtmosphereProxy()
        assert atmoPxy != None
        return atmoPxy._loadComponent('file-transcoder', 
                                      name,  label, workerPxy, 
                                      properties, timeout)
    
    
    def __init__(self, logger, parentPxy, identifier,
                 managerPxy, compCtx, compState, domain):
        component.ComponentProxy.__init__(self, logger, parentPxy, 
                                          identifier, managerPxy,
                                          compCtx, compState, domain)
        self._reportPath = AssignWaiters("Transcoder report")
        # Registering Events
        self._register("progress")
        self._register("status-changed")
        self._register("job-state-changed")

        
    ## Public Methods ##
    
    def getTranscoderProgress(self):
        return self._getUIDictValue("job-data", "progress", 0.0)
    
    def waitTranscoderProgress(self, timeout=None):
        return self._waitUIDictValue("job-data", "progress", 0.0, timeout)
    
    def getStatus(self):
        return self._getUIDictValue("job-data", "status", 
                                    TranscoderStatusEnum.pending)
        
    def waitStatus(self, timeout=None):
        """
        Wait status do not use the UI State, because in some early
        error cases the UI State cannot be retrieved.
        """
        return utils.callWithTimeout(timeout, self._callRemote, "getStatus")
    
    def getJobState(self):
        return self._getUIDictValue("job-data", "job-state", 
                                    JobStateEnum.pending)
        
    def waitJobState(self, timeout=None):
        return self._waitUIDictValue("job-data", "job-state", 
                                     JobStateEnum.pending, timeout)

    def isAcknowledged(self):
        return self._getUIDictValue("job-data", "acknowledged", False)

    def waitIsAcknowledged(self, timeout=None):
        return self._waitUIDictValue("job-data", "acknowledged", 
                                     False, timeout)

    def getReportPath(self):
        return self._reportPath.getValue()
    
    def retrieveReportPath(self, timeout=None, retry=1):
        virtPath = self._reportPath.getValue()
        if self.isRunning():
            return self.__retrieveReportPath(virtPath, timeout, retry)
        return defer.succeed(virtPath) 
    
    def getReport(self):
        return self.__loadReport(self.__getLocalReportPath())
    
    def retrieveReport(self, timeout=None, retry=1):
        virtPath = self._reportPath.getValue()
        if self.isRunning():
            d = self.__retrieveReportPath(virtPath, timeout, retry)
        else:
            d = defer.succeed(virtPath)
        d.addCallback(self.__localizeReportPath)
        d.addCallback(self.__loadReport)
        return d
    
    def waitReport(self, timeout=None):
        # Prevent blocking if not running and no report path has been received
        if self.isRunning():
            d = self._reportPath.wait(timeout)
        else:
            d = defer.succeed(self.__getLocalReportPath())
        d.addCallback(self.__loadReport)
        return d
    
    def getDocuments(self):
        docs = []
        path = self.__getConfigPath()
        if path:
            doc = self.__wrapDocument(path, DocumentTypeEnum.trans_config)
            docs.append(doc)
        path = self.__getLocalReportPath()
        if path:
            doc = self.__wrapDocument(path, DocumentTypeEnum.trans_report)
            docs.append(doc)
        return docs
    
    def acknowledge(self, timeout=None):
        return utils.callWithTimeout(timeout, self._callRemote, "acknowledge")        


    ## Overriden Methods ##
    
    _handlerLookup = {"job-data":
                      {"progress":  ("_onTranscoderProgress", None, 0.0),
                       "status":    ("_onTranscoderStatusChanged", None, 
                                     TranscoderStatusEnum.pending),
                       "job-state": ("_onTranscoderJobStateChanged", None, 
                                     JobStateEnum.pending),
                       "transcoding-report": ("_onTranscodingReport", 
                                              None, None)}}
    
    def _doBroadcastUIState(self, uiState):
        for key, handlers in self._handlerLookup.iteritems():
            keyState = uiState.get(key, None)
            for subkey, handler in handlers.iteritems():
                if not handler[0]:
                    continue
                if (not (subkey in keyState)) or (keyState == None):
                    if handler[2] != None:
                        getattr(self, handler[0])(handlers[2])
                else:
                    getattr(self, handler[0])(keyState.get(subkey))
    
    def _onUIStateSet(self, uiState, key, value):
        self.log("Transcoder UI State '%s' set to '%s'", key, value)
    
    def _onUIStateAppend(self, uiState, key, value):
        self.log("Transcoder UI State '%s' value '%s' appened", key, value)
    
    def _onUIStateRemove(self, uiState, key, value):
        self.log("Transcoder UI State '%s' value '%s' removed", key, value)
    
    def _onUIStateSetitem(self, uiState, key, subkey, value):
        self.log("Transcoder UI State '%s' item '%s' set to '%s'", 
                 key, subkey, value)
        handlers = self._handlerLookup.get(key, None)
        if handlers:
            handler = handlers.get(subkey, None)
            if handler and handler[0]:
                getattr(self, handler[0])(value)
    
    def _onUIStateDelitem(self, uiState, key, subkey, value):
        self.log("Transcoder UI State '%s' item '%s' deleted", 
                 key, subkey)
        handlers = self._handlerLookup.get(key, None)
        if handlers:
            handler = handlers.get(key, None)
            if handler and handler[1]:
                getattr(self, handler[1])(value)

    
    ## UI State Handlers Methods ##
    
    def _onTranscoderProgress(self, percent):
        self.emit("progress", percent)

    def _onTranscoderStatusChanged(self, status):
        self.emit("status-changed", status)

    def _onTranscoderJobStateChanged(self, state):
        self.emit("job-state-changed", state)

    def _onTranscodingReport(self, reportVirtPath):
        self._reportPath.setValue(reportVirtPath or None)

    
    ## Private Methodes ##
    
    def __updateReportPath(self, virtPath):
        self._reportPath.setValue(virtPath)
        return virtPath
    
    def __getLocalReportPath(self):
        virtPath = self._reportPath.getValue()
        return self.__localizeReportPath(virtPath)
    
    def __localizeReportPath(self, virtPath):
        if not virtPath: return None
        compCtx = self.getComponentContext()
        adminCtx = compCtx.getAdminContext()
        local = adminCtx.getLocal()
        return virtPath.localize(local)
    
    def __getConfigPath(self):
        virtPath = self.getProperties().getConfigPath()
        if not virtPath:
            return None
        compCtx = self.getComponentContext()
        adminCtx = compCtx.getAdminContext()
        local = adminCtx.getLocal()
        return virtPath.localize(local)
        
    def __wrapDocument(self, localPath, type):
        return FileDocument(type, os.path.basename(localPath),
                            localPath, "plain/text")
    
    def __retrieveReportPath(self, virtPath, timeout, retry):
        assert timeout is None, "Timeout not supported yet"
        localPath = self.__localizeReportPath(virtPath)
        if not localPath: return defer.succeed(None)
        if not os.path.exists(localPath):
            # Maybe the file has been moved, so we retry
            if retry > 0:
                d = self._callRemote("getReportPath")
                d.addCallback(self.__updateReportPath)
                d.addCallback(self.__retrieveReportPath, timeout, retry - 1)
                return d
        return defer.succeed(virtPath)
    
    def __loadReport(self, localPath):
        if not localPath:
            return None
        if not os.path.exists(localPath):
            message = ("Transcoder report file not found ('%s')" % localPath)
            self.warning("%s", message)
            raise TranscoderError(message)
        loader = inifile.IniFile()
        report = TranscodingReport()
        try:
            loader.loadFromFile(report, localPath)
        except Exception, e:
            message = ("Failed to load transcoder report file '%s': %s"
                       % (localPath, log.getExceptionMessage(e)))
            self.warning("%s", message)
            raise TranscoderError(message)
        return report


component.registerProxy("file-transcoder", TranscoderProxy)
