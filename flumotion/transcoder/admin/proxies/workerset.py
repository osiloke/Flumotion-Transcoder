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
from flumotion.transcoder.admin.proxies.fluproxy import RootFlumotionProxy
from flumotion.transcoder.admin.proxies.workerproxy import WorkerProxy
from flumotion.transcoder.admin.proxies.managerset import ManagerSet


class IWorkerSet(interfaces.IAdminInterface):

    def getWorkers(self):
        pass

    def iterWorkers(self):
        pass
        
    def getWorker(self, identifier):
        pass
    
    def getWorkerByName(self, name):
        pass


class WorkerSet(RootFlumotionProxy):
    implements(IWorkerSet)
    
    def __init__(self, mgrset):
        assert isinstance(mgrset, ManagerSet)
        RootFlumotionProxy.__init__(self, mgrset)
        self._managers = mgrset
        self._workers = {} # {identifier: Worker}
        self._managers.connectListener("manager-added", self, self.onManagerAddedToSet)
        self._managers.connectListener("manager-removed", self, self.onManagerRemovedFromSet)
        # Registering Events
        self._register("worker-added")
        self._register("worker-removed")
        
        
    ## Public Methods ##

    def getWorkers(self):
        return self._workers.values()

    def iterWorkers(self):
        return self._workers.itervalues()
        
    def getWorker(self, identifier):
        return self._workers[identifier]
    
    def getWorkerByName(self, name):
        for worker in self._workers.itervalues():
            if worker.getName() == name:
                return worker
        return None
    
#    def __iter__(self):
#        return self._workers.__iter__()
#    
#    def __getitem__(self, identifier):
#        return self._workers.get(identifier, None)
#    
#    def __contains__(self, value):
#        identifier = value
#        if isinstance(value, WorkerProxy):
#            identifier = value.getIdentifier()
#        return identifier in self._workers
    
    
    ## Overriden Methods ##
    
    def update(self, listener):
        self._updateProxies("_workers", listener, "worker-added")


    ### managerset.IManagerSetListener Implementation ###

    def onManagerAddedToSet(self, mgrset, manager):
        manager.connectListener("worker-added", self, self.onWorkerAdded)
        manager.connectListener("worker-removed", self, self.onWorkerRemoved)
        manager.update(self)
        
    def onManagerRemovedFromSet(self, mgrset, manager):
        manager.disconnectListener("worker-added", self)
        manager.disconnectListener("worker-removed", self)


    ### managerproxy.IManagerListener Implementation ###
    
    def onWorkerAdded(self, manager, worker):
        identifier = worker.getIdentifier()
        assert not (identifier in self._workers)
        self._workers[identifier] = worker
        self.emit("worker-added", worker)
    
    def onWorkerRemoved(self, manager, worker):
        identifier = worker.getIdentifier()
        assert identifier in self._workers
        assert self._workers[identifier] == worker
        del self._workers[identifier]
        self.emit("worker-removed", worker)

    
    ## Private Methods ##

