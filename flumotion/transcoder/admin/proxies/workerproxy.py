# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.twisted.compat import Interface
from flumotion.transcoder import log
from flumotion.transcoder.admin.proxies import fluproxy


def instantiate(logger, parent, identifier, manager, 
                workerContext, state, *args, **kwargs):
    return WorkerProxy(logger, parent, identifier, manager, 
                       workerContext, state, *args, **kwargs)
    

class IWorkerListener(Interface):
    pass


class WorkerProxy(fluproxy.FlumotionProxy):
    
    def __init__(self, logger, parent, identifier, manager, 
                 workerContext, workerState):
        fluproxy.FlumotionProxy.__init__(self, logger, parent, 
                                         identifier, manager,
                                         IWorkerListener)
        self._context = workerContext
        self._workerState = workerState
        
        
    ## Public Methods ##
    
    def getName(self):
        assert self._workerState, "Worker has been removed"
        return self._workerState.get('name')
    
    def getHost(self):
        assert self._workerState, "Worker has been removed"
        return self._workerState.get('host')

    
    ## Overriden Methods ##
    
    def _onRemoved(self):
        assert self._workerState, "Worker has already been removed"
    
    def _doDiscard(self):
        assert self._workerState, "Worker has already been discarded"
        self._workerState = None

    def _onActivated(self):
        atmosphere = self._manager.getAtmosphere()
        d = atmosphere._loadComponent('file-transcoder', 
                                      'transcoder',
                                      #'transcoder-%s' % self.getName(), 
                                      self.getName(),
                                      config="/home/sebastien/workspace/flumotion/transcoder/v0r2/conf/transcoder-job.ini")
        def ok(result):
            print "#"*20, "OK", result.__class__.__name__, result
        
        def failed(failure):
            print "#"*20, "Failed:", log.getFailureMessage(failure)
            
        d.addCallbacks(ok, failed)

    ## Protected Methods ##
    
    def _callRemote(self, methodName, *args, **kwargs):
        assert self._workerState, "Worker has been removed"
        workerName = self._workerState.get('name')
        return self._manager._workerCallRemote(workerName, 
                                               methodName, 
                                               *args, **kwargs)
