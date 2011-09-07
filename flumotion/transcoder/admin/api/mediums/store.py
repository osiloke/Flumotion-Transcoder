# -*- Mode: Python -*-
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

from zope.interface import implements

from flumotion.transcoder.admin.context import store
from flumotion.transcoder.admin.api import interfaces, api


class StoreMedium(api.Medium):

    implements(interfaces.IStoreMedium)

    api.register_medium(interfaces.IStoreMedium,
                        store.IStoreContext)

    def __init__(self, storeCtx):
        api.Medium.__init__(self, storeCtx)


    ## IWorkersMedium Methodes ##

    @api.make_remote()
    def getDefaults(self):
        pass

    @api.make_remote()
    def getCustomers(self):
        return self.reference.store.getCustomerStores()

    @api.make_remote()
    def getCustomer(self, identifier):
        return self.reference.store.getCustomerStore(identifier)

