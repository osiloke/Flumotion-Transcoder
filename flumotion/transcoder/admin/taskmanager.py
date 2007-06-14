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
from twisted.internet import defer, reactor
from twisted.python.failure import Failure

from flumotion.common.planet import moods
from flumotion.common.log import Loggable

from flumotion.transcoder import log
from flumotion.transcoder import utils
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.errors import ComponentRejectedError
from flumotion.transcoder.admin.eventsource import EventSource
from flumotion.transcoder.admin.admintask import IAdminTask
from flumotion.transcoder.admin.proxies.componentproxy import ComponentProxy
from flumotion.transcoder.admin.proxies.componentproxy import ComponentListener


class TaskManager(Loggable, EventSource, ComponentListener):
    
    logCategory = 'admin-tasks'
    
    def __init__(self, interfaces):
        EventSource.__init__(self, interfaces)
        self._identifiers = {} # {identifiers: ComponentProperties}
        self._tasks = {} # {ComponentProperties: IAdminTask}
        self._taskless = {} # {ComponentProxy: None}
        self._ready = False
        self._started = False
        self._paused = False
        self._pending = 0
        reactor.addSystemEventTrigger("before", "shutdown", self.abort)

        
    ## Public Method ##
    
    def initialize(self):
        return defer.succeed(self)
    
    def addTask(self, identifier, task):
        assert IAdminTask.providedBy(task)
        self.debug("Adding task '%s'", task.getLabel())
        props = task.getProperties()
        assert not (props in self._tasks)
        assert not (identifier in self._identifiers)
        self._identifiers[identifier] = props
        self._tasks[props] = task
        for m in self.__getTasklessComponents():
            if m.getProperties() == props:
                # Not my responsability anymore
                self.__releaseTasklessComponent(m)
                task.addMonitor(m)
        self._onTaskAdded(task)
    
    def removeTask(self, identifier):
        assert identifier in self._identifiers
        props = self._identifiers[identifier]
        task = self._tasks[props]
        self.debug("Removing task '%s'", task.getLabel())
        del self._identifiers[identifier]
        del self._tasks[props]
        self._onTaskRemoved(task)
        for c in task.stop():
            self.__apartTasklessComponent(c)

    def getTasks(self):
        return self._tasks.values()

    def iterTasks(self):
        return self._tasks.itervalues()

    def isActive(self):
        return self._started and (not self._paused)

    def start(self):
        self.log("Ready to start task manager %s", self.__class__.__name__)
        self._ready = True
        self._tryStarting()

    def pause(self):
        if self._started and (not self._paused):
            self.log("Pausing task manager %s", self.__class__.__name__)
            self._paused = True
            d = defer.succeed(self)
            d.addCallback(utils.dropResult, self._doPause)
            d.addCallback(self.__cbCallForAllTasks, "pause")
            d.addErrback(self.__ebPauseFailed)

    def resume(self):
        if self._started and self._paused:
            self.log("Resuming task manager %s", self.__class__.__name__)
            self._paused = False
            d = defer.succeed(self)
            d.addCallback(utils.dropResult, self._doResume)
            d.addCallback(self.__cbCallForAllTasks, "resume")
            d.addCallback(self.__cbStartup)
            d.addErrback(self.__ebResumeFailed)

    def abort(self):
        self.log("Aborting task manager %s", self.__class__.__name__)
        for task in self._tasks.itervalues():
            task.abort()
        self._tasks.clear()
        self._doAbort()

    def addComponent(self, component):
        assert isinstance(component, ComponentProxy)
        self.log("Component '%s' added to task manager %s", 
                 component.getLabel(), self.__class__.__name__)
        self._pending += 1
        d = component.waitProperties(adminconsts.TASKER_WAITPROPS_TIMEOUT)        
        args = (component,)
        d.addCallbacks(self.__cbAddComponent, 
                       self.__ebGetPropertiesFailed,
                       callbackArgs=args, errbackArgs=args)
        return d
    
    def removeComponent(self, component):
        assert isinstance(component, ComponentProxy)
        self.log("Component '%s' removed from task manager %s", 
                 component.getLabel(), self.__class__.__name__)
        d = component.waitProperties(adminconsts.TASKER_WAITPROPS_TIMEOUT)        
        d.addCallback(self.__cbRemoveComponent, component)
        return d


    ## Virtual Protected Methods ##

    def _waitStarting(self):
        return defer.succeed(self)

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
    
    def _doAbort(self):
        pass

    def _onTaskAdded(self, task):
        pass
    
    def _onTaskRemoved(self, task):
        pass

    def _onTasklessComponentAdded(self, component):
        pass
    
    def _onTasklessComponentRemoved(self, component):
        pass


    ## IComponentListener Overrided Methods ##
    
    def onComponentMoodChanged(self, component, mood):
        if not self.isActive(): return
        self.log("Taskless monitor '%s' goes %s", 
                 component.getLabel(), mood.name)
        if mood == moods.sleeping:
            d = component.forceDelete()
            d.addErrback(self.__ebDeleteFailed, component.getLabel())
        elif mood != moods.sad:
            d = component.forceStop()
            d.addErrback(self.__ebStopFailed, component.getLabel())

    ## Protected Methods ##
    
    def _tryStarting(self):
        if ((not self._started) and self._ready 
            and (self._pending == 0)):
            self.log("Starting task manager %s", self.__class__.__name__)
            self._started = True
            self._pause = False
            d = defer.succeed(self)
            d.addCallback(utils.dropResult, self._doStart)
            d.addCallback(self.__cbCallForAllTasks, "start")
            d.addCallback(self.__cbStartup)
            d.addErrback(self.__ebStartupFailed)


    ## Private Methods ##
    
    def __cbStartup(self, _):
        for c in self._taskless:
            self.onComponentMoodChanged(c, c.getMood())

    def __cbCallForAllTasks(self, _, action):
        assert action in ["start", "stop", "pause", "resume"]
        for t in self._tasks.itervalues():
            getattr(t, action)()
    
    def __getTasklessComponents(self):
        return self._taskless.keys()
    
    def __apartTasklessComponent(self, component):
        self._taskless[component] = None
        component.addListener(self)
        component.syncListener(self)
        self._onTasklessComponentAdded(component)
    
    def __releaseTasklessComponent(self, component):
        assert component in self._taskless
        component.removeListener(self)
        del self._taskless[component]
        self._onTasklessComponentRemoved(component)
    
    def __cbAddComponent(self, props, component):
        assert props != None
        assert props == component.getProperties()
        if props in self._tasks:
            task = self._tasks[props]
            task.addComponent(component)
        else:
            msg = ("Component '%s' added to an unknown task "
                   "configuration." % component.getLabel())
            self.warning("%s", msg)
            self.__apartTasklessComponent(component)
            raise ComponentRejectedError(msg)
        self._pending -= 1
        self._tryStarting()
        return component
    
    def __ebGetPropertiesFailed(self, failure, component):
        msg = ("Fail to retrieve component '%s' properties."
               % component.getLabel())
        self.warning("%s", msg)
        self.debug("%s", log.getFailureTraceback(failure))
        self.__apartTasklessComponent(component)
        self._pending -= 1
        self._tryStarting()
        raise ComponentRejectedError(msg, cause=failure)
        
    def __cbRemoveComponent(self, props, component):
        assert props != None
        assert props == component.getProperties()
        if props in self._tasks:
            task = self._tasks[props]
            task.removeComponent(component)
        if component in self._taskless:            
            self.__releaseTasklessComponent(component)
        return component

    def __ebStopFailed(self, failure, label):
        self.warning("Task Manager failed to stop component '%s': %s",
                     label, log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))

    def __ebDeleteFailed(self, failure, label):
        self.warning("Task Manager failed to delete component '%s': %s",
                     label, log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))

    def __ebStartupFailed(self, failure):
        self._started = False
        self.warning("Task Manager failed to startup: %s",
                     log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        
    def __ebResumeFailed(self, failure):
        self._pause = True
        self.warning("Task Manager failed to resume: %s",
                     log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        
    def __ebPauseFailed(self, failure):
        self._pause = False
        self.warning("Task Manager failed to pause: %s",
                     log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
