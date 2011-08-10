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

from flumotion.transcoder.admin import admerrs
from flumotion.transcoder.admin.datastore import base, target, notification


class IProfileStore(base.IBaseStore):

    name                 = Attribute("Name of the profile")
    subdir               = Attribute("Profile's sub-directory")
    active               = Attribute("Whether the monitoring is active (filesystem-based) or passive (http-based)")
    inputDir             = Attribute("Input files directory")
    outputDir            = Attribute("Output files directory")
    failedDir            = Attribute("Failed files directory")
    doneDir              = Attribute("Done files directory")
    linkDir              = Attribute("Links directory")
    workDir              = Attribute("Temporary directory")
    configDir            = Attribute("Transcoding configuration files directory")
    tempRepDir           = Attribute("Reports' temporary directory")
    failedRepDir         = Attribute("Failed reports directory")
    doneRepDir           = Attribute("Done reports directory")
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

    def getCustomerStore(self):
        pass

    def getTargetStores(self):
        pass

    def getTargetStore(self, targIdent, default=None):
        pass

    def getTargetStoreByName(self, targName, default=None):
        pass

    def iterTargetStores(self):
        pass


class ProfileStore(base.NotifyStore):
    implements(IProfileStore)

    name                 = base.ReadOnlyProxy("name")
    subdir               = base.ReadOnlyProxy("subdir")
    active               = base.ReadOnlyProxy("active", 0)
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


    def __init__(self, logger, custStore, dataSource, profData):
        base.NotifyStore.__init__(self, logger, custStore, dataSource, profData)
        self._targets = {} # {TARGET_IDENTIFIER: TagetStore}
        # Registering Events
        self._register("target-added")
        self._register("target-removed")


    ## Public Methods ##

    def getAdminStore(self):
        return self.parent.getAdminStore()

    def getCustomerStore(self):
        return self.parent

    def getTargetStores(self):
        return self._targets.values()

    def getTargetStore(self, targIdent, default=None):
        return self._targets.get(targIdent, default)

    def getTargetStoreByName(self, targName, default=None):
        for targStore in self._targets.itervalues():
            if targName == targStore.name:
                return targStore
        return default

    def iterTargetStores(self):
        return self._targets.itervalues()


    ## Overridden Methods ##

    def refreshListener(self, listener):
        base.NotifyStore.refreshListener(self, listener)
        for targStore in self._targets.itervalues():
            if targStore.isActive():
                self.emitTo("target-added", listener, targStore)

    def _doGetChildElements(self):
        return self.getTargetStores()

    def _doPrepareInit(self, chain):
        base.NotifyStore._doPrepareInit(self, chain)
        # Retrieve and initialize the targets
        chain.addCallback(self.__cbRetrieveTargets)

    def _onActivated(self):
        base.NotifyStore._onActivated(self)
        self.debug("Profile '%s' activated", self.label)

    def _onAborted(self, failure):
        base.NotifyStore._onAborted(self, failure)
        self.debug("Profile '%s' aborted", self.label)

    def _doRetrieveNotifications(self):
        return self._dataSource.retrieveProfileNotifications(self._data)

    def _doWrapNotification(self, notifData):
        return notification.NotificationFactory(self, notifData,
                                                self.getAdminStore(),
                                                self.getCustomerStore(),
                                                self, None)


    ## Private Methods ##

    def __cbRetrieveTargets(self, result):
        d = self._dataSource.retrieveTargets(self._data)
        d.addCallbacks(self.__cbTargetsReceived,
                       self._retrievalFailed,
                       callbackArgs=(result,))
        return d

    def __cbTargetsReceived(self, targDataList, oldResult):
        deferreds = []
        self._setIdleTarget(len(targDataList))
        for targData in targDataList:
            targStore = target.TargetStore(self, self, self._dataSource, targData)
            d = targStore.initialize()
            d.addCallbacks(self.__cbTargetInitialized,
                           self.__ebTargetInitFailed,
                           errbackArgs=(targStore,))
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

    def __cbTargetInitialized(self, targStore):
        self.debug("Target '%s' initialized; adding it to profile '%s' store",
                   targStore.label, self.label)
        if (targStore.identifier in self._targets):
            msg = ("Profile '%s' already have a target '%s', "
                   "dropping the new one"
                   % (self.name, targStore.name))
            self.warning(msg)
            error = admerrs.StoreError(msg)
            targStore._abort(error)
            return None
        self._targets[targStore.identifier] = targStore
        # Send event when the target has been activated
        self.emitWhenActive("target-added", targStore)
        # Activate the new target store
        targStore._activate()
        # Keep the callback chain result
        return targStore

    def __ebTargetInitFailed(self, failure, targStore):
        #FIXME: Better Error Handling ?
        log.notifyFailure(self, failure,
                          "Target '%s' of profile '%s' failed "
                          "to initialize; dropping it",
                          targStore.label, self.label)
        targStore._abort(failure)
        # Don't propagate failures, will be dropped anyway
        return
