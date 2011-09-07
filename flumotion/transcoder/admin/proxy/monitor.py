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

from zope.interface import implements

from flumotion.inhouse import utils, defer, log

from flumotion.transcoder import virtualpath
from flumotion.transcoder.enums import MonitorFileStateEnum
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.proxy import base, component
from flumotion.transcoder.admin.property import filemon


class IMonitorProxy(base.IBaseProxy):
    pass


class MonitorProxy(component.ComponentProxy):
    implements(IMonitorProxy)

    properties_factory = filemon.MonitorProperties

    @classmethod
    def loadTo(cls, workerPxy, name, label, properties, timeout=None):
        managerPxy = workerPxy.getManagerProxy()
        atmoPxy = managerPxy.getAtmosphereProxy()
        return atmoPxy._loadComponent(adminconsts.FILE_MONITOR,
                                      name, label, workerPxy,
                                      properties, timeout)

    def __init__(self, logger, parentPxy, identifier,
                 managerPxy, compCtx, compState, domain):
        component.ComponentProxy.__init__(self, logger, parentPxy,
                                          identifier, managerPxy,
                                          compCtx, compState, domain)
        self._alreadyAdded = {} # {file: None}
        self._stateUpdateDelta = {}
        self._stateUpdateDelay = None
        self._stateUpdateResult = None
        # Registering Events
        self._register("file-added")
        self._register("file-removed")
        self._register("file-changed")


    ## Public Methods ##

    def waitFiles(self, timeout=None):
        d = self._waitUIState(timeout)
        d.addCallback(self.__cbRetrieveFiles)
        return d

    def setFileStateBuffered(self, virtBase, relFile, state, profile_name):
        self.log("Schedule to set file %s%s state to %s", virtBase, relFile, state.nick)
        self._stateUpdateDelta[(profile_name, relFile)] = state
        self.__updateFilesState()

    def setFileState(self, virtBase, relFile, state, profile_name):
        self.log("Set file %s%s state to %s", virtBase, relFile, state.nick)
        d = utils.callWithTimeout(adminconsts.REMOTE_CALL_TIMEOUT,
                                  self._callRemote, "setFileState",
                                  virtBase, relFile, state)
        return d

    def moveFiles(self, virtSrcBase, virtDestBase, relFiles):
        d = utils.callWithTimeout(adminconsts.REMOTE_CALL_TIMEOUT,
                                  self._callRemote, "moveFiles",
                                  virtSrcBase, virtDestBase, relFiles)
        return d

    ## Overriden Methods ##

    def _doBroadcastUIState(self, uiState):
        pending = uiState.get("pending-files", None)
        if pending:
            for file, value in pending.iteritems():
                profile_name, relFile = file
                state, fileinfo, detection_time, mime_type, checksum, params = value
                self.emit("file-added", profile_name, relFile, state, fileinfo,
                          detection_time, mime_type, checksum, params)

    def _onUIStateSet(self, uiState, key, value):
        self.log("Monitor UI State '%s' set to '%s'", key, value)

    def _onUIStateAppend(self, uiState, key, value):
        self.log("Monitor UI State '%s' value '%s' appened", key, value)

    def _onUIStateRemove(self, uiState, key, value):
        self.log("Monitor UI State '%s' value '%s' removed", key, value)

    def _onUIStateSetitem(self, uiState, key, subkey, value):
        self.log("Monitor UI State '%s' item '%s' set to '%s'",
                 key, subkey, value)
        if key == "pending-files":
            virtBase, relFile = subkey
            self._onMonitorSetFile(virtBase, relFile, value)

    def _onUIStateDelitem(self, uiState, key, subkey, value):
        self.log("Monitor UI State '%s' item '%s' deleted",
                 key, subkey)
        if key == "pending-files":
            virtBase, relFile = subkey
            self._onMonitorDelFile(virtBase, relFile, value)

    def _onUnsetUIState(self, uiState):
        component.ComponentProxy._onUnsetUIState(self, uiState)
        self._alreadyAdded.clear()


    ## UI State Handlers Methods ##

    def _onMonitorSetFile(self, profile_name, relFile, filedata):
        state, fileinfo, detection_time, mime_type, checksum, params = filedata
        ident = (profile_name, relFile)

        if ident in self._alreadyAdded:
            self.emit("file-changed", profile_name, relFile, state, fileinfo,
                      mime_type, checksum, params)
        else:
            self._alreadyAdded[ident] = None
            self.emit("file-added", profile_name, relFile, state, fileinfo,
                      detection_time, mime_type, checksum, params)

    def _onMonitorDelFile(self, virtBase, relFile, filedata):
        state, _fileinfo, _detection_time, _mime_type, _checksum, _params = filedata
        ident = (virtBase, relFile)
        if ident in self._alreadyAdded:
            del self._alreadyAdded[ident]
            self.emit("file-removed", virtBase, relFile, state)


    ## Overriden Methods ##


    ## Private Methods ##

    def __updateFilesState(self):
        if self._stateUpdateDelay or not self._stateUpdateDelta:
            return
        period = adminconsts.MONITOR_STATE_UPDATE_PERIOD
        to = utils.createTimeout(period, self.__doFilesStateUpdate)
        self._stateUpdateDelay = to

    def __doFilesStateUpdate(self):
        self._stateUpdateDelay = None
        if self._stateUpdateResult != None:
            self.log("Buffered files state update still pending, wait more")
            self.__updateFilesState()
            return
        delta = [(p, r, s) for (p, r), s in self._stateUpdateDelta.iteritems()]
        self._stateUpdateDelta.clear()
        self.log("Buffered state update of %d files", len(delta))
        d = utils.callWithTimeout(adminconsts.REMOTE_CALL_TIMEOUT,
                                  self._callRemote, "setFilesState", delta)
        self._stateUpdateResult = d
        d.addCallbacks(self.__cbFilesStateUpdateSucceed,
                       self.__ebFilesStateUpdateFailed)

    def __cbFilesStateUpdateSucceed(self, result):
        self.log("Buffered files state update succeed")
        self._stateUpdateResult = None
        self.__updateFilesState()

    def __ebFilesStateUpdateFailed(self, failure):
        self._stateUpdateResult = None
        log.notifyFailure(self, failure,
                          "Failed to update file states")
        self.__updateFilesState()

    def __cbRetrieveFiles(self, ui):
        files = []
        workerPxy = self.getWorkerProxy()
        assert ui != None
        assert workerPxy != None
        workerCtx = workerPxy.getWorkerContext()
        local = workerCtx.getLocal()
        for (p, f), s in ui.get("pending-files", {}).iteritems():
            files.append((virtualpath.VirtualPath.virtualize(p, local), f, s))
        return files

class HttpMonitorProxy(MonitorProxy):
    implements(IMonitorProxy)

    properties_factory = filemon.HttpMonitorProperties

    @classmethod
    def loadTo(cls, workerPxy, name, label, properties, timeout=None):
        managerPxy = workerPxy.getManagerProxy()
        atmoPxy = managerPxy.getAtmosphereProxy()
        return atmoPxy._loadComponent(adminconsts.HTTP_MONITOR,
                                      name, label, workerPxy,
                                      properties, timeout)




component.registerProxy("file-monitor", MonitorProxy)
component.registerProxy("http-monitor", HttpMonitorProxy)
