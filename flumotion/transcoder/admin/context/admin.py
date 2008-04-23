# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.transcoder import local
from flumotion.transcoder.admin.datasource import filesource
from flumotion.transcoder.admin.context import base, worker, notifier, store, api, manager


class AdminContext(base.BaseContext):
    
    def __init__(self, clusterConfig):
        base.BaseContext.__init__(self, None)
        self.config = clusterConfig

    def getDataSource(self):
        datasourceConfig = self.config.admin.datasource
        return filesource.FileDataSource(datasourceConfig)
    
    def getNotifierContext(self):
        notifierConfig = self.config.admin.notifier
        return notifier.NotifierContext(self, notifierConfig)
    
    def getSchedulerContext(self):
        return None
        
    def getLocal(self):
        return local.Local("admin", self.config.admin.roots)
        
    def getManagerContext(self):
        managerConfig = self.config.manager
        return manager.ManagerContext(self, managerConfig)
    
    def getWorkerContextByName(self, workername):
        workerConfig = self.config.workers.get(workername, None)
        workerDefaults = self.config.workerDefaults
        return worker.WorkerContext(self, workername, workerConfig, workerDefaults)
    
    def getAPIContext(self):
        apiConfig = self.config.admin.api
        return api.APIContext(self, apiConfig)
    
    def getStoreContextFor(self, admiStore):
        return store.StoreContext(self, admiStore)
