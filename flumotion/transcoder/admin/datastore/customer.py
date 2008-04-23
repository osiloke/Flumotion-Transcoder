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

from flumotion.inhouse import log, defer, utils
 
from flumotion.transcoder.admin import adminconsts, errors as admerrs
from flumotion.transcoder.admin.datastore import base, profile, notification


class ICustomerStore(base.IStoreWithNotification):

    def getProfileStores(self):
        pass
    
    def getProfileStore(self, profIdent, default=None):
        pass    
    
    def getProfileStoreByName(self, profName, default=None):
        pass    
    
    def iterProfileStores(self):
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
    
    def getCustomerPriority(self):
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
    
    def getAccessForceUser(self):
        pass
    
    def getAccessForceGroup(self):
        pass
    
    def getAccessForceDirMode(self):
        pass
    
    def getAccessForceFileMode(self):
        pass


class CustomerStore(base.BaseStore):
    implements(ICustomerStore)

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
    base.genGetter("getCustomerPriority",     "customerPriority")
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
    base.genGetter("getAccessForceUser",      "accessForceUser")
    base.genGetter("getAccessForceGroup",     "accessForceGroup")
    base.genGetter("getAccessForceDirMode",   "accessForceDirMode")
    base.genGetter("getAccessForceFileMode",  "accessForceFileMode")

    def __init__(self, logger, adminStore, dataSource, custData):
        base.BaseStore.__init__(self, logger, adminStore,  dataSource, custData)
        self._customerInfo = None
        self._profiles = {} # {PROFILE_NAME: ProfileStore} 
        # Registering Events
        self._register("profile-added")
        self._register("profile-removed")
        
        
    ## Public Methods ##

    def getAdminStore(self):
        return self.parent

    def getLabel(self):
        return self.getName()
    
    def getIdentifier(self):
        # For now the used identifier is the name, not the datasource one
        return self.getName()
    
    def getProfileStores(self):
        return self._profiles.values()
    
    def getProfileStore(self, profIdent, default=None):
        #FIXME: differentiat name from identifier
        return self._profiles.get(profIdent, default)    
    
    def getProfileStoreByName(self, profName, default=None):
        return self._profiles.get(profName, default)    
    
    def iterProfileStores(self):
        return self._profiles.itervalues()
    

    ## Overridden Methods ##

    def refreshListener(self, listener):
        base.BaseStore.refreshListener(self, listener)
        for profStore in self._profiles.itervalues():
            if profStore.isActive():
                self.emitTo("profile-added", listener, profStore)
        
    def _doGetChildElements(self):
        return self.getProfileStores()
    
    def _doPrepareInit(self, chain):
        base.BaseStore._doPrepareInit(self, chain)
        # Ensure that the customer info are received
        # before profiles initialization
        chain.addCallback(self.__cbRetrieveInfo)
        # Retrieve and initialize the profiles
        chain.addCallback(self.__cbRetrieveProfiles)        
        
    def _onActivated(self):
        base.BaseStore._onActivated(self)
        self.debug("Customer '%s' activated", self.getLabel())
    
    def _onAborted(self, failure):
        base.BaseStore._onAborted(self, failure)
        self.debug("Customer '%s' aborted", self.getLabel())
        
    def _doRetrieveNotifications(self):
        return self._dataSource.retrieveCustomerNotifications(self._data)

    def _doWrapNotification(self, notifData):
        return notification.NotificationFactory(notifData,
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
                   profStore.getLabel(), self.getLabel())
        if (profStore.getName() in self._profiles):
            msg = ("Customer '%s' already have a profile '%s', "
                   "dropping the new one" 
                   % (self.getName(), profStore.getName()))
            self.warning(msg)
            error = admerrs.StoreError(msg)
            profStore._abort(error)
            return None
        self._profiles[profStore.getName()] = profStore
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
                          profStore.getLabel(), self.getLabel())
        profStore._abort(failure)
        # Don't propagate failures, will be dropped anyway
        return

