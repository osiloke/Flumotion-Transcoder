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

from flumotion.transcoder.admin.datastore import base, config, notification


class ITargetStore(base.IBaseStore):

    name                 = Attribute("Target's name")
    subdir               = Attribute("Target's sub-directory")
    outputDir            = Attribute("Output files directory")
    linkDir              = Attribute("Links directory")
    workDir              = Attribute("Temporary directory")
    extension            = Attribute("Output file extension")
    outputFileTemplate   = Attribute("Output file template")
    linkFileTemplate     = Attribute("Link file template")
    linkTemplate         = Attribute("Link template")
    linkURLPrefix        = Attribute("Link URL prefix")
    enablePostprocessing = Attribute("Enable post-processing")
    enableLinkFiles      = Attribute("Enable link file generation")
    postprocessCommand   = Attribute("Post-processing command line")
    postprocessTimeout   = Attribute("Post-processing timeout")

    def getCustomerStore(self):
        pass

    def getProfileStore(self):
        pass

    def getConfigStore(self):
        pass


class TargetStore(base.NotifyStore):
    implements(ITargetStore)

    name                 = base.ReadOnlyProxy("name")
    subdir               = base.ReadOnlyProxy("subdir")
    outputDir            = base.ReadOnlyProxy("outputDir")
    linkDir              = base.ReadOnlyProxy("linkDir")
    workDir              = base.ReadOnlyProxy("workDir")
    extension            = base.ReadOnlyProxy("extension")
    outputFileTemplate   = base.ReadOnlyProxy("outputFileTemplate")
    linkFileTemplate     = base.ReadOnlyProxy("linkFileTemplate")
    linkTemplate         = base.ReadOnlyProxy("linkTemplate")
    linkURLPrefix        = base.ReadOnlyProxy("linkURLPrefix")
    enablePostprocessing = base.ReadOnlyProxy("enablePostprocessing")
    enableLinkFiles      = base.ReadOnlyProxy("enableLinkFiles")
    postprocessCommand   = base.ReadOnlyProxy("postprocessCommand")
    postprocessTimeout   = base.ReadOnlyProxy("postprocessTimeout")

    def __init__(self, logger, profStore, dataSource, targData):
        base.NotifyStore.__init__(self, logger, profStore, dataSource, targData)
        self._config = None


    ## Public Methods ##

    def getAdminStore(self):
        return self.parent.getAdminStore()

    def getCustomerStore(self):
        return self.parent.getCustomerStore()

    def getProfileStore(self):
        return self.parent

    def getConfigStore(self):
        return self._config


    ## Overridden Methods ##

    def _doPrepareInit(self, chain):
        base.NotifyStore._doPrepareInit(self, chain)
        # Retrieve target configuration
        chain.addCallback(self.__cbRetrieveConfig)

    def _onActivated(self):
        base.NotifyStore._onActivated(self)
        self.debug("Target '%s' activated", self.label)

    def _onAborted(self, failure):
        base.NotifyStore._onAborted(self, failure)
        self.debug("Target '%s' aborted", self.label)

    def _doRetrieveNotifications(self):
        return self._dataSource.retrieveTargetNotifications(self._data)

    def _doWrapNotification(self, notifData):
        return notification.NotificationFactory(self, notifData,
                                                self.getAdminStore(),
                                                self.getCustomerStore(),
                                                self.getProfileStore(), self)


    ## Private Methods ##

    def __cbRetrieveConfig(self, result):
        d = self._dataSource.retrieveTargetConfig(self._data)
        d.addCallbacks(self.__cbConfigReceived,
                       self._retrievalFailed,
                       callbackArgs=(result,))
        return d

    def __cbConfigReceived(self, configData, oldResult):
        self._config = config.TargetConfigFactory(self, configData)
        return oldResult
