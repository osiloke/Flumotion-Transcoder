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

from flumotion.inhouse import log, defer, utils

from flumotion.transcoder.admin import admerrs
from flumotion.transcoder.admin.proxy import base, managerset


class ComponentSetSkeleton(base.RootProxy):
    
    def __init__(self, managerPxySet):
        assert isinstance(managerPxySet, managerset.ManagerSet)
        base.RootProxy.__init__(self, managerPxySet)
        self._managerPxySet = managerPxySet
        self._rejecteds = {} # {Identifier: ComponentProxy}
        self._compWaiters = {} # {Identifier: {Deferred: IDelayedCall}}
        self._managerPxySet.connectListener("manager-added", self,
                                            self.__onManagerAddedToSet)
        self._managerPxySet.connectListener("manager-removed", self,
                                            self.__onManagerRemovedFromSet)
        
        
    ## Public Methods ##
    
    def getManagerProxySet(self):
        return self._managerPxySet
    
    def getComponentProxies(self):
        return []

    def waitIdle(self, timeout=None):
        return self.getManagerProxySet().waitIdle(timeout)

    def isComponentProxyRejected(self, compPxy):
        """
        Return True if a component has been rejected,
        and still exists.
        """
        return compPxy.getIdentifier() in self._rejecteds
    
    def isIdentifierRejected(self, identifier):
        """
        Return True if a component with specified identifier
        has been rejected and still exists.
        """
        return identifier in self._rejecteds

    def waitComponentProxy(self, identifier, timeout=None):
        """
        Wait to a component with specified identifier.
        If it's already contained by the set, the returned
        deferred will be called rightaway.
        """
        result = defer.Deferred()
        if self.hasIdentifier(identifier):
            result.callback(self[identifier])
        elif self.isIdentifierRejected(identifier):
            result.errback(admerrs.ComponentRejectedError("Component rejected"))
        else:
            to = utils.createTimeout(timeout, 
                                     self.__waitComponentTimeout, 
                                     identifier, result)
            self._compWaiters.setdefault(identifier, {})[result] = to
        return result


    ## Abstract Public Methodes ##
    
    def hasComponentProxy(self, compPxy):
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


    ## managerset.ManagerSet Event Listeners ##

    def __onManagerAddedToSet(self, managerPxySet, managerPxy):
        managerPxy.connectListener("atmosphere-set", self,
                                   self.__onAtmosphereSet)
        managerPxy.connectListener("atmosphere-unset", self,
                                   self.__onAtmosphereUnset)
        managerPxy.connectListener("flow-added", self,
                                   self.__onFlowAdded)
        managerPxy.connectListener("flow-removed", self,
                                   self.__onFlowRemoved)
        managerPxy.refreshListener(self)
        
    def __onManagerRemovedFromSet(self, managerPxySet, managerPxy):
        managerPxy.disconnectListener("atmosphere-set", self)
        managerPxy.disconnectListener("atmosphere-unset", self)
        managerPxy.disconnectListener("flow-added", self)
        managerPxy.disconnectListener("flow-removed", self)


    ## Manager Event Listeners ##
    
    def __onAtmosphereSet(self, managerPxy, atmoPxy):
        atmoPxy.connectListener("component-added", self,
                                self.__onAtmosphereComponentAdded)
        atmoPxy.connectListener("component-removed", self,
                                self.__onAtmosphereComponentRemoved)
        atmoPxy.refreshListener(self)
    
    def __onAtmosphereUnset(self, managerPxy, atmoPxy):
        atmoPxy.disconnectListener("component-added", self)
        atmoPxy.disconnectListener("component-removed", self)
    
    def __onFlowAdded(self, managerPxy, flowPxy):
        flowPxy.connectListener("component-added", self,
                                self.__onFlowComponentAdded)
        flowPxy.connectListener("component-removed", self,
                                self.__onFlowComponentRemoved)
        flowPxy.refreshListener(self)
    
    def __onFlowRemoved(self, managerPxy, flowPxy):
        flowPxy.disconnectListener("component-added", self)
        flowPxy.disconnectListener("component-removed", self)


    ### Flow Event Listeners ###

    def __onFlowComponentAdded(self, flowPxy, compPxy):
        self.__addComponent(compPxy)
    
    def __onFlowComponentRemoved(self, flowPxy, compPxy):
        self.__removeComponent(compPxy)
    
    
    ### Atmosphere Event Listeners ###
    
    def __onAtmosphereComponentAdded(self, atmoPxy, compPxy):
        self.__addComponent(compPxy)
    
    def __onAtmosphereComponentRemoved(self, atmoPxy, compPxy):
        self.__removeComponent(compPxy)


    ## Protected Virtual Methods ##
    
    def _doAcceptState(self, state):
        #FIXME: The semantic of this method is not well defined
        return True
    
    def _doAcceptComponent(self, compPxy):
        """
        Called to check if a component should be added to the set.
        Should return True to add the component or False to reject it.
        Can return a Deferred.
        """
        return True
    
    def _doAddComponent(self, compPxy):
        """
        Add the component to the set.
        The component has been accepted.
        """
    
    def _doRejectComponent(self, compPxy):
        """
        The component has been rejected.
        """
    
    def _doRemoveComponent(self, compPxy):
        """
        Remove a component.
        Only called for the accepted components.
        """

    
    ## Overriden Protected Methods ##
    
    def _doGetChildElements(self):
        return self.getComponentProxies()

    
    ## Private Methods ##
    
    def __addComponent(self, compPxy):
        d = defer.Deferred()
        d.addCallback(self._doAcceptComponent)
        d.addCallback(self.__cbPostAcceptAddition, compPxy)
        d.addErrback(self.__ebAcceptFailure, compPxy, 
                     "Failure during component addition")
        d.callback(compPxy)
        
    def __cbPostAcceptAddition(self, accepted, compPxy):
        identifier = compPxy.getIdentifier()
        assert not (identifier in self._rejecteds)
        if accepted:
            self._doAddComponent(compPxy)
            if identifier in self._compWaiters:
                for d, to in self._compWaiters[identifier].items():
                    utils.cancelTimeout(to)
                    d.callback(compPxy)
                del self._compWaiters[identifier]
        else:
            self._rejecteds[identifier] = compPxy
            self._doRejectComponent(compPxy)
            if identifier in self._compWaiters:
                for d, to in self._compWaiters[identifier].items():
                    utils.cancelTimeout(to)
                    d.errback(admerrs.ComponentRejectedError("Component rejected"))
                del self._compWaiters[identifier]

    def __ebAcceptFailure(self, failure, compPxy, message):
        log.notifyFailure(self, failure, "%s", message)
        
    def __removeComponent(self, compPxy):
        identifier = compPxy.getIdentifier()
        if identifier in self._rejecteds:
            del self._rejecteds[identifier]
        if self.hasComponentProxy(compPxy):
            self._doRemoveComponent(compPxy)
            
    def __waitComponentTimeout(self, identifier, d):
        self._compWaiters[identifier].pop(d)
        err = admerrs.OperationTimedOutError("Timeout waiting for component '%s'" 
                                             % identifier)
        d.errback(err)
            
    
    
class BaseComponentSet(ComponentSetSkeleton):
    
    def __init__(self, managerPxySet):
        ComponentSetSkeleton.__init__(self, managerPxySet)
        self._compPxys = {} # {Identifier: ComponentProxy}

    ## Overriden Public Methods ##

    def getComponentProxies(self):
        return self._compPxys.values()
    
    def hasComponentProxy(self, compPxy):
        return compPxy.getIdentifier() in self._compPxys
    
    def hasIdentifier(self, identifier):
        return identifier in self._compPxys
    
    def __getitem__(self, identifier):
        return self._compPxys.get(identifier, None)

    def __iter__(self):
        return self._compPxys.itervalues()

    
    ## Overriden Protected Methods ##
    
    def _doAddComponent(self, compPxy):
        identifier = compPxy.getIdentifier()
        assert not (identifier in self._compPxys)
        self._compPxys[identifier] = compPxy        

    def _doRejectComponent(self, compPxy):
        identifier = compPxy.getIdentifier()
        assert not (identifier in self._compPxys)

    def _doRemoveComponent(self, compPxy):
        identifier = compPxy.getIdentifier()
        assert identifier in self._compPxys
        assert self._compPxys[identifier] == compPxy
        del self._compPxys[identifier]

    
class ComponentSet(BaseComponentSet):
    
    def __init__(self, managerPxySet):
        BaseComponentSet.__init__(self, managerPxySet)
        # Registering Events
        self._register("component-added")
        self._register("component-removed")
        
    ## Overriden Methods ##
    
    def refreshListener(self, listener):
        self._refreshProxiesListener("_compPxys", listener, "component-added")

    def _doAddComponent(self, compPxy):
        BaseComponentSet._doAddComponent(self, compPxy)
        self.emit("component-added", compPxy)
    
    def _doRemoveComponent(self, compPxy):
        
        BaseComponentSet._doRemoveComponent(self, compPxy)
        self.emit("component-removed", compPxy)
