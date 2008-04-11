# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import implements

from flumotion.transcoder.admin.proxies import workerset
from flumotion.transcoder.admin.api import interfaces, api


class WorkerSetMedium(api.Medium):
    implements(interfaces.IWorkerSetMedium)
    api.registerMedium(interfaces.IWorkerSetMedium,
                          workerset.IWorkerSet)
    
    def __init__(self, workers):
        self._workers = workers
    
    
    ## IWorkerSetMedium Methodes ##

    @api.remote()
    def getWorkers(self):
        return self._workers.getWorkers()

    @api.remote()
    def getWorker(self, identifier):
        return self._workers.getWorker(identifier)
