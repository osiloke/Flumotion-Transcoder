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

from twisted.python import components

from flumotion.transcoder.admin.proxies import workerproxy
from flumotion.transcoder.admin.api import interfaces
from flumotion.transcoder.admin.api.mediums import basemedium 


class WorkerMedium(basemedium.BaseMedium):
    
    implements(interfaces.IWorkerMedium)
    
    
    ## IWorkerMedium Methodes ##
    
    def getHost(self):
        return self.ref.getHost()
    
    
    ## Make the Methodes remote ##
    
    remote_getHost = getHost
    

## Registering Adapters ##

components.registerAdapter(WorkerMedium, workerproxy.IWorker, interfaces.IWorkerMedium)