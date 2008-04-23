# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import Interface, implements, Attribute

from twisted.internet import reactor

from flumotion.inhouse import log, defer, utils, waiters

from flumotion.transcoder import errors
from flumotion.transcoder.admin import adminelement


class IProxyElement(Interface):

    identifier = Attribute("Proxy unique identifier")
    label = Attribute("Proxy description")

    def getName(self):
        """
        The name is unique in a component group context (flow and atmosphere)
        """


class IBaseProxy(IProxyElement):
    
    def getManagerProxy(self):
        pass


#TODO: Rewrite this... It's a mess

class ProxyElement(adminelement.AdminElement):
    
    implements(IProxyElement)
    
    def __init__(self, logger, parentPxy, identifier, name=None, label=None):
        name = name or identifier
        label = label or name
        adminelement.AdminElement.__init__(self, logger, parentPxy,
                                           identifier, label)
        self.name = name or identifier
        self._pendingElements = {} # {attr: {identifier: ProxyElement}}        


    ## IProxyElement Methods ##

    def getName(self):
        return self.name
    

    ## Virtual Methods ##
    
    def _onElementInitialized(self, element):
        """
        Called when an element succeed its initialization,
        and has been added to the group.
        """
    
    def _onElementInitFailed(self, element, failure):
        """
        Called when an element fail to initialize.
        The element will not be added to the group.
        """
    
    def _onElementActivated(self, element):
        """
        Called when an element has been activated.
        """
    
    def _onElementAborted(self, element, failure):
        """
        Called when an element has been aborted.
        """
    
    def _onElementRemoved(self, element):
        """
        Called when an element has beed removed from the group.
        """
    
    def _onElementNotFound(self, identifier):
        """
        Called when an elment couldn't be removed from the group
        because it wasn't found. Probably because it fail to initialize.
        """

    ## Overriden Methods ##
    
    def _doPrepareInit(self, chain):
        pass
    
    def _doPrepareActivation(self, chain):
        pass

    ## Protected Methods ##
    
    def _refreshProxiesListener(self, attr, listener, addEvent):
        """
        Utility method to refresh a listener. 
        """
        value = self.__getAttrValue(attr)
        if not value: return
        if isinstance(value, dict):
            for element in value.values():
                assert isinstance(element, ProxyElement)
                if element.isActive():
                    self.emitTo(addEvent, listener, element)
        else:
            assert isinstance(value, ProxyElement)
            if value.isActive():
                self.emitTo(addEvent, listener, value)
    
    def _addProxyState(self, factory, attr, idfunc, addEvent, 
                       *args, **kwargs):
        """
        Utility method to add a proxy in a dict
        handling asynchronous initialization, activation,
        event broadcasting and obsolescence.                 
        """
        identifier = idfunc(*args, **kwargs)
        finalDict = self.__getAttrValue(attr)
        assert isinstance(finalDict, dict)
        assert not (identifier in finalDict)
        element = factory.instantiate(self, self, identifier, *args, **kwargs)
        assert isinstance(element, ProxyElement)
        self.__addPending(attr, identifier, element)
        d = element.initialize()
        d.addCallbacks(self.__cbDictElementInitialized,
                       self.__ebDictElementInitFailed,
                       callbackArgs=(addEvent, attr),
                       errbackArgs=(element, attr))
        return identifier
        
    def _removeProxyState(self, attr, idfunc, removeEvent, *args, **kwargs):
        """
        Utility method to remove a proxy from a dict 
        handling asynchronous initialization, activation,
        event broadcasting and obsolescence.
        """
        identifier = idfunc(*args, **kwargs)
        values = self.__getAttrValue(attr)
        assert isinstance(values, dict)
        assert (identifier in values)
        pending = self.__getPending(attr, identifier)
        if pending:
            assert isinstance(pending, ProxyElement)
            #Element is beeing initialized
            pending.setObsolete()
        else:
            if identifier in values:
                element = values.pop(identifier)
                # Do not assume the retrieved dict is a reference
                self.__setAttrValue(attr, values)
                assert isinstance(element, ProxyElement)
                element._removed()
                self.emit(removeEvent, element)
                self._onElementRemoved(element)
            else:
                self._onElementNotFound(identifier)
        return identifier

    def _setProxyState(self, factory, attr, idfunc, 
                       unsetEvent, setEvent, *args, **kwargs):
        """
        Utility method to set proxy handling
        asynchronous initialization, activation,
        event broadcasting and obsolescence.
        """
        identifier = idfunc(*args, **kwargs)
        current = self.__getAttrValue(attr)
        if current:
            assert isinstance(current, ProxyElement)
            self.__setAttrValue(attr, None)
            current._removed()
            self.emit(unsetEvent, current)
        pending = self.__getPending(attr, identifier)
        if pending:
            assert isinstance(pending, ProxyElement)
            #The element is beeing initialized
            pending.setObsolete()
        if identifier:
            element = factory.instantiate(self, self, identifier, 
                                          *args, **kwargs)
            assert isinstance(element, ProxyElement)
            self.__addPending(attr, identifier, element)
            d = element.initialize()
            d.addCallbacks(self.__cbElementInitialized,
                           self.__ebElementInitFailed,
                           callbackArgs=(setEvent, attr),
                           errbackArgs=(element, attr))            
        return identifier

    def _removeProxies(self, attr, removeEvent):
        """
        Utility method to remove proxies.
        The parameteres are attribute names of proxy or dict of proxy.
        """
        value = self.__getAttrValue(attr)
        if not value: return
        if isinstance(value, dict):
            for element in value.values():
                assert isinstance(element, ProxyElement)
                element._removed()
                self.emit(removeEvent, element)
        else:
            assert isinstance(value, ProxyElement)
            value._removed()
            self.emit(removeEvent, value)
    
    def _discardProxies(self, *args):
        """
        Utility method to discard proxies.
        The parameteres are attribute names of proxy or dict of proxy.
        """
        for attr in args:
            self.__discardPendings(attr)
            value = self.__getAttrValue(attr)
            if not value: continue
            if isinstance(value, dict):
                value.clear()
                # Do not assume the retrieved dict is a reference
                self.__setAttrValue(attr, value)
            else:
                self.__setAttrValue(attr, None)
        

    ## Private Methods ##
    
    def __getAttrValue(self, attr, default=None):
        """
        Handle waiters.IWaiters instances.
        """
        value = getattr(self, attr, default)
        if waiters.IWaiters.providedBy(value):
            return value.getValue()
        return value
    
    def __setAttrValue(self, attr, value):
        """
        Handle waiters.IWaiters instances.
        """
        current = getattr(self, attr, None)
        if waiters.IWaiters.providedBy(current):
            current.setValue(value)
        else:
            setattr(self, attr, value)

    def __addPending(self, attr, identifier, element):
        self._pendingElements.setdefault(attr, {})[identifier] = element
        
    def __removePending(self, attr, identifier, element):
        pe = self._pendingElements.get(attr, None)
        if pe and (identifier in pe) and pe[identifier] == element:
            del pe[identifier]
            
    def __getPending(self, attr, identifier):
        pe = self._pendingElements.get(attr, None)
        if pe and (identifier in pe):
            return pe[identifier]
        return None

    def __discardPendings(self, attr):
        if attr in self._pendingElements:
            del self._pendingElements[attr]

    def __cbDictElementInitialized(self, element, addEvent, attr):
        identifier = element.getIdentifier()
        name = "%s '%s'" % (element.__class__.__name__, element.getLabel())
        self.debug("%s initialized", name)
        values = self.__getAttrValue(attr)
        # Remove the pending reference if it's for the same element
        self.__removePending(attr, identifier, element)
        if element.isObsolete():
            msg = "%s obsolete before initialization over" % name
            self.debug("%s", msg)
            error = errors.HandledTranscoderError(msg)
            element._abort(errors.HandledTranscoderFailure(error))
            element._discard()
        else:
            values[identifier] = element
            # Do not assume the retrieved dict is a reference
            self.__setAttrValue(attr, values)
            self._onElementInitialized(element)
            #Send event when the element has been activated
            d = element.waitActive()
            d.addCallbacks(self.__cbElementActivated, 
                           self.__ebElementAborted,
                           callbackArgs=(addEvent, attr), 
                           errbackArgs=(element, addEvent, attr))
            #Activate the new element
            element._activate()
            #Keep the callback chain result
            return element
    
    def __ebDictElementInitFailed(self, failure, element, attr):
        identifier = element.getIdentifier()
        log.notifyFailure(self, failure, 
                          "%s '%s' failed to initialize; dropping it",
                          element.__class__.__name__, element.getLabel())
        # Remove the pending reference if it's for the same element
        self.__removePending(attr, identifier, element)
        self._onElementInitFailed(element, failure)
        element._abort(failure)
        element._discard()
        #Don't propagate failures, will be dropped anyway
        return
    
    def __cbElementInitialized(self, element, setEvent, attr):
        identifier = element.getIdentifier()
        name = "%s '%s'" % (element.__class__.__name__, element.getLabel())
        self.debug("%s initialized", name)
        # Remove the pending reference if it's for the same element
        self.__removePending(attr, identifier, element)
        if element.isObsolete():
            msg = "%s obsolete before initialization over" % name
            self.debug("%s", msg)
            error = errors.HandledTranscoderError(msg)
            element._abort(errors.HandledTranscoderFailure(error))
            element._discard()
        else:
            self.__setAttrValue(attr, element)
            self._onElementInitialized(element)
            #Send event when the element has been activated
            d = element.waitActive()
            d.addCallbacks(self.__cbElementActivated,
                           self.__ebElementAborted,
                           callbackArgs=(setEvent, attr), 
                           errbackArgs=(element, setEvent, attr))
            #Activate the new element
            element._activate()
            #Keep the callback chain result
            return element
    
    def __ebElementInitFailed(self, failure, element, attr):
        identifier = element.getIdentifier()
        log.notifyFailure(self, failure, 
                          "%s '%s' failed to initialize; dropping it",
                          element.__class__.__name__, element.getLabel())
        # Remove the pending reference if it's for the same element
        self.__removePending(attr, identifier, element)
        self._onElementInitFailed(element, failure)
        element._abort(failure)
        element._discard()
        #Don't propagate failures, will be dropped anyway
        return

    def __cbElementActivated(self, element, event, attr):
        self.emit(event, element)
        self._onElementActivated(element)
        
    def __ebElementAborted(self, failure, element, event, attr):
        self.log("Event %s aborted", event)
        self._onElementAborted(element, failure)



class RootProxy(ProxyElement):
    
    def __init__(self, logger, identifier=None, name=None, label=None):
        identifier = identifier or self.__class__.__name__
        ProxyElement.__init__(self, logger, None,
                              identifier=identifier, name=name, label=label)


class BaseProxy(ProxyElement):
    
    implements(IBaseProxy)
    
    def __init__(self, logger, parentPxy, identifier, managerPxy, name=None, label=None):
        ProxyElement.__init__(self, logger, parentPxy, identifier, name, label)
        assert IProxyElement.providedBy(managerPxy) 
        self._managerPxy = managerPxy
        
    def getManagerProxy(self):
        return self._managerPxy
    
    
