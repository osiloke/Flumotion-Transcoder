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
from twisted.internet import reactor, defer

from flumotion.transcoder import log
from flumotion.transcoder import utils
from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.context.admincontext import AdminContext
from flumotion.transcoder.admin.context.transcontext import TranscodingContext
from flumotion.transcoder.admin.proxies.managerset import ManagerSet, ManagerSetListener
from flumotion.transcoder.admin.proxies.workerset import WorkerSet
from flumotion.transcoder.admin.proxies.transcoderset import TranscoderSet
from flumotion.transcoder.admin.proxies.monitorset import MonitorSet
from flumotion.transcoder.admin.proxies.monitorproxy import MonitorListener
from flumotion.transcoder.admin.datastore.adminstore import AdminStore, AdminStoreListener
from flumotion.transcoder.admin.datastore.customerstore import CustomerStore, CustomerStoreListener
from flumotion.transcoder.admin.datastore.profilestore import ProfileStore, ProfileStoreListener
from flumotion.transcoder.admin.datastore.targetstore import TargetStore, TargetStoreListener
from flumotion.transcoder.admin.monitoring import Monitoring
from flumotion.transcoder.admin.montask import MonitoringTask
from flumotion.transcoder.admin.transcoding import Transcoding
from flumotion.transcoder.admin.scheduler import Scheduler

class TranscoderAdmin(log.Loggable,
                      ManagerSetListener,
                      MonitorListener,
                      AdminStoreListener,
                      CustomerStoreListener,
                      ProfileStoreListener):
    
    logCategory = adminconsts.ADMIN_LOG_CATEGORY
    
    def __init__(self, config):
        self._adminCtx = AdminContext(config)
        self._datasource = self._adminCtx.getDataSource()
        self._store = AdminStore(self._datasource)
        self._transCtx = TranscodingContext(self._adminCtx, self._store)
        self._managers = ManagerSet(self._adminCtx)
        self._workers = WorkerSet(self._managers)
        self._transcoders = TranscoderSet(self._managers)
        self._monitors = MonitorSet(self._managers)
        self._monitoring = Monitoring(self._workers, self._monitors)
        self._transcoding = Transcoding(self._workers, self._transcoders)
        self._scheduler = Scheduler(self._store, self._monitoring, 
                                    self._transcoding)
        self._started = False

    
    ## Public Methods ##
    
    def initialize(self):
        self.log("Initializing Transcoder Administration")
        d = defer.Deferred()
        d.addCallback(lambda r: self._datasource.initialize())
        d.addCallback(lambda r: self._store.initialize())
        d.addCallback(lambda r: self._managers.initialize())
        d.addCallback(lambda r: self._workers.initialize())
        d.addCallback(lambda r: self._monitors.initialize())
        d.addCallback(lambda r: self._transcoders.initialize())
        d.addCallback(lambda r: self._scheduler.initialize())
        d.addCallback(lambda r: self._monitoring.initialize())
        d.addCallback(lambda r: self._transcoding.initialize())
        d.addCallbacks(self.__cbAdminInitialized, 
                       self.__ebAdminInitializationFailed)
        # Register listeners
        self._store.addListener(self)
        self._managers.addListener(self)
        self._store.syncListener(self)
        self._managers.syncListener(self)
        # fire the initialization
        d.callback(defer._nothing)
        return d


    ## IManagerSetListener Overriden Methods ##
    
    def onDetached(self, managerset):
        self.debug("Transcoder admin has been detached, pausing transcoding")
        self._scheduler.pause()
        self._monitoring.pause()
        self._transcoding.pause()
        
        
    def onAttached(self, managerset):
        if not self._started:
            # Not yet started, it's not a resume but a startup
            return
        self.debug("Transcoder admin attached, resuming transcoding")
        d = defer.Deferred()
        # Wait a moment to let the workers the oportunity 
        # to log back to the manager.
        d.addCallback(utils.delayedSuccess, adminconsts.RESUME_DELAY)
        d.addCallback(utils.dropResult, self._scheduler.resume,
                      adminconsts.SCHEDULER_START_TIMEOUT)
        d.addCallback(utils.dropResult, self._monitoring.resume,
                      adminconsts.MONITORING_START_TIMEOUT)
        d.addCallback(utils.dropResult, self._transcoding.resume,
                      adminconsts.TRANSCODING_START_TIMEOUT)
        d.addErrback(self.__ebResumeFailed)
        d.callback(defer._nothing)


    ## IAdminStoreListener Overriden Methods ##
    
    def onCustomerAdded(self, admin, customer):
        self.debug("Customer '%s' Added", customer.getLabel())
        customer.addListener(self)
        customer.syncListener(self)
        custCtx = self._transCtx.getCustomerContext(customer)
        task = MonitoringTask(self._monitoring, custCtx)
        self._monitoring.addTask(custCtx.getIdentifier(), task)
        
    def onCustomerRemoved(self, admin, customer):
        self.debug("Customer '%s' Removed", customer.getLabel())
        customer.removeListener(self)
        custCtx = self._transCtx.getCustomerContext(customer)
        self._monitoring.removeTask(custCtx.getIdentifier())
        
        
    ## ICustomerStoreListener Overriden Methods ##
    
    def onProfileAdded(self, customer, profile):
        self.info("Profile '%s' Added", profile.getLabel())
        profile.addListener(self)
        profile.syncListener(self)
        
    def onProfileRemoved(self, customer, profile):
        self.info("Profile '%s' Removed", profile.getLabel())
        profile.removeListener(self)
        
    
    ## IProfileStoreListener Overriden Methods ##
    
    def onTargetAdded(self, profile, target):
        self.info("Target '%s' Added", target.getLabel())
        
    def onTargetRemoved(self, profile, target):
        self.info("Target '%s' Removed", target.getLabel())

    
    ## Private Methods ##
    
    def __startup(self):
        self.debug("Starting up transcoder admin")
        self._started = True
        d = defer.Deferred()
        d.addCallback(utils.dropResult, self._scheduler.start,
                      adminconsts.SCHEDULER_START_TIMEOUT)
        d.addCallback(utils.dropResult, self._monitoring.start,
                      adminconsts.MONITORING_START_TIMEOUT)
        d.addCallback(utils.dropResult, self._transcoding.start,
                      adminconsts.TRANSCODING_START_TIMEOUT)
        d.addErrback(self.__ebSartupFailed)
        d.callback(defer._nothing)
        
    def __cbAdminInitialized(self, result):
        # First wait for the store to become idle
        d = self._store.waitIdle(adminconsts.WAIT_IDLE_TIMEOUT)
        # And then for the managers/workers/components
        d.addBoth(utils.dropResult, self._managers.waitIdle, 
                  adminconsts.WAIT_IDLE_TIMEOUT)
        d.addBoth(utils.dropResult, self._scheduler.waitIdle, 
                  adminconsts.WAIT_IDLE_TIMEOUT)
        d.addBoth(utils.dropResult, self.__startup)
        return self
    
    def __ebAdminInitializationFailed(self, failure):
        reactor.stop()
        self.error("Transcoder Admin initialization failed: %s",
                   log.getFailureMessage(failure))

    def __ebSartupFailed(self, failure):
        self.warning("Failed to startup administration: %s",
                     log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
