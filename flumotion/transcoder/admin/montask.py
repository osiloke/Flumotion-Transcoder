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

from flumotion.common.planet import moods

from flumotion.transcoder import log
from flumotion.transcoder.enums import MonitorFileStateEnum
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.admintask import AdminTask
from flumotion.transcoder.admin.monprops import MonitorProperties
from flumotion.transcoder.admin.proxies.monitorproxy import MonitorProxy
from flumotion.transcoder.admin.proxies.monitorproxy import MonitorListener

#TODO: Schedule the component startup to prevent starting 
#      lots of component at the same time.
#      Because when starting lots of components, the monitors
#      happy timeout may be triggered. For now, just using a large timeout.

class IMonitoringTaskListener(Interface):
    def onFailToRunOnWorker(self, task, worker):
        pass
    
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

    def onFailToRunOnWorker(self, task, worker):
        pass

    def onMonitoringActivated(self, task, monitor):
        pass
    
    def onMonitoringDeactivated(self, task, monitor):
        pass
    
    def onMonitoredFileAdded(self, task, profileContext):
        pass
    
    def onMonitoredFileRemoved(self, task, profileContext):
        pass
    

class MonitoringTask(AdminTask, MonitorListener):
    
    MAX_RETRIES = adminconsts.MONITOR_MAX_RETRIES
    
    def __init__(self, logger, customerCtx):
        AdminTask.__init__(self, logger, customerCtx.getMonitorLabel(),
                           MonitorProperties.createFromContext(customerCtx),
                           IMonitoringTaskListener)
        self._customerCtx = customerCtx
    

    ## IComponentListener Overrided Methods ##
    
    def onComponentMoodChanged(self, monitor, mood):
        if not self.isActive(): return
        self.log("Monitoring task '%s' monitor '%s' goes %s", 
                 self.getLabel(), monitor.getName(), mood.name)
        if self._isPendingComponent(monitor):
            # Currently beeing started up
            return
        if self._isElectedComponent(monitor):
            if (mood != moods.lost):
                self._cancelComponentHold()
            if mood == moods.happy:
                return
            self.warning("Monitoring task '%s' selected monitor '%s' "
                         "gone %s", self.getLabel(), 
                         monitor.getName(), mood.name)
            if mood == moods.lost:
                # If the monitor goes lost, wait a fixed amount of time
                # to cope with small transient failures.
                self._holdLostComponent(monitor)                
                return
            self._abort()
            return
        if mood == moods.sleeping:
            self._deleteComponent(monitor)
            return
        if (not self._hasElectedComponent()) and (mood == moods.happy):
            # If no monitor is selected, don't stop any happy monitor
            return
        self._stopComponent(monitor)


    ## IMonitorListener Overrided Methods ##
    
    def onMonitorFileRemoved(self, monitor, virtDir, file, state):
        if not self._isElectedComponent(monitor): return
        if (state == MonitorFileStateEnum.downloading): return
        profile = self.__file2profile(virtDir, file)
        if not profile:
            self.warning("File '%s' removed but no corresponding profile "
                         "found for customer '%s'", virtDir + file,
                         self._customerCtx.store.getName())
            return
        self._fireEvent(profile, "MonitoredFileRemoved")
    
    def onMonitorFileChanged(self, monitor, virtDir, file, state):
        if not self._isElectedComponent(monitor): return
        if (state != MonitorFileStateEnum.pending): return
        profile = self.__file2profile(virtDir, file)
        if not profile:
            self.warning("File '%s' added but no corresponding profile "
                         "found for customer '%s'", virtDir + file,
                         self._customerCtx.store.getName())
            return
        self._fireEvent(profile, "MonitoredFileAdded")


    ## Virtual Methods Implementation ##
    
    def _onComponentAdded(self, component):
        component.addListener(self)
        component.syncListener(self)

    def _onComponentRemoved(self, component):
        component.removeListener(self)

    def _onComponentElected(self, component):
        self._fireEvent(component, "MonitoringActivated")
        component.syncListener(self)

    def _onComponentRelieved(self, component):
        self._fireEvent(component, "MonitoringDeactivated")

    def _onComponentStartupCanceled(self, component):
        # Because the monitor was pending to start, 
        # this event was ignored
        # So resend the mood changing event
        mood = component.getMood()
        self.onComponentMoodChanged(component, mood)
    
    def _doAcceptSuggestedWorker(self, worker):
        current = self.getWorker()
        monitor = self.getActiveComponent()
        return (worker != current) or (not monitor)

    def _doStartup(self):
        for c in self.iterComponents():
            self.onComponentMoodChanged(c, c.getMood())
    
    def _doAborted(self):
        self._fireEvent(self.getWorker(), "FailToRunOnWorker")
    
    def _doSelectPotentialComponent(self, components):
        for c in components:
            # If it exists an happy monitor on the 
            # wanted worker, just elect it
            if ((c.getWorker() == self.getWorker()) 
                and (c.getMood() == moods.happy)):
                return c
        return None
    
    def _doLoadComponent(self, worker, componentName, componentLabel,
                         componentProperties, loadTimeout):
        return MonitorProxy.loadTo(worker, componentName, 
                                   componentLabel, 
                                   componentProperties,
                                   loadTimeout)


    ## Private Methods ##
    
    def __file2profile(self, virtDir, file):
        virtPath = virtDir + file
        for p in self._customerCtx.iterProfileContexts(file):
            if p.getInputPath() == virtPath:
                return p
        return None
