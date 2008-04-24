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

from flumotion.transcoder.admin.datastore import base, config, notification


class ITargetStore(base.IBaseStore):

    def getCustomerStore(self):
        pass
    
    def getProfileStore(self):
        pass
    
    def getConfigStore(self):
        pass

    def getName(self):
        pass
    
    def getSubdir(self):
        pass
    
    def getOutputDir(self):
        pass
    
    def getLinkDir(self):
        pass
    
    def getWorkDir(self):
        pass
    
    def getExtension(self):
        pass
    
    def getOutputFileTemplate(self):
        pass
    
    def getLinkFileTemplate(self):
        pass
    
    def getLinkTemplate(self):
        pass
    
    def getLinkURLPrefix(self):
        pass
    
    def getEnablePostprocessing(self):
        pass
    
    def getEnableLinkFiles(self):
        pass
    
    def getPostprocessCommand(self):
        pass
    
    def getPostprocessTimeout(self):
        pass


class TargetStore(base.NotifyStore):
    implements(ITargetStore)

    base.readonly_proxy("name")
    base.readonly_proxy("subdir")
    base.readonly_proxy("outputDir")
    base.readonly_proxy("linkDir")
    base.readonly_proxy("workDir")
    base.readonly_proxy("extension")
    base.readonly_proxy("outputFileTemplate")
    base.readonly_proxy("linkFileTemplate")
    base.readonly_proxy("linkTemplate")
    base.readonly_proxy("linkURLPrefix")
    base.readonly_proxy("enablePostprocessing")
    base.readonly_proxy("enableLinkFiles")
    base.readonly_proxy("postprocessCommand")
    base.readonly_proxy("postprocessTimeout")

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
