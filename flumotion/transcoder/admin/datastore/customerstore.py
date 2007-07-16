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
from twisted.internet import defer

from flumotion.transcoder import log
from flumotion.transcoder import utils
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.errors import StoreError
from flumotion.transcoder.admin.datastore.basestore import BaseStore
from flumotion.transcoder.admin.datastore.profilestore import ProfileStore
from flumotion.transcoder.admin.datastore.notificationstore import NotificationFactory


class ICustomerStoreListener(Interface):    
    def onProfileAdded(self, customer, profile):
        """
        Call when a profile has been added and fully initialized.
        """
    def onProfileRemoved(self, customer, profile):
        """
        Call when a profile is about to be removed.
        """


class CustomerStoreListener(object):    
    
    implements(ICustomerStoreListener)
    
    def onProfileAdded(self, customer, profile):
        pass
    
    def onProfileRemoved(self, customer, profile):
        pass


class CustomerStore(BaseStore):

    # MetaStore metaclass will create getters/setters for these properties
    __overridable_properties__ = ["outputMediaTemplate",
                                  "outputThumbTemplate",
                                  "linkFileTemplate",
                                  "configFileTemplate",
                                  "reportFileTemplate",
                                  "linkTemplate",
                                  "linkURLPrefix",
                                  "enablePostprocessing",
                                  "enablePreprocessing",
                                  "enableLinkFiles",
                                  "transcodingPriority",
                                  "processPriority",
                                  "preprocessCommand",
                                  "postprocessCommand",
                                  "preprocessTimeout",
                                  "postprocessTimeout",
                                  "transcodingTimeout",
                                  "monitoringPeriod"]
    
    # MetaStore metaclass will create getters/setters for these properties
    __simple_properties__ = ["name",
                             "subdir",
                             "inputDir",
                             "outputDir",
                             "failedDir",
                             "doneDir",
                             "linkDir",
                             "workDir",
                             "configDir",
                             "failedRepDir",
                             "doneRepDir"]
    
    # MetaStore metaclass will create getters/setters for these properties
    __default_properties__ = {"customerPriority": 
                                  adminconsts.DEFAULT_CUSTOMER_PRIORITY}


    def __init__(self, logger, parent, dataSource, customerData):
        BaseStore.__init__(self, logger, parent,  dataSource, customerData,
                           ICustomerStoreListener)
        self._customerInfo = None
        self._profiles = {}
        
        
    ## Public Methods ##
    
    def getLabel(self):
        return self.getName()
    
    def getAdmin(self):
        return self.getParent()
    
    def getProfiles(self):
        return self._profiles.values()
    
    def getProfile(self, profileName, default=None):
        return self._profiles.get(profileName, default)    
    
    def __getitem__(self, profileName):
        return self._profiles[profileName]
    
    def __iter__(self):
        return iter(self._profiles)
    
    def iterProfiles(self):
        return self._profiles.itervalues()
    

    ## Overridden Methods ##

    def _doGetChildElements(self):
        return self.getProfiles()
    
    def _doSyncListener(self, listener):
        BaseStore._doSyncListener(self, listener)
        for profile in self._profiles.itervalues():
            if profile.isActive():
                self._fireEventTo(listener, profile, "ProfileAdded")
        
    def _doPrepareInit(self, chain):
        BaseStore._doPrepareInit(self, chain)
        # Ensure that the customer info are received
        # before profiles initialization
        chain.addCallback(self.__cbRetrieveInfo)
        # Retrieve and initialize the profiles
        chain.addCallback(self.__cbRetrieveProfiles)        
        
    def _onActivated(self):
        BaseStore._onActivated(self)
        self.debug("Customer '%s' activated", self.getLabel())
    
    def _onAborted(self, failure):
        BaseStore._onAborted(self, failure)
        self.debug("Customer '%s' aborted", self.getLabel())
        
    def _doRetrieveNotifications(self):
        return self._dataSource.retrieveCustomerNotifications(self._data)

    def _doWrapNotification(self, notificationData):
        return NotificationFactory(notificationData, self.getAdmin(),
                                   self, None, None)

        
    ## Private Methods ##
    
    def __cbRetrieveInfo(self, result):
        d = self._dataSource.retrieveDefaults()
        d.addCallbacks(self.__cbInfoReceived, 
                       self._retrievalFailed,
                       callbackArgs=(result,))
        return d
        
    def __cbInfoReceived(self, customerInfo, oldResult):
        self._customerInfo = customerInfo
        return oldResult
  
    def __cbRetrieveProfiles(self, result):
        d = self._dataSource.retrieveProfiles(self._data)
        d.addCallbacks(self.__cbProfilesReceived, 
                       self._retrievalFailed,
                       callbackArgs=(result,))
        return d
    
    def __cbProfilesReceived(self, profilesData, oldResult):
        deferreds = []
        self._setIdleTarget(len(profilesData))
        for profileData in profilesData:
            profile = ProfileStore(self, self, self._dataSource, 
                                   profileData)
            d = profile.initialize()
            d.addCallbacks(self.__cbProfileInitialized, 
                           self.__ebProfileInitFailed,
                           errbackArgs=(profile,))
            #Ensure no failure slips through
            d.addErrback(self._unexpectedError)
            deferreds.append(d)
        dl = defer.DeferredList(deferreds,
                                fireOnOneCallback=False,
                                fireOnOneErrback=False,
                                consumeErrors=True)
        #Preserve deferred result, drop all previous results even failures
        dl.addCallback(lambda result, old: old, oldResult)
        return dl
    
    def __cbProfileInitialized(self, profile):
        self.debug("Profile '%s' initialized; adding it to customer '%s' store",
                   profile.getLabel(), self.getLabel())
        if (profile.getName() in self._profiles):
            msg = ("Customer '%s' already have a profile '%s', "
                   "dropping the new one" 
                   % (self.getCustomer().getName(), profile.getName()))
            self.warning(msg)
            error = StoreError(msg)
            profile._abort(error)
            return defer._nothing
        self._profiles[profile.getName()] = profile
        #Send event when the profile has been activated
        self._fireEventWhenActive(profile, "ProfileAdded")
        #Activate the new profile store
        profile._activate()
        #Keep the callback chain result
        return profile
    
    def __ebProfileInitFailed(self, failure, profile):
        #FIXME: Better Error Handling ?
        self.warning("Profile '%s' of customer %s failed to initialize; "
                     + "dropping it: %s", profile.getLabel(),
                     self.getLabel(), log.getFailureMessage(failure))
        self.debug("Traceback of profile '%s' failure:\n%s",
                   profile.getLabel(), log.getFailureTraceback(failure))
        profile._abort(failure)
        #Don't propagate failures, will be dropped anyway
        return

