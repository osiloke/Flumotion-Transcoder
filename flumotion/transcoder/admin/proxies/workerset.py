# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from twisted.internet import defer
from flumotion.twisted.compat import Interface, implements

from flumotion.transcoder.admin.proxies import fluproxy
from flumotion.transcoder.admin.proxies import managerset
from flumotion.transcoder.admin.proxies import managerproxy


class IWorkerSetListener(Interface):
    def onWorkerAddedToSet(self, workerset, worker):
        pass
    
    def onWorkerRemovedFromSet(self, workerset, worker):
        pass


class WorkerSet(fluproxy.RootFlumotionProxy):
    
    implements(managerset.IManagerSetListener,
               managerproxy.IManagerListener)
    
    def __init__(self, mgrset):
        assert isinstance(mgrset, managerset.ManagerSet)
        fluproxy.RootFlumotionProxy.__init__(self, mgrset, IWorkerSetListener)
        self._managers = mgrset
        self._workers = {} # identifier => Worker
        self._managers.addListener(self)
        
        
    ## Public Methods ##
    
    
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

