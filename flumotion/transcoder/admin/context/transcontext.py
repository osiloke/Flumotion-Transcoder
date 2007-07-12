# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.transcoder.utils import LazyEncapsulationIterator
from flumotion.transcoder.admin.context.customercontext import CustomerContext
from flumotion.transcoder.admin.context.profilecontext import ProfileContext
from flumotion.transcoder.admin.context.profilecontext import UnboundProfileContext


    
class TranscodingContext(object):
    
    def __init__(self, adminContext, adminStore):
        self.admin = adminContext
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
    
    # Shortcuts
    def getUnboundProfileContext(self, profile):
        custCtx = self.getCustomerContext(profile.getParent())
        return UnboundProfileContext(profile, custCtx)
    
    def getProfileContext(self, profile, relPath):
        custCtx = self.getCustomerContext(profile.getParent())
        return ProfileContext(profile, custCtx, relPath)
