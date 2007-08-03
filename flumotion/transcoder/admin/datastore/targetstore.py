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

from flumotion.transcoder import log, defer
from flumotion.transcoder.admin.datastore.basestore import BaseStore
from flumotion.transcoder.admin.datastore.configstore import TargetConfigFactory
from flumotion.transcoder.admin.datastore.notifystore import NotificationFactory


class ITargetStoreListener(Interface):    
    pass


class TargetStoreListener(object):    
    
    implements(ITargetStoreListener)


class TargetStore(BaseStore):

    # MetaStore metaclass will create getters for these properties
    __getters__ = {"basic":
                       {"getName":      ("name", None),
                        "getSubdir":    ("subdir", None),
                        "getOutputDir": ("outputDir", None),
                        "getLinkDir":   ("linkDir", None),
                        "getWorkDir":   ("workDir", None),
                        "getExtension": ("extension", None)},
                   "parent_overridable":
                       {"getOutputMediaTemplate":  ("outputMediaTemplate",),
                        "getOutputThumbTemplate":  ("outputThumbTemplate",),
                        "getLinkFileTemplate":     ("linkFileTemplate",),
                        "getLinkTemplate":         ("linkTemplate",),
                        "getLinkURLPrefix":        ("linkURLPrefix",),
                        "getEnablePostprocessing": ("enablePostprocessing",),
                        "getEnableLinkFiles":      ("enableLinkFiles",),
                        "getPostprocessCommand":   ("postprocessCommand",),
                        "getPostprocessTimeout":   ("postprocessTimeout",)}}


    def __init__(self, logger, parent, dataSource, targetData):
        BaseStore.__init__(self, logger, parent, dataSource, targetData,
                           ITargetStoreListener)
        self._config = None
        

    ## Public Methods ##

    def getLabel(self):
        return self.getName()
    
    def getIdentifier(self):
        # For now the used identifier is the name, not the datasource one
        return self.getName()    
    
    def getAdmin(self):
        return self.getParent().getAdmin()

    def getCustomer(self):
        return self.getParent().getCustomer()
    
    def getProfile(self):
        return self.getParent()
    
    
    def getConfig(self):
        return self._config


    ## Overridden Methods ##
    
    def _doPrepareInit(self, chain):
        BaseStore._doPrepareInit(self, chain)
        # Retrieve target configuration
        chain.addCallback(self.__cbRetrieveConfig)

    def _onActivated(self):
        BaseStore._onActivated(self)
        self.debug("Target '%s' activated", self.getLabel())
    
    def _onAborted(self, failure):
        BaseStore._onAborted(self, failure)
        self.debug("Target '%s' aborted", self.getLabel())

    def _doRetrieveNotifications(self):
        return self._dataSource.retrieveTargetNotifications(self._data)

    def _doWrapNotification(self, notificationData):
        return NotificationFactory(notificationData, 
                                   self.getAdmin(),
                                   self.getCustomer(), 
                                   self.getProfile(), self)


    ## Private Methods ##
        
    def __cbRetrieveConfig(self, result):
        d = self._dataSource.retrieveTargetConfig(self._data)
        d.addCallbacks(self.__cbConfigReceived, 
                       self._retrievalFailed,
                       callbackArgs=(result,))
        return d

    def __cbConfigReceived(self, configData, oldResult):
        self._config = TargetConfigFactory(configData)
        return oldResult
