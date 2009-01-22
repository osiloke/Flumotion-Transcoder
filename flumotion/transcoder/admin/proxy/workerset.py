# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import implements

from flumotion.inhouse import defer

from flumotion.transcoder.admin import interfaces
from flumotion.transcoder.admin.proxy import base, worker, managerset


class IWorkerSet(interfaces.IAdminInterface):

    def getWorkerProxies(self):
        pass

    def iterWorkerProxies(self):
        pass

    def getWorkerProxy(self, identifier):
        pass

    def getWorkerProxyByName(self, name):
        pass


class WorkerSet(base.RootProxy):
    implements(IWorkerSet)

    def __init__(self, managerPxySet):
        assert isinstance(managerPxySet, managerset.ManagerSet)
        base.RootProxy.__init__(self, managerPxySet)
        self._managerPxySet = managerPxySet
        self._workerPxys = {} # {identifier: Worker}
        self._managerPxySet.connectListener("manager-added", self,
                                            self.__onManagerAddedToSet)
        self._managerPxySet.connectListener("manager-removed", self,
                                            self.__onManagerRemovedFromSet)
        # Registering Events
        self._register("worker-added")
        self._register("worker-removed")


    ## Public Methods ##

    def getWorkerProxies(self):
        return self._workerPxys.values()

    def iterWorkerProxies(self):
        return self._workerPxys.itervalues()

    def getWorkerProxy(self, identifier):
        return self._workerPxys[identifier]

    def getWorkerProxyByName(self, name):
        for workerPxy in self._workerPxys.itervalues():
            if workerPxy.getName() == name:
                return workerPxy
        return None


    ## Overriden Methods ##

    def refreshListener(self, listener):
        self._refreshProxiesListener("_workerPxys", listener, "worker-added")


    ### managerset.IManagerSetListener Implementation ###

    def __onManagerAddedToSet(self, mgrPxySet, managerPxy):
        managerPxy.connectListener("worker-added", self,
                                   self.__onWorkerAdded)
        managerPxy.connectListener("worker-removed", self,
                                   self.__onWorkerRemoved)
        managerPxy.refreshListener(self)

    def __onManagerRemovedFromSet(self, mgrPxySet, managerPxy):
        managerPxy.disconnectListener("worker-added", self)
        managerPxy.disconnectListener("worker-removed", self)


    ### managerproxy.IManagerListener Implementation ###

    def __onWorkerAdded(self, managerPxy, workerPxy):
        identifier = workerPxy.identifier
        assert not (identifier in self._workerPxys)
        self._workerPxys[identifier] = workerPxy
        self.emit("worker-added", workerPxy)

    def __onWorkerRemoved(self, managerPxy, workerPxy):
        identifier = workerPxy.identifier
        assert identifier in self._workerPxys
        assert self._workerPxys[identifier] == workerPxy
        del self._workerPxys[identifier]
        self.emit("worker-removed", workerPxy)


    ## Private Methods ##

