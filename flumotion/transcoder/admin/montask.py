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

from flumotion.common.planet import moods

from flumotion.inhouse import log, defer, utils

from flumotion.transcoder.enums import MonitorFileStateEnum
from flumotion.transcoder.admin import adminconsts, admintask
from flumotion.transcoder.admin.property import filemon
from flumotion.transcoder.admin.proxy import monitor

#TODO: Schedule the component startup to prevent starting 
#      lots of component at the same time.
#      Because when starting lots of components, the monitors
#      happy timeout may be triggered. For now, just using a large timeout.


class MonitoringTask(admintask.AdminTask):
    
    MAX_RETRIES = adminconsts.MONITOR_MAX_RETRIES
    
    def __init__(self, logger, custCtx):
        admintask.AdminTask.__init__(self, logger, custCtx.getMonitorLabel(),
                                     filemon.MonitorProperties.createFromContext(custCtx))
        self._custCtx = custCtx
        self._pendingMoves = [] # [VirtualPath, VirutalPath, [str]]
        self._movingFiles = False
        # Registering Events
        self._register("fail-to-run")
        self._register("monitoring-activated")
        self._register("monitoring-deactivated")
        self._register("file-added")
        self._register("file-state-changed")
        self._register("file-removed")
        

    
    ## Public Methods ##
    
    def setFileState(self, virtBase, relPath, state):
        monPxy = self.getActiveComponent()
        if not monPxy:
            self.warning("Monitoring task '%s' file '%s' state changed to %s "
                         "without active monitor", self.getLabel(),
                         virtBase.append(relPath), state.name)
            return
        self.log("Monitoring task '%s' file '%s' state changed to %s",
                 self.getLabel(), virtBase.append(relPath), state.name)
        monPxy.setFileStateBuffered(virtBase, relPath, state)
        
    def moveFiles(self, virtSrcBase, virtDestBase, relFiles):
        args = virtSrcBase, virtDestBase, relFiles
        self._pendingMoves.append(args)
        if not self._movingFiles:
            self.__asyncMovePendingFiles()        
    

    ## Component Event Listeners ##
    
    def _onComponentMoodChanged(self, monPxy, mood):
        if not self.isStarted(): return
        self.log("Monitoring task '%s' monitor '%s' goes %s", 
                 self.getLabel(), monPxy.getName(), mood.name)
        if self._isPendingComponent(monPxy):
            # Currently beeing started up
            return
        if self._isElectedComponent(monPxy):
            if (mood != moods.lost):
                self._cancelComponentHold()
            if mood == moods.happy:
                return
            self.warning("Monitoring task '%s' selected monitor '%s' "
                         "gone %s", self.getLabel(), 
                         monPxy.getName(), mood.name)
            if mood == moods.lost:
                # If the monitor goes lost, wait a fixed amount of time
                # to cope with small transient failures.
                self._holdLostComponent(monPxy)                
                return
            self._abort()
            return
        if mood == moods.sleeping:
            self._deleteComponent(monPxy)
            return
        if (not self._hasElectedComponent()) and (mood == moods.happy):
            # If no monitor is selected, don't stop any happy monitor
            return
        self._stopComponent(monPxy)


    ## Monitor Event Listeners ##
    
    def _onMonitorFileRemoved(self, monPxy, virtDir, file, state):
        if not self._isElectedComponent(monPxy): return
        if (state == MonitorFileStateEnum.downloading): return
        profCtx = self.__file2profileContext(virtDir, file)
        if not profCtx:
            self.warning("File '%s' removed but no corresponding profile "
                         "found for customer '%s'", virtDir + file,
                         self._custCtx.getName())
            return
        self.emit("file-removed", profCtx, state)
    
    def _onMonitorFileAdded(self, monPxy, virtDir, file, state):
        if not self._isElectedComponent(monPxy): return
        profCtx = self.__file2profileContext(virtDir, file)
        if not profCtx:
            self.warning("File '%s' added but no corresponding profile "
                         "found for customer '%s'", virtDir + file,
                         self._custCtx.getName())
            return
        self.emit("file-added", profCtx, state)

    def _onMonitorFileChanged(self, monPxy, virtDir, file, state):
        if not self._isElectedComponent(monPxy): return
        profCtx = self.__file2profileContext(virtDir, file)
        if not profCtx:
            self.warning("File '%s' state changed but no corresponding "
                         "profile found for customer '%s'", virtDir + file,
                         self._custCtx.getName())
            return
        self.emit("file-state-changed", profCtx, state)


    ## Virtual Methods Implementation ##
    
    def _onComponentAdded(self, compPxy):
        compPxy.connectListener("mood-changed", self, self._onComponentMoodChanged)
        compPxy.connectListener("file-removed", self, self._onMonitorFileRemoved)
        compPxy.connectListener("file-added", self, self._onMonitorFileAdded)
        compPxy.connectListener("file-changed", self, self._onMonitorFileChanged)
        compPxy.update(self)

    def _onComponentRemoved(self, compPxy):
        compPxy.disconnectListener("mood-changed", self)
        compPxy.disconnectListener("file-removed", self)
        compPxy.disconnectListener("file-added", self)
        compPxy.disconnectListener("file-changed", self)

    def _onComponentElected(self, compPxy):
        self.emit("monitoring-activated", compPxy)
        compPxy.update(self)

    def _onComponentRelieved(self, compPxy):
        self.emit("monitoring-deactivated", compPxy)

    def _onComponentStartupCanceled(self, compPxy):
        # Because the monitor was pending to start, 
        # this event was ignored
        # So resend the mood changing event
        mood = compPxy.getMood()
        if mood:
            self._onComponentMoodChanged(compPxy, mood)

    def _onStarted(self):
        for compPxy in self.iterComponents():
            self._onComponentMoodChanged(compPxy, compPxy.getMood())
    
    def _doAcceptSuggestedWorker(self, workerPxy):
        currWorkerPxy = self.getWorker()
        monPxy = self.getActiveComponent()
        return (workerPxy != currWorkerPxy) or (not monPxy)

    def _doAborted(self):
        self.emit("fail-to-run", self.getWorker())
    
    def _doSelectPotentialComponent(self, compPxys):
        targWorkerPxy = self.getWorker()
        for compPxy in compPxys:
            # If it exists an happy monitor on the target worker, 
            # or there not target worker set, just elect it
            if ((not targWorkerPxy or (compPxy.getWorker() == targWorkerPxy)) 
                and (compPxy.getMood() == moods.happy)):
                return compPxy
        return None
    
    def _doLoadComponent(self, workerPxy, compName, compLabel,
                         compProperties, loadTimeout):
        return monitor.MonitorProxy.loadTo(workerPxy, compName, compLabel, 
                                           compProperties, loadTimeout)


    ## Private Methods ##
    
    def __file2profileContext(self, virtDir, file):
        virtPath = virtDir + file
        for p in self._custCtx.iterProfileContexts(file):
            if p.getInputPath() == virtPath:
                return p
        return None

    def __asyncMovePendingFiles(self):
        if not self._pendingMoves:
            self._movingFiles = False
            return
        virtSrcBase, virtDestBase, relFiles = self._pendingMoves.pop()
        monPxy = self.getActiveComponent()
        if not monPxy:
            self.warning("No monitor found to move files '%s' to '%s'",
                         virtSrcBase, virtDestBase)
            # Stop moving files
            self._movingFiles = False
            return
        self.debug("Ask monitor '%s' to move files form '%s' to '%s'",
                   monPxy.getName(), virtSrcBase, virtDestBase)
        d = monPxy.moveFiles(virtSrcBase, virtDestBase, relFiles)
        args = (monPxy, virtSrcBase, virtDestBase, relFiles)
        d.addCallbacks(self.__cbFileMoved, self.__ebMoveFilesFailed, 
                       callbackArgs=args, errbackArgs=args)

    def __cbFileMoved(self, result, monPxy, 
                      virtSrcBase, virtDestBase, relFiles):
        for relFile in relFiles:
            self.log("File '%s' moved to '%s'",
                      virtSrcBase.append(relFile),
                      virtDestBase.append(relFile))
        # Continue moving files
        self.__asyncMovePendingFiles()
        
    def __ebMoveFilesFailed(self, failure, monPxy,
                            virtSrcBase, virtDestBase, relFiles):
        log.notifyFailure(self, failure,
                          "Monitoring task '%s' monitor "
                          "'%s' fail to move files from '%s' to '%s'",
                          self.getLabel(), monPxy.getName(), virtSrcBase, 
                          virtDestBase)
        # Continue moving files anyway
        self.__asyncMovePendingFiles()
