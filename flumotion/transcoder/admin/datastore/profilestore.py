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
from flumotion.transcoder.admin.errors import StoreError
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


class ProfileStoreListener(object):    
    
    implements(IProfileStoreListener)
    
    def onTargetAdded(self, profile, target):
        pass
    
    def onTargetRemoved(self, profile, target):
        pass


class ProfileStore(BaseStore):

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


    def __init__(self, logger, parent, dataSource, profileData):
        BaseStore.__init__(self, logger, parent, dataSource, profileData,
                           IProfileStoreListener)
        self._targets = {}
    
    
    ## Public Methods ##
    
    def getLabel(self):
        return self.getName()    
    
    def getTargets(self):
        return self._targets.values()

    def __getitem__(self, targetName):
        return self._targets[targetName]
    
    def __iter__(self):
        return iter(self._targets)

    def iterTargets(self):
        return self._targets.itervalues()


    ## Overridden Methods ##
    
    def _doGetChildElements(self):
        return self.getTargets()    
    
    def _doSyncListener(self, listener):
        for target in self._targets.itervalues():
            if target.isActive():
                self._fireEventTo(listener, target, "TargetAdded")
            
    def _doPrepareInit(self, chain):
        #Retrieve and initialize the targets
        chain.addCallback(self.__cbRetrieveTargets)

    def _onActivated(self):
        self.debug("Profile '%s' activated", self.getLabel())
    
    def _onAborted(self, failure):
        self.debug("Profile '%s' aborted", self.getLabel())
        
        
    ## Private Methods ##
        
    def __cbRetrieveTargets(self, result):
        d = self._dataSource.retrieveTargets(self._data)
        d.addCallbacks(self.__cbTargetsReceived, 
                       self.__ebRetrievalFailed,
                       callbackArgs=(result,))
        return d
    
    def __cbTargetsReceived(self, targetsData, oldResult):
        deferreds = []
        self._setIdleTarget(len(targetsData))
        for profileData in targetsData:
            target = TargetStore(self, self, self._dataSource, 
                                 profileData)
            d = target.initialize()
            d.addCallbacks(self.__cbTargetInitialized, 
                           self.__ebTargetInitFailed,
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
    
    def __cbTargetInitialized(self, target):
        self.debug("Target '%s' initialized; adding it to profile '%s' store",
                   target.getLabel(), self.getLabel())
        if (target.getName() in self._targets):
            msg = ("Profile '%s' already have a target '%s', "
                   "dropping the new one" 
                   % (self.getParent().getName(), target.getName()))
            self.warning(msg)
            error = StoreError(msg)
            target._abort(error)
            return defer._nothing
        self._targets[target.getName()] = target
        #Send event when the target has been activated
        self._fireEventWhenActive(target, "TargetAdded")
        #Activate the new target store
        target._activate()
        #Keep the callback chain result
        return target
    
    def __ebTargetInitFailed(self, failure, target):
        #FIXME: Better Error Handling ?
        self.warning("target '%s' of profile '%s' failed to initialize; "
                     + "dropping it: %s", target.getLabel(),
                     self.getLabel(), log.getFailureMessage(failure))
        self.debug("Traceback of target '%s' failure:\n%s",
                   target.getLabel(), log.getFailureTraceback(failure))
        target._abort(failure)
        #Don't propagate failures, will be dropped anyway
        return
        
    def __ebRetrievalFailed(self, failure):
        #FIXME: Better Error Handling ?
        self.warning("Data retrieval failed for target %s: %s", 
                     self.getLabel(), log.getFailureMessage(failure))
        #Propagate failures
        return failure
