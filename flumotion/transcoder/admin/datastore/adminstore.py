# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import datetime

from zope.interface import Interface, implements
from twisted.internet import reactor, defer

from flumotion.transcoder import constants, log
from flumotion.transcoder.enums import ActivityTypeEnum
from flumotion.transcoder.enums import ActivityStateEnum
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.errors import StoreError
from flumotion.transcoder.admin.datastore.basestore import BaseStore
from flumotion.transcoder.admin.datastore.customerstore import CustomerStore
from flumotion.transcoder.admin.datastore.activitystore import ActivityStore
from flumotion.transcoder.admin.datastore.notificationstore import NotificationFactory


class StoreLogger(log.Loggable):
    logCategory = adminconsts.STORES_LOG_CATEGORY


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
                              "transcodingPriority": 
                                  adminconsts.DEFAULT_TRANSCODING_PRIORITY,
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
        self._activities = ActivityStore(self, dataSource)

        
    ## Public Methods ##
    
    def getLabel(self):
        return "Admin Store"
    
    def getCustomers(self):
        return self._customers.values()
    
    def __getitem__(self, customerName):
        return self._customers[customerName]
    
    def getCustomer(self, customerName, default=None):
        return self._customers.get(customerName, default)
    
    def __iter__(self):
        return iter(self._customers)
    
    def iterCustomers(self):
        self._customers.itervalues()
    
    def getActivityStore(self):
        return self._activities
    
    
    ## Overridden Methods ##
        
    def _doGetChildElements(self):
        return self.getCustomers()
        
    def _doSyncListener(self, listener):
        BaseStore._doSyncListener(self, listener)
        for customer in self._customers.itervalues():
            if customer.isActive():
                self._fireEventTo(listener, customer, "CustomerAdded")
        
    def _doPrepareInit(self, chain):
        BaseStore._doPrepareInit(self, chain)
        #Ensure that the defaults are received
        #before customers initialization
        chain.addCallback(self.__cbRetrieveDefaults)
        #Retrieve and initialize the customers
        chain.addCallback(self.__cbRetrieveCustomers)

    def _doRetrieveNotifications(self):
        return self._dataSource.retrieveGlobalNotifications()
        
    def _doWrapNotification(self, notificationData):
        return NotificationFactory(notificationData, self,
                                   None, None, None)
        
        
    ## Private Methods ##
    
    def __cbRetrieveDefaults(self, result):
        d = self._dataSource.retrieveDefaults()
        d.addCallbacks(self.__cbDefaultsReceived, 
                       self._retrievalFailed,
                       callbackArgs=(result,))
        return d
        
    def __cbDefaultsReceived(self, defaultsData, oldResult):
        self._data = defaultsData
        return oldResult
    
    def __cbRetrieveCustomers(self, result):
        d = self._dataSource.retrieveCustomers()
        d.addCallbacks(self.__cbCustomersReceived, 
                       self._retrievalFailed,
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
