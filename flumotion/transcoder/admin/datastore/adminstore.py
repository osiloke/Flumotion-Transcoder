# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import Interface, implements
from twisted.internet import reactor, defer

from flumotion.transcoder import log
from flumotion.common.log import Loggable
from flumotion.transcoder import constants
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.errors import StoreError
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


class AdminStoreListener(object):
    
    implements(IAdminStoreListener)
    
    def onCustomerAdded(self, admin, customer):
        """
        Call when a customer has been added and fully initialized.        
        """
    def onCustomerRemoved(self, admin, customer):
        """
        Call when a customer is about to be removed.
        """


class AdminStore(BaseStore):
    
    # MetaStore metaclass will create getters/setters for these properties
    __default_properties__ = {"outputMediaTemplate": 
                                  adminconsts.DEFAULT_OUTPUT_MEDIA_TEMPLATE,
                              "outputThumbTemplate": 
                                  adminconsts.DEFAULT_OUTPUT_THUMB_TEMPLATE,
                              "linkFileTemplate": 
                                  adminconsts.DEFAULT_LINK_FILE_TEMPLATE,
                              "configFileTemplate": 
                                  adminconsts.DEFAULT_CONFIG_FILE_TEMPLATE,
                              "reportFileTemplate": 
                                  adminconsts.DEFAULT_REPORT_FILE_TEMPLATE,
                              "linkTemplate":
                                  constants.LINK_TEMPLATE,
                              "monitoringPeriod": 
                                  adminconsts.DEFAULT_MONITORING_PERIOD,
                              "transcodingTimeout": 
                                  adminconsts.DEFAULT_TRANSCODING_TIMEOUT,
                              "postprocessTimeout": 
                                  adminconsts.DEFAULT_POSTPROCESS_TIMEOUT,
                              "preprocessTimeout": 
                                  adminconsts.DEFAULT_PREPROCESS_TIMEOUT,
                              "mailSubjectTemplate": 
                                  adminconsts.DEFAULT_MAIL_SUBJECT_TEMPLATE,
                              "mailBodyTemplate": 
                                  adminconsts.DEFAULT_MAIL_BODY_TEMPLATE,
                              "GETRequestTimeout": 
                                  adminconsts.DEFAULT_GETREQUEST_TIMEOUT,
                              "GETRequestRetryCount": 
                                  adminconsts.DEFAULT_GETREQUEST_RETRY_COUNT,
                              "GETRequestRetrySleep": 
                                  adminconsts.DEFAULT_GETREQUEST_RETRY_SLEEP}
    
    
    def __init__(self, dataSource):
        ## Root element, no parent
        BaseStore.__init__(self, StoreLogger(), None, dataSource, None,
                           IAdminStoreListener) 
        self._customers = {}

        
    ## Public Methods ##
    
    def getLabel(self):
        return "Admin Store"
    
    def getCustomers(self):
        return self._customers.values()
    
    def __getitem__(self, customerName):
        return self._customers[customerName]
    
    def __iter__(self):
        return iter(self._customers)
    
    def iterCustomers(self):
        self._customers.itervalues()
    
    
    ## Overridden Methods ##
        
    def _doGetChildElements(self):
        return self.getCustomers()
        
    def _doSyncListener(self, listener):
        for customer in self._customers.itervalues():
            if customer.isActive():
                self._fireEventTo(listener, customer, "CustomerAdded")
        
    def _doPrepareInit(self, chain):
        #Ensure that the defaults are received
        #before customers initialization
        chain.addCallback(self.__cbRetrieveDefaults)
        #Retrieve and initialize the customers
        chain.addCallback(self.__cbRetrieveCustomers)
        
        
    ## Private Methods ##
    
    def __cbRetrieveDefaults(self, result):
        d = self._dataSource.retrieveDefaults()
        d.addCallbacks(self.__cbDefaultsReceived, 
                       self.__ebRetrievalFailed,
                       callbackArgs=(result,))
        return d
        
    def __cbDefaultsReceived(self, defaultsData, oldResult):
        self._data = defaultsData
        return oldResult
    
    def __cbRetrieveCustomers(self, result):
        d = self._dataSource.retrieveCustomers()
        d.addCallbacks(self.__cbCustomersReceived, 
                       self.__ebRetrievalFailed,
                       callbackArgs=(result,))
        return d
    
    def __cbCustomersReceived(self, customersData, oldResult):
        deferreds = []
        self._setIdleTarget(len(customersData))
        for customerData in customersData:
            customer = CustomerStore(self, self, self._dataSource, 
                                     customerData)
            d = customer.initialize()
            d.addCallbacks(self.__cbCustomerInitialized, 
                           self.__ebCustomerInitFailed,
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
    
    def __cbCustomerInitialized(self, customer):
        self.debug("Customer '%s' initialized; adding it to the admin store",
                   customer.getLabel())
        if (customer.getName() in self._customers):
            msg = ("Admin store already have a customer '%s', "
                  "dropping the new one" % customer.getName())
            self.warning("%s", msg)
            error = StoreError(msg)
            customer._abort(error)
            return defer._nothing
        self._customers[customer.getName()] = customer
        #Send event when the customer has been activated
        self._fireEventWhenActive(customer, "CustomerAdded")
        #Activate the new customer store
        customer._activate()
        #Keep the callback chain result
        return customer
    
    def __ebCustomerInitFailed(self, failure, customer):
        #FIXME: Better Error Handling ?
        self.warning("Customer '%s' failed to initialize; dropping it: %s", 
                     customer.getLabel(), log.getFailureMessage(failure))
        self.debug("Traceback of customer '%s' failure:\n%s",
                   customer.getLabel(), log.getFailureTraceback(failure))
        customer._abort(failure)
        #Don't propagate failures, will be dropped anyway
        return
    
    def __ebRetrievalFailed(self, failure):
        #FIXME: Better Error Handling ?
        self.warning("Data retrieval failed for the admin store: %s", 
                     log.getFailureMessage(failure))
        #Propagate failures
        return failure
