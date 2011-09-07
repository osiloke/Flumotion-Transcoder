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

from flumotion.transcoder import local
from flumotion.transcoder.admin.diagnostic import Prognostician
from flumotion.transcoder.admin.datasource import filesource
from flumotion.transcoder.admin.datasource import sqlsource
from flumotion.transcoder.admin.context import base, worker, notifier, store, api, manager


class AdminContext(base.BaseContext):

    def __init__(self, clusterConfig):
        base.BaseContext.__init__(self, None)
        self.config = clusterConfig

    def getDataSource(self):
        datasourceConfig = self.config.admin.datasource
        return filesource.FileDataSource(datasourceConfig)

    def getReportsDataSource(self):
        sqlSourceConfig = self.config.admin.reportsdatasource
        return sqlsource.SQLDataSource(sqlSourceConfig)

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

    def getPrognostician(self):
        config = self.config.admin.prognosis.prognosisFile
        return Prognostician(config)
