# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.twisted.compat import Interface, implements

from flumotion.transcoder.admin.proxies import fluproxy
from flumotion.transcoder.admin.proxies import managerset
from flumotion.transcoder.admin.proxies import managerproxy
from flumotion.transcoder.admin.proxies import flowproxy
from flumotion.transcoder.admin.proxies import atmosphereproxy


class BaseComponentSet(fluproxy.RootFlumotionProxy):
    
    implements(managerset.IManagerSetListener,
               managerproxy.IManagerListener,
               flowproxy.IFlowListener,
               atmosphereproxy.IAtmosphereListener)
    
    def __init__(self, mgrset, listenerInterface):
        assert isinstance(mgrset, managerset.ManagerSet)
        fluproxy.RootFlumotionProxy.__init__(self, mgrset, listenerInterface)
        self._managers = mgrset
        self._managers.addListener(self)
        
        
    ## Public Methods ##


    ### managerset.IManagerSetListener Implementation ###

    def onManagerAddedToSet(self, mgrset, manager):
        manager.addListener(self)
        manager.syncListener(self)
        
    def onManagerRemovedFromSet(self, mgrset, manager):
        manager.removeListener(self)


    ### managerproxy.IManagerListener Implementation ###
    
    def onWorkerAdded(self, manager, worker):
        pass
    
    def onWorkerRemoved(self, manager, worker):
        pass

    def onAtmosphereSet(self, manager, atmosphere):
        atmosphere.addListener(self)
        atmosphere.syncListener(self)
    
    def onAtmosphereUnset(self, manager, atmosphere):
        atmosphere.removeListener(self)
    
    def onFlowAdded(self, manager, flow):
        flow.addListener(self)
        flow.syncListener(self)
    
    def onFlowRemoved(self, manager, flow):
        flow.removeListener(self)


    ### flowproxy.IFlowListener Implementation ###

    def onFlowComponentAdded(self, flow, component):
        if self._doFilterComponent(component):
            self._doAddComponent(component)
        
    
    def onFlowComponentRemoved(self, flow, component):
        if self._doFilterComponent(component):
            self._doRemoveComponent(component)
    
    
    ### atmosphereproxy.IAtmosphereListener Implementation ###
    
    def onAtmosphereComponentAdded(self, atmosphere, component):
        if self._doFilterComponent(component):
            self._doAddComponent(component)
    
    def onAtmosphereComponentRemoved(self, atmosphere, component):
        if self._doFilterComponent(component):
            self._doRemoveComponent(component)


    ## Protected Methods ##
    
    def _doFilterComponent(self, component):
        return True
    
    def _doAddComponent(self, component):
        pass
    
    def _doRemoveComponent(self, component):
        pass



class IComponentSetListener(Interface):
    def onComponentAddedToSet(self, componentset, component):
        pass
    
    def onComponentRemovedFromSet(self, componentset, component):
        pass

    
class ComponentSet(BaseComponentSet):
    
    def __init__(self, mgrset):
        BaseComponentSet.__init__(self, mgrset, IComponentSetListener)
        self._components = {} # Identifier => ComponentProxy
        
        
    ## Overriden Methods ##
    
    def _doSyncListener(self, listener):
        self._syncProxies("_components", listener, "ComponentAddedToSet")

    def _doAddComponent(self, component):
        identifier = component.getIdentifier()
        assert not (identifier in self._components)
        self._components[identifier] = component
        self._fireEvent(component, "ComponentAddedToSet")
    
    def _doRemoveComponent(self, component):
        identifier = component.getIdentifier()
        assert identifier in self._components
        assert self._components[identifier] == component
        del self._components[identifier]
        self._fireEvent(component, "ComponentRemovedFromSet")
