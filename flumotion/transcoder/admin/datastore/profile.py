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

from flumotion.transcoder.admin import admerrs
from flumotion.transcoder.admin.datastore import base, target, notification


class IProfileStore(base.IBaseStore):

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

    def getName(self):
        pass
    
    def getSubdir(self):
        pass
    
    def getInputDir(self):
        pass
    
    def getOutputDir(self):
        pass
    
    def getFailedDir(self):
        pass
    
    def getDoneDir(self):
        pass
    
    def getLinkDir(self):
        pass
    
    def getWorkDir(self):
        pass
    
    def getConfigDir(self):
        pass
    
    def getTempRepDir(self):
        pass
    
    def getFailedRepDir(self):
        pass
    
    def getDoneRepDir(self):
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
    
    def getLinkURLPrefix(self):
        pass
    
    def getEnablePostprocessing(self):
        pass
    
    def getEnablePreprocessing(self):
        pass
    
    def getEnableLinkFiles(self):
        pass
    
    def getTranscodingPriority(self):
        pass
    
    def getProcessPriority(self):
        pass
    
    def getPreprocessCommand(self):
        pass
    
    def getPostprocessCommand(self):
        pass
    
    def getPreprocessTimeout(self):
        pass
    
    def getPostprocessTimeout(self):
        pass
    
    def getTranscodingTimeout(self):
        pass
    
    def getMonitoringPeriod(self):
        pass


class ProfileStore(base.NotifyStore):
    implements(IProfileStore)
    
    base.genGetter("getName",         "name")
    base.genGetter("getSubdir",       "subdir")
    base.genGetter("getInputDir",     "inputDir")
    base.genGetter("getOutputDir",    "outputDir")
    base.genGetter("getFailedDir",    "failedDir")
    base.genGetter("getDoneDir",      "doneDir")
    base.genGetter("getLinkDir",      "linkDir")
    base.genGetter("getWorkDir",      "workDir")
    base.genGetter("getConfigDir",    "configDir")
    base.genGetter("getTempRepDir",   "tempRepDir")
    base.genGetter("getFailedRepDir", "failedRepDir")
    base.genGetter("getDoneRepDir",   "doneRepDir")
    base.genGetter("getOutputMediaTemplate",  "outputMediaTemplate")
    base.genGetter("getOutputThumbTemplate",  "outputThumbTemplate")
    base.genGetter("getLinkFileTemplate",     "linkFileTemplate")
    base.genGetter("getConfigFileTemplate",   "configFileTemplate")
    base.genGetter("getReportFileTemplate",   "reportFileTemplate")
    base.genGetter("getLinkTemplate",         "linkTemplate")
    base.genGetter("getLinkURLPrefix",        "linkURLPrefix")
    base.genGetter("getEnablePostprocessing", "enablePostprocessing")
    base.genGetter("getEnablePreprocessing",  "enablePreprocessing")
    base.genGetter("getEnableLinkFiles",      "enableLinkFiles")
    base.genGetter("getTranscodingPriority",  "transcodingPriority")
    base.genGetter("getProcessPriority",      "processPriority")
    base.genGetter("getPreprocessCommand",    "preprocessCommand")
    base.genGetter("getPostprocessCommand",   "postprocessCommand")
    base.genGetter("getPreprocessTimeout",    "preprocessTimeout")
    base.genGetter("getPostprocessTimeout",   "postprocessTimeout")
    base.genGetter("getTranscodingTimeout",   "transcodingTimeout")
    base.genGetter("getMonitoringPeriod",     "monitoringPeriod")
    
    def __init__(self, logger, custStore, dataSource, profData):
        #FIXME: use the real data identifier insteed of the name
        identifier = profData.name
        base.NotifyStore.__init__(self, logger, custStore, dataSource,
                                  profData, identifier=identifier)
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
            if targName == targStore.getName():
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
                   % (self.getName(), targStore.getName()))
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
