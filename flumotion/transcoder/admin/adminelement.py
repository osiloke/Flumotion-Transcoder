# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from twisted.internet import defer

from flumotion.twisted.compat import implementsInterface
from flumotion.transcoder import log
from flumotion.transcoder.log import LoggerProxy
from flumotion.transcoder.eventsource import EventSource
from flumotion.transcoder.admin import datasource


class AdminElement(EventSource, LoggerProxy):
    """
    Manage element activation and initialization.
    Ensure that the activation deferreds are called 
    after the element and its parents have been activated.
    The generic waiting defered are separated from childs
    to respect callback orders: The deferreds got by calling waitActive()
    are garentee to be triggered before the child's ones.
    An element is activated after beeing published by its parent.
    The concept is: The element are created, initialized and then
    if all whent well they are added to the parent list and activated,
    or if something when wrong, they are aborted.    
    """
    
    def __init__(self, logger, parent, interfaces):
        assert (parent == None) or isinstance(parent, AdminElement)
        EventSource.__init__(self, interfaces)
        LoggerProxy.__init__(self, logger)
        self._waitForActivation = []
        self._waitingChilds = []
        self._triggered = False
        self._active = False
        self._failure = None
        self._parent = parent
        self._obsolete = False
        self._beingRemoved = False


    ## Public Methods ##
    
    def getParent(self):
        return self._parent

    def initialize(self):
        self.log("Initializing %s", self.__class__.__name__)
        if self._parent == None:
            self._activate()
        chain = defer.Deferred()
        self._doPrepareInit(chain)
        chain.addCallbacks(self.__initializationSucceed, 
                           self.__initializationFailed)
        chain.callback(self)
        return chain
    
    def setObsolete(self):
        """
        Set when an element is made obsolete 
        before the initialization terminate.
        """
        self._obsolete = True
        
    def isObsolete(self):
        return self._obsolete
    
    def isActive(self):
        return self._active
    
    def waitActive(self):
        """
        Gives a deferred that will be called when the element
        has been activated (added)
        """
        if self._active:
            return defer.succeed(self)
        if self._failure:
            return defer.fail(self._failure)        
        d = defer.Deferred()
        self._waitForActivation.append(d)
        return d

    
    ## Virtual Methods ##
    
    def _doPrepareInit(self, chain):
        """
        Called during initialization to build the deferred chain 
        for element initialization.
        """
        pass
    
    def _onInitDone(self):
        """
        Called when the initialization has been complete successfully.
        """
        pass
    
    def _onInitFailed(self, failure):
        """
        Called when the initialization failed.
        """
        pass
    
    def _doPrepareActivation(self, chain):
        """
        Called during activation chain setup to add callbacks if needed.
        """
        pass
    
    def _doFinishActivation(self):
        """
        Called when all the parents has been activated
        and before firing any deferred.
        """
    
    def _onActivated(self):
        """
        Called when the element has been activated and all the
        deferred return by waitActive() has been fired.
        """
        pass
    
    def _onAborted(self, failure):
        """
        Called when the element activation failed.
        """
        pass
    
    def _onRemoved(self):
        """
        Override to send removed events and propagate
        the action to owned elements.
        """
        pass
    
    def _doDiscard(self):
        """
        Override to cleanup element.
        """
    
    
    ## Protected/Friend Method ##
    
    def _isBeingRemoved(self):
        """
        May be use by removed element to know if its parent
        is being removed too. It permit to differentiate 
        a normal remove from a cascade removal.
        """
        return self._beingRemoved
    
    def _isParentBeingRemoved(self):
        """
        Helper method that handle root element without parent.
        """
        if self._parent:
            return self._parent._isBeingRemoved()
        return False
    
    def _removed(self):
        """
        Called when the parent removed the element.
        """
        self._beingRemoved = True
        self._onRemoved()
        
    def _discard(self):
        """
        Called when the element is removed,
        or discarded without beeing added first.
        """
        self._doDiscard()
    
    def _activate(self):
        """
        Called when the element has been added to the parent.
        To complete, the element's parent activation 
        must terminat successfully.
        """
        assert not self._triggered
        self._triggered = True
        self.log("Start %s activation", self.__class__.__name__)
        if self._parent:
            chain = self._parent._childWaitActive()
        else:
            chain = defer.succeed(None)
        self._doPrepareActivation(chain)
        chain.addCallbacks(self.__parentActivated,
                           self.__parentAborted)
                
    def _abort(self, failure):
        """
        Called when the element couldn't be added due to error.
        """
        assert not self._triggered
        self._triggered = True
        self.log("Start %s abortion for %s",
                 self.__class__.__name__,
                 log.getFailureMessage(failure))
        #Don't wait for parent when aborting
        self.__parentAborted(failure)


    def _fireEventWhenActive(self, payload, event, interface=None):
        """
        Fire an event on payload activation.
        """
        assert isinstance(payload, AdminElement)
        d = payload.waitActive()
        d.addCallbacks(self._fireEvent, 
                       self.__eventAborted,
                       callbackArgs=(event, interface),
                       errbackArgs=(event,))
        d.addErrback(self._unexpectedError)
        
    def _fireEventWhenActiveTo(self, payload, listener, event, interface=None):
        """
        Fire an event on payload activation to a specific listener.
        """
        assert isinstance(payload, AdminElement)
        d = payload.waitActive()
        d.addCallbacks(self._fireEventTo, 
                       self.__eventAborted,
                       callbackArgs=(listener, event, interface),
                       errbackArgs=(event,))
        d.addErrback(self._unexpectedError)

    def _childWaitActive(self):
        """
        Diffrent than waitActive to ensure calling order.
        First the deffered added with waitActive and then
        the ones added by _childWaitActive.
        Should not be used by child classes, it's realy a private method.
        """
        if self._active:
            return defer.succeed(self)
        if self._failure:
            return defer.fail(self._failure)        
        d = defer.Deferred()
        self._waitingChilds.append(d)
        return d
    
    def _unexpectedError(self, failure):
        """
        Prevents the lost of failure messages.
        Can be use by all child classes when adding
        a callback that is not expected to fail.
        """
        self.warning("Unexpected Failure: %s",
                     log.getFailureMessage(failure))
        self.debug("Traceback of unexpected failure:\n%s" 
                   % log.getFailureTraceback(failure))
        #Resolve the failure.
        return


    ## Private Methods ##
    
    def __initializationSucceed(self, result):
        self.log("%s successfully initialized", 
                 self.__class__.__name__)
        self._onInitDone()
        #The initialisation chain return the initialized object on success
        return self
    
    def __initializationFailed(self, failure):
        #FIXME: Better Error Handling
        self.log("%s initialization failed: %s",
                 self.__class__.__name__,
                 log.getFailureMessage(failure))
        self._onInitFailed(failure)
        #Propagate failures
        return failure
    
    def __eventAborted(self, failure, event):
        self.log("Event %s aborted", event)
        return

    def __parentActivated(self, parent):
        self._doFinishActivation()
        activations = self._waitForActivation
        childs = self._waitingChilds
        self._waitForActivation = None
        self._waitingChilds = None
        self._failure= None
        self.log("%s successfully activated", self.__class__.__name__)
        for d in activations:
            d.callback(self)
        self._onActivated()
        for d in childs:
            d.callback(self)
        self._active = True
                
    def __parentAborted(self, failure):
        activations = self._waitForActivation
        childs = self._waitingChilds
        self._waitForActivation = None
        self._waitingChilds = None
        self._failure = failure
        self._active = False
        self.log("%s activation failed: %s",
                 self.__class__.__name__,
                 log.getFailureMessage(failure))
        for d in activations:
            d.errback(failure)
        self._onAborted(failure)
        for c in childs:
            d.errback(failure)
