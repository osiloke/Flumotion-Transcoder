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

from flumotion.transcoder import log, utils
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
    
    def onMonitoredFileAdded(self, task, profileContext, state):
        pass
    
    def onMonitoredFileStateChanged(self, task, profileContext, state):
        pass
    
    def onMonitoredFileRemoved(self, task, profileContext, state):
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

    def onMonitoredFileStateChanged(self, task, profileContext, state):
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
        self._pendingMoves = [] # [VirtualPath, VirutalPath, [str]]
        self._movingFiles = False

    
    ## Public Methods ##
    
    def setFileState(self, virtBase, relPath, state):
        monitor = self.getActiveComponent()
        if not monitor:
            self.warning("Monitoring task '%s' file '%s' state changed to %s "
                         "without active monitor", self.getLabel(),
                         virtBase.append(relPath), state.name)
            return
        self.log("Monitoring task '%s' file '%s' state changed to %s",
                 self.getLabel(), virtBase.append(relPath), state.name)
        d = monitor.setFileState(virtBase, relPath, state)
        d.addErrback(self.__ebSetFileStateFailed, monitor, 
                     virtBase, relPath, state)
        
    def moveFiles(self, virtSrcBase, virtDestBase, relFiles):
        args = virtSrcBase, virtDestBase, relFiles
        self._pendingMoves.append(args)
        if not self._movingFiles:
            self.__asyncMovePendingFiles()        
    

    ## IComponentListener Overrided Methods ##
    
    def onComponentMoodChanged(self, monitor, mood):
        if not self.isStarted(): return
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
        self._fireEvent((profile, state), "MonitoredFileRemoved")
    
    def onMonitorFileAdded(self, monitor, virtDir, file, state):
        if not self._isElectedComponent(monitor): return
        profile = self.__file2profile(virtDir, file)
        if not profile:
            self.warning("File '%s' added but no corresponding profile "
                         "found for customer '%s'", virtDir + file,
                         self._customerCtx.store.getName())
            return
        self._fireEvent((profile, state), "MonitoredFileAdded")

    def onMonitorFileChanged(self, monitor, virtDir, file, state):
        if not self._isElectedComponent(monitor): return
        profile = self.__file2profile(virtDir, file)
        if not profile:
            self.warning("File '%s' state changed but no corresponding "
                         "profile found for customer '%s'", virtDir + file,
                         self._customerCtx.store.getName())
            return
        self._fireEvent((profile, state), "MonitoredFileStateChanged")


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

    def _onStarted(self):
        for c in self.iterComponents():
            self.onComponentMoodChanged(c, c.getMood())
    
    def _doAcceptSuggestedWorker(self, worker):
        current = self.getWorker()
        monitor = self.getActiveComponent()
        return (worker != current) or (not monitor)

    def _doAborted(self):
        self._fireEvent(self.getWorker(), "FailToRunOnWorker")
    
    def _doSelectPotentialComponent(self, components):
        targetWorker = self.getWorker()
        for c in components:
            # If it exists an happy monitor on the target worker, 
            # or there not target worker set, just elect it
            if ((not targetWorker or (c.getWorker() == targetWorker)) 
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

    def __asyncMovePendingFiles(self):
        if not self._pendingMoves:
            self._movingFiles = False
            return
        virtSrcBase, virtDestBase, relFiles = self._pendingMoves.pop()
        monitor = self.getActiveComponent()
        if not monitor:
            self.warning("No monitor found to move files '%s' to '%s'",
                         virtSrcBase, virtDestBase)
            # Stop moving files
            self._movingFiles = False
            return
        self.debug("Ask monitor '%s' to move files form '%s' to '%s'",
                   monitor.getName(), virtSrcBase, virtDestBase)
        d = monitor.moveFiles(virtSrcBase, virtDestBase, relFiles)
        args = (monitor, virtSrcBase, virtDestBase, relFiles)
        d.addCallbacks(self.__cbFileMoved, self.__ebMoveFilesFailed, 
                       callbackArgs=args, errbackArgs=args)

    def __ebSetFileStateFailed(self, failure, monitor, 
                                virtBase, relFile, state):
        self.warning("Monitoring task '%s' monitor '%s' Fail to change "
                     "file '%s' state to %s: %s", self.getLabel(),
                     monitor.getName(), virtBase.append(relFile), state.name,
                     log.getFailureMessage(failure))
        self.debug("Set file state failure traceback:\n%s", 
                   log.getFailureTraceback(failure))
    
    def __cbFileMoved(self, result, monitor, 
                      virtSrcBase, virtDestBase, relFiles):
        for relFile in relFiles:
            self.log("File '%s' moved to '%s'",
                      virtSrcBase.append(relFile),
                      virtDestBase.append(relFile))
        # Continue moving files
        self.__asyncMovePendingFiles()
        
    def __ebMoveFilesFailed(self, failure, monitor,
                            virtSrcBase, virtDestBase, relFiles):
        self.warning("Monitoring task '%s' monitor '%s' fail to move files "
                     "from '%s' to '%s': %s", self.getLabel(),
                     monitor.getName(), virtSrcBase, virtDestBase,
                     log.getFailureMessage(failure))
        self.debug("Move files failure traceback:\n%s", 
                   log.getFailureTraceback(failure))
        # Continue moving files anyway
        self.__asyncMovePendingFiles()
