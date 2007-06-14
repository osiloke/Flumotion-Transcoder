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

from flumotion.common.log import Loggable
from flumotion.common.planet import moods

from flumotion.transcoder import log
from flumotion.transcoder import utils
from flumotion.transcoder.log import LoggerProxy
from flumotion.transcoder.enums import MonitorFileStateEnum
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.eventsource import EventSource
from flumotion.transcoder.admin.admintask import IAdminTask
from flumotion.transcoder.admin.monprops import MonitorProperties
from flumotion.transcoder.admin.proxies.monitorproxy import MonitorProxy
from flumotion.transcoder.admin.proxies.monitorproxy import MonitorListener

#TODO: Schedule the component startup to prevent to starts 
#      lots of component at the same time.
#      Because when starting lots of components, the monitors
#      happy timeout may be triggered. For now, just using a large timeout.

class IMonitoringTaskListener(Interface):
    def onMonitoringActivated(self, task, monitor):
        pass
    
    def onMonitoringDeactivated(self, task, monitor):
        pass
    
    def onMonitoredFileAdded(self, task, profileContext):
        pass
    
    def onMonitoredFileRemoved(self, task, profileContext):
        pass

    
class MonitoringTaskListener(object):
    
    implements(IMonitoringTaskListener)

    def onMonitoringActivated(self, task, monitor):
        pass
    
    def onMonitoringDeactivated(self, task, monitor):
        pass
    
    def onMonitoredFileAdded(self, task, profileContext):
        pass
    
    def onMonitoredFileRemoved(self, task, profileContext):
        pass
    

class MonitoringTask(LoggerProxy, EventSource, MonitorListener):
    
    implements(IAdminTask)
    
    def __init__(self, logger, customerCtx):
        LoggerProxy.__init__(self, logger)
        EventSource.__init__(self, IMonitoringTaskListener)
        self._customerCtx = customerCtx
        self._worker = None # WorkerProxy
        self._started = False
        self._pendingName = None
        self._active = True
        self._delayed = None # IDelayedCall
        self._monitor = None # MonitorProxy
        self._monitors = {} # {MonitorProxy: None}
        self._label = customerCtx.getMonitorLabel()
        self._properties = MonitorProperties.createFromContext(customerCtx)
        

    ## IAdminTask IMplementation ##
        
    def getLabel(self):
        return self._label
    
    def getProperties(self):
        return self._properties

    def isActive(self):
        return self._started and (not self._paused)

    def getActiveComponent(self):
        return self._monitor

    def getActiveWorker(self):
        if self._monitor:
            return self._monitor.getWorker()
        for m in self._monitors:
            if m.getMood() == moods.happy:
                return m.getWorker()
        return None

    def addComponent(self, monitor):
        assert isinstance(monitor, MonitorProxy)
        assert not (monitor in self._monitors)
        self.log("Monitor '%s' added to task %s", 
                 monitor.getLabel(), self.getLabel())
        self._monitors[monitor] = None
        monitor.addListener(self)
        monitor.syncListener(self)
        
    def removeComponent(self, monitor):
        assert isinstance(monitor, MonitorProxy)
        assert monitor in self._monitors
        self.log("Monitor '%s' removed from task %s", 
                 monitor.getLabel(), self.getLabel())
        del self._monitors[monitor]
        monitor.removeListener(self)
        if monitor == self._monitor:
            self.__relieveMonitor()
    
    def start(self, components=None):
        if self._started: return
        self.log("Starting monitoring task '%s'", self.getLabel())
        self._started = True
        self._paused = False
        self.__startup()
    
    def pause(self):
        if self._started and (not self._paused):
            self.log("Pausing monitoring task '%s'", self.getLabel())
            self._paused = True
    
    def resume(self):
        if self._started and self._paused:
            self.log("Resuming monitoring task '%s'", self.getLabel())
            self._paused = False
            self.__startup()
                    
    
    def stop(self):
        """
        Relieve the selected monitor, and return
        all the monitors for the caller to choose what
        to do with them.
        After this, no monitor will/should be added or removed.
        """
        self.log("Stopping monitoring task '%s'", self.getLabel())
        self.__relieveMonitor()
        for m in self._monitors:
            m.removeListener()
        self._active = False
        return self._monitors.keys()
    
    def abort(self):
        """
        After this, no monitor will/should be added or removed.
        """
        self.log("Aborting monitoring task '%s'", self.getLabel())
        self.__relieveMonitor()
        for m in self._monitors:
            m.removeListener(self)
        self._monitors.clear()
        self._active = False

    def suggestWorker(self, worker):
        self.log("Worker '%s' suggested to monitoring task '%s'", 
                 worker and worker.getLabel(), self.getLabel())
        if (worker != self._worker) or (not self._monitor):
            self._worker = worker
            self.__startMonitor()


    ## IComponentListener Overrided Methods ##
    
    def onComponentMoodChanged(self, component, mood):
        if not self.isActive(): return
        self.log("Monitoring task '%s' monitor '%s' goes %s", 
                 self.getLabel(), component.getLabel(), mood.name)
        if component.getName() == self._pendingName:
            return
        if component == self._monitor:
            if mood == moods.happy:
                return
            self.warning("Selected monitor for '%s' gone %s", 
                         self._label, mood.name)
            self.__relieveMonitor()
            self.__delayedStartMonitor()
            return
        if mood == moods.sleeping:
            d = component.forceDelete()
            d.addErrback(self.__ebMonitorDeleteFailed, component)
            return
        # If no monitor is selected, don't stop any happy monitor
        if (not self._monitor) and (mood == moods.happy):
            return
        d = component.forceStop()
        d.addErrback(self.__ebMonitorStopFailed, component)


    ## IMonitorListener Overrided Methods ##
    
    def onMonitorFileRemoved(self, monitor, virtDir, file, state):
        if (monitor != self._monitor): return
        if (state == MonitorFileStateEnum.downloading): return
        profile = self.__file2profile(virtDir, file)
        if not profile:
            self.warning("File '%s' removed but no corresponding profile "
                         "found for customer '%s'", virtDir + file,
                         self._customerCtx.store.getName())
            return
        self._fireEvent(profile, "MonitoredFileRemoved")
    
    def onMonitorFileChanged(self, monitor, virtDir, file, state):
        if (monitor != self._monitor): return
        if (state != MonitorFileStateEnum.pending): return
        profile = self.__file2profile(virtDir, file)
        if not profile:
            self.warning("File '%s' added but no corresponding profile "
                         "found for customer '%s'", virtDir + file,
                         self._customerCtx.store.getName())
            return
        self._fireEvent(profile, "MonitoredFileAdded")


    ## Overrided 
        

    ## Private Methods ##
    
    def __file2profile(self, virtDir, file):
        virtPath = virtDir + file
        for p in self._customerCtx.iterProfileContexts(file):
            if p.getInputPath() == virtPath:
                return p
        return None
    
    def __startup(self):
        for m in self._monitors:
            self.onComponentMoodChanged(m, m.getMood())
        self.__startMonitor()            
    
    def __relieveMonitor(self):
        if self._monitor:
            self.log("Monitor %s releved by monitoring task %s",
                     self._monitor.getName(), self.getLabel())
            self._fireEvent(self._monitor, "MonitoringDeactivated")
            self._monitor = None
            
    def __electMonitor(self, monitor):
        assert monitor != None
        if self._monitor:
            self.__relieveMonitor()
        self._monitor = monitor
        self.log("Monitor %s elected by monitoring task %s",
                 self._monitor.getName(), self.getLabel())
        self._fireEvent(self._monitor, "MonitoringActivated")
        # Synchronize all monitored files
        d = monitor.waitFiles(adminconsts.MONITORING_UI_TIMEOUT)
        d.addCallbacks(self.__cbForwardFileEvents,
                       self.__ebGetFilesTimeout,
                       callbackArgs=(monitor,), errbackArgs=(monitor,))
        # Stop all monitor other than the selected one
        for m in self._monitors:
            if m != self._monitor:
                self.__stopMonitor(m)

    def  __cbForwardFileEvents(self, files, monitor):
        if monitor != self._monitor: return
        for d, f, s in files:
            self.onMonitorFileChanged(monitor, d, f, s)
            
    def __ebGetFilesTimeout(self, failure, monitor):
        if monitor != self._monitor: return
        self.warning("Failed to retrieve actual file list of monitor %s: %s",
                     monitor.getLabel(), log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
            
    def __delayedStartMonitor(self):
        if self._delayed:
            return
        self.log("Scheduling monitor start for task '%s'",
                 self.getLabel())
        self._delayed = reactor.callLater(adminconsts.MONITORING_START_DELAY,
                                          self.__startMonitor)

    def __startMonitor(self):
        if not self.isActive(): return
        if self._delayed:
            if self._delayed.active():
                self._delayed.cancel()
            self._delayed = None
        if self._pendingName:
            self.log("Canceling monitor startup for task '%s', "
                     "monitor '%s' is pending", self.getLabel(),
                     self._pendingName)
            return
        if not self._worker:
            self.warning("Couldn't start monitor for '%s', no worker found",
                         self._label)
            return
        # Check there is a valid monitor already running
        for m in self._monitors:
            # If it exists an happy monitor on the 
            # wanted worker, just elect it
            if ((m.getWorker() == self._worker) 
                and (m.getMood() == moods.happy)):
                self.__electMonitor(m)
                return
        monitorName = utils.genUniqueIdentifier()
        workerName = self._worker.getName()
        self.debug("Starting %s monitor %s on %s",
                   self._label, monitorName, workerName)
        self._pendingName = monitorName
        d = MonitorProxy.loadTo(self._worker, monitorName, 
                                self._label, self._properties,
                                adminconsts.MONITORING_LOAD_TIMEOUT)
        args = (monitorName, workerName)
        d.addCallbacks(self.__cbMonitorStartSucceed,
                       self.__ebMonitorStartFailed,
                       callbackArgs=args, errbackArgs=args)

    def __stopMonitor(self, monitor):
        self.debug("Stopping %s monitor %s", self._label, monitor.getName())
        # Don't stop sad monitors
        if monitor.getMood() != moods.sad:
            d = monitor.forceStop()
            d.addErrback(self.__ebMonitorStopFailed, monitor.getName())

    def __deleteMonitor(self, monitor):
        self.debug("Deleting %s monitor %s", self._label, monitor.getName())
        d = monitor.forceDelete()
        d.addErrback(self.__ebMonitorDeleteFailed, monitor.getName())
    
    def __cbMonitorStartSucceed(self, result, monitorName, workerName):
        self.debug("Succeed to load %s monitor '%s' on worker '%s'", 
                   self._label, monitorName, workerName)
        assert monitorName == result.getName()
        assert monitorName == self._pendingName
        # If the target worker changed, abort and start another monitor
        if ((not self._worker) 
            or (self._worker and (workerName != self._worker.getName()))):
            self._pendingName = None
            self.__stopMonitor(result)
            self.__delayedStartMonitor()
            return
        # If not, wait for the monitor to go happy
        d = result.waitHappy(adminconsts.HAPPY_TIMEOUT)
        args = (result, workerName)
        d.addCallbacks(self.__cbMonitorGoesHappy, 
                       self.__ebMonitorNotHappy,
                       callbackArgs=args, errbackArgs=args)
        
    def __ebMonitorStartFailed(self, failure, monitorName, workerName):
        self.warning("Failed to start %s monitor '%s' on worker '%s': %s", 
                     self._label, monitorName, workerName, 
                     log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        self._pendingName = None
        self.__delayedStartMonitor()
        
    def __cbMonitorGoesHappy(self, mood, monitor, workerName):
        self.debug("%s monitor '%s' on worker '%s' goes Happy", 
                   self._label, monitor.getName(), workerName)
        self._pendingName = None
        if workerName == self._worker:
            self.__electMonitor(monitor)
        else:
            # If the wanted worker changed, just start a new monitor
            self.__startMonitor()
                
    def __ebMonitorNotHappy(self, failure, monitor, workerName):
        self.warning("%s monitor '%s' on worker '%s' fail to be happy: %s", 
                     self._label, monitor.getName(), workerName,
                     log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        self._pendingName = None
        mood = monitor.getMood()
        # Because the monitor was pending to start, its event were ignored
        # So resend the mood changing event
        self.onComponentMoodChanged(monitor, mood)
        # And schedule starting a new one
        self.__delayedStartMonitor()
        
    def __ebMonitorStopFailed(self, failure, name):
        self.warning("Failed to stop %s monitor %s: %s", 
                     self._label, name, log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        
    def __ebMonitorDeleteFailed(self, failure, monitor):
        self.warning("Failed to delete monitor '%s': %s", 
                     monitor.getLabel(), log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
