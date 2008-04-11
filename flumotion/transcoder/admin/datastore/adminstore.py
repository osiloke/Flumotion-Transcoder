# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import implements

from flumotion.inhouse import log, defer

from flumotion.transcoder import constants
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.enums import ActivityTypeEnum
from flumotion.transcoder.admin.enums import ActivityStateEnum
from flumotion.transcoder.admin.errors import StoreError
from flumotion.transcoder.admin.datastore.basestore import IBaseStore, BaseStore
from flumotion.transcoder.admin.datastore.customerstore import CustomerStore
from flumotion.transcoder.admin.datastore.activitystore import ActivityStore
from flumotion.transcoder.admin.datastore.notifystore import NotificationFactory


class IAdminStore(IBaseStore):
    pass
    

class StoreLogger(log.Loggable):
    logCategory = adminconsts.STORES_LOG_CATEGORY


class AdminStore(BaseStore):
    implements(IAdminStore)
    
    # MetaStore metaclass will create getters for these properties
    __getters__ = {"basic": 
                       {"getOutputMediaTemplate": ("outputMediaTemplate",
                           adminconsts.DEFAULT_OUTPUT_MEDIA_TEMPLATE),
                        "getOutputThumbTemplate": ("outputThumbTemplate",
                           adminconsts.DEFAULT_OUTPUT_THUMB_TEMPLATE),
                        "getLinkFileTemplate": ("linkFileTemplate",
                           adminconsts.DEFAULT_LINK_FILE_TEMPLATE),
                        "getConfigFileTemplate": ("configFileTemplate",
                           adminconsts.DEFAULT_CONFIG_FILE_TEMPLATE),
                        "getReportFileTemplate": ("reportFileTemplate",
                           adminconsts.DEFAULT_REPORT_FILE_TEMPLATE),
                        "getLinkTemplate": ("linkTemplate",
                           constants.LINK_TEMPLATE),
                        "getMonitoringPeriod": ("monitoringPeriod",
                           adminconsts.DEFAULT_MONITORING_PERIOD),
                        "getAccessForceUser": ("accessForceUser",
                           adminconsts.DEFAULT_ACCESS_FORCE_USER),
                        "getAccessForceGroup": ("accessForceGroup",
                           adminconsts.DEFAULT_ACCESS_FORCE_GROUP),
                        "getAccessForceDirMode": ("accessForceDirMode",
                           adminconsts.DEFAULT_ACCESS_FORCE_DIR_MODE),
                        "getAccessForceFileMode": ("accessForceFileMode",
                           adminconsts.DEFAULT_ACCESS_FORCE_FILE_MODE),
                        "getTranscodingPriority": ("transcodingPriority",
                           adminconsts.DEFAULT_TRANSCODING_PRIORITY),
                        "getTranscodingTimeout": ("transcodingTimeout",
                           adminconsts.DEFAULT_TRANSCODING_TIMEOUT),
                        "getPostprocessTimeout": ("postprocessTimeout",
                           adminconsts.DEFAULT_POSTPROCESS_TIMEOUT),
                        "getPreprocessTimeout": ("preprocessTimeout",
                           adminconsts.DEFAULT_PREPROCESS_TIMEOUT),
                        "getMailSubjectTemplate": ("mailSubjectTemplate",
                           adminconsts.DEFAULT_MAIL_SUBJECT_TEMPLATE),
                        "getMailBodyTemplate": ("mailBodyTemplate",
                           adminconsts.DEFAULT_MAIL_BODY_TEMPLATE),
                        "getMailTimeout": ("mailTimeout",
                           adminconsts.DEFAULT_MAIL_TIMEOUT),
                        "getMailRetryMax": ("mailRetryMax",
                           adminconsts.DEFAULT_MAIL_RETRY_MAX),
                        "getMailRetrySleep": ("mailRetrySleep",
                           adminconsts.DEFAULT_MAIL_RETRY_SLEEP),
                        "getHTTPRequestTimeout": ("HTTPRequestTimeout",
                           adminconsts.DEFAULT_HTTPREQUEST_TIMEOUT),
                        "getHTTPRequestRetryMax": ("HTTPRequestRetryMax",
                           adminconsts.DEFAULT_HTTPREQUEST_RETRY_MAX),
                        "getHTTPRequestRetrySleep": ("HTTPRequestRetrySleep",
                           adminconsts.DEFAULT_HTTPREQUEST_RETRY_SLEEP)}}
    
    
    def __init__(self, dataSource):
        ## Root element, no parent
        BaseStore.__init__(self, StoreLogger(), None, dataSource, None) 
        self._customers = {}
        self._activities = ActivityStore(self, self, dataSource)
        # Registering Events
        self._register("customer-added")
        self._register("customer-removed")

        
    ## Public Methods ##
    
    def getLabel(self):
        return "Admin Store"
    
    def getIdentifier(self):
        return self.getLabel()
    
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

    def update(self, listener):
        BaseStore.update(self, listener)
        for customer in self._customers.itervalues():
            if customer.isActive():
                self.emitTo("customer-added", listener, customer)
        
    def _doGetChildElements(self):
        return self.getCustomers()
        
    def _doPrepareInit(self, chain):
        BaseStore._doPrepareInit(self, chain)
        # Ensure that the defaults are received
        # before customers initialization
        chain.addCallback(self.__cbRetrieveDefaults)
        # Retrieve and initialize the customers
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
            # Ensure no failure slips through
            d.addErrback(self._unexpectedError)
            deferreds.append(d)
        dl = defer.DeferredList(deferreds,
                                fireOnOneCallback=False,
                                fireOnOneErrback=False,
                                consumeErrors=True)
        # Preserve deferred result, drop all previous results even failures
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
            return None
        self._customers[customer.getName()] = customer
        # Send event when the customer has been activated
        self.emitWhenActive("customer-added", customer)
        # Activate the new customer store
        customer._activate()
        # Keep the callback chain result
        return customer
    
    def __ebCustomerInitFailed(self, failure, customer):
        #FIXME: Better Error Handling ?
        log.notifyFailure(self, failure, 
                          "Customer '%s' failed to initialize; dropping it",
                          customer.getLabel())
        customer._abort(failure)
        # Don't propagate failures, will be dropped anyway
        return
