# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.


from twisted.internet import reactor, defer
from flumotion.common.log import Loggable
from flumotion.twisted.compat import implements

from flumotion.transcoder import log
from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.admin.jobprops import JobProperties
from flumotion.transcoder.admin.monitorprops import MonitorProperties
from flumotion.transcoder.admin.contexts.admincontext import AdminContext
from flumotion.transcoder.admin.proxies import managerset
from flumotion.transcoder.admin.proxies import workerset
#from flumotion.transcoder.admin.proxies import componentset
from flumotion.transcoder.admin.proxies import transcoderset
from flumotion.transcoder.admin.proxies import managerproxy
from flumotion.transcoder.admin.proxies import monitorset
from flumotion.transcoder.admin.proxies import monitorproxy
from flumotion.transcoder.admin.proxies import workerproxy
from flumotion.transcoder.admin.proxies import atmosphereproxy
from flumotion.transcoder.admin.proxies import flowproxy
from flumotion.transcoder.admin.proxies import componentproxy
from flumotion.transcoder.admin.proxies import transcoderproxy
from flumotion.transcoder.admin.datastore import adminstore, customerstore
from flumotion.transcoder.admin.datastore import profilestore, targetstore


class TranscoderAdmin(Loggable):
    
    logCategory = 'trans-admin'
    
    implements(monitorproxy.IMonitorListener,
               monitorset.IMonitorSetListener,
               transcoderproxy.ITranscoderListener,
               transcoderset.ITranscoderSetListener,
               componentproxy.IComponentListener,
               #componentset.IComponentSetListener,
               flowproxy.IFlowListener,
               workerset.IWorkerSetListener,
               workerproxy.IWorkerListener,
               managerset.IManagerSetListener,
               managerproxy.IManagerListener,
               adminstore.IAdminStoreListener,
               customerstore.ICustomerStoreListener,
               profilestore.IProfileStoreListener,
               targetstore.ITargetStoreListener)
    
    def __init__(self, config):
        self._context = AdminContext(config)
        self._datasource = self._context.getDataSource()
        self._store = adminstore.AdminStore(self._datasource)
        self._managers = managerset.ManagerSet(self._context)
        self._workers = workerset.WorkerSet(self._managers)
        #self._components = componentset.ComponentSet(self._managers)
        self._transcoders = transcoderset.TranscoderSet(self._managers)
        self._monitors = monitorset.MonitorSet(self._managers)
        self._store.addListener(self)
        self._managers.addListener(self)
        self._workers.addListener(self)
        #self._components.addListener(self)
        self._transcoders.addListener(self)
        self._monitors.addListener(self)
    
    
    ## Public Methods ##
    
    def initialize(self):
        self.log("Initializing Transcoder Administration")
        d = defer.Deferred()
        d.addCallback(lambda r: self._datasource.initialize())
        d.addCallback(lambda r: self._store.initialize())
        d.addCallback(lambda r: self._managers.initialize())
        d.addCallback(lambda r: self._workers.initialize())
        #d.addCallback(lambda r: self._components.initialize())
        d.addCallback(lambda r: self._transcoders.initialize())
        d.addCallback(lambda r: self._monitors.initialize())
        d.addErrback(self.__initializationFailed)
        #Ensure that the result of the callback added to the
        #deferred return by this method to be self
        d.addCallback(lambda r, p: p, self)
        #fire the initialization
        d.callback(defer._nothing)
        return d


    ### managerset.IManagerSetListener Implementation ###

    def onManagerAddedToSet(self, managerset, manager):
        self.info("Manager '%s' Added to Set", manager.getName())
        manager.addListener(self)
        manager.syncListener(self)
    
    def onManagerRemovedFromSet(self, managerset, manager):
        self.info("Manager '%s' Removed from Set", manager.getName())
        manager.removeListener(self)

    
    ### managerproxy.IManagerListener Implementation ###
    
    def onWorkerAdded(self, manager, worker):
        self.info("Worker '%s' Added to Manager '%s'", 
                  worker.getName(), manager.getName())
    
    def onWorkerRemoved(self, manager, worker):
        self.info("Worker '%s' Removed from Manager '%s'", 
                  worker.getName(), manager.getName())

    def onAtmosphereSet(self, manager, atmosphere):
        self.info("Atmosphere of Manager '%s' Set to '%s'", 
                  manager.getName(), atmosphere.getName())
    
    def onAtmosphereUnset(self, manager, atmosphere):
        self.info("Atmosphere '%s' of Manager '%s' Unset", 
                  atmosphere.getName(), manager.getName())        
    
    def onFlowAdded(self, manager, flow):
        self.info("Flow '%s' Added to Manager '%s'", 
                  flow.getName(), manager.getName())
        flow.addListener(self)
        flow.syncListener(self)
    
    def onFlowRemoved(self, manager, flow):
        self.info("Flow '%s' Removed from Manager '%s'", 
                  flow.getName(), manager.getName())
        flow.removeListener(self)

    
    ### workerset.IWorkerSetListener Implementation ###
    
    def onWorkerAddedToSet(self, workerset, worker):
        self.info("Worker '%s' Added to Set", worker.getName())
        worker.addListener(self)
        worker.syncListener(self)
        props = MonitorProperties(["/home/file/fluendo/files/incoming",
                                   "/home/file/big/client/files/incoming"], 2)
        d = self._monitors.startMonitor("monitor-on-%s" % worker.getName(), worker, props)
        def ok(monitor):
            print "#"*20, "monitor:", monitor, "successfuly added"
        def puah(failure):
            print "!"*20, "monitor add failed:", log.getFailureMessage(failure)
        d.addCallbacks(ok, puah)
    
    def onWorkerRemovedFromSet(self, workerset, worker):
        self.info("Worker '%s' Removed from Set", worker.getName())
        worker.removeListener(self)
    

    ### workerproxy.IWorkerListener Implementation ###
    
    
    ### flowproxy.IFlowListener Implementation ###
    
    def onFlowComponentAdded(self, flow, component):
        self.info("Component '%s' Added to flow '%s'", 
                  component.getName(), flow.getName())
    
    def onFlowComponentRemoved(self, flow, component):
        self.info("Component '%s' Removed from flow '%s'", 
                  component.getName(), flow.getName())
        
        
    ### atmosphereproxy.IAtmosphereListener Implementation ###
    
    def onAtmosphereComponentAdded(self, atmosphere, component):
        self.info("Component '%s' Added to atmosphere '%s'", 
                  component.getName(), atmosphere.getName())
    
    def onAtmospherComponentRemoved(self, atmosphere, component):
        self.info("Component '%s' Removed from atmosphere '%s'", 
                  component.getName(), atmosphere.getName())


    ### componentset.IComponentSetListener Implementation ###
    
    def onComponentAddedToSet(self, componentset, component):
        if not isinstance(component, transcoderproxy.TranscoderProxy):
            self.info("Component '%s' Added to Set", component.getName())
            component.addListener(self)
            component.syncListener(self)
    
    def onComponentRemovedFromSet(self, componentset, component):
        if not isinstance(component, transcoderproxy.TranscoderProxy):
            self.info("Component '%s' Removed from Set", component.getName())
            component.removeListener(self)
        
        
    ### componentproxy.IComponentListener Implemenetation ###
    
    def onComponenetMoodChanged(self, component, mood):
        self.info("Component '%s' Mood Changed to %s", 
                  component.getName(), mood.name)
        
    def onComponentRunning(self, component, worker):
        self.info("Component '%s' Running on worker '%s'", 
                  component.getName(), worker.getName())
    
    def onComponentLost(self, component, worker):
        self.info("Component '%s' Lost from worker '%s'", 
                  component.getName(), worker.getName())
    


    ### transcoderset.ITranscoderSetListener Implemenetation ###
    
    def onTranscoderAddedToSet(self, transcoderset, transcoder):
        self.info("Transcoder '%s' Added to Set", transcoder.getName())
        transcoder.addListener(self)
        transcoder.syncListener(self)
    
    def onTranscoderRemovedFromSet(self, transcoderset, transcoder):
        self.info("Transcoder '%s' Removed from Set", transcoder.getName())
        transcoder.removeListener(self)


    ### transcoderproxy.ITranscoderListener Implemenetation ###
    
    def onTranscoderProgress(self, transcoder, percent):
        self.info("Transcoder '%s' Progression: %d %%", 
                  transcoder.getName(), percent)
    
    def onTranscoderStatusChanged(self, transcoder, status):
        self.info("Transcoder '%s' Status changed to %s", 
                  transcoder.getName(), status.name)


    ### monitorset.IMonitorSetListener Implemenetation ###
    
    def onMonitorAddedToSet(self, monitorset, monitor):
        self.info("monitor '%s' Added to Set", monitor.getName())
        monitor.addListener(self)
        monitor.syncListener(self)
    
    def onMonitorRemovedFromSet(self, monitorset, monitor):
        self.info("monitor '%s' Removed from Set", monitor.getName())
        monitor.removeListener(self)

    
    ### monitorproxy.IMonitorListener Implemenetation ###
    
    def onMonitorFileAdded(self, monitor, file, state):
        self.info("Monitor '%s' File Added: '%s' (%s)", 
                  monitor.getName(), file, state.name)
    
    def onMonitorFileRemoved(self, monitor, file, state):
        self.info("Monitor '%s' File Removed: '%s'", 
                  monitor.getName(), file)
    
    def onMonitorFileStateChanged(self, monitor, file, state):
        self.info("Monitor '%s' File Changed to '%s': '%s'", 
                  monitor.getName(), state.name, file)

    
    ### adminstore.IAdminStoreListener Implementation ###
    
    def onCustomerAdded(self, admin, customer):
        self.info("Customer '%s' Added", customer.getLabel())
        customer.addListener(self)
        #customer.syncListener(self)
        
    def onCustomerRemoved(self, admin, customer):
        self.info("Customer '%s' Removed", customer.getLabel())
        customer.removeListener(self)                
    
    
    ### adminstore.ICustomerStoreListener Implementation ###
    
    def onProfileAdded(self, admin, profile):
        self.info("Profile '%s' Added", profile.getLabel())
        profile.addListener(self)
        #profile.syncListener(self)
        
    def onProfileRemoved(self, admin, profile):
        self.info("Profile '%s' Removed", profile.getLabel())
        profile.removeListener(self)
        
    
    ### adminstore.IProfileStoreListener Implementation ###
    
    def onTargetAdded(self, admin, target):
        self.info("Target '%s' Added", target.getLabel())
        target.addListener(self)
        #target.syncListener(self)
        
    def onTargetRemoved(self, admin, target):
        self.info("Target '%s' Removed", target.getLabel())
        target.removeListener(self)
    
    
    ### adminstore.ITargetStoreListener Implementation ###
        
    
    ## Private Methods ##
    
    def __initializationFailed(self, failure):
        reactor.stop()
        self.error("Transcoder Admin initialization failed: %s",
                   log.getFailureMessage(failure))


        