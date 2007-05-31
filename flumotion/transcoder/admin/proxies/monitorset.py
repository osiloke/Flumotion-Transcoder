# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import math

from zope.interface import Interface, implements
from twisted.internet import defer, reactor
from twisted.python.failure import Failure

from flumotion.common.planet import moods
from flumotion.common.errors import ComponentError, BusyComponentError

from flumotion.transcoder import log
from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.admin import constants, utils
from flumotion.transcoder.admin.taskbalancer import TaskBalancer
from flumotion.transcoder.admin.monitoringtask import MonitoringTaskListener
from flumotion.transcoder.admin.proxies.componentset import BaseComponentSet
from flumotion.transcoder.admin.proxies.monitorproxy import MonitorProxy, MonitorListener
from flumotion.transcoder.admin.proxies.workerset import WorkerSetListener
from flumotion.transcoder.admin.proxies.managerset import ManagerSetListener


class IMonitorSetListener(Interface):
    def onMonitorAddedToSet(self, monitorset, monitor):
        pass
    
    def onMonitorRemovedFromSet(self, monitorset, monitor):
        pass


class MonitorSetListener(object):
    
    implements(IMonitorSetListener)
    
    def onMonitorAddedToSet(self, monitorset, monitor):
        pass
    
    def onMonitorRemovedFromSet(self, monitorset, monitor):
        pass


class MonitorSet(BaseComponentSet, 
                 WorkerSetListener,
                 ManagerSetListener, 
                 MonitorListener,
                 MonitoringTaskListener):
    
    def __init__(self, mgrset, wkrset):
        BaseComponentSet.__init__(self, mgrset,
                                  IMonitorSetListener)
        self._workers = wkrset
        self._workers.addListener(self)
        self._identifiers = {} # {identifiers: MonitorProperties}
        self._monitorings = {} # {MonitorProperties: MonitoringEntry}
        self._apartedMonitors = {} # {MonitorProxy: None}
        self._balancer = TaskBalancer()
        self._pendingGetProperties = 0
        self._started = False
        self._synchronized = False
        self._shutdown = False
        self._monitoring = False
        reactor.addSystemEventTrigger("before", "shutdown", self.__shutdown)

        
    ## Public Method ##
    
    def addMonitoring(self, identifier, task):
        self.debug("Adding monitoring entry for %s", task.getLabel())
        props = task.getProperties()
        assert not (props in self._monitorings)
        assert not (identifier in self._identifiers)
        self._identifiers[identifier] = props
        self._monitorings[props] = task
        task.addListener(self)
        for m in self._apartedMonitors.keys():
            if m.getProperties() == props:
                # Not my responsability anymore
                m.removeListener(self)
                del self._apartedMonitors[m]
                task.addMonitor(m)
        if self._synchronized:
            self._balancer.addTask(task)
    
    def removeMonitoring(self, identifier):
        assert identifier in self._identifiers
        props = self._identifiers[identifier]
        task = self._monitorings[props]
        self.debug("Removing monitoring entry for %s", task.getLabel())
        task.removeListener(self)
        del self._identifiers[identifier]
        del self._monitorings[props]
        for m in task.stopMonitoring():
            self.__apartMonitor(m)
        if self._synchronized:
            self._balancer.removeTask(task)

    def startMonitoring(self):
        self._started = True
        self.__tryStartingMonitoring()


    ## Overriden Methods ##
    
    def _doSyncListener(self, listener):
        self._syncProxies("_components", listener, "MonitorAddedToSet")

    def _doAcceptComponent(self, component):
        if not isinstance(component, MonitorProxy):
            return False
        return True

    def _doAddComponent(self, component):
        BaseComponentSet._doAddComponent(self, component)
        self.debug("Monitor component '%s' added to set",
                   component.getLabel())
        self._pendingGetProperties += 1
        d = component.waitProperties(constants.MONITORSET_WAITPROPS_TIMEOUT)        
        d.addCallbacks(self.__asyncGotProperties, self.__asyncGetPropertiesFailed, 
                       callbackArgs=(component,), errbackArgs=(component,))
        
    
    def _doRemoveComponent(self, component):
        BaseComponentSet._doRemoveComponent(self, component)
        self.debug("Monitor component '%s' removed from set",
                   component.getLabel())
        props = component.getProperties()
        assert props != None
        if props in self._monitorings:
            entry = self._monitorings[props]
            entry.removeMonitor(component)
        if component in self._apartedMonitors:
            component.removeListener(self)
            del self._apartedMonitors[component]


    ## managerproxy.IManagerListener Implementation ##
    
    def onAtmosphereSet(self, manager, atmosphere):
        BaseComponentSet.onAtmosphereSet(self, manager, atmosphere)
        d = atmosphere.waitSynchronized(constants.SYNCHRONIZE_TIMEOUT)
        d.addBoth(self.__asyncSynchronized)

    
    ## IWorkerSet Overrided Methods ##
    
    def onWorkerAddedToSet(self, workerset, worker):
        self._balancer.addWorker(worker)
        self._balancer.balanceTasks()
        
    
    def onWorkerRemovedFromSet(self, workerset, worker):
        self._balancer.removeWorker(worker)
        self._balancer.balanceTasks()
    
    ## IComponentListener Overrided Methods ##
    
    def onComponentMoodChanged(self, component, mood):
        if mood == moods.sleeping:
            d = component.forceDelete()
            d.addErrback(self.__asyncDeleteFailed, component.getLabel())
        elif mood != moods.sad:
            d = component.forceStop()
            d.addErrback(self.__asyncStopFailed, component.getLabel())
    
    
    ## IMonitoringListener Overrided Methods ##
    
    def onMonitorElected(self, monitoring, monitor):
        self._fireEvent(monitor, "MonitorAddedToSet")
    
    def onMonitorRelieved(self, monitoring, monitor):
        self._fireEvent(monitor, "MonitorRemovedFromSet")

    
    ## Private Methods ##
    
    def __shutdown(self):
        self._shutdown = True
        for task in self._monitorings.itervalues():
            task.removeListener(self)
            task.abortMonitoring()
        self._monitorings.clear()
        self._balancer.clearTasks()
    
    def __asyncSynchronized(self, _):
        self._synchronized = True
        self.__tryStartingMonitoring()
    
    def __tryStartingMonitoring(self):
        if ((not self._monitoring) 
            and self._started 
            and self._synchronized 
            and (self._pendingGetProperties == 0)):
            self.__startMonitoring()
    
    def __startMonitoring(self):
        self._monitoring = True
        for entry in self._monitorings.itervalues():            
            self._balancer.addTask(entry, entry.getActiveWorker())
        self._balancer.balanceTasks()
    
    def __asyncGotProperties(self, props, monitor):
        assert props != None
        assert props == monitor.getProperties()
        if props in self._monitorings:
            entry = self._monitorings[props]
            entry.addMonitor(monitor)
        else:
            self.warning("Component '%s' added for an unknown monitoring "
                         "configuration.", monitor.getLabel())
            self.__appartMonitor(monitor)
        self._pendingGetProperties -= 1
        self.__tryStartingMonitoring()
    
    def __asyncGetPropertiesFailed(self, failure, monitor):
        self.warning("Fail to retrieve component '%s' properties.",
                     monitor.getLabel())
        self.debug("%s", log.getFailureTraceback(failure))
        self.__appartMonitor(monitor)
        self._pendingGetProperties -= 1
        self.__tryStartingMonitoring()
        
    def __appartMonitor(self, monitor):
        # Take responsability
        monitor.addListener(self)
        monitor.syncListener(self)
        self._apartedMonitors[monitor] = None
    
    def __asyncStopFailed(self, failure, label):
        self.warning("MonitorSet failed to stop monitor '%s': %s",
                     label, log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))

    def __asyncDeleteFailed(self, failure, label):
        self.warning("MonitorSet failed to delete monitor '%s': %s",
                     label, log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
