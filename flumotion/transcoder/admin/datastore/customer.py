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

from flumotion.inhouse import log, defer, utils

from flumotion.transcoder.admin import adminconsts, admerrs
from flumotion.transcoder.admin.datastore import base, profile, notification


class ICustomerStore(base.IBaseStore):

    name                 = Attribute("Name of the customer")
    subdir               = Attribute("Customer sub-directory")
    inputDir             = Attribute("Input files directory")
    outputDir            = Attribute("Output files directory")
    failedDir            = Attribute("Failure directory")
    doneDir              = Attribute("Success directory")
    linkDir              = Attribute("Links directory")
    workDir              = Attribute("Temporary directory")
    configDir            = Attribute("Transcoding configuration directory")
    tempRepDir           = Attribute("Reports temporary directory")
    failedRepDir         = Attribute("Reports failure directory")
    doneRepDir           = Attribute("Reports success directory")
    customerPriority     = Attribute("Customer transcoding priority")
    outputMediaTemplate  = Attribute("Output media file template")
    outputThumbTemplate  = Attribute("Output thumbnail file temaplte")
    linkFileTemplate     = Attribute("Link file template")
    configFileTemplate   = Attribute("Configuration file template")
    reportFileTemplate   = Attribute("Report file template")
    linkTemplate         = Attribute("Link template")
    linkURLPrefix        = Attribute("link URL prefix")
    enablePostprocessing = Attribute("Enable post-processing")
    enablePreprocessing  = Attribute("Enable pre-processing")
    enableLinkFiles      = Attribute("Enable link file generation")
    transcodingPriority  = Attribute("Transcoding priority")
    processPriority      = Attribute("Transcoding process priority")
    preprocessCommand    = Attribute("Pre-processing command line")
    postprocessCommand   = Attribute("Post-processing command line")
    preprocessTimeout    = Attribute("Pre-processing timeout")
    postprocessTimeout   = Attribute("Post-processing timeout")
    transcodingTimeout   = Attribute("Transcoding timeout")
    monitoringPeriod     = Attribute("Monitoring period")
    monitorType          = Attribute("Monitor type")
    setup_callback       = Attribute("Where to notify the worker's hostname and port")
    accessForceUser      = Attribute("Force user of new files and directories")
    accessForceGroup     = Attribute("Force group of new files and directories")
    accessForceDirMode   = Attribute("Force rights of new directories")
    accessForceFileMode  = Attribute("Force rights of new files")

    def getProfileStores(self):
        pass

    def getProfileStore(self, profIdent, default=None):
        pass

    def getProfileStoreByName(self, profName, default=None):
        pass

    def iterProfileStores(self):
        pass


class CustomerStore(base.NotifyStore):
    implements(ICustomerStore)

    name                 = base.ReadOnlyProxy("name")
    subdir               = base.ReadOnlyProxy("subdir")
    inputDir             = base.ReadOnlyProxy("inputDir")
    outputDir            = base.ReadOnlyProxy("outputDir")
    failedDir            = base.ReadOnlyProxy("failedDir")
    doneDir              = base.ReadOnlyProxy("doneDir")
    linkDir              = base.ReadOnlyProxy("linkDir")
    workDir              = base.ReadOnlyProxy("workDir")
    configDir            = base.ReadOnlyProxy("configDir")
    tempRepDir           = base.ReadOnlyProxy("tempRepDir")
    failedRepDir         = base.ReadOnlyProxy("failedRepDir")
    doneRepDir           = base.ReadOnlyProxy("doneRepDir")
    customerPriority     = base.ReadOnlyProxy("customerPriority")
    outputMediaTemplate  = base.ReadOnlyProxy("outputMediaTemplate")
    outputThumbTemplate  = base.ReadOnlyProxy("outputThumbTemplate")
    linkFileTemplate     = base.ReadOnlyProxy("linkFileTemplate")
    configFileTemplate   = base.ReadOnlyProxy("configFileTemplate")
    reportFileTemplate   = base.ReadOnlyProxy("reportFileTemplate")
    linkTemplate         = base.ReadOnlyProxy("linkTemplate")
    linkURLPrefix        = base.ReadOnlyProxy("linkURLPrefix")
    enablePostprocessing = base.ReadOnlyProxy("enablePostprocessing")
    enablePreprocessing  = base.ReadOnlyProxy("enablePreprocessing")
    enableLinkFiles      = base.ReadOnlyProxy("enableLinkFiles")
    transcodingPriority  = base.ReadOnlyProxy("transcodingPriority")
    processPriority      = base.ReadOnlyProxy("processPriority")
    preprocessCommand    = base.ReadOnlyProxy("preprocessCommand")
    postprocessCommand   = base.ReadOnlyProxy("postprocessCommand")
    preprocessTimeout    = base.ReadOnlyProxy("preprocessTimeout")
    postprocessTimeout   = base.ReadOnlyProxy("postprocessTimeout")
    transcodingTimeout   = base.ReadOnlyProxy("transcodingTimeout")
    monitoringPeriod     = base.ReadOnlyProxy("monitoringPeriod")
    monitorType          = base.ReadOnlyProxy("monitorType")
    monitorPort          = base.ReadOnlyProxy("monitorPort")
    setup_callback       = base.ReadOnlyProxy("setup_callback")
    accessForceUser      = base.ReadOnlyProxy("accessForceUser")
    accessForceGroup     = base.ReadOnlyProxy("accessForceGroup")
    accessForceDirMode   = base.ReadOnlyProxy("accessForceDirMode")
    accessForceFileMode  = base.ReadOnlyProxy("accessForceFileMode")


    def __init__(self, logger, adminStore, dataSource, custData):
        base.NotifyStore.__init__(self, logger, adminStore, dataSource, custData)
        self._customerInfo = None
        self._profiles = {} # {PROFILE_IDENTIFIER: ProfileStore}
        # Registering Events
        self._register("profile-added")
        self._register("profile-removed")


    ## Public Methods ##

    def getProfileStores(self):
        return self._profiles.values()

    def getProfileStore(self, profIdent, default=None):
        return self._profiles.get(profIdent, default)

    def getProfileStoreByName(self, profName, default=None):
        for profStore in self._profiles.itervalues():
            if profName == profStore.name:
                return profStore
        return default

    def iterProfileStores(self):
        return self._profiles.itervalues()

    def getAdminStore(self):
        return self.parent


    ## Overridden Methods ##

    def refreshListener(self, listener):
        base.NotifyStore.refreshListener(self, listener)
        for profStore in self._profiles.itervalues():
            if profStore.isActive():
                self.emitTo("profile-added", listener, profStore)

    def _doGetChildElements(self):
        return self.getProfileStores()

    def _doPrepareInit(self, chain):
        base.NotifyStore._doPrepareInit(self, chain)
        # Ensure that the customer info are received
        # before profiles initialization
        chain.addCallback(self.__cbRetrieveInfo)
        # Retrieve and initialize the profiles
        chain.addCallback(self.__cbRetrieveProfiles)

    def _onActivated(self):
        base.NotifyStore._onActivated(self)
        self.debug("Customer '%s' activated", self.label)

    def _onAborted(self, failure):
        base.NotifyStore._onAborted(self, failure)
        self.debug("Customer '%s' aborted", self.label)

    def _doRetrieveNotifications(self):
        return self._dataSource.retrieveCustomerNotifications(self._data)

    def _doWrapNotification(self, notifData):
        return notification.NotificationFactory(self, notifData,
                                                self.getAdminStore(),
                                                self, None, None)


    ## Private Methods ##

    def __cbRetrieveInfo(self, result):
        d = self._dataSource.retrieveDefaults()
        d.addCallbacks(self.__cbInfoReceived, self._retrievalFailed,
                       callbackArgs=(result,))
        return d

    def __cbInfoReceived(self, custInfo, oldResult):
        self._customerInfo = custInfo
        return oldResult

    def __cbRetrieveProfiles(self, result):
        d = self._dataSource.retrieveProfiles(self._data)
        d.addCallbacks(self.__cbProfilesReceived,
                       self._retrievalFailed,
                       callbackArgs=(result,))
        return d

    def __cbProfilesReceived(self, profDataList, oldResult):
        deferreds = []
        self._setIdleTarget(len(profDataList))
        for profData in profDataList:
            profStore = profile.ProfileStore(self, self, self._dataSource, profData)
            d = profStore.initialize()
            d.addCallbacks(self.__cbProfileInitialized,
                           self.__ebProfileInitFailed,
                           errbackArgs=(profStore,))
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

    def __cbProfileInitialized(self, profStore):
        self.debug("Profile '%s' initialized; adding it to customer '%s' store",
                   profStore.label, self.label)
        if (profStore.identifier in self._profiles):
            msg = ("Customer '%s' already have a profile '%s', "
                   "dropping the new one"
                   % (self.name, profStore.name))
            self.warning(msg)
            error = admerrs.StoreError(msg)
            profStore._abort(error)
            return None
        self._profiles[profStore.identifier] = profStore
        # Send event when the profile has been activated
        self.emitWhenActive("profile-added", profStore)
        # Activate the new profile store
        profStore._activate()
        # Keep the callback chain result
        return profStore

    def __ebProfileInitFailed(self, failure, profStore):
        #FIXME: Better Error Handling ?
        log.notifyFailure(self, failure,
                          "Profile '%s' of customer '%s' failed "
                          "to initialize; dropping it",
                          profStore.label, self.label)
        profStore._abort(failure)
        # Don't propagate failures, will be dropped anyway
        return

