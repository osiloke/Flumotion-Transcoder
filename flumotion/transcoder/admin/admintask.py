# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import Interface, implements, Attribute
from twisted.internet import reactor
from twisted.internet.error import ConnectionLost
from twisted.spread.pb import PBConnectionLost
from twisted.python.failure import Failure

from flumotion.common.planet import moods

from flumotion.inhouse import log, defer, utils, events, waiters

from flumotion.transcoder.admin import adminconsts, admerrs, interfaces
from flumotion.transcoder.admin.enums import TaskStateEnum
from flumotion.transcoder.admin.proxy import component


class IAdminTask(interfaces.IAdminInterface):

    label = Attribute("Task label")
    
    def isStarted(self):
        pass
    
    def hasTerminated(self):
        pass
    
    def getProperties(self):
        pass
    
    def addComponent(self, compPxy):
        pass
    
    def removeComponent(self, compPxy):
        pass
    
    def getActiveComponent(self):
        pass
    
    def getWorkerProxy(self):
        pass
    
    def start(self, paused=False, timeout=None):
        """
        Return a Deferred.
        """
    
    def pause(self, timeout=None):
        """
        Return a Deferred.
        """
    
    def resume(self, timeout=None):
        """
        Return a Deferred.
        """
    
    def stop(self, timeout=None):
        """
        Returns a Deferred.
        It's result will be the list of components 
        previously managed by this task.
        """
    
    def abort(self):
        pass
    
    def suggestWorker(self, worker):
        pass
    
    def waitPotentialWorker(self, timeout=None):
        """
        Return a Deferred.
        """

    def waitIdle(self, timeout=None):
        """
        Return a Deferred.
        Wait for the task to be in a stable idle state.
        """
        
    def waitActive(self, timeout=None):
        """
        Return a Deferred called when a component has been elected.
        """


class AdminTask(log.LoggerProxy, events.EventSourceMixin):
    
    implements(IAdminTask)

    LOAD_TIMEOUT = adminconsts.TASK_LOAD_TIMEOUT
    HAPPY_TIMEOUT = adminconsts.TASK_HAPPY_TIMEOUT
    START_DELAY = adminconsts.TASK_START_DELAY
    START_DELAY_FACTOR = adminconsts.TASK_START_DELAY_FACTOR
    HOLD_TIMEOUT = adminconsts.TASK_HOLD_TIMEOUT
    POTENTIAL_TIMEOUT = adminconsts.TASK_POTENTIAL_COMPONENT_TIMEOUT
    UISTATE_TIMEOUT = adminconsts.TASK_UISTATE_TIMEOUT
    MAX_RETRIES = 0
    
    def __init__(self, logger, label, properties):
        log.LoggerProxy.__init__(self, logger)
        self.label = label
        self._workerPxy = None # WorkerProxy
        self._state = TaskStateEnum.stopped
        self._startWaiters = waiters.PassiveWaiters("Admin Task Startup/Resuming")
        self._pendingName = None
        self._delayed = None # IDelayedCall
        self._activePxy = waiters.AssignWaiters("Admin Task Active Component")
        self._compPxys = {} # {component.ComponentProxy: None}
        self._properties = properties
        self._retry = 0
        self._holdTimeout = None
        self._processInterruptions = 0
    

    ## IAdminTask Implementation ##
        
    def getProperties(self):
        return self._properties

    def getProcessInterruptionCount(self):
        return self._processInterruptions

    def isStarted(self):
        return self._state == TaskStateEnum.started

    def hasTerminated(self):
        return self._state == TaskStateEnum.terminated

    def getActiveComponent(self):
        return self._activePxy.getValue()
    
    def getWorkerProxy(self):
        return self._workerPxy
    
    def getComponentProxies(self):
        return self._compPxys.keys()
    
    def iterComponentProxies(self):
        return self._compPxys.iterkeys()

    def addComponent(self, compPxy):
        assert isinstance(compPxy, component.ComponentProxy)
        assert not (compPxy in self._compPxys)
        self.log("Component '%s' added to task '%s'", 
                 compPxy.getName(), self.label)
        self._compPxys[compPxy] = None
        self._onComponentAdded(compPxy)
        # If there already is an elected component, stop it
        if self._hasElectedComponent():
            if not self._isElectedComponent(compPxy):
                self._stopComponent(compPxy)
        
    def removeComponent(self, compPxy):
        assert isinstance(compPxy, component.ComponentProxy)
        assert compPxy in self._compPxys
        self.log("Component '%s' removed from task '%s'", 
                 compPxy.getName(), self.label)
        del self._compPxys[compPxy]
        self._onComponentRemoved(compPxy)
        if compPxy == self.getActiveComponent():
            self.__relieveComponent()
    
    def start(self, paused=False, timeout=None):
        if not (self._state in [TaskStateEnum.stopped, 
                                TaskStateEnum.starting]):
            return defer.fail(admerrs.TranscoderError("Cannot start %s task '%s'"
                                              % (self._state.name,
                                                 self.label)))
        if self._state == TaskStateEnum.stopped:
            if paused:
                self.log("Starting already paused admin task '%s'",
                         self.label)
                self._state = TaskStateEnum.paused
                return defer.succeed(self)
            else:
                self.log("Ready to start admin task '%s'", self.label)
                self._state = TaskStateEnum.starting
                self.__startup()
        return self._startWaiters.wait(timeout)
    
    def pause(self, timeout=None):
        if self._state == TaskStateEnum.terminated:
            # If terminated, a task can be paused and resume silently
            return defer.succeed(self)
        if not (self._state in [TaskStateEnum.started]):
            return defer.fail(admerrs.TranscoderError("Cannot pause %s task '%s'"
                                              % (self._state.name,
                                                 self.label)))
        self.log("Pausing admin task '%s'", self.label)
        self._state = TaskStateEnum.paused
        # No longer have associated worker
        self._workerPxy = None
        # No longer started
        self._startWaiters.reset()
        return defer.succeed(self)
    
    def resume(self, timeout=None):
        if self._state == TaskStateEnum.terminated:
            # If terminated, a task can be rpaused and resume silently
            return defer.succeed(self)
        if not (self._state in [TaskStateEnum.paused, 
                                TaskStateEnum.resuming]):
            return defer.fail(admerrs.TranscoderError("Cannot resume %s task '%s'"
                                              % (self._state.name,
                                                 self.label)))
        if self._state == TaskStateEnum.paused:
            self.log("Ready to resume admin task '%s'", self.label)
            self._state = TaskStateEnum.resuming
            self.__startup()
        # Resuming and starting is the same for now
        return self._startWaiters.wait(timeout)
    
    def stop(self, timeout=None):
        """
        Relieve the selected component, and return a deferred that
        will be callback with the list of all the components 
        for the caller to take responsability of.
        After this, no component will/should be added or removed.
        """
        if self._state in [TaskStateEnum.stopped]:
            return defer.fail(admerrs.TranscoderError("Cannot stop %s task '%s'"
                                              % (self._state.name,
                                                 self.label)))
        self.log("Stopping admin task '%s'", self.label)
        self._state = TaskStateEnum.terminated
        self.__relieveComponent()
        for compPxy in self._compPxys:
            self._onComponentRemoved(compPxy)
        result = self._compPxys.keys()
        self._compPxys.clear()
        return defer.succeed(result)
    
    def abort(self):
        """
        After this, no components will/should be added or removed.
        """
        if self._state in [TaskStateEnum.terminated]:
            # Silently return because abort should always succeed
            return
        self.log("Aborting admin task '%s'", self.label)
        self._state = TaskStateEnum.terminated
        self.__relieveComponent()
        for compPxy in self._compPxys:
            self._onComponentRemoved(compPxy)
        self._compPxys.clear()
        return

    def suggestWorker(self, workerPxy):
        self.log("Worker '%s' suggested to admin task '%s'", 
                 workerPxy and workerPxy.label, self.label)
        if self._doAcceptSuggestedWorker(workerPxy):
            # Cancel pending components if any
            self._pendingName = None
            # If we change the worker, reset the retry counter
            self._resetRetryCounter()
            self._workerPxy = workerPxy
            # If we currently holding for a lost component, 
            # do not start a new one right now.
            if self._isHoldingLostComponent():
                self.log("Admin task '%s' avoid starting a new component "
                         "because it's holding a lost component", self.label)
            else:
                self.__startComponent()
            return self._workerPxy
        return None

    def waitIdle(self, timeout=None):
        compPxy = self.getActiveComponent()
        if compPxy:
            # Wait UI State to be sure the file events are fired
            d = compPxy.waitUIState(timeout)
            d.addBoth(defer.overrideResult, self)
        else:
            d = defer.succeed(self)
        self._doChainWaitIdle(d)
        return d

    def waitPotentialWorker(self, timeout=None):
        compPxy = self.getActiveComponent()
        if compPxy:
            return defer.succeed(compPxy.getWorkerProxy())
        d = self.__waitPotentialComponent(timeout)
        d.addCallbacks(self.__cbGetValidWorker,
                       self.__ebNoValidWorker)
        return d
    
    def waitActive(self, timeout=None):
        return self._activePxy.wait(timeout)
    

    ## Virtual Protected Methods ##
    
    def _onComponentAdded(self, compPxy):
        pass

    def _onComponentRemoved(self, compPxy):
        pass

    def _onComponentHold(self, compPxy):
        pass
    
    def _onComponentHoldCanceled(self, compPxy):
        pass
    
    def _onComponentLost(self, compPxy):
        pass
    
    def _onComponentRestored(self, compPxy):
        pass

    def _onComponentElected(self, compPxy):
        pass

    def _onComponentRelieved(self, compPxy):
        pass

    def _onComponentStartingUp(self, compPxy):
        pass

    def _onComponentStartupCanceled(self, compPxy):
        pass
    
    def _doChainWaitIdle(self, chain):
        pass
    
    def _doChainWaitPotentialComponent(self, chain):
        pass
    
    def _onStarted(self):
        pass
    
    def _doStartup(self):
        """
        Can return a Deferred.
        """
    
    def _doAcceptSuggestedWorker(self, workerPxy):
        return True
    
    def _doChainTerminate(self, chain, result):
        pass
    
    def _doTerminated(self, result):
        pass
    
    def _doAborted(self):
        pass
    
    def _doSelectPotentialComponent(self, compPxys):
        return None
    
    def _doLoadComponent(self, workerPxy, compName, compLabel,
                         compProperties, loadTimeout):
        return defer.failed(NotImplementedError())

    
    ## Protected Methods ##
    
    def _processInterruptionDetected(self):
        self._processInterruptions += 1
    
    def _terminate(self, result):
        """
        Terminate the task deleting all components.
        """
        self._state = TaskStateEnum.terminated
        self.__relieveComponent()
        # Stop all components
        defs = [self._waitDeleteComponent(c) for c in self._compPxys]
        dl = defer.DeferredList(defs,
                                fireOnOneCallback=False,
                                fireOnOneErrback=False,
                                consumeErrors=True)
        dl.addCallback(self.__cbMultiDeleteResults, result)
        self._doChainTerminate(dl, result)
        dl.addBoth(self.__bbTaskTerminated, result)

    def _abort(self):
        """
        Abort the task.
        Will increment the retry counter,
        and schedule a new component to be started.
        If the maximum attempts are reache,
        _doAborted will be called.
        """
        if self.__canRetry():
            self.__relieveComponent()
            self.__incRetryCounter()
            self.__delayedStartComponent()
        else:
            self.warning("Admin task '%s' reach the maximum attempts (%s) "
                         "of starting a component on worker '%s'", 
                         self.label, str(self.__getRetryCount() + 1),
                         self._workerPxy and self._workerPxy.getName())
            self._doAborted()
            self.__relieveComponent()
            return
        
    def _isPendingComponent(self, compPxy):
        return compPxy.getName() == self._pendingName
        
    def _isElectedComponent(self, compPxy):
        return compPxy == self.getActiveComponent()
    
    def _hasElectedComponent(self):
        return self.getActiveComponent() != None
        
    def _resetRetryCounter(self):
        self.log("Reset task '%s' retry counter", self.label)
        self._retry = 0

    def _holdLostComponent(self, compPxy):
        if self._holdTimeout != None:
            return
        self.log("Admin task '%s' is holding component '%s'",
                 self.label, compPxy.getName())
        self._onComponentHold(compPxy)
        timeout = self.HOLD_TIMEOUT
        to = utils.createTimeout(timeout, self.__asyncHoldTimeout, 
                                 compPxy)
        self._holdTimeout = to
    
    def _cancelComponentHold(self):
        if self._holdTimeout == None:
            return
        compPxy = self.getActiveComponent()
        self.log("Admin task '%s' cancel the lost component '%s' hold",
                 self.label, compPxy.getName())
        utils.cancelTimeout(self._holdTimeout)
        self._holdTimeout = None
        self._onComponentHoldCanceled(compPxy)
    
    def _isHoldingLostComponent(self):
        return self._holdTimeout != None
    
    def _restoreLostComponent(self, compPxy):
        d = compPxy.waitUIState(self.UISTATE_TIMEOUT)
        args = (compPxy,)
        d.addCallbacks(self.__cbComponentUIStateRestored,
                       self.__ebComponentRestorationFailed,
                       callbackArgs=args, errbackArgs=args)

    def _waitStopComponent(self, compPxy):
        self.debug("Admin task '%s' is stopping component '%s'", 
                   self.label, compPxy.getName())
        # Don't stop sad component
        if compPxy.getMood() not in (moods.sad, moods.sleeping):
            d = compPxy.forceStop()
            d.addErrback(self.__ebComponentStopFailed, compPxy.getName())
            return d
        # If sad, act like if the component was successfully stopped
        return defer.succeed(compPxy)

    def _stopComponent(self, compPxy):
        d = self._waitStopComponent(compPxy)
        d.addErrback(defer.resolveFailure, None)

    def _waitDeleteComponent(self, compPxy):
        self.debug("Admin task '%s' is deleting component '%s'", 
                   self.label, compPxy.getName())
        # Don't delete sad component
        if compPxy.getMood() != moods.sad:
            d = compPxy.forceDelete()
            d.addErrback(self.__ebComponentDeleteFailed, compPxy.getName())
            return d
        # If sad, act like if the component was successfully deleted
        return defer.succeed(compPxy)

    def _deleteComponent(self, compPxy):
        d = self._waitDeleteComponent(compPxy)
        d.addErrback(defer.resolveFailure, None)


    ## Private Methods ##
    
    def __setActiveComponent(self, compPxy):
        self._activePxy.setValue(compPxy)
    
    def __startup(self):
        self.log("Starting/Resuming admin task '%s'", self.label)
        assert self._state in [TaskStateEnum.starting,
                               TaskStateEnum.resuming]
        d = defer.Deferred()
        d.addCallback(defer.dropResult, self._doStartup)
        args = (self._state.name,)
        d.addCallbacks(self.__cbStartupSucceed, self.__ebStartupFailed,
                       callbackArgs=args, errbackArgs=args)
        d.callback(None)
        
    def __stateChangedError(self, waiters, actionDesc):
        error = admerrs.TranscoderError("State changed to %s during "
                                        "%s of admin task '%s'"
                                        % (self._state.name,
                                           actionDesc, 
                                           self.label))
        waiters.fireErrbacks(error)
        
    def __cbStartupSucceed(self, result, actionDesc):
        self.debug("Admin task '%s' started/resumed successfully",
                   self.label)
        if not (self._state in [TaskStateEnum.starting,
                                TaskStateEnum.resuming]):
            self.__stateChangedError(self._startWaiters, actionDesc)
            return
        self._state = TaskStateEnum.started
        self._startWaiters.fireCallbacks(result)
        self._onStarted()
        self.__startComponent()        
            
        
    def __ebStartupFailed(self, failure, actionDesc):
        log.notifyFailure(self, failure,
                          "Admin task '%s' failed to startup/resume", self.label)
        if self._state == TaskStateEnum.starting:
            self._state = TaskStateEnum.stopped
            self._startWaiters.fireErrbacks(failure)
        elif self._state == TaskStateEnum.resuming:
            self._state = TaskStateEnum.paused
            self._startWaiters.fireErrbacks(failure)
        else:
            self.__stateChangedError(self._startWaiters, actionDesc)

    def __cbMultiDeleteResults(self, results, newResult):
        for succeed, result in results:
            if not succeed:
                log.notifyFailure(self, result,
                                  "Failure waiting admin task '%s' "
                                  "components beeing deleted", self.label)
        return newResult        
        
    def __bbTaskTerminated(self, resultOrFailure, result):
        if isinstance(resultOrFailure, Failure):
            log.notifyFailure(self, resultOrFailure,
                              "Failure terminating admin task '%s'", self.label)
            self._doTerminated(result)
        else:
            self._doTerminated(resultOrFailure)
        
    def __relieveComponent(self):
        active = self.getActiveComponent()
        if active:
            self.log("Component '%s' relieved by admin task '%s'",
                     active.getName(), self.label)
            self._cancelComponentHold()
            self._onComponentRelieved(active)
            self.__setActiveComponent(None)
            
    def __electComponent(self, compPxy):
        assert compPxy != None
        if self.getActiveComponent():
            self.__relieveComponent()
        self.__setActiveComponent(compPxy)
        self.log("Component '%s' elected by admin task '%s'",
                 compPxy.getName(), self.label)
        self._onComponentElected(compPxy)
        # Stop all component other than the selected one
        for m in self._compPxys:
            if m != compPxy:
                self._stopComponent(m)

    def __waitPotentialComponent(self, timeout=None):
        to = self.UISTATE_TIMEOUT
        defs = [c.waitUIState(to) for c in self._compPxys if c.isRunning()]
        dl = defer.DeferredList(defs, fireOnOneCallback=False,
                                fireOnOneErrback=False,
                                consumeErrors=True)
        dl.addCallback(self.__cbMultiUIStateResults)
        self._doChainWaitPotentialComponent(dl)
        dl.addCallbacks(self.__bbSelectPotentialComponent)
        return dl
        
    def __cbMultiUIStateResults(self, results):
        newResult = []
        for succeed, result in results:
            if succeed:
                if result != None:
                    newResult.append(result)
            else:
                log.notifyFailure(self, result,
                                  "Failure waiting admin task '%s' "
                                  "components UI State", self.label)
        return newResult        
        
    def __bbSelectPotentialComponent(self, resultOrFailure):
        if isinstance(resultOrFailure, Failure):
            log.notifyFailure(self, resultOrFailure,
                              "Failure in admin task '%s' during potential "
                              "component selection", self.label)
            compPxys = []
        else:
            compPxys = resultOrFailure
        return self._doSelectPotentialComponent(compPxys)

    def __cancelComponentStartup(self, compPxy=None):
        if compPxy:
            self._stopComponent(compPxy)
            self._onComponentStartupCanceled(compPxy)
        self._pendingName = None
        self.__startComponent()
        
    def __abortComponentStartup(self, compPxy=None):
        if compPxy:
            if not compPxy.isRunning():
                # Probably segfault or killed
                self._processInterruptionDetected()
            self._stopComponent(compPxy)
            self._onComponentStartupCanceled(compPxy)
        self._pendingName = None
        self._abort()

    def __componentStarted(self, compPxy):
        self._pendingName = None
        
    def __componentLoaded(self, compPxy):
        self._onComponentStartingUp(compPxy)

    def __delayedStartComponent(self):
        if self._delayed:
            self.log("Component startup already scheduled for task '%s'",
                     self.label)
            return
        self.log("Scheduling component startup for task '%s'", self.label)
        timeout = self.__getRetryDelay()
        self._delayed = utils.createTimeout(timeout, self.__startComponent)

    def __startComponent(self):
        if not self.isStarted(): return
        utils.cancelTimeout(self._delayed)
        self._delayed = None
        if self._pendingName:
            self.log("Canceling component startup for task '%s', "
                     "component '%s' is pending", self.label, self._pendingName)
            return
        if not self._workerPxy:
            self.warning("Couldn't start component for task '%s', "
                         "no worker found", self.label)
            return
        compPxy = self.getActiveComponent()
        if compPxy:
            workerPxy = compPxy.getWorkerProxy()
            if workerPxy == self._workerPxy:
                self.debug("The valid component '%s' is already started",
                           compPxy.getName())
                return
        # Set the pendingName right now to prevent other
        # transoder to be started
        self._pendingName = utils.genUniqueIdentifier()
        self.log("Admin task '%s' is looking for a potential component",
                 self.label)
        # Check there is a valid transcoder already running
        d = self.__waitPotentialComponent(self.POTENTIAL_TIMEOUT)
        d.addCallbacks(self.__cbGotPotentialComponent,
                       self.__ebPotentialComponentFailure)
        
    def __ebPotentialComponentFailure(self, failure):
        log.notifyFailure(self, failure,
                          "Failure looking for a potential component "
                          "for admin task '%s'", self.label)
        self.__loadNewComponent()
        
    def __cbGotPotentialComponent(self, compPxy):
        if compPxy:
            self.log("Admin task '%s' found the potential component '%s'",
                     self.label, compPxy.getName())            
            self._pendingName = None
            self.__electComponent(compPxy)
        else:
            self.log("Admin task '%s' doesn't found potential component",
                     self.label)
            self.__loadNewComponent()

    def __loadNewComponent(self):
        componentName = self._pendingName
        workerName = self._workerPxy.getName()
        self.debug("Admin task '%s' loading component '%s' on  worker '%s'",
                   self.label, componentName, workerName)
        try:
            d = self._doLoadComponent(self._workerPxy, componentName,
                                      self.label, self._properties,
                                      self.LOAD_TIMEOUT)
            args = (componentName, workerName)
            d.addCallbacks(self.__cbComponentLoadSucceed,
                           self.__ebComponentLoadFailed,
                           callbackArgs=args, errbackArgs=args)
        except Exception, e:
            self.__ebComponentLoadFailed(Failure(e), componentName, workerName)

    def __shouldContinueComponentStartup(self, compPxy, workerName):
        # If the pending component changed, cancel
        if compPxy.getName() != self._pendingName:
            self.log("Admin task '%s' pending component changed while "
                     "starting component '%s'", 
                     self.label, compPxy.getName())
            return False
        # If the target worker changed, cancel 
        if ((not self._workerPxy) 
            or (self._workerPxy and (workerName != self._workerPxy.getName()))):
            self.log("Admin task '%s' suggested worker changed while "
                     "starting component '%s'", 
                     self.label, compPxy.getName())
            return False
        return True

    def __cbComponentLoadSucceed(self, result, componentName, workerName):
        self.debug("Admin task '%s' succeed to load component '%s' "
                   "on worker '%s'", self.label, componentName, workerName)
        assert componentName == result.getName()
        if self.__shouldContinueComponentStartup(result, workerName):
            self.__componentLoaded(result)
            d = result.waitHappy(self.HAPPY_TIMEOUT)
            args = (result, workerName)
            d.addCallbacks(self.__cbComponentGoesHappy, 
                           self.__ebComponentNotHappy,
                           callbackArgs=args, errbackArgs=args)
            return
        self.__cancelComponentStartup(result)
        
    def __ebComponentLoadFailed(self, failure, componentName, workerName):
        log.notifyFailure(self, failure,
                          "Admin task '%s' fail to load "
                          "component '%s' on worker '%s'",
                          self.label, componentName, workerName)
        self.__abortComponentStartup()
        
    def __cbComponentGoesHappy(self, mood, compPxy, workerName):
        self.debug("Admin task '%s' component '%s' goes happy on worker '%s'", 
                   self.label, compPxy.getName(), workerName)
        if self.__shouldContinueComponentStartup(compPxy, workerName):
            d = compPxy.waitUIState(self.UISTATE_TIMEOUT)
            args = (compPxy, workerName)
            d.addCallbacks(self.__cbGotUIState,
                           self.__ebUIStateFailed,
                           callbackArgs=args, errbackArgs=args)
            return
        self.__cancelComponentStartup(compPxy)
    
    def __ebComponentNotHappy(self, failure, compPxy, workerName):
        self.warning("Admin task '%s' component '%s' "
                     "fail to become happy on worker '%s': %s", 
                     self.label, compPxy.getName(), workerName,
                     log.getFailureMessage(failure))
        self.__abortComponentStartup(compPxy)

    def  __cbGotUIState(self, _, compPxy, workerName):
        self.debug("Admin task '%s' retrieved component '%s' UI State", 
                   self.label, compPxy.getName())
        if self.__shouldContinueComponentStartup(compPxy, workerName):
            self.__componentStarted(compPxy)
            self.__electComponent(compPxy)
        else:
            self.__cancelComponentStartup(compPxy)
            
    def __ebUIStateFailed(self, failure, compPxy, workerName):
        if not failure.check(ConnectionLost, PBConnectionLost):
            # Do not notify failure because of component crash
            log.notifyFailure(self, failure,
                              "Admin task '%s' failed to retrieve "
                              "component '%s' UI state",
                              self.label, compPxy.getName())
        self.__abortComponentStartup(compPxy)
        
    def __ebComponentStopFailed(self, failure, name):
        log.notifyFailure(self, failure,
                          "Admin task '%s' failed to stop "
                          "component '%s'", self.label, name)
        return failure
        
    def __ebComponentDeleteFailed(self, failure, name):
        log.notifyFailure(self, failure,
                          "Admin task '%s' failed to delete "
                          "component '%s'", self.label, name)
        return failure

    def __cbGetValidWorker(self, compPxy):
        if compPxy:
            workerPxy = compPxy.getWorkerProxy()
            self.log("Admin task '%s' found the valid worker '%s'",
                     self.label, workerPxy.getName())            
            return workerPxy
        return None
    
    def __ebNoValidWorker(self, failure):
        log.notifyFailure(self, failure,
                          "Failure looking for a valid worker "
                          "for admin task '%s'", self.label)
        return None
        

    def __asyncHoldTimeout(self, compPxy):
        self._holdTimeout = None
        if compPxy != self.getActiveComponent():
            self.log("Admin task '%s' held component '%s' is not "
                     "currently elected", self.label, compPxy.getName())
            return
        if not compPxy.isValid():
            self.warning("Admin task '%s' held component '%s' is not "
                         "valid anymore", self.label, compPxy.getName())
            return
        if compPxy.getMood() != moods.lost:
            self.log("Admin task '%s' component '%s' not lost anymore, "
                     "releasing the hold", self.label, compPxy.getName())
            return
        self.log("Admin task '%s' component '%s' still lost",
                 self.label, compPxy.getName())
        self._abort()
        if component.getMood() != moods.lost:
            self._stopComponent(compPxy)
    
    def __checkHeldComponentStatus(self, compPxy):
        if self._holdTimeout is None:
            self.log("Admin task '%s' is not holding component '%s'",
                     self.getLabel(), compPxy.getName())
            return False
        if compPxy != self.getActiveComponent():
            self.log("Admin task '%s' held component '%s' is not "
                     "currently elected", self.getLabel(), compPxy.getName())
            return False
        if not compPxy.isValid():
            self.warning("Admin task '%s' held component '%s' is not "
                         "valid anymore", self.getLabel(), compPxy.getName())
            return False
        return True
    
    def __cbComponentUIStateRestored(self, _, compPxy):
        if not self.__checkHeldComponentStatus(compPxy):
            return
        self.log("Admin task '%s' restored held component '%s'",
                 self.getLabel(), compPxy.getName())
        self._cancelComponentHold()        
        self._onComponentRestored(compPxy)
    
    def __ebComponentRestorationFailed(self, failure, compPxy):
        if not self.__checkHeldComponentStatus(compPxy):
            return
        log.notifyFailure(self, failure,
                          "Failure during task '%s' restoration of held "
                          "component '%s'", self.getLabel(),
                          compPxy.getName())
        self._cancelComponentHold()
        self._abort()
        self._stopComponent(compPxy)

    def __getRetryCount(self):
        return self._retry
        
    def __incRetryCounter(self):
        self._retry += 1
        self.log("Admin task '%s' retry counter set to %s out of %s",
                 self.label, self._retry, self.MAX_RETRIES)
        
    def __canRetry(self):
        return self._retry < self.MAX_RETRIES
    
    def __getRetryDelay(self):
        base = self.START_DELAY
        factor = self.START_DELAY_FACTOR
        return base * factor ** (self._retry - 1)
    
