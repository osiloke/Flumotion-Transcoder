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

from flumotion.transcoder.admin.proxies import componentproxy
from flumotion.transcoder.enums import MonitorFileStateEnum


class IMonitorListener(componentproxy.IComponentListener):
    def onMonitorFileAdded(self, monitor, file, state):
        pass
    
    def onMonitorFileRemoved(self, monitor, file, state):
        pass
    
    def onMonitorFileStateChanged(self, monitor, file, state):
        pass


class MonitorProxy(componentproxy.ComponentProxy):
    
    def __init__(self, logger, parent, identifier, manager, 
                 componentContext, componentState, domain):
        componentproxy.ComponentProxy.__init__(self, logger, parent,  
                                               identifier, manager,
                                               componentContext, 
                                               componentState, domain,
                                               IMonitorListener)
        self._alreadyAdded = {} # file => None
        
    ## Public Methods ##
    
    
    ## Overriden Methods ##
    
    def _doBroadcastUIState(self, uiState):
        pending = uiState.get("pending-files", None)
        if pending:
            for file, statenum in pending.iteritems():
                self._onMonitorSetFile(file, statenum)
    
    def _onUIStateSet(self, uiState, key, value):
        self.log("Monitor UI State '%s' set to '%s'", key, value)
    
    def _onUIStateAppend(self, uiState, key, value):
        self.log("Monitor UI State '%s' value '%s' appened", key, value)
    
    def _onUIStateRemove(self, uiState, key, value):
        self.log("Monitor UI State '%s' value '%s' removed", key, value)
    
    def _onUIStateSetitem(self, uiState, key, subkey, value):
        self.log("Monitor UI State '%s' item '%s' set to '%s'", 
                 key, subkey, value)
        if key == "pending-files":
            self._onMonitorSetFile(subkey, value)
    
    def _onUIStateDelitem(self, uiState, key, subkey, value):
        self.log("Monitor UI State '%s' item '%s' deleted", 
                 key, subkey)
        if key == "pending-files":
            self._onMonitorDelFile(subkey, value)

    def _onUnsetUIState(self, uiState):
        componentproxy.ComponentProxy._onUnsetUIState(self, uiState)
        self._alreadyAdded.clear()

    
    ## UI State Handlers Methods ##
    
    def _onMonitorSetFile(self, file, statenum):
        state = MonitorFileStateEnum.get(statenum)
        if file in self._alreadyAdded:
            self._fireEvent((file, state), "MonitorFileStateChanged")
        else:
            self._alreadyAdded[file] = None
            self._fireEvent((os.path.join(*file), state), "MonitorFileAdded")
            
    def _onMonitorDelFile(self, file, statenum):
        assert file in self._alreadyAdded
        state = MonitorFileStateEnum.get(statenum)
        self._fireEvent((os.path.join(*file), state), "MonitorFileRemoved")



componentproxy.registerProxy("file-monitor", MonitorProxy)
