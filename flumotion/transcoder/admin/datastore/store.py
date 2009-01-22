# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import implements, Attribute

from flumotion.inhouse import log, defer

from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin import admerrs
from flumotion.transcoder.admin.datastore import base, customer, state, activity, notification


class IAdminStore(base.IBaseStore):

    outputMediaTemplate   = Attribute("Output media file template")
    outputThumbTemplate   = Attribute("Output thumbnail file temaplte")
    linkFileTemplate      = Attribute("Link file template")
    configFileTemplate    = Attribute("Configuration file template")
    reportFileTemplate    = Attribute("Report file template")
    linkTemplate          = Attribute("Link template")
    monitoringPeriod      = Attribute("Monitoring period")
    accessForceUser       = Attribute("Force user of new files and directories")
    accessForceGroup      = Attribute("Force group of new files and directories")
    accessForceDirMode    = Attribute("Force rights of new directories")
    accessForceFileMode   = Attribute("Force rights of new files")
    processPriority       = Attribute("Transcoding process priority")
    transcodingPriority   = Attribute("Transcoding priority")
    transcodingTimeout    = Attribute("Transcoding timeout")
    postprocessTimeout    = Attribute("Post-processing timeout")
    preprocessTimeout     = Attribute("Pre-processing timeout")
    mailSubjectTemplate   = Attribute("Mail notifications subject template")
    mailBodyTemplate      = Attribute("Mail notifications body template")
    mailTimeout           = Attribute("Mail notifications timeout")
    mailRetryMax          = Attribute("Maximum mail notification attempts")
    mailRetrySleep        = Attribute("Time to wait between mail notification attempts")
    HTTPRequestTimeout    = Attribute("HTTP notifications timeout")
    HTTPRequestRetryMax   = Attribute("HTTP notifications maximum attempt count")
    HTTPRequestRetrySleep = Attribute("Time to wait between HTTP notification attempts")
    sqlTimeout            = Attribute("SQL notifications timeout")
    sqlRetryMax           = Attribute("Maximum SQL notification attempts")
    sqlRetrySleep         = Attribute("Time to wait between SQL notification attempts")

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


class StoreLogger(log.Loggable):
    logCategory = adminconsts.STORES_LOG_CATEGORY


class AdminStore(base.NotifyStore):
    implements(IAdminStore)

    outputMediaTemplate   = base.ReadOnlyProxy("outputMediaTemplate")
    outputThumbTemplate   = base.ReadOnlyProxy("outputThumbTemplate")
    linkFileTemplate      = base.ReadOnlyProxy("linkFileTemplate")
    configFileTemplate    = base.ReadOnlyProxy("configFileTemplate")
    reportFileTemplate    = base.ReadOnlyProxy("reportFileTemplate")
    linkTemplate          = base.ReadOnlyProxy("linkTemplate")
    monitoringPeriod      = base.ReadOnlyProxy("monitoringPeriod")
    accessForceUser       = base.ReadOnlyProxy("accessForceUser")
    accessForceGroup      = base.ReadOnlyProxy("accessForceGroup")
    accessForceDirMode    = base.ReadOnlyProxy("accessForceDirMode")
    accessForceFileMode   = base.ReadOnlyProxy("accessForceFileMode")
    processPriority       = base.ReadOnlyProxy("processPriority")
    transcodingPriority   = base.ReadOnlyProxy("transcodingPriority")
    transcodingTimeout    = base.ReadOnlyProxy("transcodingTimeout")
    postprocessTimeout    = base.ReadOnlyProxy("postprocessTimeout")
    preprocessTimeout     = base.ReadOnlyProxy("preprocessTimeout")
    mailSubjectTemplate   = base.ReadOnlyProxy("mailSubjectTemplate")
    mailBodyTemplate      = base.ReadOnlyProxy("mailBodyTemplate")
    mailTimeout           = base.ReadOnlyProxy("mailTimeout")
    mailRetryMax          = base.ReadOnlyProxy("mailRetryMax")
    mailRetrySleep        = base.ReadOnlyProxy("mailRetrySleep")
    HTTPRequestTimeout    = base.ReadOnlyProxy("HTTPRequestTimeout")
    HTTPRequestRetryMax   = base.ReadOnlyProxy("HTTPRequestRetryMax")
    HTTPRequestRetrySleep = base.ReadOnlyProxy("HTTPRequestRetrySleep")
    sqlTimeout            = base.ReadOnlyProxy("sqlTimeout")
    sqlRetryMax           = base.ReadOnlyProxy("sqlRetryMax")
    sqlRetrySleep         = base.ReadOnlyProxy("sqlRetrySleep")

    def __init__(self, dataSource):
        identifier = "store.admin"
        label = "Admin Store"
        ## Root element, no parent
        base.NotifyStore.__init__(self, StoreLogger(), None, dataSource, None,
                                  identifier=identifier, label=label)
        self._customers = {} # {CUSTOMER_IDENTIFIER: CustomerStore}
        self._state = state.StateStore(self, self, dataSource)
        # Registering Events
        self._register("customer-added")
        self._register("customer-removed")


    ## Public Methods ##

    def getAdminStore(self):
        return self

    def getStateStore(self):
        return self._state

    def getCustomerStores(self):
        return self._customers.values()

    def getCustomerStore(self, custIdent, default=None):
        return self._customers.get(custIdent, default)

    def getCustomerStoreByName(self, custName, default=None):
        for custStore in self._customers.itervalues():
            if custName == custStore.name:
                return custStore
        return default

    def iterCustomerStores(self):
        self._customers.itervalues()


    ## Overridden Methods ##

    def refreshListener(self, listener):
        base.NotifyStore.refreshListener(self, listener)
        for custStore in self._customers.itervalues():
            if custStore.isActive():
                self.emitTo("customer-added", listener, custStore)

    def _doGetChildElements(self):
        return self.getCustomerStores()

    def _doPrepareInit(self, chain):
        base.NotifyStore._doPrepareInit(self, chain)
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
                   custStore.label)
        if (custStore.identifier in self._customers):
            msg = ("Admin store already have a customer '%s', "
                   "dropping the new one" % custStore.name)
            self.warning("%s", msg)
            error = admerrs.StoreError(msg)
            custStore._abort(error)
            return None
        self._customers[custStore.identifier] = custStore
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
                          custStore.label)
        custStore._abort(failure)
        # Don't propagate failures, will be dropped anyway
        return
