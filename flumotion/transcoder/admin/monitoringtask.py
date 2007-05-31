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

from flumotion.common.log import Loggable
from flumotion.common.planet import moods

from flumotion.transcoder import log
from flumotion.transcoder.admin import constants, utils
from flumotion.transcoder.admin.eventsource import EventSource
from flumotion.transcoder.admin.taskbalancer import ITask
from flumotion.transcoder.admin.proxies.monitorproxy import MonitorProxy
from flumotion.transcoder.admin.proxies.monitorproxy import MonitorListener

#TODO: Schedule the component startup to prevent to starts 
#      lots of component at the same time

class IMonitoringTaskListener(Interface):
    def onMonitorElected(self, monitoringtask, monitor):
        pass
    
    def onMonitorRelieved(self, monitoringtask, monitor):
        pass

    
class MonitoringTaskListener(object):
    
    implements(IMonitoringTaskListener)

    def onMonitorElected(self, monitoringtask, monitor):
        pass
    
    def onMonitorRelieved(self, monitoringtask, monitor):
        pass


class MonitoringTask(Loggable, EventSource, MonitorListener):
    
    implements(ITask)
    
    logCategory = 'admin-monitoring'
    
    def __init__(self, label, properties):
        EventSource.__init__(self, IMonitoringTaskListener)
        self._label = label
        self._properties = properties # MonitorProperties
        self._worker = None # WorkerProxy
        self._pendingName = None
        self._active = True
        self._selected = None # MonitorProxy
        self._monitors = {} # {MonitorProxy: None}
        
    def getLabel(self):
        return self._label
    
    def getProperties(self):
        return self._properties

    def getActiveWorker(self):
        if self._selected:
            return self._selected.getWorker()
        for m in self._monitors:
            if m.getMood() == moods.happy:
                return m.getWorker()
        return None

    def addMonitor(self, monitor):
        assert not (monitor in self._monitors)
        self._monitors[monitor] = None
        monitor.addListener(self)
        monitor.syncListener(self)
        
    def removeMonitor(self, monitor):
        assert monitor in self._monitors
        del self._monitors[monitor]
        monitor.removeListener(self)
        if monitor == self._selected:
            self.__relieveMonitor()
    
    def stopMonitoring(self):
        """
        Relieve the selected monitor, and return
        all the monitors for the caller to choose what
        to do with them.
        After this, no monitor will/should be added or removed.
        """
        self.__relieveMonitor()
        for m in self._monitors:
            m.removeListener()
        self._active = False
        return self._monitors.keys()
    
    def abortMonitoring(self):
        """
        After this, no monitor will/should be added or removed.
        """
        self.__relieveMonitor()
        for m in self._monitors:
            m.removeListener(self)
        self._monitors.clear()
        self._active = False


    ## ITask Implementation ##
    
    def setTaskWorker(self, worker):
        if (worker != self._worker) or (not self._selected):
            self._worker = worker
            self.__startMonitor()


    ## IComponentListener Overrided Methods ##
    
    def onComponentMoodChanged(self, component, mood):
        if component.getName() == self._pendingName:
            return
        if component == self._selected:
            if mood == moods.happy:
                return
            self.warning("Selected monitor for '%s' gone %s", 
                         self._label, mood.name)
            self.__relieveMonitor()
            self.__startMonitor()
            return
        if mood == moods.sleeping:
            d = component.forceDelete()
            d.addErrback(self.__asyncMonitorDeleteFailed, component)
            return
        # If no monitor is selected, don't stop any happy monitor
        if (not self._selected) and (mood == moods.happy):
            return
        d = component.forceStop()
        d.addErrback(self.__asyncMonitorStopFailed, component)


    ## Private Methods ##
    
    def __relieveMonitor(self):
        if self._selected:
            self._fireEvent(self._selected, "MonitorRelieved")
            self._selected = None
            
    def __electMonitor(self, monitor):
        if self._selected:
            self.__relieveMonitor()
        self._selected = monitor
        self._fireEvent(self._selected, "MonitorElected")
        # Stop all monitor other than the selected one
        for m in self._monitors:
            if m != self._selected:
                self.__stopMonitor(m)

    def __startMonitor(self):
        if self._pendingName:
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
                                self._label, self._properties)
        d.setTimeout(constants.MONITORING_START_TIMEOUT)
        args = (monitorName, workerName)
        d.addCallbacks(self.__asyncMonitorStartSucceed,
                       self.__asyncMonitorStartFailed,
                       callbackArgs=args, errbackArgs=args)

    def __stopMonitor(self, monitor):
        self.debug("Stopping %s monitor %s", self._label, monitor.getName())
        # Don't stop sad monitors
        if monitor.getMood() != moods.sad:
            d = monitor.forceStop()
            d.addErrback(self.__asyncMonitorStopFailed, monitor.getName())

    def __deleteMonitor(self, monitor):
        self.debug("Deleting %s monitor %s", self._label, monitor.getName())
        d = monitor.forceDelete()
        d.addErrback(self.__asyncMonitorDeleteFailed, monitor.getName())
    
    def __asyncMonitorStartSucceed(self, result, monitorName, workerName):
        self.debug("Succeed to start %s monitor '%s' on worker '%s'", 
                   self._label, monitorName, workerName)
        assert monitorName == result.getName()
        assert monitorName == self._pendingName
        # If the target worker changed, abort and start another monitor
        if self._worker and (workerName != self._worker.getName()):
            self._pendingName = None
            self.__stopMonitor(result)
            self.__startMonitor()
            return
        # If not, wait for the monitor to go happy
        d = result.waitHappy()
        args = (result, workerName)
        d.addCallbacks(self.__asyncMonitorGoesHappy, 
                       self.__asyncMonitorNotHappy,
                       callbackArgs=args, errbackArgs=args)
        
    def __asyncMonitorStartFailed(self, failure, monitorName, workerName):
        self.warning("Failed to start %s monitor '%s' on worker '%s': %s", 
                     self._label, monitorName, workerName, 
                     log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        self._pendingName = None
        self.__startMonitor()
        
    def __asyncMonitorGoesHappy(self, mood, monitor, workerName):
        self.debug("%s monitor '%s' on worker '%s' goes Happy", 
                   self._label, monitor.getName(), workerName)
        self._pendingName = None
        if workerName == self._worker:
            self.__electMonitor(monitor)
        else:
            # If the wanted worker changed, just start a new monitor
            self.__startMonitor()
                
    def __asyncMonitorNotHappy(self, failure, monitor, workerName):
        self.warning("%s monitor '%s' on worker '%s' fail to be happy: %s", 
                     self._label, monitor.getName(), workerName,
                     log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        self._pendingName = None
        mood = monitor.getMood()
        # Because the monitor was pending to start, its event were ignored
        # So resend the mood changing event
        self.onComponentMoodChanged(monitor, mood)
        
    def __asyncMonitorStopFailed(self, failure, name):
        self.warning("Failed to stop %s monitor %s: %s", 
                     self._label, name, log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        
    def __asyncMonitorDeleteFailed(self, failure, monitor):
        self.warning("Failed to delete monitor '%s': %s", 
                     monitor.getLabel(), log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
