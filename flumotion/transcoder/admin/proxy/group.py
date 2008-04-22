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

from flumotion.inhouse import defer, utils

from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.errors import OperationTimedOutError
from flumotion.transcoder.admin.proxy import base
from flumotion.transcoder.admin.proxy import component


class ComponentGroupProxy(base.BaseProxy):
    
    _componentDomain = None
    
    def __init__(self, logger, parentPxy, identifier, managerPxy, context, state):
        base.BaseProxy.__init__(self, logger, parentPxy, identifier, managerPxy)
        self._context = context
        self._state = state
        self._compPxys = {} # {identifier: ComponentProxy}
        self._waitCompLoaded = {} # {identifier: Deferred}
        self.__updateIdleTarget()
        # Registering Events
        self._register("component-added")
        self._register("component-removed")
        
        
    ## Public Methods ##
    
    def getName(self):
        assert self._state, "Element has been removed"
        return self._state.get('name')

    def getComponentProxies(self):
        return self._compPxys.values()

    def iterComponentProxies(self):
        return self._compPxys.itervalues()

    ## Virtual Methods ##
    
    def _onStateAppend(self, key, value):
        pass
    
    def _onStateRemove(self, key, value):
        pass

    def _onComponentsLoaded(self):
        pass

    
    ## Overriden Methods ##
    
    def refreshListener(self, listener):
        assert self._state, "Element has been removed"
        self._refreshProxiesListener("_compPxys", listener, "component-added")

    def _doGetChildElements(self):
        return self.getComponentProxies()
    
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
        self._removeProxies("_compPxys", "component-removed")
    
    def _doDiscard(self):
        assert self._state, "Element has already been discarded"
        self._discardProxies("_compPxys")
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
    
    def _loadComponent(self, componentType, componentName, componentLabel,
                       workerPxy, properties, timeout=None):
        compId = common.componentId(self._state.get('name'), componentName)
        identifier = self.__getComponentUniqueIdByName(componentName)
        workerCtx = workerPxy.getWorkerContext()
        properties.prepare(workerCtx)
        props = properties.asComponentProperties(workerCtx)
        resDef = defer.Deferred()
        initDef = defer.Deferred()
        self._waitCompLoaded[identifier] = initDef
        
        callDef = self._managerPxy._callRemote('loadComponent', componentType,
                                            compId, componentLabel, 
                                            props, workerPxy.getName())
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
    
    def __getComponentUniqueId(self, managerPxy, compCtx, compState, domain):
        if compState == None:
            return None
        return self.__getComponentUniqueIdByName(compState.get('name'))
    
    def __getComponentUniqueIdByName(self, name):
        return "%s.%s" % (self.getIdentifier(), name)
    
    def __componentStateAdded(self, compState):
        name = compState.get('name')
        compCtx = self._context.getComponentContextByName(name)
        self._addProxyState(component, "_compPxys",
                            self.__getComponentUniqueId, 
                            "component-added", self._managerPxy,
                            compCtx, compState, self._componentDomain)
        self.__updateIdleTarget()
    
    def __componentStateRemoved(self, compState):
        name = compState.get('name')
        compCtx = self._context.getComponentContextByName(name)
        self._removeProxyState("_compPxys", self.__getComponentUniqueId,
                               "component-removed", self._managerPxy,
                               compCtx, compState, 
                               self._componentDomain)
        self.__updateIdleTarget()

    def __cbComponentLoaded(self, compState, identifier, initDef, resultDef, to):
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
