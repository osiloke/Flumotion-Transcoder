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
from twisted.internet import reactor

from flumotion.transcoder import log, defer, utils
from flumotion.transcoder.errors import OperationTimedOutError
from flumotion.transcoder.admin.errors import ComponentRejectedError
from flumotion.transcoder.admin.proxies.fluproxy import RootFlumotionProxy
from flumotion.transcoder.admin.proxies.managerset import ManagerSet, ManagerSetListener
from flumotion.transcoder.admin.proxies.managerproxy import ManagerListener
from flumotion.transcoder.admin.proxies.flowproxy import FlowListener
from flumotion.transcoder.admin.proxies.atmosphereproxy import AtmosphereListener


class ComponentSetSkeleton(RootFlumotionProxy,
                           ManagerSetListener,
                           ManagerListener,
                           FlowListener,
                           AtmosphereListener):
    
    def __init__(self, mgrset, listenerInterface):
        assert isinstance(mgrset, ManagerSet)
        RootFlumotionProxy.__init__(self, mgrset, listenerInterface)
        self._managers = mgrset
        self._managers.addListener(self)
        self._rejecteds = {} # {Identifier: ComponentProxy}
        self._compWaiters = {} # {Identifier: {Deferred: IDelayedCall}}
        
        
    ## Public Methods ##
    
    def getManagerSet(self):
        return self._managers
    
    def getComponents(self):
        return []

    def waitIdle(self, timeout=None):
        return self.getManagerSet().waitIdle(timeout)

    def isComponentRejected(self, component):
        """
        Return True if a component has been rejected,
        and still exists.
        """
        return component.getIdentifier() in self._rejecteds
    
    def isIdentifierRejected(self, identifier):
        """
        Return True if a component with specified identifier
        has been rejected and still exists.
        """
        return identifier in self._rejecteds

    def waitComponent(self, identifier, timeout=None):
        """
        Wait to a component with specified identifier.
        If it's already contained by the set, the returned
        deferred will be called rightaway.
        """
        result = defer.Deferred()
        if self.hasIdentifier(identifier):
            result.callback(self[identifier])
        elif self.isIdentifierRejected(identifier):
            result.errback(ComponentRejectedError("Component rejected"))
        else:
            to = utils.createTimeout(timeout, 
                                     self.__waitComponentTimeout, 
                                     identifier, result)
            self._compWaiters.setdefault(identifier, {})[result] = to
        return result


    ## Abstract Public Methodes ##
    
    def hasComponent(self, component):
        """
        Return True if the component has been accepted,
        and added to the set.
        """
        raise NotImplementedError()

    def hasIdentifier(self, identifier):
        """
        Return True if a component with specified identifier
        has been accepted and added to the set.
        """
        raise NotImplementedError()

    def __getitem__(self, identifier):
        """
        Return the component with specified identifier,
        accepted by the set or None.
        """
        raise NotImplementedError()

    def __iter__(self):
        """
        Return an iterator over the acctepted components.
        """
        raise NotImplementedError()


    ## managerset.IManagerSetListener Implementation ##

    def onManagerAddedToSet(self, mgrset, manager):
        manager.addListener(self)
        manager.syncListener(self)
        
    def onManagerRemovedFromSet(self, mgrset, manager):
        manager.removeListener(self)


    ## managerproxy.IManagerListener Implementation ##
    
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
        self.__addComponent(component)
    
    def onFlowComponentRemoved(self, flow, component):
        self.__removeComponent(component)
    
    
    ### atmosphereproxy.IAtmosphereListener Implementation ###
    
    def onAtmosphereComponentAdded(self, atmosphere, component):
        self.__addComponent(component)
    
    def onAtmosphereComponentRemoved(self, atmosphere, component):
        self.__removeComponent(component)


    ## Protected Virtual Methods ##
    
    def _doAcceptState(self, state):
        #FIXME: The semantic of this method is not well defined
        return True
    
    def _doAcceptComponent(self, component):
        """
        Called to check if a component should be added to the set.
        Should return True to add the component or False to reject it.
        Can return a Deferred.
        """
        return True
    
    def _doAddComponent(self, component):
        """
        Add the component to the set.
        The component has been accepted.
        """
    
    def _doRejectComponent(self, component):
        """
        The component has been rejected.
        """
    
    def _doRemoveComponent(self, component):
        """
        Remove a component.
        Only called for the accepted components.
        """

    
    ## Overriden Protected Methods ##
    
    def _doGetChildElements(self):
        return self.getComponents()

    
    ## Private Methods ##
    
    def __addComponent(self, component):
        d = defer.Deferred()
        d.addCallback(self._doAcceptComponent)
        d.addCallback(self.__cbPostAcceptAddition, component)
        d.addErrback(self.__ebAcceptFailure, component, 
                     "Failure during component addition")
        d.callback(component)
        
    def __cbPostAcceptAddition(self, accepted, component):
        identifier = component.getIdentifier()
        assert not (identifier in self._rejecteds)
        if accepted:
            self._doAddComponent(component)
            if identifier in self._compWaiters:
                for d, to in self._compWaiters[identifier].items():
                    utils.cancelTimeout(to)
                    d.callback(component)
                del self._compWaiters[identifier]
        else:
            self._rejecteds[identifier] = component
            self._doRejectComponent(component)
            if identifier in self._compWaiters:
                for d, to in self._compWaiters[identifier].items():
                    utils.cancelTimeout(to)
                    d.errback(ComponentRejectedError("Component rejected"))
                del self._compWaiters[identifier]

    def __ebAcceptFailure(self, failure, component, message):
        log.notifyFailure(self, failure, "%s", message)
        
    def __removeComponent(self, component):
        identifier = component.getIdentifier()
        if identifier in self._rejecteds:
            del self._rejecteds[identifier]
        if self.hasComponent(component):
            self._doRemoveComponent(component)
            
    def __waitComponentTimeout(self, identifier, d):
        self._compWaiters[identifier].pop(d)
        err = OperationTimedOutError("Timeout waiting for component '%s'" 
                                     % identifier)
        d.errback(err)
            
    
    
class BaseComponentSet(ComponentSetSkeleton):
    
    def __init__(self, mgrset, listenerInterface):
        ComponentSetSkeleton.__init__(self, mgrset, listenerInterface)
        self._components = {} # {Identifier: ComponentProxy}

    ## Overriden Public Methods ##

    def getComponents(self):
        return self._components.values()
    
    def hasComponent(self, component):
        return component.getIdentifier() in self._components
    
    def hasIdentifier(self, identifier):
        return identifier in self._components
    
    def __getitem__(self, identifier):
        return self._components.get(identifier, None)

    def __iter__(self):
        return self._components.itervalues()

    
    ## Overriden Protected Methods ##
    
    def _doAddComponent(self, component):
        identifier = component.getIdentifier()
        assert not (identifier in self._components)
        self._components[identifier] = component        

    def _doRejectComponent(self, component):
        identifier = component.getIdentifier()
        assert not (identifier in self._components)

    def _doRemoveComponent(self, component):
        identifier = component.getIdentifier()
        assert identifier in self._components
        assert self._components[identifier] == component
        del self._components[identifier]

    

class IComponentSetListener(Interface):
    def onComponentAddedToSet(self, componentset, component):
        pass
    
    def onComponentRemovedFromSet(self, componentset, component):
        pass


class ComponentSetListener(object):
    
    implements(IComponentSetListener)
    
    def onComponentAddedToSet(self, componentset, component):
        pass
    
    def onComponentRemovedFromSet(self, componentset, component):
        pass

    
class ComponentSet(BaseComponentSet):
    
    def __init__(self, mgrset):
        BaseComponentSet.__init__(self, mgrset, IComponentSetListener)
        
        
    ## Overriden Methods ##
    
    def _doSyncListener(self, listener):
        self._syncProxies("_components", listener, "ComponentAddedToSet")

    def _doAddComponent(self, component):
        BaseComponentSet._doAddComponent(self, component)
        self._fireEvent(component, "ComponentAddedToSet")
    
    def _doRemoveComponent(self, component):
        
        BaseComponentSet._doRemoveComponent(self, component)
        self._fireEvent(component, "ComponentRemovedFromSet")
