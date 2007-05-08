# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.
# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from twisted.internet import defer

from flumotion.common import common

from flumotion.transcoder.admin.errors import OperationTimedOut
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
        self._components = {} # identifier => component
        self._waitLoaded = {} # identifier => Deferred
        
        
    ## Public Methods ##
    
    def getName(self):
        assert self._state, "Element has been removed"
        return self._state.get('name')

    
    ## Virtual Methods ##
    
    def _onStateAppend(self, key, value):
        pass
    
    def _onStateRemove(self, key, value):
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

    def _onElementActivated(self, element):
        identifier = element.getIdentifier()
        d = self._waitLoaded.pop(identifier, None)
        if d:
            d.callback(element)
        
    def _onElementAborted(self, element, failure):
        identifier = element.getIdentifier()
        d = self._waitLoaded.pop(identifier, None)
        if d:
            d.errback(failure)


    ## State Listeners ##
               
    def _stateAppend(self, state, key, value):
        if key == 'components':
            assert value != None
            self.log("Component state %s added to ", value.get('name'))
            if self.isActive():
                self.__componentStateAdded(value)
        self._onStateAppend(key, value)
    
    def _stateRemove(self, state, key, value):
        if key == 'components':
            assert value != None
            self.log("Component state %s removed", value.get('name'))
            if self.isActive():
                self.__componentStateRemoved(value)
        self._onStateRemove(key, value)
    
    
    ## Protected/Friend Methods
    
    def _loadComponent(self, componentType, componentName, 
                       workerName, properties):
        compId = common.componentId(self._state.get('name'), componentName)
        identifier = self.__getComponentUniqueIdByName(componentName)
        resDef = defer.Deferred()
        initDef = defer.Deferred()
        self._waitLoaded[identifier] = initDef
        callDef = self._manager._callRemote('loadComponent', componentType, 
                                            compId, properties, workerName)
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
        self._removeProxyState("_components", self.__getComponentUniqueId, 
                               self._componentRemovedEvent, self._manager,
                               componentContext, componentState, 
                               self._componentDomain)

    def __componentLoaded(self, componenetState, identifier, initDef, resultDef):
        initDef.chainDeferred(resultDef)
    
    def __componentLoadingFailed(self, failure, identifier, initDef, resultDef):
        self._waitLoaded.pop(identifier, None)
        resultDef.errback(failure)
        
    def __componentLoadTimeout(self, resultDef, identifier):
        err = OperationTimedOut("Timeout waiting component '%s' to be loaded" 
                                % identifier)
        resultDef.errback(err)
        
