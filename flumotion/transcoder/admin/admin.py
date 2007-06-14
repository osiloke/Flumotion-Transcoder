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

from flumotion.common.log import Loggable

from flumotion.transcoder import log
from flumotion.transcoder import utils
from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.context.admincontext import AdminContext
from flumotion.transcoder.admin.context.transcontext import TranscodingContext
from flumotion.transcoder.admin.proxies.managerset import ManagerSet
from flumotion.transcoder.admin.proxies.workerset import WorkerSet
from flumotion.transcoder.admin.proxies.transcoderset import TranscoderSet
from flumotion.transcoder.admin.proxies.monitorset import MonitorSet, MonitorSetListener
from flumotion.transcoder.admin.proxies.monitorproxy import MonitorListener
from flumotion.transcoder.admin.datastore.adminstore import AdminStore, AdminStoreListener
from flumotion.transcoder.admin.datastore.customerstore import CustomerStore, CustomerStoreListener
from flumotion.transcoder.admin.datastore.profilestore import ProfileStore, ProfileStoreListener
from flumotion.transcoder.admin.datastore.targetstore import TargetStore, TargetStoreListener
from flumotion.transcoder.admin.montask import MonitoringTask, MonitoringTaskListener
from flumotion.transcoder.admin.monitoring import Monitoring
from flumotion.transcoder.admin.transtask import TranscodingTask, TranscodingTaskListener
from flumotion.transcoder.admin.transcoding import Transcoding

## Just for debug ##
from flumotion.transcoder.admin.proxies.transcoderproxy import TranscoderProxy
from flumotion.transcoder.admin.transprops import TranscoderProperties
#from flumotion.transcoder.admin.proxies.componentset import ComponentSet, ComponentSetListener
#from flumotion.transcoder.admin.proxies.atmosphereproxy import AtmosphereProxy, AtmosphereListener
#from flumotion.transcoder.admin.proxies.componentproxy import ComponentProxy, ComponentListener
#from flumotion.transcoder.admin.proxies.managerset import ManagerSetListener
#from flumotion.transcoder.admin.proxies.managerproxy import ManagerListener

class TranscoderAdmin(Loggable,
                      MonitorSetListener,
                      MonitorListener,
                      AdminStoreListener,
                      CustomerStoreListener,
                      ProfileStoreListener,
                      MonitoringTaskListener,
                      ## Just for debug ##
                      #TargetStoreListener,
                      #ComponentSetListener,
                      #AtmosphereListener,
                      #ComponentListener,
                      #ManagerSetListener,
                      #ManagerListener
                      ):
    
    logCategory = 'trans-admin'
    
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
        
        ## Just for debug ##
        #self._components = ComponentSet(self._managers)
        #self._components.addListener(self)
        #self._managers.addListener(self)
        
        self._store.addListener(self)
        self._monitors.addListener(self)

    
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
        d.addCallback(lambda r: self._monitoring.initialize())
        d.addCallbacks(self.__cbAdminInitialized, 
                       self.__ebAdminInitializationFailed)
        #fire the initialization
        d.callback(defer._nothing)
        return d


    ## Just for debug ##
#    def onComponentAddedToSet(self, componentset, component):
#        self.info("Component %s Added To Set", component.getLabel())
#        
#    def onComponentRemovedFromSet(self, componentset, component):
#        self.info("Component %s Removed From Set", component.getLabel())
#        
#    def onManagerAddedToSet(self, managerset, manager):
#        self.info("Manager %s Added To Set", manager.getLabel())
#        manager.addListener(self)
#        manager.syncListener(self)
#        
#    def onManagerRemovedFromSet(self, managerset, manager):
#        self.info("Manager %s Removed From Set", manager.getLabel())
#        manager.removeListener(self)
#        
#    def onAtmosphereSet(self, manager, atmosphere):
#        self.info("Atmosphere %s Added", atmosphere.getLabel())
#        atmosphere.addListener(self)
#        atmosphere.syncListener(self)
#        
#    def onAtmosphereUnset(self, manager, atmosphere):
#        self.info("Atmosphere %s Removed", atmosphere.getLabel())
#        atmosphere.removeListener(self)
#        
#    def onAtmosphereComponentAdded(self, atmosphere, component):
#        self.info("Atmosphere Component %s Added", component.getLabel())
#        
#    def onAtmosphereComponentRemoved(self, atmosphere, component):
#        self.info("Atmosphere Component %s Removed", component.getLabel())


    ## IManagerSetListener Overriden Methods ##
    
    def onDetached(self, managerset):
        self._monitoring.pause()
        
    def onAttached(self, managerset):
        self._monitoring.resume()


    ## IMonitorSetListener Overriden Methods ##
    
    def onMonitorAddedToSet(self, monitorset, monitor):
        self.info("Monitor %s Added To Set", monitor.getLabel())
        
    def onMonitorRemovedFromSet(self, monitorset, monitor):
        self.info("Monitor %s Removed From Set", monitor.getLabel())


    ## IMonitoringTaskListener Overriden Methods ## 
    
    def onMonitoringActivated(self, monitoringtask, monitor):
        self.info("Monitoring %s activated", monitoringtask.getLabel())
    
    def onMonitoringDeactivated(self, monitoringtask, monitor):
        self.info("Monitoring %s deactivated", monitoringtask.getLabel())

    def onMonitoredFileAdded(self, monitoringtask, profileCtx):
        self.info("Monitoring %s: File %s added", monitoringtask.getLabel(), 
                  profileCtx.getInputPath())
        task = TranscodingTask(self._transcoding, profileCtx)
        self._transcoding.addTask(profileCtx.getIdentifier(), task)

    
    def onMonitoredFileRemoved(self, monitoringtask, profileCtx):
        self.info("Monitoring %s: File %s removed", monitoringtask.getLabel(), 
                  profileCtx.getInputPath())


    ## IAdminStoreListener Overriden Methods ##
    
    def onCustomerAdded(self, admin, customer):
        self.info("Customer '%s' Added", customer.getLabel())
        customer.addListener(self)
        customer.syncListener(self)
        custCtx = self._transCtx.getCustomerContext(customer)
        task = MonitoringTask(self._monitoring, custCtx)
        task.addListener(self)
        self._monitoring.addTask(customer.getName(), task)
        
    def onCustomerRemoved(self, admin, customer):
        self.info("Customer '%s' Removed", customer.getLabel())
        customer.removeListener(self)
        
        
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
        self._transcoding.start()
        self._monitoring.start()
        
    def __cbAdminInitialized(self, result):
        # First wait for the store to become idle
        d = self._store.waitIdle(adminconsts.WAIT_IDLE_TIMEOUT)
        # And then for the managers/workers/components
        d.addBoth(utils.dropResult, self._managers.waitIdle, 
                  adminconsts.WAIT_IDLE_TIMEOUT)
        d.addBoth(utils.dropResult, self.__startup)
        return self
    
    def __ebAdminInitializationFailed(self, failure):
        reactor.stop()
        self.error("Transcoder Admin initialization failed: %s",
                   log.getFailureMessage(failure))
