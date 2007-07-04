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

from flumotion.transcoder.virtualpath import VirtualPath
from flumotion.transcoder.enums import MonitorFileStateEnum
from flumotion.transcoder.admin.monprops import MonitorProperties
from flumotion.transcoder.admin.proxies.componentproxy import ComponentProxy
from flumotion.transcoder.admin.proxies.componentproxy import IComponentListener
from flumotion.transcoder.admin.proxies.componentproxy import ComponentListener
from flumotion.transcoder.admin.proxies.componentproxy import registerProxy


class IMonitorListener(IComponentListener):
    def onMonitorFileAdded(self, monitor, virtDir, file, state):
        pass
    
    def onMonitorFileRemoved(self, monitor, virtDir, file, state):
        pass
    
    def onMonitorFileChanged(self, monitor, virtDir, file, state):
        pass


class MonitorListener(ComponentListener):
    
    implements(IMonitorListener)
    
    def onMonitorFileAdded(self, monitor, virtDir, file, state):
        pass
    
    def onMonitorFileRemoved(self, monitor, virtDir, file, state):
        pass
    
    def onMonitorFileChanged(self, monitor, virtDir, file, state):
        pass


class MonitorProxy(ComponentProxy):
    
    properties_factory = MonitorProperties
    
    @classmethod
    def loadTo(cls, worker, name, label, properties, timeout=None):
        manager = worker.getParent()
        atmosphere = manager.getAtmosphere()
        return atmosphere._loadComponent('file-monitor', 
                                         name,  label, worker, 
                                         properties, timeout)
    
    def __init__(self, logger, parent, identifier, manager, 
                 componentContext, componentState, domain):
        ComponentProxy.__init__(self, logger, parent,  
                                identifier, manager,
                                componentContext, 
                                componentState, domain,
                                IMonitorListener)
        self._alreadyAdded = {} # {file: None}

        
    ## Public Methods ##
    
    def waitFiles(self, timeout=None):
        d = self._waitUIState(timeout)
        d.addCallback(self.__cbRetrieveFiles)
        return d
            
    
    ## Overriden Methods ##
    
    def _doBroadcastUIState(self, uiState):
        pending = uiState.get("pending-files", None)
        if pending:
            for file, statenum in pending.iteritems():
                virtBase, relFile = file
                self._onMonitorSetFile(virtBase, relFile, statenum)
    
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
            virtBase, relFile = subkey
            self._onMonitorSetFile(virtBase, relFile, value)
    
    def _onUIStateDelitem(self, uiState, key, subkey, value):
        self.log("Monitor UI State '%s' item '%s' deleted", 
                 key, subkey)
        if key == "pending-files":
            virtBase, relFile = subkey
            self._onMonitorDelFile(virtBase, relFile, value)

    def _onUnsetUIState(self, uiState):
        ComponentProxy._onUnsetUIState(self, uiState)
        self._alreadyAdded.clear()

    
    ## UI State Handlers Methods ##
    
    def _onMonitorSetFile(self, virtBase, relFile, state):
        ident = (virtBase, relFile)
        args = (virtBase, relFile, state)
        if ident in self._alreadyAdded:
            self._fireEvent(args, "MonitorFileChanged")
        else:
            self._alreadyAdded[ident] = None
            self._fireEvent(args, "MonitorFileAdded")            
            self._callRemote("test")
            
    def _onMonitorDelFile(self, virtBase, relFile, state):
        ident = (virtBase, relFile)
        args = (virtBase, relFile, state)
        assert ident in self._alreadyAdded
        del self._alreadyAdded[ident]
        self._fireEvent(args, "MonitorFileRemoved")


    ## Overriden Methods ##

    
    ## Private Methods ##
    
    def __cbRetrieveFiles(self, ui):
        files = []
        worker = self.getWorker()
        assert ui != None
        assert worker != None
        context = worker.getContext()
        local = context.getLocal()
        for (p, f), s in ui.get("pending-files", {}).iteritems():
            files.append((VirtualPath.virtualize(p, local), f, s))
        return files
    

registerProxy("file-monitor", MonitorProxy)
