# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import Interface, implements

from flumotion.inhouse import log

from flumotion.transcoder.admin.proxies import fluproxy


def instantiate(logger, parent, identifier, manager, 
                workerContext, state, *args, **kwargs):
    return WorkerProxy(logger, parent, identifier, manager, 
                       workerContext, state, *args, **kwargs)
    

class IWorkerDefinition(Interface):
    
    def getName(self):
        pass
    
    def getContext(self):
        pass


class IWorker(IWorkerDefinition, fluproxy.IFlumotionProxy):
    pass


class WorkerDefinition(object):
    """
    Used to represent non-running workers.
    """
    
    implements(IWorkerDefinition)
    
    def __init__(self, workerName, workerContext):
        self._context = workerContext
        self._name = workerName
    
    
    ## IWorkerDefinition Methodes ##
    
    def getName(self):
        return self._name
    
    def getContext(self):
        return self._context
 
 
class WorkerProxy(fluproxy.FlumotionProxy):
    
    implements(IWorker)
    
    def __init__(self, logger, parent, identifier, manager, 
                 workerContext, workerState):
        fluproxy.FlumotionProxy.__init__(self, logger, parent, 
                                         identifier, manager)
        
        self._workerState = workerState
        self._context = workerContext
        
        
    ## IWorkerDefinition and IFlumotionProxxyRO Methods ##
    
    def getName(self):
        assert self._workerState, "Worker has been removed"
        return self._workerState.get('name')
    
    def getHost(self):
        assert self._workerState, "Worker has been removed"
        return self._workerState.get('host')

    def getContext(self):
        return self._context

    
    ## Overriden Methods ##
    
    def _onRemoved(self):
        assert self._workerState, "Worker has already been removed"
    
    def _doDiscard(self):
        assert self._workerState, "Worker has already been discarded"
        self._workerState = None


    ## Protected Methods ##
    
    def _callRemote(self, methodName, *args, **kwargs):
        assert self._workerState, "Worker has been removed"
        workerName = self._workerState.get('name')
        return self._manager._workerCallRemote(workerName, 
                                               methodName, 
                                               *args, **kwargs)
