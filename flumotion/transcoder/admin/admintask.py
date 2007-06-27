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
from twisted.internet import reactor, defer
from twisted.python.failure import Failure

from flumotion.common.planet import moods

from flumotion.transcoder import log, utils
from flumotion.transcoder.log import LoggerProxy
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.eventsource import EventSource
from flumotion.transcoder.admin.proxies.componentproxy import ComponentProxy


class IAdminTask(Interface):

    def getLabel(self):
        pass
    
    def isActive(self):
        pass
    
    def hasTerminated(self):
        pass
    
    def getProperties(self):
        pass
    
    def addComponent(self, component):
        pass
    
    def removeComponent(self, component):
        pass
    
    def getActiveComponent(self):
        pass
    
    def getWorker(self):
        pass
    
    def start(self, paused=False):
        pass
    
    def pause(self):
        pass
    
    def resume(self):
        pass
    
    def stop(self):
        """
        Returns the list of components previously managed by this task.
        """
    
    def abort(self):
        pass
    
    def suggestWorker(self, worker):
        pass
    
    def waitValidWorker(self, timeout=None):
        pass

    def waitSynchronized(self, timeout=None):
        pass

    
class AdminTask(LoggerProxy, EventSource):
    
    implements(IAdminTask)

    LOAD_TIMEOUT = adminconsts.TASK_LOAD_TIMEOUT
    HAPPY_TIMEOUT = adminconsts.TASK_HAPPY_TIMEOUT
    START_DELAY = adminconsts.TASK_START_DELAY
    START_DELAY_FACTOR = adminconsts.TASK_START_DELAY_FACTOR
    HOLD_TIMEOUT = adminconsts.TASK_HOLD_TIMEOUT
    POTENTIAL_TIMEOUT = adminconsts.TASK_POTENTIAL_COMPONENT_TIMEOUT
    UISTATE_TIMEOUT = adminconsts.TASK_UISTATE_TIMEOUT
    MAX_ATTEMPTS = 0
    
    def __init__(self, logger, label, properties, interface):
        LoggerProxy.__init__(self, logger)
        EventSource.__init__(self, interface)
        self._worker = None # WorkerProxy
        self._started = False
        self._paused = False
        self._terminated = False
        self._pendingName = None
        self._delayed = None # IDelayedCall
        self._elected = None # MonitorProxy
        self._components = {} # {MonitorProxy: None}
        self._label = label
        self._properties = properties
        self._retry = 0
        self._holdTimeout = None
    

    ## IAdminTask Implementation ##
        
    def getLabel(self):
        return self._label
    
    def getProperties(self):
        return self._properties

    def isActive(self):
        return (not self._terminated) and self._started and (not self._paused)

    def hasTerminated(self):
        return self._terminated

    def getActiveComponent(self):
        return self._elected
    
    def getWorker(self):
        return self._worker
    
    def getComponents(self):
        return self._components.keys()
    
    def iterComponents(self):
        return self._components.iterkeys()

    def addComponent(self, component):
        assert isinstance(component, ComponentProxy)
        assert not (component in self._components)
        self.log("Component '%s' added to task '%s'", 
                 component.getName(), self.getLabel())
        self._components[component] = None
        self._onComponentAdded(component)
        
    def removeComponent(self, component):
        assert isinstance(component, ComponentProxy)
        assert component in self._components
        self.log("Component '%s' removed from task '%s'", 
                 component.getName(), self.getLabel())
        del self._components[component]
        self._onComponentRemoved(component)
        if component == self._elected:
            self.__relieveComponent()
    
    def start(self, paused=False):
        if self._started: return
        self.log("Starting admin task '%s'", self.getLabel())
        self._started = True
        if paused:
            self.pause()
        else:
            self._paused = False
            self.__startup()
    
    def pause(self):
        if self._started and (not self._paused):
            self.log("Pausing admin task '%s'", self.getLabel())
            self._paused = True
    
    def resume(self):
        if self._started and self._paused:
            self.log("Resuming componenting task '%s'", self.getLabel())
            self._paused = False
            self.__startup()
                    
    
    def stop(self):
        """
        Relieve the selected component, and return
        all the components for the caller to take responsability.
        After this, no component will/should be added or removed.
        """
        self.log("Stopping admin task '%s'", self.getLabel())
        self._terminated = True
        self.__relieveComponent()
        for c in self._components:
            self._onComponentRemoved(c)
        result = self._components.keys()
        self._components.clear()
        return result
    
    def abort(self):
        """
        After this, no components will/should be added or removed.
        """
        self.log("Aborting admin task '%s'", self.getLabel())
        self._terminated = True
        self.__relieveComponent()
        for c in self._components:
            self._onComponentRemoved(c)
        self._components.clear()
        

    def suggestWorker(self, worker):
        self.log("Worker '%s' suggested to admin task '%s'", 
                 worker and worker.getLabel(), self.getLabel())
        if self._doAcceptSuggestedWorker(worker):
            # If we change the worker, reset the retry counter
            self._resetRetryCounter()
            self._worker = worker
            # If we currently holding for a lost component, 
            # do not start a new one right now.
            if self._isHoldingLostComponent():
                self.log("Admin task '%s' avoid starting a new component "
                         "because it's holding a lost component",
                         self.getLabel())
            else:
                self.__startComponent()
            return self._worker
        return None

    def waitSynchronized(self, timeout=None):
        if self._elected:
            # Wait UI State to be sure the file events are fired
            d = self._elected.waitUIState(timeout)
            d.addCallback(utils.overrideResult, self)
        else:
            d = defer.succeed(self)
        self._doChainWaitSynchronized(d)
        return d

    def waitValidWorker(self, timeout=None):
        if self._elected:
            return defer.succeed(self._elected.getWorker())
        d = self.__waitPotentialComponent(timeout)
        d.addCallbacks(self.__cbGetValidWorker,
                       self.__ebNoValidWorker)
        return d
    

    ## Virtual Protected Methods ##
    
    def _onComponentAdded(self, component):
        pass

    def _onComponentRemoved(self, component):
        pass

    def _onComponentHold(self, component):
        pass
    
    def _onComponentHoldCanceled(self, component):
        pass
    
    def _onComponentLost(self, component):
        pass
    
    def _onComponentElected(self, component):
        pass

    def _onComponentRelieved(self, component):
        pass

    def _onComponentStartingUp(self, component):
        pass

    def _onComponentStartupCanceled(self, component):
        pass
    
    def _doChainWaitSynchronized(self, chain):
        pass
    
    def _doChainWaitPotentialComponent(self, chain):
        pass
    
    def _doStartup(self):
        pass
    
    def _doAcceptSuggestedWorker(self, worker):
        return True
    
    def _doChainTerminate(self, chain, result):
        pass
    
    def _doTerminated(self, result):
        pass
    
    def _doAborted(self):
        pass
    
    def _doSelectPotentialComponent(self, components):
        return None
    
    def _doLoadComponent(self, worker, componentName, componentLabel,
                         componentProperties, loadTimeout):
        return defer.failed(NotImplementedError())

    
    ## Protected Methods ##
    
    def _terminate(self, result):
        """
        Terminate the task deleting all components.
        """
        self._terminated = True        
        self.__relieveComponent()
        # Stop all components
        defs = []
        for c in self._components:
            defs.append(self._waitDeleteComponent(c))
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
        self.__incRetryCounter()
        self.__relieveComponent()
        if self.__canRetry():
            self.__delayedStartComponent()
        else:
            self.warning("Admin task '%s' reach the maximum attempts (%s) "
                         "of starting a component on worker '%s'", 
                         self.getLabel(), str(self.__getRetryCount()), 
                         self._worker.getName())
            self._doAborted()
            return
        
    def _isPendingComponent(self, component):
        return component.getName() == self._pendingName
        
    def _isElectedComponent(self, component):
        return component == self._elected
    
    def _hasElectedComponent(self):
        return self._elected != None
        
    def _resetRetryCounter(self):
        self.log("Reset task '%s' retry counter", self.getLabel())
        self._retry = 0

    def _holdLostComponent(self, component):
        if self._holdTimeout != None:
            return
        self.log("Admin task '%s' is holding component '%s'",
                 self.getLabel(), component.getName())
        self._onComponentHold(component)
        timeout = self.HOLD_TIMEOUT
        to = utils.createTimeout(timeout, self.__asyncHoldTimeout, 
                                 component)
        self._holdTimeout = to
    
    def _cancelComponentHold(self):
        if self._holdTimeout == None:
            return
        self.log("Admin task '%s' cancel the lost component '%s' hold",
                 self.getLabel(), self._elected.getName())
        utils.cancelTimeout(self._holdTimeout)
        self._holdTimeout = None
        self._onComponentHoldCanceled(self._elected)
    
    def _isHoldingLostComponent(self):
        return self._holdTimeout != None
    
    def _waitStopComponent(self, component):
        self.debug("Admin task '%s' is stopping component '%s'", 
                   self.getLabel(), component.getName())
        # Don't stop sad component
        if component.getMood() != moods.sad:
            d = component.forceStop()
            d.addErrback(self.__ebComponentStopFailed, component.getName())
            return d
        # If sad, act like if the component was successfully stopped
        return defer.succeed(component)

    def _stopComponent(self, component):
        d = self._waitStopComponent(component)
        d.addErrback(utils.resolveFailure, None)

    def _waitDeleteComponent(self, component):
        self.debug("Admin task task '%s' is deleting component '%s'", 
                   self.getLabel(), component.getName())
        # Don't delete sad component
        if component.getMood() != moods.sad:
            d = component.forceDelete()
            d.addErrback(self.__ebComponentDeleteFailed, component.getName())
            return d
        # If sad, act like if the component was successfully deleted
        return defer.succeed(component)

    def _deleteComponent(self, component):
        d = self._waitDeleteComponent(component)
        d.addErrback(utils.resolveFailure, None)


    ## Private Methods ##
    
    def __startup(self):
        self.log("Startup admin task '%s'", self.getLabel())
        self._doStartup()
        self.__startComponent()  
        
    def __cbMultiDeleteResults(self, results, newResult):
        for succeed, result in results:
            if not succeed:
                self.warning("Failure waiting admin task '%s' "
                             "components beeing deleted: %s", 
                             self.getLabel(), log.getFailureMessage(result))
                self.debug("%s", log.getFailureTraceback(result))
        return newResult        
        
    def __bbTaskTerminated(self, resultOrFailure, result):
        if isinstance(resultOrFailure, Failure):
            self.warning("Failure terminating admin task '%s': %s",
                         self.getLabel(), 
                         log.getFailureMessage(resultOrFailure))
            self.debug("%s", log.getFailureTraceback(resultOrFailure))
            self._doTerminated(result)
        else:
            self._doTerminated(resultOrFailure)
        
    def __relieveComponent(self):
        if self._elected:
            self.log("Component '%s' relieved by admin task '%s'",
                     self._elected.getName(), self.getLabel())
            self._cancelComponentHold()
            self._onComponentRelieved(self._elected)
            self._elected = None
            
    def __electComponent(self, component):
        assert component != None
        if self._elected:
            self.__relieveComponent()
        self._elected = component
        self.log("Component '%s' elected by admin task '%s'",
                 self._elected.getName(), self.getLabel())
        self._onComponentElected(component)
        # Stop all component other than the selected one
        for m in self._components:
            if m != self._elected:
                self._stopComponent(m)

    def __waitPotentialComponent(self, timeout=None):
        defs = []
        for c in self._components:
            if c.isRunning():
                d = c.waitUIState(self.UISTATE_TIMEOUT)
                defs.append(d)
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
                self.warning("Failure waiting admin task '%s' "
                             "components UI State: %s", 
                             self.getLabel(), log.getFailureMessage(result))
                self.debug("%s", log.getFailureTraceback(result))
        return newResult        
        
    def __bbSelectPotentialComponent(self, resultOrFailure):
        if isinstance(resultOrFailure, Failure):
            self.warning("Failure in admin task '%s' during potential "
                         "component selection: %s", self.getLabel(), 
                         log.getFailureMessage(resultOrFailure))
            self.debug("%s", log.getFailureTraceback(resultOrFailure))
            components = []
        else:
            components = resultOrFailure
        return self._doSelectPotentialComponent(components)

    def __cancelComponentStartup(self, component=None):
        if component:
            self._stopComponent(component)
            self._onComponentStartupCanceled(component)
        self._pendingName = None
        self.__startComponent()

    def __componentStarted(self, component):
        self._pendingName = None
        
    def __componentLoaded(self, component):
        self._onComponentStartingUp(component)

    def __delayedStartComponent(self):
        if self._delayed:
            self.log("Component startup already scheduled for task '%s'",
                     self.getLabel())
            return
        self.log("Scheduling component startup for task '%s'",
                 self.getLabel())
        timeout = self.__getRetryDelay()
        self._delayed = utils.createTimeout(timeout, self.__startComponent)

    def __startComponent(self):
        if not self.isActive(): return
        utils.cancelTimeout(self._delayed)
        self._delayed = None
        if self._pendingName:
            self.log("Canceling component startup for task '%s', "
                     "component '%s' is pending", self.getLabel(),
                     self._pendingName)
            return
        if not self._worker:
            self.warning("Couldn't start component for task '%s', "
                         "no worker found", self.getLabel())
            return
        # Set the pendingName right now to prevent other
        # transoder to be started
        self._pendingName = utils.genUniqueIdentifier()
        self.log("Admin task '%s' is looking for a potential component",
                 self.getLabel())
        # Check there is a valid transcoder already running
        d = self.__waitPotentialComponent(self.POTENTIAL_TIMEOUT)
        d.addCallbacks(self.__cbGotPotentialComponent,
                       self.__ebPotentialComponentFailure)
        
    def __ebPotentialComponentFailure(self, failure):
        self.warning("Failure looking for a potential component "
                     "for admin task '%s': %s", self.getLabel(), 
                     log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        self.__loadNewComponent()
        
    def __cbGotPotentialComponent(self, component):
        if component:
            self.log("Admin task '%s' found the potential component '%s'",
                     self.getLabel(), component.getName())            
            self._pendingName = None
            self.__electComponent(component)
            return
        self.__loadNewComponent()

    def __loadNewComponent(self):
        componentName = self._pendingName
        workerName = self._worker.getName()
        self.debug("Admin task '%s' loading component '%s' on  worker '%s'",
                   self.getLabel(), componentName, workerName)
        d = self._doLoadComponent(self._worker, componentName,
                                  self._label, self._properties,
                                  self.LOAD_TIMEOUT)
        args = (componentName, workerName)
        d.addCallbacks(self.__cbComponentLoadSucceed,
                       self.__ebComponentLoadFailed,
                       callbackArgs=args, errbackArgs=args)

    def __shouldContinueComponentStartup(self, component, workerName):
        # If the target worker changed, cancel 
        if ((not self._worker) 
            or (self._worker and (workerName != self._worker.getName()))):
            self.log("Admin task '%s' suggested worker changed while "
                     "starting component '%s'", 
                     self.getLabel(), component.getName())
            return False
        return True

    def __cbComponentLoadSucceed(self, result, componentName, workerName):
        self.debug("Admin task '%s' succeed to load component '%s' "
                   "on worker '%s'", self.getLabel(), 
                   componentName, workerName)
        assert componentName == result.getName()
        assert componentName == self._pendingName
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
        self.warning("Admin task '%s' fail to load component '%s' "
                     "on worker '%s': %s", self.getLabel(), componentName,
                     workerName, log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        self.__cancelComponentStartup()
        
    def __cbComponentGoesHappy(self, mood, component, workerName):
        self.debug("Admin task '%s' component '%s' goes happy on worker '%s'", 
                   self.getLabel(), component.getName(), workerName)
        if self.__shouldContinueComponentStartup(component, workerName):
            d = component.waitUIState(self.UISTATE_TIMEOUT)
            args = (component, workerName)
            d.addCallbacks(self.__cbGotUIState,
                           self.__ebUIStateFailed,
                           callbackArgs=args, errbackArgs=args)
            return
        self.__cancelComponentStartup(component)
    
    def __ebComponentNotHappy(self, failure, component, workerName):
        self.warning("Admin task '%s' component '%s' "
                     "fail to become happy on worker '%s': %s", 
                     self.getLabel(), component.getName(), workerName,
                     log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        self.__cancelComponentStartup(component)

    def  __cbGotUIState(self, _, component, workerName):
        self.debug("Admin task '%s' retrieved component '%s' UI State", 
                   self.getLabel(), component.getName())
        if self.__shouldContinueComponentStartup(component, workerName):
            self.__componentStarted(component)
            self.__electComponent(component)
        else:
            self.__cancelComponentStartup(component)
            
    def __ebUIStateFailed(self, failure, component, workerName):
        self.warning("Admin task '%s' failed to retrieve "
                     "component '%s' UI state: %s",
                     self.getLabel(), component.getName(), 
                     log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        self.__cancelComponentStartup(component)
        
    def __ebComponentStopFailed(self, failure, name):
        self.warning("Admin task '%s' failed to stop component '%s': %s",
                     self.getLabel(), name, log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        return failure
        
    def __ebComponentDeleteFailed(self, failure, name):
        self.warning("Admin task '%s' failed to delete component '%s': %s",
                     self.getLabel(), name, 
                     log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        return failure

    def __cbGetValidWorker(self, component):
        if component:
            worker = component.getWorker()
            self.log("Admin task '%s' found the valid worker '%s'",
                     self.getLabel(), worker.getName())            
            return worker
        return None
    
    def __ebNoValidWorker(self, failure):
        self.warning("Failure looking for a valid worker "
                     "for admin task '%s': %s", self.getLabel(), 
                     log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        return None
        

    def __asyncHoldTimeout(self, component):
        self._holdTimeout = None
        if component != self._elected:
            self.log("Admin task '%s' hold component '%s' is not "
                     "currently elected", self.getLabel(), 
                     component.getName())
            return
        if not component.isValid():
            self.warning("Admin task '%s' hold component '%s' is not "
                         "valid anymore", self.getLabel(),
                         component.getName())
            return
        if component.getMood() != moods.lost:
            self.log("Admin task '%s' component '%s' not lost anymore, "
                     "releasing the hold", self.getLabel(), 
                     component.getName())
            return
        self.log("Admin task '%s' component '%s' still lost",
                 self.getLabel(), component.getName())
        self._abort()
    
    def __getRetryCount(self):
        return self._retry
        
    def __incRetryCounter(self):
        self._retry += 1
        self.log("Admin task '%s' retry counter set to %s of %s",
                 self.getLabel(), self._retry, self.MAX_ATTEMPTS)
        
    def __canRetry(self):
        return self._retry <= self.MAX_ATTEMPTS
    
    def __getRetryDelay(self):
        base = self.START_DELAY
        factor = self.START_DELAY_FACTOR
        return base * factor ** (self._retry - 1)
    
