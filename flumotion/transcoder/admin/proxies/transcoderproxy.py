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

from flumotion.transcoder import utils, inifile, log
from flumotion.transcoder.transreport import TranscodingReport
from flumotion.transcoder.enums import TranscoderStatusEnum
from flumotion.transcoder.enums import JobStateEnum
from flumotion.transcoder.virtualpath import VirtualPath
from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.admin.proxies.componentproxy import registerProxy
from flumotion.transcoder.admin.proxies.componentproxy import IComponentListener
from flumotion.transcoder.admin.proxies.componentproxy import ComponentListener
from flumotion.transcoder.admin.proxies.componentproxy import ComponentProxy
from flumotion.transcoder.admin.transprops import TranscoderProperties


class ITranscoderListener(IComponentListener):
    def onTranscoderProgress(self, transcoder, percent):
        pass
    
    def onTranscoderStatusChanged(self, transcoder, status):
        pass
    
    def onTranscoderJobStateChanged(self, transcoder, jobState):
        pass


class TranscoderListener(ComponentListener):
    
    implements(ITranscoderListener)
    
    def onTranscoderProgress(self, transcoder, percent):
        pass
    
    def onTranscoderStatusChanged(self, transcoder, status):
        pass

    def onTranscoderJobStateChanged(self, transcoder, jobState):
        pass


class TranscoderProxy(ComponentProxy):

    properties_factory = TranscoderProperties
    
    @classmethod
    def loadTo(cls, worker, name, label, properties, timeout=None):
        manager = worker.getParent()
        atmosphere = manager.getAtmosphere()
        return atmosphere._loadComponent('file-transcoder', 
                                         name,  label, worker, 
                                         properties, timeout)
    
    
    def __init__(self, logger, parent, identifier, manager, 
                 componentContext, componentState, domain):
        ComponentProxy.__init__(self, logger, parent, 
                                identifier, manager,
                                componentContext, 
                                componentState, domain,
                                ITranscoderListener)
    
        
    ## Public Methods ##
    
    def getTranscoderProgress(self):
        return self._getUIDictValue("job-data", "progress", 0.0)
    
    def waitTranscoderProgress(self, timeout=None):
        return self._waitUIDictValue("job-data", "progress", 0.0, timeout)
    
    def getStatus(self):
        return self._getUIDictValue("job-data", "status", 
                                    TranscoderStatusEnum.pending)
        
    def waitStatus(self, timeout=None):
        return self._waitUIDictValue("job-data", "status", 
                                     TranscoderStatusEnum.pending,
                                     timeout)
    
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
    
    def getReport(self, timeout=None):
        d = utils.callWithTimeout(timeout, self._callRemote, "getReportPath")
        d.addCallback(self.__cbLoadReport)
        return d
    
    def acknowledge(self, timeout=None):
        return utils.callWithTimeout(timeout, self._callRemote, "acknowledge")        


    ## Overriden Methods ##
    
    _handlerLookup = {"job-data":
                      {"progress":  ("_onTranscoderProgress", None, 0.0),
                       "status":    ("_onTranscoderStatusChanged", None, 
                                     TranscoderStatusEnum.pending),
                       "job-state": ("_onTranscoderJobStateChanged", None, 
                                     JobStateEnum.pending)}}
    
    def _doBroadcastUIState(self, uiState):
        for key, handlers in self._handlerLookup.iteritems():
            keyState = uiState.get(key, None)
            for subkey, handler in handlers.iteritems():
                if not handler[0]:
                    continue
                if (not (subkey in keyState)) or (keyState == None):
                    if handlers[2] != None:
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
        self._fireEvent(percent, "TranscoderProgress")

    def _onTranscoderStatusChanged(self, status):
        self._fireEvent(status, "TranscoderStatusChanged")

    def _onTranscoderJobStateChanged(self, state):
        self._fireEvent(state, "TranscoderJobStateChanged")

    
    ## Private Methodes ##
    
    def __cbLoadReport(self, path):
        context = self.getContext()
        local = context.group.manager.admin.getLocal()
        localPath = VirtualPath(path).localize(local)
        if not os.path.exists(localPath):
            message = ("Transcoder report file '%s' not found" % localPath)
            self.log.warning("%s", message)
            raise TranscoderError(message)
        loader = inifile.IniFile()
        report = TranscodingReport()
        try:
            loader.loadFromFile(report, localPath)
        except Exception, e:
            message = ("Failed to load transcoder report file '%s': %s"
                       % (localPath, log.getExceptionMessage(e)))
            log.warning("%s", message)
            raise TranscoderError(message)
        return report


registerProxy("file-transcoder", TranscoderProxy)
