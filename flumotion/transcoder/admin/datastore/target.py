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

    base.genGetter("getName",      "name")
    base.genGetter("getSubdir",    "subdir")
    base.genGetter("getOutputDir", "outputDir")
    base.genGetter("getLinkDir",   "linkDir")
    base.genGetter("getWorkDir",   "workDir")
    base.genGetter("getExtension", "extension")
    base.genGetter("getOutputFileTemplate",   "outputFileTemplate")
    base.genGetter("getLinkFileTemplate",     "linkFileTemplate")
    base.genGetter("getLinkTemplate",         "linkTemplate")
    base.genGetter("getLinkURLPrefix",        "linkURLPrefix")
    base.genGetter("getEnablePostprocessing", "enablePostprocessing")
    base.genGetter("getEnableLinkFiles",      "enableLinkFiles")
    base.genGetter("getPostprocessCommand",   "postprocessCommand")
    base.genGetter("getPostprocessTimeout",   "postprocessTimeout")

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
    
    def getLabel(self):
        return self.getName()
    
    def getIdentifier(self):
        # For now the used identifier is the name, not the datasource one
        return self.getName()    
    
    def getConfigStore(self):
        return self._config


    ## Overridden Methods ##
    
    def _doPrepareInit(self, chain):
        base.NotifyStore._doPrepareInit(self, chain)
        # Retrieve target configuration
        chain.addCallback(self.__cbRetrieveConfig)

    def _onActivated(self):
        base.NotifyStore._onActivated(self)
        self.debug("Target '%s' activated", self.getLabel())
    
    def _onAborted(self, failure):
        base.NotifyStore._onAborted(self, failure)
        self.debug("Target '%s' aborted", self.getLabel())

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
