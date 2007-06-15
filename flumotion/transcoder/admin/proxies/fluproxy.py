# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from twisted.internet import defer, reactor

from flumotion.transcoder import log
from flumotion.transcoder import utils
from flumotion.transcoder.errors import HandledTranscoderFailure
from flumotion.transcoder.errors import HandledTranscoderError
from flumotion.transcoder.admin import adminelement
from flumotion.transcoder.admin.waiters import IWaiters

#TODO: Rewrite this... It's a mess

class BaseFlumotionProxy(adminelement.AdminElement):
    
    def __init__(self, logger, parent, identifier, listenerInterface):
        adminelement.AdminElement.__init__(self, logger, parent, 
                                           listenerInterface)
        self._identifier = identifier
        self._pendingElements = {} # {attr: {identifier: BaseFlumotionProxy}}


    ## Public Methods ##

    def getIdentifier(self):
        """
        The identifier is unique in a manager context.
        """
        return self._identifier

    def getName(self):
        """
        The name is unique in a component group context (flow and atmosphere)
        """
        return self._identifier
    
    def getLabel(self):
        """
        The label is a description without uniquness constraints.
        By default the label is the name.
        """
        return self.getName()
    

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
        #FIXME: Remove this, its only for testing
        import random
        chain.addCallback(utils.delayedSuccess, random.random())
        
    def _doPrepareActivation(self, chain):
        #FIXME: Remove this, its only for testing
        import random
        chain.addCallback(utils.delayedSuccess, random.random())


    ## Protected Methods ##
    
    def _syncProxies(self, attr, listener, addEvent):
        """
        Utility method to synchronize a listener. 
        """
        value = self.__getAttrValue(attr)
        if not value: return
        if isinstance(value, dict):
            for element in value.values():
                assert isinstance(element, BaseFlumotionProxy)
                if element.isActive():
                    self._fireEventTo(element, listener, addEvent)
        else:
            assert isinstance(value, BaseFlumotionProxy)
            if value.isActive():
                self._fireEventTo(value, listener, addEvent)
    
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
        assert isinstance(element, BaseFlumotionProxy)
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
            assert isinstance(pending, BaseFlumotionProxy)
            #Element is beeing initialized
            pending.setObsolete()
        else:
            if identifier in values:
                element = values.pop(identifier)
                # Do not assume the retrieved dict is a reference
                self.__setAttrValue(attr, values)
                assert isinstance(element, BaseFlumotionProxy)
                element._removed()
                self._fireEvent(element, removeEvent)
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
            assert isinstance(current, BaseFlumotionProxy)
            self.__setAttrValue(attr, None)
            current._removed()
            self._fireEvent(current, unsetEvent)
        pending = self.__getPending(attr, identifier)
        if pending:
            assert isinstance(pending, BaseFlumotionProxy)
            #The element is beeing initialized
            pending.setObsolete()
        if identifier:
            element = factory.instantiate(self, self, identifier, 
                                          *args, **kwargs)
            assert isinstance(element, BaseFlumotionProxy)
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
                assert isinstance(element, BaseFlumotionProxy)
                element._removed()
                self._fireEvent(element, removeEvent)
        else:
            assert isinstance(value, BaseFlumotionProxy)
            value._removed()
            self._fireEvent(value, removeEvent)
    
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
        Handle IWaiters instances.
        """
        value = getattr(self, attr, default)
        if IWaiters.providedBy(value):
            return value.getValue()
        return value
    
    def __setAttrValue(self, attr, value):
        """
        Handle IWaiters instances.
        """
        current = getattr(self, attr, None)
        if IWaiters.providedBy(current):
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
            error = HandledTranscoderError(msg)
            element._abort(HandledTranscoderFailure(error))
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
        name = "%s '%s'" % (element.__class__.__name__, element.getLabel())
        self.warning("%s failed to initialize; dropping it: %s", 
                     name, log.getFailureMessage(failure))
        self.debug("Traceback of %s failure:\n%s",
                   name, log.getFailureTraceback(failure))
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
            error = HandledTranscoderError(msg)
            element._abort(HandledTranscoderFailure(error))
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
        name = "%s '%s'" % (element.__class__.__name__, element.getLabel())
        self.warning("%s failed to initialize; dropping it: %s", 
                     name, log.getFailureMessage(failure))
        self.debug("Traceback of %s failure:\n%s",
                   name, log.getFailureTraceback(failure))
        # Remove the pending reference if it's for the same element
        self.__removePending(attr, identifier, element)
        self._onElementInitFailed(element, failure)
        element._abort(failure)
        element._discard()
        #Don't propagate failures, will be dropped anyway
        return

    def __cbElementActivated(self, element, event, attr):
        self._fireEvent(element, event)
        self._onElementActivated(element)
        
    def __ebElementAborted(self, failure, element, event, attr):
        self.log("Event %s aborted", event)
        self._onElementAborted(element, failure)



class RootFlumotionProxy(BaseFlumotionProxy):
    
    def __init__(self, logger, listenerInterface):
        BaseFlumotionProxy.__init__(self, logger, None, 
                                    self.__class__.__name__,
                                    listenerInterface)



class FlumotionProxy(BaseFlumotionProxy):
    
    def __init__(self, logger, parent, identifier, manager, listenerInterface):
        BaseFlumotionProxy.__init__(self, logger, parent, identifier,
                                    listenerInterface)
        self._manager = manager
        
    def getManager(self):
        return self._manager
    
    
