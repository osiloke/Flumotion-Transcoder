# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import signal

from zope.interface import Interface, implements
from twisted.internet import defer

from flumotion.common import common
#To register Jellyable classes
from flumotion.common import componentui
from flumotion.common.errors import UnknownComponentError
from flumotion.common.errors import ComponentError, BusyComponentError
from flumotion.common.planet import moods

from flumotion.transcoder import log
from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.enums import ComponentDomainEnum
from flumotion.transcoder.admin import utils, constants
from flumotion.transcoder.admin.waiters import SimpleWaiter, ValueWaiter
from flumotion.transcoder.admin.errors import OrphanComponentError
from flumotion.transcoder.admin.compprops import GenericComponentProperties
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
    def onComponentMoodChanged(self, component, mood):
        pass
    
    def onComponentRunning(self, component, worker):
        pass
    
    def onComponentOrphaned(self, component, worker):
        pass


class ComponentListener(object):
    
    implements(IComponentListener)
    
    def onComponentMoodChanged(self, component, mood):
        pass
    
    def onComponentRunning(self, component, worker):
        pass
    
    def onComponentOrphaned(self, component, worker):
        pass


class BaseComponentProxy(FlumotionProxy):

    properties_factory = GenericComponentProperties

    def __init__(self, logger, parent, identifier, manager, 
                 componentContext, componentState, domain, listenerInterfaces):
        FlumotionProxy.__init__(self, logger, parent, identifier, 
                                manager, listenerInterfaces)
        self._context = componentContext
        self._domain = domain
        self._componentState = componentState
        self._uiState = None
        self._requestedWorkerName = None
        self._worker = None
        self._mood = ValueWaiter()
        self._properties = SimpleWaiter()
        

    def addListener(self, listener):
        FlumotionProxy.addListener(self, listener)
        
    ## Public Methods ##
    
    def isValid(self):
        return self._componentState != None
    
    def getName(self):
        assert self._componentState, "Component has been removed"
        return self._componentState.get('name')
    
    def getContext(self):
        return self._context
    
    def getDomain(self):
        return self._domain
    
    def isRunning(self):
        return (self._worker != None)
    
    def getWorker(self):
        return self._worker
    
    def getRequestedWorkerName(self):
        self._requestedWorkerName
    
    def getRequestedWorker(self):
        if self._requestedWorkerName:
            return self._manager.getWorkerByName(self._requestedWorkerName)
        return None
    
    def getMood(self):
        return self._mood.getValue()

    def waitHappy(self, timeout=None):
        return self._mood.wait([moods.happy], 
                               [moods.lost, moods.sad], 
                               timeout)

    def waitMood(self, mood, timeout=None):
        return self._mood.wait([mood], None, timeout)

    def waitMoodChange(self, timeout=None):
        return self._mood.wait(None, None, timeout)

    def getProperties(self):
        return self._properties.getValue()
    
    def waitProperties(self, timeout=None):
        return self._properties.wait(timeout)

    def start(self):
        assert self._componentState, "Component has been removed"
        d = self._manager._callRemote('componentStart', 
                                      self._componentState)
        d.addCallback(utils.overrideResult, self)
        return d
    
    def stop(self):
        assert self._componentState, "Component has been removed"
        d = self._manager._callRemote('componentStop', 
                                      self._componentState)
        d.addCallback(utils.overrideResult, self)
        return d
    
    def restart(self):
        assert self._componentState, "Component has been removed"
        d = self._manager._callRemote('componentRestart', 
                                      self._componentState)
        d.addCallback(utils.overrideResult, self)
        return d
    
    def delete(self):
        assert self._componentState, "Component has been removed"
        d = self._manager._callRemote('deleteComponent', 
                                      self._componentState)
        d.addCallback(utils.overrideResult, self)
        return d

    def forceStop(self):
        """
        Use with caution, this method will try all it can and
        more than one time to stop the component.
        It will stop it, and kill it if neccessary.
        """
        assert self._componentState, "Component has been removed"
        mood = self.getMood()
        if mood == moods.sleeping:
            return defer.succeed(self)
        else:
            d = defer.Deferred()
            status = {"can_delete": False}
            self.__asyncForceStop(defer._nothing, status, self.getLabel(), d)
            return d
        
    def forceDelete(self):
        """
        Use with caution, this method will try all it can and
        more than one time to delete the component.
        It will stop it, delete it and kill it if neccessary.
        """
        assert self._componentState, "Component has been removed"
        d = defer.Deferred()
        self.__asyncStopOrDelete(defer._nothing, {}, self.getLabel(), d)
        return d

    def kill(self):
        # First try SIGTERM
        d = self.signal(signal.SIGTERM)
        # And wait for a while
        d.addCallback(utils.delayedSuccess, constants.COMPONENT_WAIT_TO_KILL)
        # Try SIGKILL if the component still exists on the worker
        d.addCallback(utils.dropResult, self.signal, signal.SIGKILL)        
        # And wait for a while
        d.addCallback(utils.delayedSuccess, constants.COMPONENT_WAIT_TO_KILL)
        # If UnknownComponentError has not been raise try a last time
        d.addCallback(utils.dropResult, self.signal, signal.SIGKILL)
        d.addCallbacks(utils.overrideResult, utils.resolveFailure, 
                       callbackArgs=(False,),
                       errbackArgs=(True, UnknownComponentError))
        return d
    
    def signal(self, sig):
        assert self._componentState, "Component has been removed"
        if not self._worker:
            msg = "Component '%s' worker is not running" % self.getLabel()
            err = OrphanComponentError(msg)
            return defer.fail(err)
        return self._worker._callRemote("killJob", self._getAvatarId(), sig)

    ## Virtual Methods ##
    
    def _onSetUIState(self, uiState):
        pass
    
    def _onUnsetUIState(self, uiState):
        pass

    
    ## Overriden Methods ##
    
    def _doSyncListener(self, listener):
        assert self._componentState, "Component has been removed"
        if self.isActive():
            self._fireEventTo(self._mood.getValue(), listener, "ComponentMoodChanged")
            if self._worker:
                self._fireEventTo(self._worker, listener, "ComponentRunning")

    def _onActivated(self):
        cs = self._componentState
        cs.addListener(self, self._componentStateSet)
        self.__componentMoodChanged(cs.get('mood'))
        self.__componentActiveWorkerChanged(cs.get('workerName'))
        self.__componentRequestedWorkerChanged(cs.get('workerRequested'))

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
                 self.getLabel(), key, value)
        if key == 'mood':
            if self.isActive():
                self.__componentMoodChanged(value)
        elif key == 'workerName':
            self.__componentActiveWorkerChanged(value)
        elif key == 'workerRequested':
            self.__componentRequestedWorkerChanged(value)


    ## Protected Virtual Methods ##
    
    def _extractProperties(self, workerContext, state):
        conf = state.get("config")
        assert conf != None, "Component state without config dict"
        props = conf.get("properties")
        assert props != None, "Component state without porperty dict"
        return self.properties_factory.createFromWorkerDict(workerContext, props)
    
    def _onComponentRunning(self, worker):
        pass
    
    def _onComponentOrphaned(self, worker):
        pass
    

    ## Protected Methods ##

    def _getAvatarId(self):
        return common.componentId(self._parent.getName(), self.getName())
        
    def _callRemote(self, methodName, *args, **kwargs):
        assert self._componentState, "Component has been removed"
        return self._manager._componentCallRemote(self._componentState,
                                                  methodName, 
                                                  *args, **kwargs)


    ## Private Methods ##
    
    def __componentRequestedWorkerChanged(self, workerName):
        self._requestedWorkerName = workerName
        mgrCtx = self.getManager().getContext()
        workerCtx = mgrCtx.getWorkerContext(workerName)
        props = self._extractProperties(workerCtx, self._componentState)
        self._properties.setValue(props)
    
    def __componentActiveWorkerChanged(self, workerName):
        # Because the active worker name is set to None 
        # when the worker is removed, we can keep an hard 
        # reference to the object
        if self._worker:
            oldWorker = self._worker
            self._worker = None
            self.__discardUIState()
            self._onComponentOrphaned(oldWorker)
            if self.isActive():
                self._fireEvent(oldWorker, "ComponentOrphaned")
        if workerName:
            newWorker = self._manager.getWorkerByName(workerName)
            if newWorker:
                self._worker = newWorker
                self._onComponentRunning(newWorker)
                if self.isActive():
                    self._fireEvent(newWorker, "ComponentRunning")
            else:
                self.warning("Component '%s' said to be running "
                             + "on an unknown worker '%s'",
                             self.getLabel(), workerName)
                
    def __componentMoodChanged(self, moodnum):
        mood = moods.get(moodnum)
        if (mood == moods.happy) and (self._uiState == None):
            self.__retrieveUIState()
        if mood != self._mood.getValue():
            self._mood.setValue(mood)
            self._fireEvent(mood, "ComponentMoodChanged")

    def __discardUIState(self):
        if self._uiState:
            self._onUnsetUIState(self._uiState)
            self._uiState = None

    def __retrieveUIState(self):
        d = self._callRemote('getUIState')
        d.addCallbacks(self.__asyncUIStateRetrievalDone,
                       self.__asyncUIStateRetrievalFailed)
    
    def __asyncUIStateRetrievalDone(self, uiState):
        self.log("Component '%s' received UI State", self.getLabel())
        self._uiState = uiState
        self._onSetUIState(uiState)
    
    def __asyncUIStateRetrievalFailed(self, failure):
        self.warning("Component '%s' fail to retrieve its UI state: %s",
                     self.getLabel(), log.getFailureMessage(failure))

    def __isOperationTerminated(self, status, resultDeferred):
        if not self.isValid():
            # Assume the objectives is fulfilled,
            resultDeferred.callback(self)
            return True
        return False
    
    def __asyncStopOrDelete(self, _, status, label, resultDeferred):
        if self.__isOperationTerminated(status, resultDeferred): return
        mood = self.getMood()
        if mood != moods.sleeping:
            self.__asyncForceStop(_, status, label, resultDeferred)
        else:
            self.__asyncForceDelete(_, status, label, resultDeferred)
    
    def __asyncForceStop(self, _, status, label, resultDeferred):
        if self.__isOperationTerminated(status, resultDeferred): return
        if not status.get("can_stop", True):
            resultDeferred.callback(self)
            return
        d = self.stop()
        args = (status, label, resultDeferred)
        d.addCallbacks(self.__asyncForceDelete,
                       self.__asyncForceStopFailed,  
                       callbackArgs=args, errbackArgs=args)  

    def __asyncForceDelete(self, _, status, label, resultDeferred):
        if self.__isOperationTerminated(status, resultDeferred): return
        if not status.get("can_delete", True):
            resultDeferred.callback(self)
            return
        d = self.delete()
        args = (status, label, resultDeferred)
        d.addCallbacks(resultDeferred.callback,
                       self.__asyncForceDeleteFailed,
                       errbackArgs=args)
    
    def __asyncRetryKillIfNeeded(self, success, status, label, resultDeferred):
        if self.__isOperationTerminated(status, resultDeferred): return
        if success:
            # After beeing killed the componenet go sad, so it should be 
            # stopped again. For this we reset the stop retries counter.
            status["stop-retries"] = 0
            status["already_killed"] = True
            self.__asyncForceStop(defer._nothing, status, label, resultDeferred)
            return
        status["kill-retries"] = status.setdefault("Kill-retries", 0) + 1
        if status["kill-retries"] > constants.FORCED_DELETION_MAX_RETRY:
             # if kill fail, theres nothing we can do, do we ?
            msg = "Could not force component '%s' deletion" % label
            self.warning("%s", msg)
            resultDeferred.errback(TranscoderError(msg))
            return
        # Failed to kill, try again to stop or delete
        self.__asyncStopOrDelete(defer._nothing, status, 
                                 label, resultDeferred)
        
    def __asyncForceKillFailed(self, failure, status, label, resultDeferred):
        if self.__isOperationTerminated(status, resultDeferred): return
        if failure.check(OrphanComponentError):
            # The component don't have worker
            self.__asyncStopOrDelete(defer._nothing, status, 
                                     label, resultDeferred)
            return
        self.warning("Component '%s' killing failed: %s",
                     label, log.getFailureMessage(failure))
        self.__asyncRetryKillIfNeeded(False, status, label, resultDeferred)
    
    def __asyncForceStopFailed(self, failure, status, label, resultDeferred):
        if self.__isOperationTerminated(status, resultDeferred): return
        status["stop-retries"] = status.setdefault("stop-retries", 0) + 1
        if status["stop-retries"] > constants.FORCED_DELETION_MAX_RETRY:
            if (status.get("already_killed", False) 
                or (not status.get("can_kill", True))):
                # if already killed or we are not allowed to kill, 
                # theres nothing we can do, do we ?
                msg = "Could not force component '%s' deletion" % label
                self.warning("%s", msg)
                resultDeferred.errback(TranscoderError(msg))
                return
            # If we already tried too much, kill the component
            d = self.kill()
            args = (status, label, resultDeferred)
            d.addCallbacks(self.__asyncRetryKillIfNeeded, 
                           self.__asyncForceKillFailed,
                           callbackArgs=args, errbackArgs=args)
            return
        if failure.check(BusyComponentError):
            # The component is buzy changing mood,
            # so wait mood change (with a timeout)    
            d = self.waitMoodChange(constants.FORCED_DELETION_TIMEOUT)
            d.addBoth(self.__asyncForceStop, status, label, resultDeferred)
            return
        # FIXME: make flumotion raise a specific exception 
        # when there is mood conflicts
        if failure.check(ComponentError):
            #Maybe the component was already stopped ?
            if self.getMood() == moods.sleeping:
                self.__asyncForceDelete(defer._nothing, status, 
                                        label, resultDeferred)
                return
        # The component raised an error
        # so just log the error and try again
        self.warning("Fail to stop component '%s': %s",
                     label, log.getFailureMessage(failure))
        self.__asyncForceStop(defer._nothing, status, label, resultDeferred)
    
    def __asyncForceDeleteFailed(self, failure, status, label, resultDeferred):
        if self.__isOperationTerminated(status, resultDeferred): return
        status["delete-retries"] = status.setdefault("delete-retries", 0) + 1
        if status["delete-retries"] > constants.FORCED_DELETION_MAX_RETRY:
             # if deletion fail, theres nothing we can do, do we ?
            msg = "Could not force component '%s' deletion" % label
            self.warning("%s", msg)
            resultDeferred.errback(TranscoderError(msg))
            return
        # The component is still buzzy, don't log, just retry
        if not failure.check(BusyComponentError):
            self.warning("Fail to delete component '%s': %s",
                         label, log.getFailureMessage(failure))
        #FIXME: What about already deleted component ?
        self.__asyncForceDelete(defer._nothing, status, label, resultDeferred)


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

    
    