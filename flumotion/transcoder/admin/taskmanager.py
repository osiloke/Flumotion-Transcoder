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
from twisted.internet import reactor
from twisted.python.failure import Failure

from flumotion.common.planet import moods

from flumotion.inhouse import log, defer, utils, events, waiters

from flumotion.transcoder import errors
from flumotion.transcoder.admin import adminconsts, admintask, admerrs
from flumotion.transcoder.admin.enums import TaskStateEnum
from flumotion.transcoder.admin.proxy import component


class TaskManager(log.Loggable, events.EventSourceMixin):
    
    logCategory = "" # Should be set by child classes
    
    def __init__(self):
        self.label = self.__class__.__name__
        self._identifiers = {} # {identifiers: ComponentProperties}
        self._tasks = {} # {ComponentProperties: admintask.IAdminTask}
        self._taskless = {} # {component.ComponentProxy: None}
        self._state = TaskStateEnum.stopped
        self._starting = False
        self._startWaiters = waiters.PassiveWaiters("Task Manager Startup")
        self._pauseWaiters = waiters.PassiveWaiters("Task Manager Paused")
        self._pending = 0
        reactor.addSystemEventTrigger("before", "shutdown", self.abort)

        
    ## Public Method ##
    
    def initialize(self):
        return defer.succeed(self)
    
    def addTask(self, identifier, task):
        assert admintask.IAdminTask.providedBy(task)
        self.debug("Adding task '%s' to manager '%s'", 
                   task.label, self.label)
        props = task.getProperties()
        assert not (props in self._tasks)
        assert not (identifier in self._identifiers)
        self._identifiers[identifier] = props
        self._tasks[props] = task
        for compPxy in self.__getTasklessComponents():
            if compPxy.getProperties() == props:
                # Not my responsability anymore
                self.__releaseTasklessComponent(compPxy)
                task.addComponent(compPxy)
        self._onTaskAdded(task)
        if self.isStarted():
            task.start(paused=self.isPaused())
    
    def removeTask(self, identifier):
        assert identifier in self._identifiers
        props = self._identifiers[identifier]
        task = self._tasks[props]
        self.debug("Removing task '%s' from manager '%s'", 
                   task.label, self.label)
        del self._identifiers[identifier]
        del self._tasks[props]
        self._onTaskRemoved(task)
        d = task.stop()
        d.addCallbacks(self.__cbAppartStopResults, 
                       self.__ebTaskStopFailed,
                       errbackArgs=(task,))

    def getTasks(self):
        return self._tasks.values()

    def getTask(self, identifier, default=None):
        props = self._identifiers.get(identifier, None)
        if not props:
            return default
        return self._tasks.get(props, default)

    def iterTasks(self):
        return self._tasks.itervalues()

    def isStarted(self):
        return self._state == TaskStateEnum.started
    
    def isPaused(self):
        return self._state == TaskStateEnum.paused

    def start(self, timeout=None):
        if not (self._state in [TaskStateEnum.stopped, 
                                TaskStateEnum.starting]):
            return defer.fail(errors.TranscoderError("Cannot start %s if %s"
                                                     % (self.label, 
                                                        self._state.name)))
        if self._state == TaskStateEnum.stopped:
            self.log("Ready to start task manager '%s'", self.label)
            self._state = TaskStateEnum.starting
            self._pauseWaiters.reset()
            self._tryStartup()
        return self._startWaiters.wait(timeout)

    def pause(self, timeout=None):
        if not (self._state in [TaskStateEnum.started]):
            return defer.fail(errors.TranscoderError("Cannot pause %s if %s"
                                                     % (self.label, 
                                                        self._state.name)))
        if self._state == TaskStateEnum.started:
            self.log("Pausing task manager '%s'", self.label)
            self._state = TaskStateEnum.pausing
            # No longer started
            self._startWaiters.reset()
            self.__pauseTaskManager()
        return self._pauseWaiters.wait(timeout)

    def resume(self, timeout=None):
        if not (self._state in [TaskStateEnum.paused, 
                                TaskStateEnum.resuming]):
            return defer.fail(errors.TranscoderError("Cannot resume %s if %s"
                                                     % (self.label, 
                                                        self._state.name)))
        if self._state == TaskStateEnum.paused:
            self.log("Ready to resume task manager '%s'", self.label)
            self._state = TaskStateEnum.resuming
            self._pauseWaiters.reset()
            self._tryStartup()
        return self._startWaiters.wait(timeout)

    def abort(self):
        if self._state in [TaskStateEnum.terminated]:
            # Silently return because abort should always succeed
            return
        self.log("Aborting task manager '%s'", self.label)
        self._state = TaskStateEnum.terminated
        for task in self.iterTasks():
            task.abort()
        self._tasks.clear()
        self._doAbort()

    def addComponent(self, compPxy):
        assert isinstance(compPxy, component.ComponentProxy)
        self.log("Component '%s' added to task manager '%s'", 
                 compPxy.getName(), self.label)
        self._pending += 1
        d = compPxy.waitProperties(adminconsts.TASKMANAGER_WAITPROPS_TIMEOUT)        
        args = (compPxy,)
        d.addCallbacks(self.__cbAddComponent, 
                       self.__ebGetPropertiesFailed,
                       callbackArgs=args, errbackArgs=args)
        return d
    
    def removeComponent(self, compPxy):
        assert isinstance(compPxy, component.ComponentProxy)
        self.log("Component '%s' removed from task manager '%s'", 
                 compPxy.getName(), self.label)
        d = compPxy.waitProperties(adminconsts.TASKMANAGER_WAITPROPS_TIMEOUT)        
        d.addCallback(self.__cbRemoveComponent, compPxy)
        return d

    def waitIdle(self, timeout=None):
        return self.__waitIdle(timeout)

    def waitActive(self, timeout=None):
        d = self._startWaiters.wait(timeout)
        d.addCallback(self.__cbWaitActive, timeout)
        return d
        

    ## Virtual Protected Methods ##

    def _doStart(self):
        """
        Can return a Deferred.
        """
        pass

    def _doPause(self):
        """
        Can return a Deferred.
        """
        pass
    
    def _doResume(self):
        """
        Can return a Deferred.
        """
        pass
    
    def _doChainWaitIdle(self, chain):
        pass
    
    def _doChainWaitActive(self, chain):
        pass
    
    def _doAbort(self):
        pass

    def _onTaskAdded(self, task):
        pass
    
    def _onTaskRemoved(self, task):
        pass

    def _onTasklessComponentAdded(self, compPxy):
        pass
    
    def _onTasklessComponentRemoved(self, compPxy):
        pass


    ## Component Event Listeners ##
    
    def __onComponentMoodChanged(self, compPxy, mood):
        if not self.isStarted(): return
        self.log("Task manager '%s' taskless component '%s' goes %s",
                 self.label, compPxy.getName(), mood.name)
        if mood == moods.sleeping:
            d = compPxy.forceDelete()
            d.addErrback(self.__ebComponentDeleteFailed, compPxy.getName())
        elif mood != moods.sad:
            d = compPxy.forceStop()
            d.addErrback(self.__ebComponentStopFailed, compPxy.getName())

    ## Protected Methods ##
    
    def _tryStartup(self):
        if ((not self._starting)
            and (self._pending == 0)
            and (self._state in [TaskStateEnum.starting,
                                 TaskStateEnum.resuming])):
            self.debug("Starting/Resuming task manager '%s'", self.label)
            self._starting = True
            d = defer.succeed(self)
            if self._state == TaskStateEnum.starting:
                d.addCallback(defer.dropResult, self._doStart)
                d.addCallback(self.__cbCallForAllTasks, "start")
            else:
                d.addCallback(defer.dropResult, self._doResume)
                d.addCallback(self.__cbCallForAllTasks, "resume")
            d.addCallback(self.__cbStartup)
            args = (self._state.name,)
            d.addCallbacks(self.__cbStartupSucceed, self.__ebStartupFailed,
                           callbackArgs=args, errbackArgs=args)


    ## Private Methods ##
    
    def __pauseTaskManager(self):
        d = defer.succeed(self)
        d.addCallback(defer.dropResult, self._doPause)
        d.addCallback(self.__cbCallForAllTasks, "pause")
        d.addCallbacks(self.__cbPauseSucceed, self.__ebPauseFailed)
    
    def __cbStartup(self, _):
        return self.__waitIdle(adminconsts.TASKMANAGER_IDLE_TIMEOUT)

    def __cbCallForAllTasks(self, _, action):
        assert action in ["start", "pause", "resume"]
        d = defer.Deferred()
        for t in self._tasks.itervalues():
            d.addCallback(defer.dropResult, getattr(t, action))
            d.addErrback(self.__ebResolveCallFailure, t, action)
        d.callback(None)
        return d
    
    def __ebResolveCallFailure(self, failure, task, action):
        assert action in ["start", "pause", "resume"]
        log.notifyFailure(self, failure,
                          "Task manager '%s' failed to %s "
                          "task '%s'", self.label, action, task.label)
        
    def __getTasklessComponents(self):
        return self._taskless.keys()
    
    def __apartTasklessComponent(self, compPxy):
        self.log("Task manager '%s' takes apart taskless component '%s'",
                 self.label, compPxy.getName())
        self._taskless[compPxy] = None
        compPxy.connectListener("mood-changed", self,
                                self.__onComponentMoodChanged)
        compPxy.refreshListener(self)
        self._onTasklessComponentAdded(compPxy)
    
    def __releaseTasklessComponent(self, compPxy):
        self.log("Task manager '%s' release taskless component '%s'",
                 self.label, compPxy.getName())
        assert compPxy in self._taskless
        del self._taskless[compPxy]
        compPxy.disconnectListener("mood-changed", self)
        self._onTasklessComponentRemoved(compPxy)
    
    def __cbAddComponent(self, props, compPxy):
        assert props != None
        assert props == compPxy.getProperties()
        if props in self._tasks:
            task = self._tasks[props]
            task.addComponent(compPxy)
        else:
            msg = ("Task manager '%s' ask to add component '%s' "
                   "without matching task" 
                   % (self.label, compPxy.getName()))
            self.debug("%s", msg)
            self.__apartTasklessComponent(compPxy)
        self._pending -= 1
        self._tryStartup()
        return compPxy
    
    def __ebGetPropertiesFailed(self, failure, compPxy):
        msg = ("Task manager '%s' fail to retrieve component '%s' properties."
               % (self.label, compPxy.getName()))
        log.notifyFailure(self, failure, "%s", msg)
        self.__apartTasklessComponent(compPxy)
        self._pending -= 1
        self._tryStartup()
        raise admerrs.ComponentRejectedError(msg, cause=failure)
        
    def __cbRemoveComponent(self, props, compPxy):
        assert props != None
        assert props == compPxy.getProperties()
        if props in self._tasks:
            task = self._tasks[props]
            task.removeComponent(compPxy)
        if compPxy in self._taskless:
            self.__releaseTasklessComponent(compPxy)
        return compPxy

    def __ebComponentStopFailed(self, failure, name):
        if not failure.check("flumotion.transcoder.errors.OperationAbortedError"):
            log.notifyFailure(self, failure,
                              "Task manager '%s' failed to stop "
                              "component '%s'", self.label, name)

    def __ebComponentDeleteFailed(self, failure, name):
        if not failure.check("flumotion.transcoder.errors.OperationAbortedError"):
            log.notifyFailure(self, failure,
                              "Task manager '%s' failed to delete "
                              "component '%s'", self.label, name)

    def __stateChangedError(self, waiters, actionDesc):
        error = errors.TranscoderError("State changed to %s during %s of '%s'"
                                       % (self._state.name, 
                                          actionDesc, self.label))
        waiters.fireErrbacks(error)

    def __cbStartupSucceed(self, result, actionDesc):
        self.debug("Task manager '%s' started/resumed successfully", self.label)
        self._starting = False
        if not (self._state in [TaskStateEnum.starting,
                                TaskStateEnum.resuming]):
            self.__stateChangedError(self._startWaiters, actionDesc)
            return
        self._state = TaskStateEnum.started
        self._startWaiters.fireCallbacks(result)
        # Now we can manage the taskless components
        for c in self._taskless:
            self.__onComponentMoodChanged(c, c.getMood())

    def __ebStartupFailed(self, failure, actionDesc):
        log.notifyFailure(self, failure,
                          "Task Manager '%s' failed to startup/resume",
                          self.label)
        self._starting = False
        if self._state == TaskStateEnum.starting:
            self._state = TaskStateEnum.stopped
            self._startWaiters.fireErrbacks(failure)
        elif self._state == TaskStateEnum.resuming:
            self._state = TaskStateEnum.paused
            self._startWaiters.fireErrbacks(failure)
        else:
            self.__stateChangedError(self._startWaiters, actionDesc)

    def __cbPauseSucceed(self, result):
        self.debug("Task manager '%s' paused successfully", self.label)
        if self._state == TaskStateEnum.pausing:
            self._state = TaskStateEnum.paused
            self._pauseWaiters.fireCallbacks(result)
        else:
            self.__stateChangedError(self._pauseWaiters, "pausing")
        
    def __ebPauseFailed(self, failure):
        log.notifyFailure(self, failure,
                          "Task Manager '%s' failed to pause", self.label)
        if self._state == TaskStateEnum.pausing:
            self._state = TaskStateEnum.started
            self._pauseWaiters.fireErrbacks(failure)
        else:
            self.__stateChangedError(self._pauseWaiters, "pausing")

    def __waitIdle(self, timeout):
        defs = [t.waitIdle(timeout) for t in self.iterTasks()]
        dl = defer.DeferredList(defs,
                                fireOnOneCallback=False,
                                fireOnOneErrback=False,
                                consumeErrors=True)
        dl.addCallback(defer.propagateFailure, self)
        self._doChainWaitIdle(dl)
        return dl
    
    def __cbWaitActive(self, result, timeout):
        defs = [t.waitActive(timeout) for t in self.iterTasks()]
        dl = defer.DeferredList(defs,
                                fireOnOneCallback=False,
                                fireOnOneErrback=False,
                                consumeErrors=True)
        dl.addCallback(defer.propagateFailure, self)
        self._doChainWaitActive(dl)
        return dl
    
    def __cbAppartStopResults(self, compPxys):
        for compPxy in compPxys:
            self.__apartTasklessComponent(compPxy)
    
    def __ebTaskStopFailed(self, failure, task):
        log.notifyFailure(self, failure,
                          "Task Manager '%s' failed to stop task '%s'",
                          self.label, task.label)
