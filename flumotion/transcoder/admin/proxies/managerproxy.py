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

from flumotion.transcoder import defer, utils
from flumotion.transcoder.admin.waiters import AssignWaiters
from flumotion.transcoder.admin.waiters import ItemWaiters
from flumotion.transcoder.admin.proxies import fluproxy
from flumotion.transcoder.admin.proxies import workerproxy
from flumotion.transcoder.admin.proxies import flowproxy
from flumotion.transcoder.admin.proxies import atmosphereproxy


def instantiate(logger, parent, identifier, admin, 
                managerContext, state, *args, **kwargs):
    return ManagerProxy(logger, parent, identifier, admin,
                        managerContext, state, *args, **kwargs)


class IManagerListener(Interface):
    def onWorkerAdded(self, manager, worker):
        pass
    
    def onWorkerRemoved(self, manager, worker):
        pass
    
    def onAtmosphereSet(self, manager, atmosphere):
        pass
    
    def onAtmosphereUnset(self, manager, atmosphere):
        pass
    
    def onFlowAdded(self, manager, flow):
        pass
    
    def onFlowRemoved(self, manager, flow):
        pass


class ManagerListener(object):
    
    implements(IManagerListener)
    
    def onWorkerAdded(self, manager, worker):
        pass
    
    def onWorkerRemoved(self, manager, worker):
        pass
    
    def onAtmosphereSet(self, manager, atmosphere):
        pass
    
    def onAtmosphereUnset(self, manager, atmosphere):
        pass
    
    def onFlowAdded(self, manager, flow):
        pass
    
    def onFlowRemoved(self, manager, flow):
        pass


class ManagerProxy(fluproxy.BaseFlumotionProxy):
    
    def __init__(self, logger, parent, identifier, 
                 admin, managerContext, planetState):
        fluproxy.BaseFlumotionProxy.__init__(self, logger, parent, identifier,
                                             IManagerListener)
        self._context = managerContext
        self._admin = admin
        self._planetState = planetState
        self._workers = ItemWaiters("Manager Workers") # {identifier: Worker}
        self._atmosphere = AssignWaiters("Manager Atmosphere")
        self._flows = {} # {identifier: Flow}
        self.__updateIdleTarget()
    
    
    ## Public Methods ##
    
    def getName(self):
        assert self._planetState, "Manager has been removed"
        return self._planetState.get('name')

    def getAtmosphere(self):
        return self._atmosphere.getValue()
    
    def waitAtmosphere(self, timeout=None):
        return self._atmosphere.wait(timeout)

    def getFlows(self):
        return self._flows.values()
    
    def getWorkers(self):
        return self._workers.getItems()

    def getContext(self):
        return self._context
    
    def getWorkerByName(self, name):
        workerId = self.__getWorkerUniqueIdByName(name)
        return self._workers.getItem(workerId, None)

    def waitWorkerByName(self, name, timeout=None):
        workerId = self.__getWorkerUniqueIdByName(name)
        return self._workers.wait(workerId, timeout)

    
    ## Overriden Public Methods ##
    

    ## Overriden Methods ##
    
    def _doGetChildElements(self):
        childs = self.getWorkers()
        childs.extend(self.getFlows())
        atmosphere = self.getAtmosphere()
        if atmosphere:
            childs.append(atmosphere)
        return childs
    
    def _doSyncListener(self, listener):
        assert self._planetState, "Manager has been removed"
        self._syncProxies("_workers", listener, "WorkerAdded")
        self._syncProxies("_atmosphere", listener, "AtmosphereAdded")
        self._syncProxies("_flows", listener, "FlowAdded")

    def _onActivated(self):
        whs = self._admin.getWorkerHeavenState()
        whs.addListener(self, None, 
                        self._heavenStateAppend, 
                        self._heavenStateRemove)
        ps = self._planetState
        ps.addListener(self, 
                       self._planetStateSet,
                       self._planetStateAppend, 
                       self._planetStateRemove)
        for workerState in whs.get('workers'):
            self.__workerStateAdded(workerState)
        self.__atmosphereSetState(ps.get('atmosphere'))
        for flowState in ps.get('flows'):
            self.__flowStateAdded(flowState)
            
    def _onRemoved(self):
        assert self._planetState, "Manager has already been removed"
        whs = self._admin.getWorkerHeavenState()
        whs.removeListener(self)
        ps = self._planetState
        ps.removeListener(self)
        self._removeProxies("_flows", "FlowRemoved")
        self._removeProxies("_atmosphere", "AtmosphereUnset")
        self._removeProxies("_workers", "WorkerRemoved")
    
    def _doDiscard(self):
        assert self._planetState, "Manager has already been discarded"
        self._discardProxies("_flows", "_atmosphere", "_workers")
        self._admin = None
        self._planetState = None
    

    ## WorkerHeavenState Listeners ##
    
    def _heavenStateAppend(self, state, key, value):        
        if key == 'workers':
            assert value != None
            self.log("Worker state %s added", value.get('name'))
            if self.isActive():
                self.__workerStateAdded(value)
    
    def _heavenStateRemove(self, state, key, value):
        if key == 'workers':
            assert value != None
            self.log("Worker state %s removed", value.get('name'))
            if self.isActive():
                self.__workerStateRemoved(value)
               
               
    ## PlanetState Listeners ##
               
    def _planetStateAppend(self, state, key, value):
        if key == 'flows':
            assert value != None
            self.log("Flow state %s added", value.get('name'))
            if self.isActive():
                self.__flowStateAdded(value)
    
    def _planetStateRemove(self, state, key, value):
       if key == 'flows':
           assert value != None
           self.log("Flow state %s removed", value.get('name'))
           if self.isActive():
                self.__flowStateRemoved(value)
               
    def _planetStateSet(self, state, key, value):
       if key == 'atmosphere':
           assert value != None
           self.log("Atmosphere state %s changed", value.get('name'))
           if self.isActive():
               self.__atmosphereSetState(value)
    
    
    ## Protected Methods ##
    
    def _callRemote(self, methodName, *args, **kwargs):
        return self._admin.callRemote(methodName, *args, **kwargs)
    
    def _workerCallRemote(self, workerName, methodName, *args, **kwargs):
        return self._admin.workerCallRemote(workerName, methodName, 
                                            *args, **kwargs)
    
    def _componentCallRemote(self, componentState, methodName, 
                             *args, **kwargs):
        return self._admin.componentCallRemote(componentState, methodName, 
                                               *args, **kwargs)

    ## Private Methods ##
    
    def __updateIdleTarget(self):
        state = self._planetState
        count = 1  # The atmosphere
        count += len(state.get("flows", []))
        whs = self._admin.getWorkerHeavenState()
        count += len(whs.get("workers", []))
        self._setIdleTarget(count)
    
    def __getWorkerUniqueId(self, manager, workerContext, workerState):
        if workerState == None:
            return None
        return self.__getWorkerUniqueIdByName(workerState.get('name'))
        
    def __getWorkerUniqueIdByName(self, name):
        return "%s/Wkr:%s" % (self.getIdentifier(), name)
        
    def __getAtmosphereUniqueId(self, manager, atmosphereContext, 
                                atmosphereState):
        if atmosphereState == None:
            return None
        return "%s/Atm:%s" % (self.getIdentifier(),
                          atmosphereState.get('name'))

    def __getFlowUniqueId(self, manager, flowContext, flowState):
        if flowState == None:
            return None
        return "%s/Flw:%s" % (self.getIdentifier(),
                          flowState.get('name'))

    def __workerStateAdded(self, workerState):
        name = workerState.get('name')
        workerContext = self._context.admin.getWorkerContext(name)
        self._addProxyState(workerproxy, "_workers",
                            self.__getWorkerUniqueId,
                           "WorkerAdded", self, 
                           workerContext, workerState)
        self.__updateIdleTarget()
    
    def __workerStateRemoved(self, workerState):
        name = workerState.get('name')
        workerContext = self._context.admin.getWorkerContext(name)
        self._removeProxyState("_workers", self.__getWorkerUniqueId,
                              "WorkerRemoved", self, 
                              workerContext, workerState)
        self.__updateIdleTarget()

    def __atmosphereSetState(self, atmosphereState):
        name = atmosphereState.get('name')
        atmosphereContext = self._context.getAtmosphereContext(name)
        self._setProxyState(atmosphereproxy, "_atmosphere",
                            self.__getAtmosphereUniqueId,
                           "AtmosphereUnset", "AtmosphereSet",
                           self, atmosphereContext, atmosphereState)
    
    def __flowStateAdded(self, flowState):
        name = flowState.get('name')
        flowContext = self._context.getFlowContext(name)
        self._addProxyState(flowproxy, "_flows",
                            self.__getFlowUniqueId,
                           "FlowAdded", self, flowContext, flowState)
        self.__updateIdleTarget()
    
    def __flowStateRemoved(self, flowState):
        name = flowState.get('name')
        flowContext = self._context.getFlowContext(name)
        self._removeProxyState("_flows", self.__getFlowUniqueId,
                              "FlowRemoved", self, flowContext, flowState)
        self.__updateIdleTarget()
