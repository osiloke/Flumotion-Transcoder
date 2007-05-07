# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from twisted.internet import reactor, defer

from flumotion.twisted.compat import Interface
from flumotion.transcoder import log
from flumotion.common.log import Loggable
from flumotion.transcoder.admin.datastore.basestore import BaseStore
from flumotion.transcoder.admin.datastore.customerstore import CustomerStore


class StoreLogger(Loggable):
    logCategory = 'admin-stores'


class IAdminStoreListener(Interface):
    def onCustomerAdded(self, admin, customer):
        """
        Call when a customer has been added and fully initialized.        
        """
    def onCustomerRemoved(self, admin, customer):
        """
        Call when a customer is about to be removed.
        """


class AdminStore(BaseStore):
    
    def __init__(self, dataSource):
        ## Root element, no parent
        BaseStore.__init__(self, StoreLogger(), None, dataSource, 
                           IAdminStoreListener) 
        self._defaultsData = None
        self._customers = []

        
    ## Public Methods ##
    
    def customers(self):
        return list(self._customers)
    
    
    ## Overridden Methods ##
        
    def _doSyncListener(self, listener):
        for customer in self._customers:
            if customer.isActive():
                self._fireEventTo(listener, customer, "CustomerAdded")
        
    def _doPrepareInit(self, chain):
        #Ensure that the defaults are received
        #before customers initialization
        chain.addCallback(self.__retrieveDefaults)
        #Retrieve and initialize the customers
        chain.addCallback(self.__retrieveCustomers)
        
        
    ## Private Methods ##
    
    def __retrieveDefaults(self, result):
        d = self._dataSource.retrieveDefaults()
        d.addCallbacks(self.__defaultsReceived, 
                       self.__retrievalFailed,
                       callbackArgs=(result,))
        return d
        
    def __defaultsReceived(self, defaultsData, oldResult):
        self._defaultsData = defaultsData
        return oldResult
    
    def __retrieveCustomers(self, result):
        d = self._dataSource.retrieveCustomers()
        d.addCallbacks(self.__customersReceived, 
                       self.__retrievalFailed,
                       callbackArgs=(result,))
        return d
    
    def __customersReceived(self, customersData, oldResult):
        deferreds = []
        for customerData in customersData:
            customer = CustomerStore(self, self, self._dataSource, 
                                     customerData)
            d = customer.initialize()
            d.addCallbacks(self.__customerInitialized, 
                           self.__customerInitFailed,
                           errbackArgs=(customer,))
            #Ensure no failure slips through
            d.addErrback(self._unexpectedError)
            deferreds.append(d)
        dl = defer.DeferredList(deferreds,
                                fireOnOneCallback=False,
                                fireOnOneErrback=False,
                                consumeErrors=True)
        #Preserve deferred result, drop all previous results even failures
        dl.addCallback(lambda result, old: old, oldResult)
        return dl
    
    def __customerInitialized(self, customer):
        self.debug("Customer '%s' initialized; adding it to the admin store",
                   customer.getLabel())
        self._customers.append(customer)
        #Send event when the customer has been activated
        self._fireEventWhenActive(customer, "CustomerAdded")
        #Activate the new customer store
        customer._activate()        
        #Keep the callback chain result
        return customer
    
    def __customerInitFailed(self, failure, customer):
        #FIXME: Better Error Handling ?
        self.warning("Customer '%s' failed to initialize; dropping it: %s", 
                     customer.getLabel(), log.getFailureMessage(failure))
        self.debug("Traceback of customer '%s' failure:\n%s" 
                   % (customer.getLabel(), log.getFailureTraceback(failure)))
        customer._abort(failure)
        #Don't propagate failures, will be dropped anyway
        return
    
    def __retrievalFailed(self, failure):
        #FIXME: Better Error Handling ?
        self.warning("Data retrieval failed for the admin store: %s", 
                     log.getFailureMessage(failure))
        #Propagate failures
        return failure
