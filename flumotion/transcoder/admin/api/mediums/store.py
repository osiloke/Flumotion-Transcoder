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

from flumotion.transcoder.admin.datastore import store
from flumotion.transcoder.admin.api import interfaces, api


class StoreMedium(api.Medium):
    implements(interfaces.IStoreMedium)
    api.registerMedium(interfaces.IStoreMedium,
                       store.IAdminStore)
    
    def __init__(self, store):
        self._reference = store
    
    
    ## IWorkersMedium Methodes ##

    @api.remote()
    def getCustomers(self):
        return self._reference.getCustomerStores()

    @api.remote()
    def getCustomer(self, identifier):
        return self._reference.getCustomerStore(identifier)

