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

#To register Jellyable classes
from flumotion.common import componentui

from flumotion.common.planet import moods
from flumotion.transcoder import log
from flumotion.transcoder.enums import ComponentDomainEnum
from flumotion.transcoder.admin.proxies.fluproxy import FlumotionProxy


_componentRegistry = {}

def registerProxy(type, cls):
    assert not (type in _componentRegistry), "Already Registered"
    _componentRegistry[type] = cls
    
def getProxyClass(state, domain):
    assert domain in ComponentDomainEnum
    type = state.get("type")
    cls = _componentRegistry.get(type, DefaultComponentProxy)
    assert issubclass(cls, BaseComponentProxy)
    return cls

def instantiate(logger, parent, identifier, manager, 
                componentContext, state, domain, *args, **kwargs):
    cls = getProxyClass(state, domain)
    return cls(logger, parent, identifier, manager, 
               componentContext, state, domain, *args, **kwargs)


class IComponentListener(Interface):
    def onComponenetMoodChanged(self, component, mood):
        pass
    
    def onComponentRunning(self, component, worker):
        pass
    
    def onComponentLost(self, component, worker):
        pass


class BaseComponentProxy(FlumotionProxy):

    def __init__(self, logger, parent, identifier, manager, 
                 componentContext, componentState, domain, listenerInterfaces):
        FlumotionProxy.__init__(self, logger, parent, identifier, 
                                manager, listenerInterfaces)
        self._context = componentContext
        self._domain = domain
        self._componentState = componentState
        self._uiState = None
        self._worker = None
        self._mood = None
        
        
    ## Public Methods ##
    
    def getName(self):
        assert self._componentState, "Component has been removed"
        return self._componentState.get('name')
    
    def getDomain(self):
        return self._domain
    
    def isRunning(self):
        return (self._worker != None)
    
    def getWorker(self):
        return self._worker
    
    def getMood(self):
        return self._mood

    
    ## Virtual Methods ##
    
    def _onSetUIState(self, uiState):
        pass
    
    def _onUnsetUIState(self, uiState):
        pass

    
    ## Overriden Methods ##
    
    def _doSyncListener(self, listener):
        assert self._componentState, "Component has been removed"
        if self.isActive():
            self._fireEventTo(self._mood, listener, "ComponenetMoodChanged")
            if self._worker:
                self._fireEventTo(self._worker, listener, "ComponenetRunning")

    def _onActivated(self):
        cs = self._componentState
        cs.addListener(self, self._componentStateSet)
        self.__componentMoodChanged(cs.get('mood'))
        self.__componentWorkerChanged(cs.get('workerName'))

    def _onRemoved(self):
        assert self._componentState, "Component has already been removed"
        cs = self._componentState
        cs.removeListener(self)
        if self._uiState:
            self._onUnsetUIState(self._uiState)
    
    def _doDiscard(self):
        assert self._componentState, "Component has already been discarded"
        self._uiState = None
        self._componentState = None
    

    ## Component State Listeners ##
    
    def _componentStateSet(self, state, key, value):
        self.log("Component '%s' state '%s' set to '%s'",
                 self.getName(), key, value)
        if key == 'mood':
            if self.isActive():
                self.__componentMoodChanged(value)
        elif key == 'workerName':
            self.__componentWorkerChanged(value)


    ## Protected Virtual Methods ##
    
    def _onComponenetRunning(self, worker):
        pass
    
    def _onComponentLost(self, worker):
        pass
    

    ## Protected Methods ##
    
    def _callRemote(self, methodName, *args, **kwargs):
        assert self._componentState, "Component has been removed"
        return self._manager._componentCallRemote(self._componentState,
                                                  methodName, 
                                                  *args, **kwargs)


    ## Private Methods ##
    
    def __componentWorkerChanged(self, workerName):
        if self._worker:
            oldWorker = self._worker
            self._worker = None
            self.__discardUIState()
            self._onComponentLost(oldWorker)
            self._fireEvent(oldWorker, "ComponentLost")
        if workerName:
            newWorker = self._manager.getWorkerByName(workerName)
            if newWorker:
                self._worker = newWorker
                self._onComponenetRunning(newWorker)
                self._fireEvent(newWorker, "ComponentRunning")
            else:
                self.warning("Component '%s' said to be running "
                             + "on an unknown worker '%s'",
                             self.getName(), workerName)
                
    def __componentMoodChanged(self, moodnum):
        mood = moods.get(moodnum)
        if (mood == moods.happy) and (self._uiState == None):
            self.__retrieveUIState()
        if mood != self._mood:
            self._mood = mood
            self._fireEvent(mood, "ComponenetMoodChanged")

    def __discardUIState(self):
        if self._uiState:
            self._onUnsetUIState(self._uiState)
            self._uiState = None

    def __retrieveUIState(self):
        d = self._callRemote('getUIState')
        d.addCallbacks(self.__uiStateRetrievalDone,
                       self.__uiStateRetrievalFailed)
    
    def __uiStateRetrievalDone(self, uiState):
        self.log("Component '%s' received UI State", self.getName())
        self._uiState = uiState
        self._onSetUIState(uiState)
    
    def __uiStateRetrievalFailed(self, failure):
        self.warning("Component '%s' fail to retrieve its UI state: %s",
                     self.getName(), log.getFailureMessage(failure))



class DefaultComponentProxy(BaseComponentProxy):
    
    def __init__(self, logger, parent, identifier, manager, 
                 componentContext, componentState, domain):
        BaseComponentProxy.__init__(self, logger, parent, identifier, manager,
                                    componentContext, componentState, 
                                    domain, IComponentListener)


class ComponentProxy(BaseComponentProxy):
    
    def __init__(self, logger, parent, identifier, manager, 
                 componentContext, componentState, domain, listenerInterfaces):
        BaseComponentProxy.__init__(self, logger, parent, identifier, manager,
                                    componentContext, componentState, domain, 
                                    listenerInterfaces)

        
    ## Virtual Methods ##
    
    def _doBroadcastUIState(self, uiState):
        pass
    
    def _onUIStateSet(self, uiState, key, value):
        pass
    
    def _onUIStateAppend(self, uiState, key, value):
        pass
    
    def _onUIStateRemove(self, uiState, key, value):
        pass
    
    def _onUIStateSetitem(self, uiState, key, subkey, value):
        pass
    
    def _onUIStateDelitem(self, uiState, key, subkey, value):
        pass

    
    ## Overriden Methods ##
    
    def _onSetUIState(self, uiState):
        uiState.addListener(self, 
                            self._onUIStateSet,
                            self._onUIStateAppend,
                            self._onUIStateRemove,
                            self._onUIStateSetitem,
                            self._onUIStateDelitem)
        self._doBroadcastUIState(uiState)
    
    def _onUnsetUIState(self, uiState):
        uiState.removeListener(self)

    
    