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
from flumotion.transcoder.admin.datastore.targetstore import TargetStore

class IProfileStoreListener(Interface):    
    def onTargetAdded(self, profile, target):
        """
        Call when a target has been added and fully initialized.
        """
    def onTargetRemoved(self, profile, target):
        """
        Call when a target is about to be removed.
        """


class ProfileStore(BaseStore):

    def __init__(self, logger, parent, dataSource, profileData):
        BaseStore.__init__(self, logger, parent, dataSource,
                           IProfileStoreListener)
        self._profileData = profileData
        self._targets = []
    
    
    ## Public Methods ##
    
    def targets(self):
        return list(self._targets)
    
    def getLabel(self):
        return self._profileData.label

    
    ## Overridden Methods ##
    
    def _doSyncListener(self, listener):
        for target in self._targets:
            if target.isActive():
                self._fireEventTo(listener, target, "TargetAdded")
            
    def _doPrepareInit(self, chain):
        #Retrieve and initialize the targets
        chain.addCallback(self.__retrieveTargets)

    def _onActivated(self):
        self.debug("Profile '%s' activated" % self.getLabel())
    
    def _onAborted(self, failure):
        self.debug("Profile '%s' aborted" % self.getLabel())
        
        
    ## Private Methods ##
        
    def __retrieveTargets(self, result):
        d = self._dataSource.retrieveTargets(self._profileData)
        d.addCallbacks(self.__targetsReceived, 
                       self.__retrievalFailed,
                       callbackArgs=(result,))
        return d
    
    def __targetsReceived(self, targetsData, oldResult):
        deferreds = []
        for profileData in targetsData:
            target = TargetStore(self, self, self._dataSource, 
                                 profileData)
            d = target.initialize()
            d.addCallbacks(self.__targetInitialized, 
                           self.__targetInitFailed,
                           errbackArgs=(target,))
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
    
    def __targetInitialized(self, target):
        self.debug("Target '%s' initialized; adding it to profile '%s' store",
                   target.getLabel(), self.getLabel())
        self._targets.append(target)
        #Send event when the target has been activated
        self._fireEventWhenActive(target, "TargetAdded")
        #Activate the new target store
        target._activate()
        #Keep the callback chain result
        return target
    
    def __targetInitFailed(self, failure, target):
        #FIXME: Better Error Handling ?
        self.warning("target '%s' of profile '%s' failed to initialize; "
                     + "dropping it: %s", target.getLabel(),
                     self.getLabel(), log.getFailureMessage(failure))
        self.debug("Traceback of target '%s' failure:\n%s" 
                   % (target.getLabel(), log.getFailureTraceback(failure)))
        target._abort(failure)
        #Don't propagate failures, will be dropped anyway
        return
        
    def __retrievalFailed(self, failure):
        #FIXME: Better Error Handling ?
        self.warning("Data retrieval failed for target %s: %s", 
                     self.getLabel(), log.getFailureMessage(failure))
        #Propagate failures
        return failure

    def __unexpectedError(self, failure, target):
        """
        Prevents the lost of failure messages.
        """
        self.warning("Unexpected Error: %s",
                     log.getFailureMessage(failure))    
