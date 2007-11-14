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
from flumotion.transcoder.admin.errors import StoreError
from flumotion.transcoder.admin.datastore.basestore import BaseStore
from flumotion.transcoder.admin.datastore.targetstore import TargetStore
from flumotion.transcoder.admin.datastore.notifystore import NotificationFactory


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
    
    # MetaStore metaclass will create getters for these properties
    __getters__ = {"basic":
                      {"getName":         ("name", None),
                       "getSubdir":       ("subdir", None),
                       "getInputDir":     ("inputDir", None),
                       "getOutputDir":    ("outputDir", None),
                       "getFailedDir":    ("failedDir", None),
                       "getDoneDir":      ("doneDir", None),
                       "getLinkDir":      ("linkDir", None),
                       "getWorkDir":      ("workDir", None),
                       "getConfigDir":    ("configDir", None),
                       "getTempRepDir":   ("tempRepDir", None),
                       "getFailedRepDir": ("failedRepDir", None),
                       "getDoneRepDir":   ("doneRepDir", None)},
                   "parent_overridable":
                      {"getOutputMediaTemplate":  ("outputMediaTemplate",),
                       "getOutputThumbTemplate":  ("outputThumbTemplate",),
                       "getLinkFileTemplate":     ("linkFileTemplate",),
                       "getConfigFileTemplate":   ("configFileTemplate",),
                       "getReportFileTemplate":   ("reportFileTemplate",),
                       "getLinkTemplate":         ("linkTemplate",),
                       "getLinkURLPrefix":        ("linkURLPrefix",),
                       "getEnablePostprocessing": ("enablePostprocessing",),
                       "getEnablePreprocessing":  ("enablePreprocessing",),
                       "getEnableLinkFiles":      ("enableLinkFiles",),
                       "getTranscodingPriority":  ("transcodingPriority",),
                       "getProcessPriority":      ("processPriority",),
                       "getPreprocessCommand":    ("preprocessCommand",),
                       "getPostprocessCommand":   ("postprocessCommand",),
                       "getPreprocessTimeout":    ("preprocessTimeout",),
                       "getPostprocessTimeout":   ("postprocessTimeout",),
                       "getTranscodingTimeout":   ("transcodingTimeout",),
                       "getMonitoringPeriod":     ("monitoringPeriod",)}}


    def __init__(self, logger, parent, dataSource, profileData):
        BaseStore.__init__(self, logger, parent, dataSource, profileData,
                           IProfileStoreListener)
        self._targets = {}
    
    
    ## Public Methods ##
    
    def getLabel(self):
        return self.getName()    
    
    def getIdentifier(self):
        # For now the used identifier is the name, not the datasource one
        return self.getName()
    
    def getAdmin(self):
        return self.getParent().getAdmin()
    
    def getCustomer(self):
        return self.getParent()
    
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
        BaseStore._doSyncListener(self, listener)
        for target in self._targets.itervalues():
            if target.isActive():
                self._fireEventTo(listener, target, "TargetAdded")
            
    def _doPrepareInit(self, chain):
        BaseStore._doPrepareInit(self, chain)
        # Retrieve and initialize the targets
        chain.addCallback(self.__cbRetrieveTargets)

    def _onActivated(self):
        BaseStore._onActivated(self)
        self.debug("Profile '%s' activated", self.getLabel())
    
    def _onAborted(self, failure):
        BaseStore._onAborted(self, failure)
        self.debug("Profile '%s' aborted", self.getLabel())

    def _doRetrieveNotifications(self):
        return self._dataSource.retrieveProfileNotifications(self._data)
        
    def _doWrapNotification(self, notificationData):
        return NotificationFactory(notificationData, self.getAdmin(),
                                   self.getCustomer(), self, None)
        
        
    ## Private Methods ##
        
    def __cbRetrieveTargets(self, result):
        d = self._dataSource.retrieveTargets(self._data)
        d.addCallbacks(self.__cbTargetsReceived, 
                       self._retrievalFailed,
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
                   % (self.getName(), target.getName()))
            self.warning(msg)
            error = StoreError(msg)
            target._abort(error)
            return None
        self._targets[target.getName()] = target
        #Send event when the target has been activated
        self._fireEventWhenActive(target, "TargetAdded")
        #Activate the new target store
        target._activate()
        #Keep the callback chain result
        return target
    
    def __ebTargetInitFailed(self, failure, target):
        #FIXME: Better Error Handling ?
        log.notifyFailure(self, failure, 
                          "Target '%s' of profile '%s' failed "
                          "to initialize; dropping it", 
                          target.getLabel(), self.getLabel())
        target._abort(failure)
        #Don't propagate failures, will be dropped anyway
        return
