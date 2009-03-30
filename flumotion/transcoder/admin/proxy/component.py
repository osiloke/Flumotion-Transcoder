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

from twisted.spread.pb import PBConnectionLost, DeadReferenceError

from flumotion.common import common
#To register Jellyable classes
from flumotion.common import componentui, errors as ferrors
from flumotion.common.planet import moods

from flumotion.inhouse import log, defer, utils, waiters

from flumotion.transcoder import errors
from flumotion.transcoder.admin import adminconsts, admerrs
from flumotion.transcoder.admin.enums import ComponentDomainEnum
from flumotion.transcoder.admin.property import base as pbase
from flumotion.transcoder.admin.proxy import base


_componentRegistry = {}

def registerProxy(type, cls):
    #assert not (type in _componentRegistry), "Already Registered"
    _componentRegistry[type] = cls

def getProxyClass(state, domain):
    assert domain in ComponentDomainEnum
    type = state.get("type")
    cls = _componentRegistry.get(type, DefaultComponentProxy)
    assert issubclass(cls, BaseComponentProxy)
    return cls

def instantiate(logger, parentPxy, identifier, managerPxy,
                compCtx, compState, domain, *args, **kwargs):
    cls = getProxyClass(compState, domain)
    return cls(logger, parentPxy, identifier, managerPxy,
               compCtx, compState, domain, *args, **kwargs)


class BaseComponentProxy(base.BaseProxy):

    properties_factory = pbase.GenericComponentProperties

    def __init__(self, logger, parentPxy, identifier,
                 managerPxy, compCtx, comptState, domain):
        conf = comptState.get('config', None)
        name = comptState.get('name')
        label = (conf and conf.get('label', None))
        base.BaseProxy.__init__(self, logger, parentPxy, identifier,
                                managerPxy, name=name, label=label)
        self._compCtx = compCtx
        self._domain = domain
        self._compState = comptState
        self._retrievingUIState = False
        self._uiState = waiters.AssignWaiters("Component UIState")
        self._requestedWorkerName = comptState.get('workerRequested')
        self._workerPxy = None
        self._pid = None
        self._mood = waiters.ValueWaiters("Component Mood")
        self._properties = waiters.AssignWaiters("Component Properties")
        self._messageIds = {} # {identifier: None}
        # Registering Events
        self._register("mood-changed")
        self._register("running")
        self._register("orphaned")


    ## Public Methods ##

    def isValid(self):
        return self._compState != None

    def getComponentContext(self):
        return self._compCtx

    def getDomain(self):
        return self._domain

    def waitUIState(self, timeout=None):
        if not self.isRunning():
            error = errors.TranscoderError("Cannot retrieve UI state of "
                                           "a non-running component")
            return defer.fail(error)
        self.__retrieveUIState(timeout)
        d = self._waitUIState(timeout)
        d.addCallback(defer.overrideResult, self)
        return d

    def isRunning(self):
        return (self._workerPxy != None)

    def getWorkerProxy(self):
        return self._workerPxy

    def getRequestedWorkerName(self):
        return self._requestedWorkerName

    def getRequestedWorkerProxy(self):
        if self._requestedWorkerName:
            return self._managerPxy.getWorkerProxyByName(self._requestedWorkerName)
        return None

    def getPID(self):
        return self._pid

    def getMood(self):
        return self._mood.getValue()

    def getProperties(self):
        return self._properties.getValue()

    def waitHappy(self, timeout=None):
        return self._mood.wait([moods.happy],
                               [moods.lost, moods.sad],
                               timeout)

    def waitMood(self, mood, timeout=None):
        return self._mood.wait([mood], None, timeout)

    def waitMoodChange(self, timeout=None):
        return self._mood.wait(None, None, timeout)

    def waitProperties(self, timeout=None):
        return self._properties.wait(timeout)

    def start(self):
        assert self._compState, "Component has been removed"
        self.log("Starting component '%s'", self.label)
        d = self._managerPxy._callRemote('componentStart',
                                      self._compState)
        d.addCallback(defer.overrideResult, self)
        return d

    def stop(self):
        assert self._compState, "Component has been removed"
        self.log("Stopping component '%s'", self.label)
        d = self._managerPxy._callRemote('componentStop',
                                      self._compState)
        d.addCallback(defer.overrideResult, self)
        return d

    def restart(self):
        assert self._compState, "Component has been removed"
        self.log("Restarting component '%s'", self.label)
        d = self._managerPxy._callRemote('componentRestart',
                                      self._compState)
        d.addCallback(defer.overrideResult, self)
        return d

    def delete(self):
        assert self._compState, "Component has been removed"
        self.log("Deleting component '%s'", self.label)
        d = self._managerPxy._callRemote('deleteComponent',
                                      self._compState)
        d.addCallback(defer.overrideResult, self)
        return d

    def forceStop(self):
        """
        Use with caution, this method will try all it can and
        more than one time to stop the component.
        It will stop it, and kill it if neccessary.
        """
        assert self._compState, "Component has been removed"
        self.log("Stopping (Forced) component '%s'", self.label)
        mood = self.getMood()
        if mood == moods.sleeping:
            return defer.succeed(self)
        else:
            d = defer.Deferred()
            status = {"can_delete": False}
            self.__asyncForceStop(None, status, self.label, d)
            return d

    def forceDelete(self):
        """
        Use with caution, this method will try all it can and
        more than one time to delete the component.
        It will stop it, delete it and kill it if neccessary.
        """
        assert self._compState, "Component has been removed"
        self.log("Deleting (Forced) component '%s'", self.label)
        d = defer.Deferred()
        self.__stopOrDelete(None, {}, self.label, d)
        return d

    def kill(self):
        self.log("Killing component '%s'", self.label)
        # First try SIGTERM
        d = self.signal(signal.SIGTERM)
        # And wait for a while
        d.addCallback(defer.delayedSuccess, adminconsts.COMPONENT_WAIT_TO_KILL)
        # Try SIGKILL if the component still exists on the worker
        d.addCallback(defer.dropResult, self.signal, signal.SIGKILL)
        # And wait for a while
        d.addCallback(defer.delayedSuccess, adminconsts.COMPONENT_WAIT_TO_KILL)
        # If ferrors.UnknownComponentError has not been raise try a last time
        d.addCallback(defer.dropResult, self.signal, signal.SIGKILL)
        d.addCallbacks(defer.overrideResult, defer.resolveFailure,
                       callbackArgs=(False,),
                       errbackArgs=(True, ferrors.UnknownComponentError))
        return d

    def signal(self, sig):
        assert self._compState, "Component has been removed"
        if not self._workerPxy:
            msg = "Component '%s' worker is not running" % self.label
            err = admerrs.OrphanComponentError(msg)
            return defer.fail(err)
        return self._workerPxy._callRemote("killJob", self._getAvatarId(), sig)


    ## Overriden Methods ##

    def refreshListener(self, listener):
        assert self._compState, "Component has been removed"
        if self.isActive():
            self.emitTo("mood-changed", listener, self._mood.getValue())
            if self._workerPxy:
                self.emitTo("running", listener, self._workerPxy)
            if self._hasUIState():
                self._doBroadcastUIState(self._getUIState())

    def _onActivated(self):
        cs = self._compState
        cs.addListener(self, self._componentStateSet,
                       self._componentStateAppend)
        self.__componentMoodChanged(cs.get('mood'))
        self.__componentActiveWorkerChanged(cs.get('workerName'))
        self.__componentRequestedWorkerChanged(cs.get('workerRequested'))

    def _onRemoved(self):
        assert self._compState, "Component has already been removed"
        if self.isActive():
            cs = self._compState
            cs.removeListener(self)
        if self._hasUIState():
            self._onUnsetUIState(self._getUIState())

    def _doDiscard(self):
        assert self._compState, "Component has already been discarded"
        self._setUIState(None)
        self._compState = None


    ## Component State Listeners ##

    def _componentStateSet(self, state, key, value):
        self.log("Component '%s' state '%s' set to '%s'",
                 self.label, key, value)
        try:
            if key == 'mood':
                if self.isActive():
                    self.__componentMoodChanged(value)
            elif key == 'workerName':
                self.__componentActiveWorkerChanged(value)
            elif key == 'workerRequested':
                self.__componentRequestedWorkerChanged(value)
            elif key == 'pid':
                self._pid = value
        except Exception, e:
            log.notifyException(self, e,
                                "Exception when setting component '%s' "
                                "state key '%s' to '%s'",
                                self.label, key, value)
            #FIXME: Do some error handling ?

    def _componentStateAppend(self, state, key, value):
        try:
            if key == 'messages':
                if value.id in self._messageIds:
                    return
                self._messageIds[value.id] = None
                self._onComponentMessage(value)
        except Exception, e:
            log.notifyException(self, e,
                                "Exception when appening value '%s' "
                                "to component '%s' state list '%s'",
                                value, self.label, key)
            #FIXME: Do some error handling ?


    ## Protected Virtual Methods ##

    def _doBroadcastUIState(self, uiState):
        pass

    def _onSetUIState(self, uiState):
        pass

    def _onUnsetUIState(self, uiState):
        pass

    def _doExtractProperties(self, workerCtx, state):
        conf = state.get("config")
        assert conf != None, "Component state without config dict"
        props = conf.get("properties")
        assert props != None, "Component state without porperty dict"
        try:
            return self.properties_factory.createFromComponentDict(workerCtx, props)
        except Exception, e:
            log.notifyException(self, e,
                                "Exception during component '%s' "
                                "properties creation", self.label)
            return None

    def _onComponentRunning(self, workerPxy):
        pass

    def _onComponentOrphaned(self, workerPxy):
        pass

    def _onComponentMessage(self, message):
        pass


    ## Protected Methods ##

    def _getUIDictValue(self, key, name, default):
        if not self._hasUIState():
            return default
        return self.__getUIDictValue(self._getUIState(), key, name, default)

    def _waitUIDictValue(self, key, name, default, timeout=None):
        d = self._waitUIState(timeout)
        d.addCallback(self.__getUIDictValue, key, name, default)
        return d

    def _waitUIState(self, timeout=None):
        return self._uiState.wait(timeout)

    def _hasUIState(self):
        return self._uiState.getValue() != None

    def _getUIState(self):
        return self._uiState.getValue()

    def _setUIState(self, uistate):
        self._uiState.setValue(uistate)

    def _getAvatarId(self):
        return common.componentId(self.parent.getName(), self.getName())

    def _callRemote(self, methodName, *args, **kwargs):
        assert self._compState, "Component has been removed"
        return self._managerPxy._componentCallRemote(self._compState,
                                                     methodName,
                                                     *args, **kwargs)


    ## Private Methods ##

    def __cbGotActiveWorker(self, workerPxy, name):
        currName = self._compState.get('workerName')
        if currName != name:
            self.log("Component '%s' active worker changed from '%s' to '%s'",
                     self.label, name, currName)
            return
        self._workerPxy = workerPxy
        self._onComponentRunning(workerPxy)
        if self.isActive():
            self.emit("running", workerPxy)

    def __ebGetActiveWorkerFail(self, failure, name):
        currName = self._compState.get('workerName')
        if currName != name:
            self.log("Component '%s' active worker changed from '%s' to '%s'",
                     self.label, name, currName)
            return
        self.warning("Component '%s' said to be running "
                     + "on an unknown worker '%s'",
                     self.label, name)

    def __getUIDictValue(self, state, key, name, default):
        values = state.get(key, None)
        if values:
            return values.get(name, default)
        return default

    def __componentRequestedWorkerChanged(self, workerName):
        self._requestedWorkerName = workerName
        compCtx = self.getComponentContext()
        mgrCtx = compCtx.getManagerContext()
        adminCtx = mgrCtx.getAdminContext()
        workerCtx = adminCtx.getWorkerContextByName(workerName)
        props = self._doExtractProperties(workerCtx, self._compState)
        self._properties.setValue(props)

    def __componentActiveWorkerChanged(self, workerName):
        # Because the active worker name is set to None
        # when the worker is removed, we can keep an hard
        # reference to the object
        if self._workerPxy:
            oldWorker = self._workerPxy
            self._workerPxy = None
            self.__discardUIState()
            self._onComponentOrphaned(oldWorker)
            if self.isActive():
                self.emit("orphaned", oldWorker)
        if workerName:
            timeout = adminconsts.WAIT_WORKER_TIMEOUT
            d = self._managerPxy.waitWorkerProxyByName(workerName, timeout)
            args = (workerName,)
            d.addCallbacks(self.__cbGotActiveWorker,
                           self.__ebGetActiveWorkerFail,
                           callbackArgs=args, errbackArgs=args)

    def __componentMoodChanged(self, moodnum):
        mood = moods.get(moodnum)
        if mood != self._mood.getValue():
            self._mood.setValue(mood)
            self.emit("mood-changed", mood)

    def __discardUIState(self):
        self._retrievingUIState = False
        if self._hasUIState():
            self._onUnsetUIState(self._getUIState())
            self._setUIState(None)

    def __retrieveUIState(self, timeout=None):
        if self._retrievingUIState: return
        self._retrievingUIState = True
        d = utils.callWithTimeout(timeout, self._callRemote, 'getUIState')
        d.addCallbacks(self.__cbUIStateRetrievalDone,
                       self.__ebUIStateRetrievalFailed)

    def __cbUIStateRetrievalDone(self, uiState):
        self.log("Component '%s' received UI State", self.label)
        if self._retrievingUIState:
            self._setUIState(uiState)
            self._onSetUIState(uiState)

    def __ebUIStateRetrievalFailed(self, failure):
        self._retrievingUIState = False
        self.warning("Component '%s' fail to retrieve its UI state: %s",
                     self.label, log.getFailureMessage(failure))
        self._uiState.fail(failure)

    def __isOperationTerminated(self, failure, status, resultDef):
        if not self.isValid():
            # Assume the objectives is fulfilled,
            resultDef.callback(self)
            return True
        if failure:
            if failure.check(DeadReferenceError):
                msg = ("Forced Stop/Delete of component '%s' aborted "
                       "because the PB reference is dead" % self.getLabel())
                self.warning("%s", msg)
                error = errors.OperationAbortedError(msg, cause=failure)
                resultDef.errback(error)
                return True
            if failure.check(ferrors.UnknownComponentError):
                self.debug("Forced Stop/Delete of component '%s' aborted "
                           "because the component is unknown (already deleted ?)",
                           self.label)
                resultDef.callback(self)
                return True
            if failure.check(PBConnectionLost):
                msg = ("Forced Stop/Delete of component '%s' aborted "
                       "because the remote connection was lost" % self.label)
                self.warning("%s", msg)
                error = admerrs.OperationAbortedError(msg, cause=failure)
                resultDef.errback(error)
                return True
            status['last-message'] = log.getFailureMessage(failure)
        return False

    def __deletionFailed(self, status, label, resultDef):
        info = "Could not force component '%s' deletion" % label
        self.warning("%s", info)
        err = status.get('last-message', None)
        msg = info + ((err and (": " + err)) or "")
        resultDef.errback(errors.TranscoderError(msg))

    def __stopOrDelete(self, _, status, label, resultDef):
        if self.__isOperationTerminated(None, status, resultDef): return
        mood = self.getMood()
        if mood != moods.sleeping:
            self.__asyncForceStop(_, status, label, resultDef)
        else:
            self.__asyncForceDelete(_, status, label, resultDef)

    def __asyncForceStop(self, _, status, label, resultDef):
        if self.__isOperationTerminated(None, status, resultDef): return
        if not status.get("can_stop", True):
            resultDef.callback(self)
            return
        d = self.stop()
        args = (status, label, resultDef)
        # Call again __stopOrDelete, because flumotion do not changed
        # sad component's mood to sleeping when stopping them,
        # so we have to stop them again...
        d.addCallbacks(self.__stopOrDelete,
                       self.__asyncForceStopFailed,
                       callbackArgs=args, errbackArgs=args)

    def __asyncForceDelete(self, _, status, label, resultDef):
        if self.__isOperationTerminated(None, status, resultDef): return
        if not status.get("can_delete", True):
            resultDef.callback(self)
            return
        d = self.delete()
        args = (status, label, resultDef)
        d.addCallbacks(resultDef.callback,
                       self.__asyncForceDeleteFailed,
                       errbackArgs=args)

    def __asyncRetryKillIfNeeded(self, success, status, label, resultDef):
        if self.__isOperationTerminated(None, status, resultDef): return
        if success:
            # After beeing killed the componenet go sad, so it should be
            # stopped again. For this we reset the stop retries counter.
            status["stop-retries"] = 0
            status["already_killed"] = True
            self.__asyncForceStop(None, status, label, resultDef)
            return
        # Failed to kill, try again to stop or delete
        self.__stopOrDelete(None, status,
                            label, resultDef)

    def __asyncForceKillFailed(self, failure, status, label, resultDef):
        if self.__isOperationTerminated(failure, status, resultDef): return
        if failure.check(admerrs.OrphanComponentError):
            # The component don't have worker
            self.__stopOrDelete(None, status,
                                label, resultDef)
            return
        self.warning("Component '%s' killing failed: %s",
                     label, log.getFailureMessage(failure))
        self.__asyncRetryKillIfNeeded(False, status, label, resultDef)

    def __asyncForceStopFailed(self, failure, status, label, resultDef):
        if self.__isOperationTerminated(failure, status, resultDef): return
        status["stop-retries"] = status.setdefault("stop-retries", 0) + 1
        if status["stop-retries"] > adminconsts.FORCED_DELETION_MAX_RETRY:
            if (status.get("already_killed", False)
                or (not status.get("can_kill", True))):
                # if already killed or we are not allowed to kill,
                # theres nothing we can do, do we ?
                self.__deletionFailed(status, label, resultDef)
                return
            # If we already tried too much, kill the component
            status["kill-retries"] = status.setdefault("kill-retries", 0) + 1
            if status["kill-retries"] > adminconsts.FORCED_DELETION_MAX_RETRY:
                # if kill fail, theres nothing we can do, do we ?
                self.__deletionFailed(status, label, resultDef)
                return
            d = self.kill()
            args = (status, label, resultDef)
            d.addCallbacks(self.__asyncRetryKillIfNeeded,
                           self.__asyncForceKillFailed,
                           callbackArgs=args, errbackArgs=args)
            return
        if failure.check(ferrors.BusyComponentError):
            # The component is buzy changing mood,
            # so wait mood change (with a larger timeout)
            d = self.waitMoodChange(adminconsts.FORCED_DELETION_BUZY_TIMEOUT)
            d.addBoth(self.__stopOrDelete, status, label, resultDef)
            return
        # FIXME: make flumotion raise a specific exception
        # when there is mood conflicts
        if failure.check(ferrors.ComponentError):
            #Maybe the component was already stopped ?
            if self.getMood() == moods.sleeping:
                self.__asyncForceDelete(None, status,
                                        label, resultDef)
                return
        # The component raised an error
        # so just log the error and try again
        self.warning("Fail to stop component '%s': %s",
                     label, log.getFailureMessage(failure))
        self.__asyncForceStop(None, status, label, resultDef)

    def __asyncForceDeleteFailed(self, failure, status, label, resultDef):
        if self.__isOperationTerminated(failure, status, resultDef): return
        status["delete-retries"] = status.setdefault("delete-retries", 0) + 1
        if status["delete-retries"] > adminconsts.FORCED_DELETION_MAX_RETRY:
            # if deletion fail, theres nothing we can do, do we ?
            self.__deletionFailed(status, label, resultDef)
            return
        if failure.check(ferrors.BusyComponentError):
            # The component is buzy changing mood,
            # so wait mood change (with a larger timeout)
            d = self.waitMoodChange(adminconsts.FORCED_DELETION_BUZY_TIMEOUT)
            d.addBoth(self.__stopOrDelete, status, label, resultDef)
            return
        self.warning("Fail to delete component '%s': %s",
                     label, log.getFailureMessage(failure))
        self.__asyncForceDelete(None, status, label, resultDef)


class DefaultComponentProxy(BaseComponentProxy):

    def __init__(self, logger, parentPxy, identifier,
                 managerPxy, compCtx, compState, domain):
        BaseComponentProxy.__init__(self, logger, parentPxy, identifier,
                                    managerPxy, compCtx, compState, domain)


class ComponentProxy(BaseComponentProxy):

    def __init__(self, logger, parentPxy, identifier,
                 managerPxy, compCtx, compState, domain):
        BaseComponentProxy.__init__(self, logger, parentPxy, identifier,
                                    managerPxy, compCtx, compState, domain)
        # Registering Events
        self._register("message")


    ## Virtual Methods ##

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

    def _onComponentMessage(self, message):
        self.emit("message", message)
