# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from twisted.internet import defer

from flumotion.twisted.compat import Interface
from flumotion.transcoder import log
from flumotion.transcoder.admin.datastore.basestore import BaseStore
from flumotion.transcoder.admin.datastore import configstore


class ITargetStoreListener(Interface):    
    pass


class TargetStore(BaseStore):

    def __init__(self, logger, parent, dataSource, targetData):
        BaseStore.__init__(self, logger, parent, dataSource,
                           ITargetStoreListener)
        self._targetData = targetData
        self._config = None
        

    ## Public Methods ##
        
    def getLabel(self):
        return self._targetData.label
    
    def getConfig(self):
        return self._config
    
    
    ## Overridden Methods ##
    
    def _doPrepareInit(self, chain):
        chain.addCallback(self.__retrieveConfig)

    def _onActivated(self):
        self.debug("Target '%s' activated" % self.getLabel())
    
    def _onAborted(self, failure):
        self.debug("Target '%s' aborted" % self.getLabel())


    ## Private Methods ##
        
    def __retrieveConfig(self, result):
        d = self._dataSource.retrieveTargetConfig(self._targetData)
        d.addCallbacks(self.__configReceived, 
                       self.__retrievalFailed,
                       callbackArgs=(result,))
        return d

    def __configReceived(self, configData, oldResult):
        self._config = configstore.TargetConfig(configData)
        return oldResult

    def __retrievalFailed(self, failure):
        #FIXME: Better Error Handling ?
        self.warning("Data retrieval failed for target %s: %s", 
                     self.getLabel(), log.getFailureMessage(failure))
        #Propagate failures
        return failure
