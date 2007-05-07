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
from flumotion.transcoder.admin.datastore.profilestore import ProfileStore


class ICustomerStoreListener(Interface):    
    def onProfileAdded(self, customer, profile):
        """
        Call when a profile has been added and fully initialized.
        """
    def onProfileRemoved(self, customer, profile):
        """
        Call when a profile is about to be removed.
        """


class CustomerStore(BaseStore):

    def __init__(self, logger, parent, dataSource, customerData):
        BaseStore.__init__(self, logger, parent,  dataSource, 
                           ICustomerStoreListener)
        self._customerData = customerData
        self._customerInfo = None
        self._profiles = []        
        
        
    ## Public Methods ##
    
    def profiles(self):
        return list(self._profiles)
    
    def getLabel(self):
        return self._customerData.label

    
    ## Overridden Methods ##
    
    def _doSyncListener(self, listener):
        for profile in self._profiles:
            if profile.isActive():
                self._fireEventTo(listener, profile, "ProfileAdded")
        
    def _doPrepareInit(self, chain):
        #Ensure that the customer info are received
        #before profiles initialization
        chain.addCallback(self.__retrieveInfo)
        #Retrieve and initialize the profiles
        chain.addCallback(self.__retrieveProfiles)        
        
    def _onActivated(self):
        self.debug("Customer '%s' activated" % self.getLabel())
    
    def _onAborted(self, failure):
        self.debug("Customer '%s' aborted" % self.getLabel())
        
        
    ## Private Methods ##
    
    def __retrieveInfo(self, result):
        d = self._dataSource.retrieveDefaults()
        d.addCallbacks(self.__infoReceived, 
                       self.__retrievalFailed,
                       callbackArgs=(result,))
        return d
        
    def __infoReceived(self, customerInfo, oldResult):
        self._customerInfo = customerInfo
        return oldResult
  
    def __retrieveProfiles(self, result):
        d = self._dataSource.retrieveProfiles(self._customerData)
        d.addCallbacks(self.__profilesReceived, 
                       self.__retrievalFailed,
                       callbackArgs=(result,))
        return d
    
    def __profilesReceived(self, profilesData, oldResult):
        deferreds = []
        for profileData in profilesData:
            profile = ProfileStore(self, self, self._dataSource, 
                                   profileData)
            d = profile.initialize()
            d.addCallbacks(self.__profileInitialized, 
                           self.__profileInitFailed,
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
    
    def __profileInitialized(self, profile):
        self.debug("Profile '%s' initialized; adding it to customer '%s' store",
                   profile.getLabel(), self.getLabel())
        self._profiles.append(profile)
        #Send event when the profile has been activated
        self._fireEventWhenActive(profile, "ProfileAdded")
        #Activate the new profile store
        profile._activate()
        #Keep the callback chain result
        return profile
    
    def __profileInitFailed(self, failure, profile):
        #FIXME: Better Error Handling ?
        self.warning("Profile '%s' of customer %s failed to initialize; "
                     + "dropping it: %s", profile.getLabel(),
                     self.getLabel(), log.getFailureMessage(failure))
        self.debug("Traceback of profile '%s' failure:\n%s" 
                   % (profile.getLabel(), log.getFailureTraceback(failure)))
        profile._abort(failure)
        #Don't propagate failures, will be dropped anyway
        return
        
    def __retrievalFailed(self, failure):
        #FIXME: Better Error Handling ?
        self.warning("Data retrieval failed for customer %s: %s", 
                     self.getLabel(), log.getFailureMessage(failure))
        #Propagate failures
        return failure
