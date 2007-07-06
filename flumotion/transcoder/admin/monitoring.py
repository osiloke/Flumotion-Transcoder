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

from flumotion.transcoder import log
from flumotion.transcoder import utils
from flumotion.transcoder.errors import OperationTimedOutError
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.taskmanager import TaskManager
from flumotion.transcoder.admin.monbalancer import MonitorBalancer
from flumotion.transcoder.admin.proxies.workerset import WorkerSetListener
from flumotion.transcoder.admin.proxies.monitorset import MonitorSetListener
from flumotion.transcoder.admin.proxies.monitorproxy import MonitorListener

#FIXME: Better handling of listener subclassing,
# Right now, Monitoring have to inherrit from MonitorListener,
# even if TaskManager already inherrit from ComponentListener,
# and it only use the ComponentListener handlers.

class IMonitoringListener(Interface):
    def onMonitoringTaskAdded(self, takser, task):
        pass
    
    def onMonitoringTaskRemoved(self, tasker, task):
        pass

    
class MonitoringListener(object):
    
    implements(IMonitoringListener)

    def onMonitoringTaskAdded(self, takser, task):
        pass
    
    def onMonitoringTaskRemoved(self, tasker, task):
        pass


class Monitoring(TaskManager, WorkerSetListener, 
                 MonitorSetListener, MonitorListener):
    
    logCategory = adminconsts.MONITORING_LOG_CATEGORY
    
    def __init__(self, workerset, monitorset):
        TaskManager.__init__(self, IMonitoringListener)
        self._workers = workerset
        self._monitors = monitorset
        self._balancer = MonitorBalancer()
        

    ## Public Method ##
    
    def initialize(self):
        self.log("Initializing Monitoring Manager")
        self._workers.addListener(self)
        self._monitors.addListener(self)
        self._workers.syncListener(self)
        self._monitors.syncListener(self)
        return TaskManager.initialize(self)

    
    ## Overrided Virtual Methods ##

    def _doStart(self):
        self.log("Ready to start monitoring, waiting monitors to become idle")
        d = self._monitors.waitIdle(adminconsts.WAIT_IDLE_TIMEOUT)
        d.addBoth(self.__cbMonitorSetGoesIdle)
        return d
    
    def _doResume(self):
        self.log("Ready to resume monitoring, waiting monitors to become idle")
        d = self._monitors.waitIdle(adminconsts.WAIT_IDLE_TIMEOUT)
        d.addBoth(self.__cbMonitorSetGoesIdle)
        return d
    
    def _doAbort(self):
        self.log("Aborting monitoring")
        self._balancer.clearTasks()

    def _onTaskAdded(self, task):
        if self.isStarted():
            self._balancer.addTask(task)
            self._balancer.balance()
        self._fireEvent(task, "MonitoringTaskAdded")
    
    def _onTaskRemoved(self, task):
        if self.isStarted():
            self._balancer.removeTask(task)
            self._balancer.balance()
        self._fireEvent(task, "MonitoringTaskRemoved")

            
    ## IWorkerSetListener Overrided Methods ##
    
    def onWorkerAddedToSet(self, workerset, worker):
        self.log("Worker '%s' added to monitoring", worker.getLabel())
        self._balancer.addWorker(worker)
        self._balancer.balance()
    
    def onWorkerRemovedFromSet(self, workerset, worker):
        self.log("Worker '%s' removed from monitoring", worker.getLabel())
        self._balancer.removeWorker(worker)
        self._balancer.balance()


    ## IMonitorSetListener Overrided Methods ##
    
    def onMonitorAddedToSet(self, monitorset, monitor):
        self.log("Monitor '%s' added to monitoring", monitor.getLabel())
        d = self.addComponent(monitor)
        d.addErrback(self.__ebAddComponentFailed, monitor.getName())
    
    def onMonitorRemovedFromSet(self, monitorset, monitor):
        self.log("Monitor '%s' removed from monitoring", monitor.getLabel())
        d = self.removeComponent(monitor)
        d.addErrback(self.__ebRemoveComponentFailed, monitor.getName())


    ## Overriden Methods ##
    
    def _doSyncListener(self, listener):
        for t in self._tasks.itervalues():
            self._fireEventTo(t, listener, "MonitoringTaskAdded")


    ## Private Methods ##
    
    def __cbMonitorSetGoesIdle(self, result):
        if (isinstance(result, Failure) 
            and not result.check(OperationTimedOutError)):
            self.warning("Failure during waiting monitor set "
                         "to become idle: %s",
                         log.getFailureMessage(result))
            self.debug("Monitor idle failure traceback:\n%s",
                       log.getFailureTraceback(result))
        self.log("Free to continue monitoring starting/resuming")
        d = defer.Deferred()
        for task in self.iterTasks():
            d.addCallback(self.__cbRetrievePotentialWorker, task)
        d.addCallback(utils.dropResult, self._balancer.balance)
        d.addErrback(self.__ebStartingFailure)
        d.callback(defer._nothing)
        return d

    def __cbRetrievePotentialWorker(self, _, task):
        timeout = adminconsts.MONITORING_POTENTIAL_WORKER_TIMEOUT
        d = task.waitPotentialWorker(timeout)
        # Call self._balancer.addTask(task, worker)
        d.addCallback(utils.shiftResult, self._balancer.addTask, 1, task)
        return d

    def __ebStartingFailure(self, failure):
        self.warning("Failure during monitoring starting/resuming: %s",
                     log.getFailureMessage(failure))
        self.debug("Startup failure traceback:\n%s",
                   log.getFailureTraceback(failure))
        return failure

    def __ebAddComponentFailed(self, failure, name):
        self.warning("Failed to add monitor '%s' "
                     "to monitoring manager: %s", 
                     name, log.getFailureMessage(failure))
        self.debug("Add monitor failure traceback:\n%s",
                   log.getFailureTraceback(failure))
    
    def __ebRemoveComponentFailed(self, failure, name):
        self.warning("Failed to remove monitor '%s' "
                     "from monitoring manager: %s",
                     name, log.getFailureMessage(failure))
        self.debug("Remove component failure traceback:\n%s",
                   log.getFailureTraceback(failure))
