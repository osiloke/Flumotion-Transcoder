# vi:si:et:sw=4:sts=4:ts=4

# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007,2008,2009 Fluendo, S.L.
# Copyright (C) 2010,2011 Flumotion Services, S.A.
# All rights reserved.
#
# This file may be distributed and/or modified under the terms of
# the GNU Lesser General Public License version 2.1 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.LGPL" in the source distribution for more information.
#
# Headers in this file shall remain intact.


from twisted.spread.pb import PBConnectionLost, DeadReferenceError

from flumotion.common.planet import moods

from flumotion.inhouse import log

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
        try:
            monitor_type = custCtx.monitorType
        except:
            monitor_type = None

        if monitor_type == adminconsts.HTTP_MONITOR:
            props = filemon.HttpMonitorProperties.createFromContext(custCtx)
        else:
            props = filemon.MonitorProperties.createFromContext(custCtx)

        admintask.AdminTask.__init__(self, logger, custCtx.monitorLabel, props)
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

    def setFileState(self, virtBase, relPath, state, profile_name):
        monPxy = self.getActiveComponent()
        if not monPxy:
            self.warning("Monitoring task '%s' file '%s' state changed to %s "
                         "without active monitor", self.label,
                         virtBase.append(relPath), state.name)
            return
        self.log("Monitoring task '%s' file '%s' state changed to %s",
                 self.label, virtBase.append(relPath), state.name)
        monPxy.setFileStateBuffered(virtBase, relPath, state, profile_name)

    def moveFiles(self, virtSrcBase, virtDestBase, relFiles):
        args = virtSrcBase, virtDestBase, relFiles
        self._pendingMoves.append(args)
        if not self._movingFiles:
            self.__async_move_pending_files()


    ## Component Event Listeners ##

    def __on_component_mood_changed(self, monPxy, mood):
        if not self.isStarted(): return
        self.log("Monitoring task '%s' monitor '%s' goes %s",
                 self.label, monPxy.getName(), mood.name)
        if self._isPendingComponent(monPxy):
            # Currently beeing started up
            return
        if self._isElectedComponent(monPxy):
            if mood == moods.happy:
                if self._isHoldingLostComponent():
                    self._restoreLostComponent(monPxy)
                return
            self.warning("Monitoring task '%s' selected monitor '%s' "
                         "gone %s", self.label,
                         monPxy.getName(), mood.name)
            if mood == moods.lost:
                # If the monitor goes lost, wait a fixed amount of time
                # to cope with small transient failures.
                self._holdLostComponent(monPxy)
                return
            self._abort()
        if mood == moods.waking:
            # Keep the waking components
            return
        if mood == moods.sleeping:
            self._deleteComponent(monPxy)
            return
        if (not self._hasElectedComponent()) and (mood == moods.happy):
            # If no monitor is selected, don't stop any happy monitor
            return
        self._stopComponent(monPxy)


    ## Monitor Event Listeners ##

    def __on_monitor_file_removed(self, monPxy, profile_name, file, state):
        if not self._isElectedComponent(monPxy): return
        if (state == MonitorFileStateEnum.downloading): return
        profile_context = self.__file_to_profile_context(profile_name, file)
        if not profile_context:
            self.warning("File '%s' removed but no corresponding profile "
                         "found for customer '%s'", profile_name + file,
                         self._custCtx.name)
            return
        self.emit("file-removed", profile_context, state)

    def __on_monitor_file_added(self, monPxy, profile_name, file, state, fileinfo,
                             detection_time, mime_type, checksum, params=None):
        if not self._isElectedComponent(monPxy): return
        profile_context = self.__file_to_profile_context(profile_name, file)
        if not profile_context:
            self.warning("File '%s' added but no corresponding profile "
                         "%s found for customer '%s'", file, profile_name,
                         self._custCtx.name)
            return
        self.emit("file-added", profile_context, state, fileinfo, detection_time,
                  mime_type, checksum, params)

    def __on_monitor_file_changed(self, monPxy, profile_name, file, state, fileinfo,
                               mime_type, checksum, params=None):
        if not self._isElectedComponent(monPxy): return
        profile_context = self.__file_to_profile_context(profile_name, file)
        if not profile_context:
            self.warning("File '%s' state changed but no corresponding "
                         "profile %s found for customer '%s'", file, profile_name,
                         self._custCtx.name)
            return
        self.emit("file-state-changed", profile_context, state, fileinfo,
                  mime_type, checksum, params)


    ## Virtual Methods Implementation ##

    def _onComponentAdded(self, proxy):
        proxy.connectListener("mood-changed", self,
                                self.__on_component_mood_changed)
        proxy.connectListener("file-removed", self,
                                self.__on_monitor_file_removed)
        proxy.connectListener("file-added", self,
                                self.__on_monitor_file_added)
        proxy.connectListener("file-changed", self,
                                self.__on_monitor_file_changed)
        proxy.refreshListener(self)

    def _onComponentRemoved(self, proxy):
        proxy.disconnectListener("mood-changed", self)
        proxy.disconnectListener("file-removed", self)
        proxy.disconnectListener("file-added", self)
        proxy.disconnectListener("file-changed", self)

    def _onComponentElected(self, proxy):
        self._resetRetryCounter() # The monitor is working
        self.emit("monitoring-activated", proxy)
        proxy.refreshListener(self)

    def _onComponentRelieved(self, proxy):
        self.emit("monitoring-deactivated", proxy)

    def _onComponentStartupCanceled(self, proxy):
        # Because the monitor was pending to start,
        # this event was ignored
        # So resend the mood changing event
        mood = proxy.getMood()
        if mood:
            self.__on_component_mood_changed(proxy, mood)

    def _onStarted(self):
        for proxy in self.iterComponentProxies():
            self.__on_component_mood_changed(proxy, proxy.getMood())

    def _doAcceptSuggestedWorker(self, worker_proxy):
        current_worker_proxy = self.getWorkerProxy()
        monitor_proxy = self.getActiveComponent()
        return worker_proxy != current_worker_proxy or not monitor_proxy

    def _doAborted(self):
        self.emit("fail-to-run", self.getWorkerProxy())

    def _doSelectPotentialComponent(self, compPxys):
        target_worker_proxy = self.getWorkerProxy()
        for proxy in compPxys:
            # If it exists an happy monitor on the target worker,
            # or there not target worker set, just elect it
            if ((not target_worker_proxy or (proxy.getWorkerProxy() == target_worker_proxy))
                and (proxy.getMood() == moods.happy)):
                return proxy
        return None

    def _doLoadComponent(self, worker_proxy, component_name, component_label,
                         component_properties, load_timeout):
        # decide, in function of the type of monitor, what type of monitor should be loaded.
        try:
            monitor_type = self._custCtx.monitorType
        except:
            monitor_type = adminconsts.HTTP_MONITOR

        monitor_proxy_class = MONITOR_TYPES.get(monitor_type, MONITOR_TYPES.get(adminconsts.HTTP_MONITOR))
        return monitor_proxy_class.loadTo(worker_proxy, component_name,
            component_label, component_properties, load_timeout)


    ## Private Methods ##

    def __file_to_profile_context(self, profile_name, file):
        for profile_context in self._custCtx.iterProfileContexts(file):
            if profile_name == profile_context.name:
                return profile_context
        return None

    def __async_move_pending_files(self):
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
        d.addCallbacks(
            self.__file_moved,
            self.__move_files_failed,
            callbackArgs=args,
            errbackArgs=args
        )

    def __file_moved(self, result, monPxy, virtSrcBase, virtDestBase, relFiles):
        for relFile in relFiles:
            self.log("File '%s' moved to '%s'",
                      virtSrcBase.append(relFile),
                      virtDestBase.append(relFile))
        # Continue moving files
        self.__async_move_pending_files()

    def __move_files_failed(self, failure, monitor_proxy,
                            src_base, dest_base, relFiles):
        try:
            failure.trap(PBConnectionLost, DeadReferenceError)
        except:
            log.notifyFailure(self, failure,
                              "Monitoring task '%s' monitor "
                              "'%s' fail to move files from '%s' to '%s'",
                              self.label, monitor_proxy.getName(), src_base,
                              dest_base)
        # Continue moving files anyway
        self.__async_move_pending_files()


MONITOR_TYPES = {
        adminconsts.HTTP_MONITOR: monitor.HttpMonitorProxy,
        adminconsts.FILE_MONITOR: monitor.MonitorProxy,
}
