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

from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin import errors as admerrs
from flumotion.transcoder.admin.datastore import base, customer, state, activity, notification


class IAdminStore(base.IBaseStore):

    def getCustomerStores(self):
        pass
    
    def getCustomerStore(self, custIdent, default=None):
        pass

    def getCustomerStoreByName(self, custName, default=None):
        pass
        
    def iterCustomerStores(self):
        pass
    
    def getStateStore(self):
        pass

    def getOutputMediaTemplate(self):
        pass
    
    def getOutputThumbTemplate(self):
        pass
    
    def getLinkFileTemplate(self):
        pass
    
    def getConfigFileTemplate(self):
        pass
    
    def getReportFileTemplate(self):
        pass
    
    def getLinkTemplate(self):
        pass
    
    def getMonitoringPeriod(self):
        pass
    
    def getAccessForceUser(self):
        pass
    
    def getAccessForceGroup(self):
        pass
    
    def getAccessForceDirMode(self):
        pass
    
    def getAccessForceFileMode(self):
        pass
    
    def getProcessPriority(self):
        pass
    
    def getTranscodingPriority(self):
        pass
    
    def getTranscodingTimeout(self):
        pass
    
    def getPostprocessTimeout(self):
        pass
    
    def getPreprocessTimeout(self):
        pass
    
    def getMailSubjectTemplate(self):
        pass
    
    def getMailBodyTemplate(self):
        pass
    
    def getMailTimeout(self):
        pass
    
    def getMailRetryMax(self):
        pass
    
    def getMailRetrySleep(self):
        pass
    
    def getHTTPRequestTimeout(self):
        pass
    
    def getHTTPRequestRetryMax(self):
        pass
    
    def getHTTPRequestRetrySleep(self):
        pass


class StoreLogger(log.Loggable):
    logCategory = adminconsts.STORES_LOG_CATEGORY


class AdminStore(base.BaseStore):
    implements(IAdminStore)
    
    base.genGetter("getOutputMediaTemplate", "outputMediaTemplate")
    base.genGetter("getOutputThumbTemplate", "outputThumbTemplate")
    base.genGetter("getLinkFileTemplate", "linkFileTemplate")
    base.genGetter("getConfigFileTemplate", "configFileTemplate")
    base.genGetter("getReportFileTemplate", "reportFileTemplate")
    base.genGetter("getLinkTemplate", "linkTemplate")
    base.genGetter("getMonitoringPeriod", "monitoringPeriod")
    base.genGetter("getAccessForceUser", "accessForceUser")
    base.genGetter("getAccessForceGroup", "accessForceGroup")
    base.genGetter("getAccessForceDirMode", "accessForceDirMode")
    base.genGetter("getAccessForceFileMode", "accessForceFileMode")
    base.genGetter("getProcessPriority", "processPriority")
    base.genGetter("getTranscodingPriority", "transcodingPriority")
    base.genGetter("getTranscodingTimeout", "transcodingTimeout")
    base.genGetter("getPostprocessTimeout", "postprocessTimeout")
    base.genGetter("getPreprocessTimeout", "preprocessTimeout")
    base.genGetter("getMailSubjectTemplate", "mailSubjectTemplate")
    base.genGetter("getMailBodyTemplate", "mailBodyTemplate")
    base.genGetter("getMailTimeout", "mailTimeout")
    base.genGetter("getMailRetryMax", "mailRetryMax")
    base.genGetter("getMailRetrySleep", "mailRetrySleep")
    base.genGetter("getHTTPRequestTimeout", "HTTPRequestTimeout")
    base.genGetter("getHTTPRequestRetryMax", "HTTPRequestRetryMax")
    base.genGetter("getHTTPRequestRetrySleep", "HTTPRequestRetrySleep")

    def __init__(self, dataSource):
        ## Root element, no parent
        base.BaseStore.__init__(self, StoreLogger(), None, dataSource, None) 
        self._customers = {} # {CUSTOMER_NAME: CustomerStore}
        self._state = state.StateStore(self, self, dataSource)
        # Registering Events
        self._register("customer-added")
        self._register("customer-removed")

        
    ## Public Methods ##
    
    def getAdminStore(self):
        return self
    
    def getIdentifier(self):
        return self.getLabel()

    def getLabel(self):
        return "Admin Store"
        
    def getCustomerStores(self):
        return self._customers.values()
    
    def getCustomerStore(self, custIdent, default=None):
        #FIXME: differentiat name from identifier
        return self._customers.get(custIdent, default)

    def getCustomerStoreByName(self, custName, default=None):
        return self._customers.get(custName, default)
        
#    def __iter__(self):
#        return iter(self._customers)
    
    def iterCustomerStores(self):
        self._customers.itervalues()
    
    def getStateStore(self):
        return self._state
    
    
    ## Overridden Methods ##

    def refreshListener(self, listener):
        base.BaseStore.refreshListener(self, listener)
        for custStore in self._customers.itervalues():
            if custStore.isActive():
                self.emitTo("customer-added", listener, custStore)
        
    def _doGetChildElements(self):
        return self.getCustomerStores()
        
    def _doPrepareInit(self, chain):
        base.BaseStore._doPrepareInit(self, chain)
        # Ensure that the defaults are received
        # before customers initialization
        chain.addCallback(self.__cbRetrieveDefaults)
        # Retrieve and initialize the customers
        chain.addCallback(self.__cbRetrieveCustomers)

    def _doRetrieveNotifications(self):
        return self._dataSource.retrieveGlobalNotifications()
        
    def _doWrapNotification(self, notifData):
        return notification.NotificationFactory(notifData, self,
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
    
    def __cbCustomersReceived(self, custDataList, oldResult):
        deferreds = []
        self._setIdleTarget(len(custDataList))
        for custData in custDataList:
            custStore = customer.CustomerStore(self, self, self._dataSource, custData)
            d = custStore.initialize()
            d.addCallbacks(self.__cbCustomerInitialized, 
                           self.__ebCustomerInitFailed,
                           errbackArgs=(custStore,))
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
    
    def __cbCustomerInitialized(self, custStore):
        self.debug("Customer '%s' initialized; adding it to the admin store",
                   custStore.getLabel())
        if (custStore.getName() in self._customers):
            msg = ("Admin store already have a customer '%s', "
                  "dropping the new one" % custStore.getName())
            self.warning("%s", msg)
            error = admerrs.StoreError(msg)
            custStore._abort(error)
            return None
        self._customers[custStore.getName()] = custStore
        # Send event when the customer has been activated
        self.emitWhenActive("customer-added", custStore)
        # Activate the new customer store
        custStore._activate()
        # Keep the callback chain result
        return custStore
    
    def __ebCustomerInitFailed(self, failure, custStore):
        #FIXME: Better Error Handling ?
        log.notifyFailure(self, failure, 
                          "Customer '%s' failed to initialize; dropping it",
                          custStore.getLabel())
        custStore._abort(failure)
        # Don't propagate failures, will be dropped anyway
        return
