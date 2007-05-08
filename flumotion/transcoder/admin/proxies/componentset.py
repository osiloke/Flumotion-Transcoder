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
from flumotion.twisted.compat import Interface, implements

from flumotion.transcoder.admin.errors import OperationTimedOut
from flumotion.transcoder.admin.proxies import fluproxy
from flumotion.transcoder.admin.proxies import managerset
from flumotion.transcoder.admin.proxies import managerproxy
from flumotion.transcoder.admin.proxies import flowproxy
from flumotion.transcoder.admin.proxies import atmosphereproxy

ADD_DEFAULT_TIMEOUT = 30.0

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

    def waitComponent(self, identifier, timeout=None):
        """
        Wait to a component with specified identifier.
        If it's already contained by the set, the returned
        deferred will be called rightaway.
        """
        raise NotImplementedError()
    

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


    ## Protected Virtual Methods ##
    
    def _doFilterComponent(self, component):
        return True
    
    def _doAddComponent(self, component):
        pass
    
    def _doRemoveComponent(self, component):
        pass
    
    
class ComponentSetHelper(BaseComponentSet):
    
    def __init__(self, mgrset, listenerInterface):
        BaseComponentSet.__init__(self, mgrset, listenerInterface)
        self._components = {} # Identifier => ComponentProxy
        self._pendingAdd = {} # Identifier => {Deferred => timeout}


    ## Overriden Public Methods ##
    
    def waitComponent(self, identifier, timeout=None):
        result = defer.Deferred()
        if identifier in self._components:
            result.callback(self._components[identifier])
        else:
            to = None
            if timeout:
                to = reactor.callLater(timeout, 
                                       self.__waitComponentTimeout, 
                                       identifier, result)
            pending = self._pendingAdd.get(identifier, None)
            if not pending:
                pending = dict()
                self._pendingAdd[identifier] = pending
            pending[result] = to
        return result
            
    
    ## Overriden Protected Methods ##
    
    def _doAddComponent(self, component):
        identifier = component.getIdentifier()
        assert not (identifier in self._components)
        self._components[identifier] = component
        if identifier in self._pendingAdd:
            for d, to in self._pendingAdd[identifier].items():
                if to:
                    to.cancel()
                d.callback(component)
            del self._pendingAdd[identifier]

    def _doRemoveComponent(self, component):
        identifier = component.getIdentifier()
        assert identifier in self._components
        assert self._components[identifier] == component
        del self._components[identifier]

    
    ## Private Methods ##
    
    def __waitComponentTimeout(self, identifier, d):
        to = self._pendingAdd.pop(d)
        err = OperationTimedOut("Timeout waiting for component '%s' "
                                "to be added to set" % identifier)
        d.errback(err)
    

class IComponentSetListener(Interface):
    def onComponentAddedToSet(self, componentset, component):
        pass
    
    def onComponentRemovedFromSet(self, componentset, component):
        pass

    
class ComponentSet(ComponentSetHelper):
    
    def __init__(self, mgrset):
        ComponentSetHelper.__init__(self, mgrset, IComponentSetListener)
        
        
    ## Overriden Methods ##
    
    def _doSyncListener(self, listener):
        self._syncProxies("_components", listener, "ComponentAddedToSet")

    def _doAddComponent(self, component):
        ComponentSetHelper._doAddComponent(self, component)
        self._fireEvent(component, "ComponentAddedToSet")
    
    def _doRemoveComponent(self, component):
        ComponentSetHelper._doRemoveComponent(self, component)
        self._fireEvent(component, "ComponentRemovedFromSet")
