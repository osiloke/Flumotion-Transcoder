# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.
# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from twisted.internet import defer, reactor

from flumotion.common import common

from flumotion.transcoder.admin.errors import OperationTimedOutError
from flumotion.transcoder.admin.waiters import CounterWaiter
from flumotion.transcoder.admin.proxies import fluproxy
from flumotion.transcoder.admin.proxies import componentproxy

LOAD_COMPONENT_TIMEOUT = 30.0

class ComponentGroupProxy(fluproxy.FlumotionProxy):
    
    _componentAddedEvent = None
    _componentRemovedEvent = None
    _componentDomain = None
    
    def __init__(self, logger, parent, identifier, manager,
                 context, state, listenerInterface):
        fluproxy.FlumotionProxy.__init__(self, logger, parent, identifier, 
                                manager, listenerInterface)
        self._context = context
        self._state = state
        self._components = {} # {identifier: ComponentProxy}
        self._waitCompLoaded = {} # {identifier: Deferred}
        target = len(state.get("components", []))
        self._waitSynchronized = CounterWaiter(target, 0, self)
        
        
    ## Public Methods ##
    
    def getName(self):
        assert self._state, "Element has been removed"
        return self._state.get('name')

    def waitSynchronized(self, timeout=None):
        """
        Wait for all state components to be initilized,
        """
        return self._waitSynchronized.wait(timeout)

    
    ## Virtual Methods ##
    
    def _onStateAppend(self, key, value):
        pass
    
    def _onStateRemove(self, key, value):
        pass

    def _onComponentsLoaded(self):
        pass
    
    ## Overriden Methods ##
    
    def _doSyncListener(self, listener):
        assert self._state, "Element has been removed"
        self._syncProxies("_components", listener, self._componentAddedEvent)

    def _onActivated(self):
        state = self._state
        state.addListener(self, None,
                          self._stateAppend, 
                          self._stateRemove)
        for componentState in state.get('components'):
            self.__componentStateAdded(componentState)
            
    def _onRemoved(self):
        assert self._state, "Element has already been removed"
        state = self._state
        state.removeListener(self)
        self._removeProxies("_components", self._componentRemovedEvent)
    
    def _doDiscard(self):
        assert self._state, "Element has already been discarded"
        self._discardProxies("_components")
        self._atmosphereState = None

    def _onElementInitFailed(self, element, failure):
        self._waitSynchronized.inc()
    
    def _onElementRemoved(self, element):
        self._waitSynchronized.dec()
        
    def _onElementNotFound(self, identifier):
        # The element was not found during deletion
        # probably because it previously fail to initialize
        self._waitSynchronized.dec()

    def _onElementActivated(self, element):
        self._waitSynchronized.inc()
        identifier = element.getIdentifier()
        d = self._waitCompLoaded.pop(identifier, None)
        if d:
            d.callback(element)
        
    def _onElementAborted(self, element, failure):
        identifier = element.getIdentifier()
        d = self._waitCompLoaded.pop(identifier, None)
        if d:
            d.errback(failure)
            
    ## State Listeners ##
               
    def _stateAppend(self, state, key, value):
        if key == 'components':
            assert value != None
            self._waitSynchronized.setTarget(len(state.get(key)))
            self.log("Component state %s added to ", value.get('name'))
            if self.isActive():
                self.__componentStateAdded(value)
        self._onStateAppend(key, value)
    
    def _stateRemove(self, state, key, value):
        if key == 'components':
            assert value != None
            self._waitSynchronized.setTarget(len(state.get(key)))
            self.log("Component state %s removed", value.get('name'))
            if self.isActive():
                self.__componentStateRemoved(value)
        self._onStateRemove(key, value)
    
    
    ## Protected/Friend Methods
    
    def _loadComponent(self, componentType, componentName,
                       componentLabel, worker, properties):
        compId = common.componentId(self._state.get('name'), componentName)
        identifier = self.__getComponentUniqueIdByName(componentName)
        props = properties.getComponentProperties(worker.getContext())
        resDef = defer.Deferred()
        initDef = defer.Deferred()
        self._waitCompLoaded[identifier] = initDef
        callDef = self._manager._callRemote('loadComponent', componentType,
                                            compId, props, worker.getName())
        callDef.addCallbacks(self.__componentLoaded, 
                             self.__componentLoadingFailed,
                             callbackArgs=(identifier, initDef, resDef,), 
                             errbackArgs=(identifier, initDef, resDef,))
        callDef.setTimeout(LOAD_COMPONENT_TIMEOUT,
                           self.__componentLoadTimeout,
                           identifier)
        return resDef


    ## Private Methods ##
    
    def __getComponentUniqueId(self, manager, componentContext, 
                               componentState, domain):
        if componentState == None:
            return None
        return self.__getComponentUniqueIdByName(componentState.get('name'))
    
    def __getComponentUniqueIdByName(self, name):
        return "%s/Cmp:%s" % (self.getIdentifier(), name)
    
    def __componentStateAdded(self, componentState):
        name = componentState.get('name')
        componentContext = self._context.getComponentContext(name)
        self._addProxyState(componentproxy, "_components", 
                            self.__getComponentUniqueId, 
                            self._componentAddedEvent, self._manager,
                            componentContext, componentState, 
                            self._componentDomain)
    
    def __componentStateRemoved(self, componentState):
        name = componentState.get('name')
        componentContext = self._context.getComponentContext(name)
        i = self._removeProxyState("_components", self.__getComponentUniqueId,
                                   self._componentRemovedEvent, self._manager,
                                   componentContext, componentState, 
                                   self._componentDomain)

    def __componentLoaded(self, componentState, identifier, initDef, resultDef):
        initDef.chainDeferred(resultDef)
    
    def __componentLoadingFailed(self, failure, identifier, initDef, resultDef):
        self._waitCompLoaded.pop(identifier, None)
        resultDef.errback(failure)
        
    def __componentLoadTimeout(self, resultDef, identifier):
        err = OperationTimedOutError("Timeout waiting component '%s' "
                                     "to be loaded" % identifier)
        resultDef.errback(err)
