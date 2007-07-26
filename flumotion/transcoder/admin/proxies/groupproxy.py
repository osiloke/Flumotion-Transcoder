# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.
# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.common import common

from flumotion.transcoder import defer, utils
from flumotion.transcoder.errors import OperationTimedOutError
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.proxies import fluproxy
from flumotion.transcoder.admin.proxies import componentproxy


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
        self.__updateIdleTarget()
        
        
    ## Public Methods ##
    
    def getName(self):
        assert self._state, "Element has been removed"
        return self._state.get('name')

    def getComponents(self):
        return self._components.values()

    def iterComponents(self):
        return self._components.itervalues()

    ## Virtual Methods ##
    
    def _onStateAppend(self, key, value):
        pass
    
    def _onStateRemove(self, key, value):
        pass

    def _onComponentsLoaded(self):
        pass
    
    ## Overriden Methods ##
    
    def _doGetChildElements(self):
        return self.getComponents()
    
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
        if self.isActive():
            state = self._state
            state.removeListener(self)
        self._removeProxies("_components", self._componentRemovedEvent)
    
    def _doDiscard(self):
        assert self._state, "Element has already been discarded"
        self._discardProxies("_components")
        self._atmosphereState = None

    def _onElementActivated(self, element):
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
            self.log("Component state %s added", value.get('name'))
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
                       componentLabel, worker, properties, timeout=None):
        compId = common.componentId(self._state.get('name'), componentName)
        identifier = self.__getComponentUniqueIdByName(componentName)
        props = properties.asComponentProperties(worker.getContext())
        resDef = defer.Deferred()
        initDef = defer.Deferred()
        self._waitCompLoaded[identifier] = initDef
        
        callDef = self._manager._callRemote('loadComponent', componentType,
                                            compId, componentLabel, 
                                            props, worker.getName())
        to = utils.createTimeout(timeout or adminconsts.LOAD_COMPONENT_TIMEOUT,
                                 self.__asyncComponentLoadedTimeout, callDef)
        args = (identifier, initDef, resDef, to)
        callDef.addCallbacks(self.__cbComponentLoaded, 
                             self.__ebComponentLoadingFailed,
                             callbackArgs=args, errbackArgs=args)
        return resDef


    ## Private Methods ##
    
    def __updateIdleTarget(self):
        count = len(self._state.get("components", []))
        self._setIdleTarget(count)
    
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
        self.__updateIdleTarget()
    
    def __componentStateRemoved(self, componentState):
        name = componentState.get('name')
        componentContext = self._context.getComponentContext(name)
        self._removeProxyState("_components", self.__getComponentUniqueId,
                               self._componentRemovedEvent, self._manager,
                               componentContext, componentState, 
                               self._componentDomain)
        self.__updateIdleTarget()

    def __cbComponentLoaded(self, componentState, identifier, initDef, resultDef, to):
        utils.cancelTimeout(to)
        initDef.chainDeferred(resultDef)
    
    def __asyncComponentLoadedTimeout(self, d, label):
        msg = "Timeout loading component '%s'" % label
        self.warning("%s", msg)
        err = OperationTimedOutError(msg)
        d.errback(err)
    
    def __ebComponentLoadingFailed(self, failure, identifier, initDef, resultDef, to):
        utils.cancelTimeout(to)
        self._waitCompLoaded.pop(identifier, None)
        resultDef.errback(failure)
