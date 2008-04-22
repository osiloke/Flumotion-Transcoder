# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import implements

from flumotion.inhouse import log

from flumotion.transcoder.admin import interfaces
from flumotion.transcoder.admin.proxy import base
    

class IWorkerDefinition(interfaces.IAdminInterface):
    
    def getName(self):
        pass
    
    def getWorkerContext(self):
        pass


class IWorkerProxy(IWorkerDefinition, base.IBaseProxy):
    
    def getHost(self):
        pass


class WorkerDefinition(object):
    """
    Used to represent non-running workers.
    """
    
    implements(IWorkerDefinition)
    
    def __init__(self, workerName, workerCtx):
        self._workerCtx = workerCtx
        self._name = workerName
    
    
    ## IWorkerDefinition Methodes ##
    
    def getName(self):
        return self._name
    
    def getWorkerContext(self):
        return self._workerCtx
 
 
class WorkerProxy(base.BaseProxy):
    implements(IWorkerProxy)
    
    def __init__(self, logger, parentPxy, identifier, managerPxy, workerCtx, workerState):
        base.BaseProxy.__init__(self, logger, parentPxy, identifier, managerPxy)
        self._workerState = workerState
        self._workerCtx = workerCtx
        
        
    ## IWorkerDefinition and IFlumotionProxxyRO Methods ##
    
    def getName(self):
        assert self._workerState, "Worker has been removed"
        return self._workerState.get('name')
    
    def getHost(self):
        assert self._workerState, "Worker has been removed"
        return self._workerState.get('host')

    def getWorkerContext(self):
        return self._workerCtx

    
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
        return self._managerPxy._workerCallRemote(workerName, 
                                                  methodName, 
                                                  *args, **kwargs)


def instantiate(logger, parentPxy, identifier, managerPxy, 
                workerContext, workerState, *args, **kwargs):
    return WorkerProxy(logger, parentPxy, identifier, managerPxy, 
                       workerContext, workerState, *args, **kwargs)
