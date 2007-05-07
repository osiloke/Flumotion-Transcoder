# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.transcoder import log
from flumotion.transcoder.errors import HandledTranscoderFailure
from flumotion.transcoder.errors import HandledTranscoderError
from flumotion.transcoder.admin import adminelement


class BaseFlumotionProxy(adminelement.AdminElement):
    
    def __init__(self, logger, parent, identifier, listenerInterface):
        adminelement.AdminElement.__init__(self, logger, parent, 
                                           listenerInterface)
        self._identifier = identifier


    ## Public Methods ##

    def getIdentifier(self):
        return self._identifier

    def getName(self):
        return self._identifier
    
    
    ## Virtual Methods ##
    def _onElementInitialized(self, element):
        pass
    
    def _onElementInitFailed(self, element, failure):
        pass
    
    def _onElementActivated(self, element):
        pass
    
    def _onElementAborted(self, element, failure):
        pass
    

    ## Overriden Methods ##
    
    def _doPrepareInit(self, chain):
        #FIXME: Remove this, its only for testing
        from twisted.internet import reactor, defer
        def async(result):
            d = defer.Deferred()
            reactor.callLater(0.2, d.callback, result)
            return d
        chain.addCallback(async)
        
    def _doPrepareActivation(self, chain):
        #FIXME: Remove this, its only for testing
        from twisted.internet import reactor, defer
        def async(result):
            d = defer.Deferred()
            reactor.callLater(0.2, d.callback, result)
            return d
        chain.addCallback(async)


    ## Protected Methods ##
    
    def _syncProxies(self, attr, listener, addEvent):
        """
        Utility method to synchronize a listener. 
        """
        value = getattr(self, attr, None)
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
        finalDict = getattr(self, attr)
        assert isinstance(finalDict, dict)
        pendingName = attr + "Pending"
        if not hasattr(self, pendingName):
            setattr(self, pendingName, dict())
        pendingDict = getattr(self, pendingName)
        assert isinstance(pendingDict, dict)
        assert not (identifier in finalDict)
        element = factory.instantiate(self, self, identifier, *args, **kwargs)
        assert isinstance(element, BaseFlumotionProxy)        
        pendingDict[identifier] = element
        d = element.initialize()
        d.addCallbacks(self.__dictElementInitialized,
                       self.__dictElementInitFailed,
                       callbackArgs=(addEvent, pendingDict, finalDict),
                       errbackArgs=(element, pendingDict))
        
    def _removeProxyState(self, attr, idfunc, removeEvent, *args, **kwargs):
        """
        Utility method to remove a proxy from a dict 
        handling asynchronous initialization, activation,
        event broadcasting and obsolescence.
        """
        identifier = idfunc(*args, **kwargs)
        finalDict = getattr(self, attr)
        assert isinstance(finalDict, dict)
        pendingName = attr + "Pending"
        if not hasattr(self, pendingName):
            setattr(self, pendingName, dict())
        pendingDict = getattr(self, pendingName)
        assert isinstance(pendingDict, dict)
        assert ((identifier in finalDict) or (identifier in pendingDict))
        if identifier in pendingDict:
            assert isinstance(pendingDict[identifier], FlumotionProxy)
            #Element is beeing initialized
            pendingDict[identifier].setObsolete()
        else:
            element = finalDict.pop(identifier)
            assert isinstance(element, BaseFlumotionProxy)
            element._removed()
            self._fireEvent(element, removeEvent)

    def _setProxyState(self, factory, attr, idfunc, 
                       unsetEvent, setEvent, *args, **kwargs):
        """
        Utility method to set proxy handling
        asynchronous initialization, activation,
        event broadcasting and obsolescence.
        """
        identifier = idfunc(*args, **kwargs)
        pendingAttr = attr + "Pending"
        current = getattr(self, attr, None)
        pending = getattr(self, pendingAttr, None)
        if current:
            assert isinstance(current, BaseFlumotionProxy)
            setattr(self, "attr", None)
            current._removed()
            self._fireEvent(current, unsetEvent)
        if pending:
            assert isinstance(pending, BaseFlumotionProxy)
            #The element is beeing initialized
            pending.setObsolete()
        if identifier:
            element = factory.instantiate(self, self, identifier, 
                                          *args, **kwargs)
            assert isinstance(element, BaseFlumotionProxy)
            setattr(self, pendingAttr, element)
            d = element.initialize()
            d.addCallbacks(self.__elementInitialized,
                           self.__elementInitFailed,
                           callbackArgs=(setEvent, attr, pendingAttr),
                           errbackArgs=(element, pendingAttr))

    def _removeProxies(self, attr, removeEvent):
        """
        Utility method to remove proxies.
        The parameteres are attribute names of proxy or dict of proxy.
        """
        value = getattr(self, attr, None)
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
            pendingAttr = attr + "Pending"
            value = getattr(self, attr, None)
            if not value: continue
            if isinstance(value, dict):
                pending = getattr(self, pendingAttr, None)
                if pending:
                    assert isinstance(pending, dict)
                    pending.clear()
                value.clear()
            else:
                setattr(self, pendingAttr, None)
                setattr(self, attr, None)
        

    ## Private Methods ##

    def __dictElementInitialized(self, element, addEvent, pendingDict, finalDict):
        identifier = element.getIdentifier()
        name = "%s '%s'" % (element.__class__.__name__, element.getName())
        self.debug("%s initialized", name)
        # Remove the pending reference if it's for the same element
        if pendingDict[identifier] == element:
            del pendingDict[identifier]
        if element.isObsolete():
            msg = "%s obsolete before initialization over" % name
            self.debug(msg)
            error = HandledTranscoderError(msg)
            element._abort(HandledTranscoderFailure(error))
            element._discard()
        else:
            finalDict[identifier] = element
            self._onElementInitialized(element)
            #Send event when the element has been activated
            d = element.waitActive()
            d.addCallbacks(self.__elementActivated, self.__elementAborted,
                           callbackArgs=(addEvent,), 
                           errbackArgs=(element, addEvent))
            #Activate the new element
            element._activate()        
            #Keep the callback chain result
            return element
    
    def __dictElementInitFailed(self, failure, element, pendingDict):
        identifier = element.getIdentifier()
        name = "%s '%s'" % (element.__class__.__name__, element.getName())
        self.warning("%s failed to initialize; dropping it: %s", 
                     name, log.getFailureMessage(failure))
        self.debug("Traceback of %s failure:\n%s" 
                   % (name, log.getFailureTraceback(failure)))
        # Remove the pending reference if it's for the same element
        if pendingDict[identifier] == element:
            del pendingDict[identifier]
        self._onElementInitFailed(element, failure)
        element._abort(failure)
        element._discard()
        #Don't propagate failures, will be dropped anyway
        return
    
    def __elementInitialized(self, element, setEvent, attr, pendingAttr):
        pending = getattr(self, pendingAttr, None)
        name = "%s '%s'" % (element.__class__.__name__, element.getName())
        self.debug("%s initialized", name)
        # Remove the pending reference if it's for the same element
        if pending == element:
            setattr(self, pendingAttr, None)
        if element.isObsolete():
            msg = "%s obsolete before initialization over" % name
            self.debug(msg)
            error = HandledTranscoderError(msg)
            element._abort(HandledTranscoderFailure(error))
            element._discard()
        else:
            setattr(self, attr, element)
            self._onElementInitialized(element)
            #Send event when the element has been activated
            d = element.waitActive()
            d.addCallbacks(self.__elementActivated, self.__elementAborted,
                           callbackArgs=(setEvent,), 
                           errbackArgs=(element, setEvent))
            #Activate the new element
            element._activate()        
            #Keep the callback chain result
            return element
    
    def __elementInitFailed(self, failure, element, pendingAttr):
        pending = getattr(self, pendingAttr, None)
        name = "%s '%s'" % (element.__class__.__name__, element.getName())
        self.warning("%s failed to initialize; dropping it: %s", 
                     name, log.getFailureMessage(failure))
        self.debug("Traceback of %s failure:\n%s" 
                   % (name, log.getFailureTraceback(failure)))
        # Remove the pending reference if it's for the same element
        if pending == element:
            setattr(self, pendingAttr, None)
        self._onElementInitFailed(element, failure)
        element._abort(failure)
        element._discard()
        #Don't propagate failures, will be dropped anyway
        return

    def __elementActivated(self, element, event):
        self._fireEvent(element, event)
        self._onElementActivated(element)
        
    def __elementAborted(self, failure, element, event):
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
        
    
    
