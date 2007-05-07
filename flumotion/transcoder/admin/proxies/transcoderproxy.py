# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.transcoder.admin.proxies import componentproxy
from flumotion.transcoder.enums import TranscoderStatusEnum


class ITranscoderListener(componentproxy.IComponentListener):
    def onTranscoderProgress(self, transcoder, percent):
        pass
    
    def onTranscoderStatusChanged(self, transcoder, status):
        pass


class TranscoderProxy(componentproxy.ComponentProxy):
    
    def __init__(self, logger, parent, identifier, manager, 
                 componentContext, componentState, domain):
        componentproxy.ComponentProxy.__init__(self, logger, parent, 
                                               identifier, manager,
                                               componentContext, 
                                               componentState, domain,
                                               ITranscoderListener)
        
    ## Public Methods ##
    
    def getTranscoderProgress(self):
        assert self._uiState, "No UI State"
        jobData = self._uiState.get("job-data", None)
        if jobData:
            return jobData.get('progress', 0.0)
        return 0.0
    
    ## Overriden Methods ##
    
    _handlerLookup = {"job-data":
                      {"progress":  ("_onTranscoderProgress", None, 0.0),
                       "status":    ("_onTranscoderStatusChanged", None, 
                                     TranscoderStatusEnum.pending)}}

    
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


componentproxy.registerProxy("file-transcoder", TranscoderProxy)
