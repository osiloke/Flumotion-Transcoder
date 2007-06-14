# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.transcoder.local import Local
from flumotion.transcoder.admin.context.managercontext import ManagerContext
from flumotion.transcoder.admin.datasource import filesource
from flumotion.transcoder.admin.context.workercontext import WorkerContext


class AdminContext(object):
    
    def __init__(self, clusterConfig):
        self.config = clusterConfig
        self._vars = None

    def getDataSource(self):
        file = self.config.admin.datasource.file
        return filesource.FileDataSource(file)
        
    def getLocal(self):
        return Local("admin", self.config.admin.roots)
        
    def getManagerContext(self):
        return ManagerContext(self, self.config.manager)
    
    def getWorkerContext(self, workername):
        return WorkerContext(self, workername, 
                             self.config.workers.get(workername, None),
                             self.config.workerDefaults)
    
