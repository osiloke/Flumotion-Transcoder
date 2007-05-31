# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.transcoder.admin.utils import LazyEncapsulationIterator
from flumotion.transcoder.admin.context.customercontext import CustomerContext

    
class TranscodingContext(object):
    
    def __init__(self, adminStore):
        self.store = adminStore
        self._vars = None

    def getCustomerContext(self, customer):
        assert customer.getParent() == self.store
        return CustomerContext(customer, self)
    
    def getCustomerContextByName(self, customerName):
        return CustomerContext(self.store[customerName], self)
    
    def iterCustomerContexts(self):
        return LazyEncapsulationIterator(CustomerContext, 
                                         self.store.iterCustomers(), self)
    
