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

from flumotion.inhouse import defer

from flumotion.transcoder.admin.proxies.fluproxy import RootFlumotionProxy
from flumotion.transcoder.admin.proxies.workerproxy import WorkerProxy
from flumotion.transcoder.admin.proxies.managerset import ManagerSet, ManagerSetListener
from flumotion.transcoder.admin.proxies.managerproxy import ManagerListener

class IWorkerSetListener(Interface):
    def onWorkerAddedToSet(self, workerset, worker):
        pass
    
    def onWorkerRemovedFromSet(self, workerset, worker):
        pass


class WorkerSetListener(object):
    
    implements(IWorkerSetListener)
    
    def onWorkerAddedToSet(self, workerset, worker):
        pass
    
    def onWorkerRemovedFromSet(self, workerset, worker):
        pass


class WorkerSet(RootFlumotionProxy,
                ManagerSetListener, ManagerListener):
    
    def __init__(self, mgrset):
        assert isinstance(mgrset, ManagerSet)
        RootFlumotionProxy.__init__(self, mgrset, IWorkerSetListener)
        self._managers = mgrset
        self._workers = {} # {identifier: Worker}
        self._managers.addListener(self)
        
        
    ## Public Methods ##

    def iterWorkers(self):
        return self._workers.itervalues()
    
    def getWorkers(self):
        return self._workers.values()
    
    def getWorker(self, name):
        for worker in self._workers.itervalues():
            if worker.getName() == name:
                return worker
        return None
    
    def __iter__(self):
        return self._workers.__iter__()
    
    def __getitem__(self, identifier):
        return self._workers.get(identifier, None)
    
    def __contains__(self, value):
        identifier = value
        if isinstance(value, WorkerProxy):
            identifier = value.getIdentifier()
        return identifier in self._workers
    
    
    ## Overriden Methods ##
    
    def _doSyncListener(self, listener):
        self._syncProxies("_workers", listener, "WorkerAddedToSet")


    ### managerset.IManagerSetListener Implementation ###

    def onManagerAddedToSet(self, mgrset, manager):
        manager.addListener(self)
        manager.syncListener(self)
        
    def onManagerRemovedFromSet(self, mgrset, manager):
        manager.removeListener(self)


    ### managerproxy.IManagerListener Implementation ###
    
    def onWorkerAdded(self, manager, worker):
        identifier = worker.getIdentifier()
        assert not (identifier in self._workers)
        self._workers[identifier] = worker
        self._fireEvent(worker, "WorkerAddedToSet")
    
    def onWorkerRemoved(self, manager, worker):
        identifier = worker.getIdentifier()
        assert identifier in self._workers
        assert self._workers[identifier] == worker
        del self._workers[identifier]
        self._fireEvent(worker, "WorkerRemovedFromSet")

    def onAtmosphereSet(self, manager, atmosphere):
        pass
    
    def onAtmosphereUnset(self, manager, atmosphere):
        pass
    
    def onFlowAdded(self, manager, flow):
        pass
    
    def onFlowRemoved(self, manager, flow):
        pass

    
    ## Private Methods ##

