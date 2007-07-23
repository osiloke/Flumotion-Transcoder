# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from twisted.internet import reactor
from twisted.python.failure import Failure

from flumotion.transcoder import log, defer, utils
from flumotion.transcoder.log import LoggerProxy
from flumotion.transcoder.admin import eventsource
from flumotion.transcoder.admin import datasource
from flumotion.transcoder.admin.waiters import PassiveWaiters
from flumotion.transcoder.admin.waiters import CounterWaiters


class AdminElement(eventsource.EventSource, LoggerProxy):
    """
    Manage element activation and initialization.
    Ensure that the activation deferreds are called 
    after the element and its parents have been activated.
    The generic waiting defered are separated from childs
    to respect callback orders: The deferreds got by calling waitActive()
    are garenteed to be triggered before the child's ones.
    An element is activated after beeing published by its parent.
    The concept is: The element are created, initialized and then
    if all whent well they are added to the parent list and activated,
    or if something when wrong, they are aborted.
    This class trac an activation counter to know if it's in a stable state
    (No pending initialization/activation). The child class are in charge
    of setting the idle target value and be sure to activate 
    or abort all elements.
    """
    
    def __init__(self, logger, parent, interfaces):
        assert (parent == None) or isinstance(parent, AdminElement)
        eventsource.EventSource.__init__(self, interfaces)
        LoggerProxy.__init__(self, logger)
        self._activeWaiters = PassiveWaiters("Element Activation")
        self._activeChildWaiters = PassiveWaiters("Element Child Activation")
        self._triggered = False
        self._active = False
        self._failure = None
        self._parent = parent
        self._obsolete = False
        self._beingRemoved = False
        self._idleWaiters = CounterWaiters("Element Idle", 0, 0, self)


    ## Public Methods ##
    
    def getLabel(self):
        raise NotImplementedError()
    
    def getIdentifier(self):
        raise NotImplementedError()
    
    def getParent(self):
        return self._parent
    
    def isIdle(self):
        return not self._idleWaiters.isWaiting()
    
    def waitIdle(self, timeout=None):
        """
        Wait for all pending elements to be activated or aborted,
        and then all child elements to become idle too.
        """
        if self.isIdle():
            d = defer.succeed(self)
        else:
            d = self._idleWaiters.wait(timeout)
        d.addCallback(self.__cbWaitChildIdle, timeout)
        return d

    def initialize(self):
        self.log("Initializing %s", self.__class__.__name__)
        if self._parent == None:
            self._activate()
        chain = defer.Deferred()
        self._doPrepareInit(chain)
        chain.addCallbacks(self.__cbInitializationSucceed, 
                           self.__ebInitializationFailed)
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
    
    def waitActive(self, timeout=None):
        """
        Gives a deferred that will be called when the element
        has been activated (added)
        """
        if self._active:
            return defer.succeed(self)
        if self._failure:
            return defer.fail(self._failure)        
        return self._activeWaiters.wait(timeout)

    
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
    
    def _doGetChildElements(self):
        """
        Used to retrieve sub elements when waiting for idle state.
        """
        return []
    
    
    ## Protected/Friend Method ##
    
    def _setIdleTarget(self, value):
        self._idleWaiters.setTarget(value)
    
    def _incIdlTarget(self):
        self._idleWaiters.incTarget()
        
    def _decIdlTarget(self):
        self._idleWaiters.decTarget()
    
    def _childElementActivated(self):
        self._idleWaiters.inc()
        
    def _childElementRemoved(self):
        self._idleWaiters.dec()

    def _childElementAborted(self):
        self._idleWaiters.decTarget()
    
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
        if self._parent:
            self._parent._childElementRemoved()
        
        
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
        chain.addCallbacks(self.__cbParentActivated,
                           self.__ebParentAborted)
                
    def _abort(self, failure):
        """
        Called when the element couldn't be added due to error.
        """
        assert not self._triggered
        self._triggered = True
        if not isinstance(failure, Failure):
            failure = Failure(failure)
        self.log("Start %s abortion for %s",
                 self.__class__.__name__,
                 log.getFailureMessage(failure))
        #Don't wait for parent when aborting
        self.__ebParentAborted(failure)


    def _fireEventWhenActive(self, payload, event, interface=None):
        """
        Fire an event on payload activation.
        """
        assert isinstance(payload, AdminElement)
        d = payload.waitActive()
        d.addCallbacks(self._fireEvent, 
                       self.__ebEventAborted,
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
                       self.__ebEventAborted,
                       callbackArgs=(listener, event, interface),
                       errbackArgs=(event,))
        d.addErrback(self._unexpectedError)

    def _childWaitActive(self, timeout=None):
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
        return self._activeChildWaiters.wait(timeout)
    
    def _unexpectedError(self, failure):
        """
        Prevents the lost of failure messages.
        Can be use by all child classes when adding
        a callback that is not expected to fail.
        """
        self.logFailure(failure, "Unexpected Failure")
        #Resolve the failure.
        return


    ## Private Methods ##
    
    def __cbWaitChildIdle(self, element, timeout):
        childs = self._doGetChildElements()
        if not childs: return element
        defs = [c.waitIdle(timeout) for c in childs]
        d = defer.DeferredList(defs, 
                               fireOnOneCallback=False,
                               fireOnOneErrback=False, 
                               consumeErrors=True)
        d.addCallback(self.__cbLogFailures, self)
        return d
    
    def __cbLogFailures(self, results, newResult):
        for succeed, result in results:
            if not succeed:
                self.logFailure(result, "Failure waiting for element '%s' "
                                "to become idle", self.getLabel())
        return newResult
    
    def __cbInitializationSucceed(self, result):
        self.log("%s successfully initialized", 
                 self.__class__.__name__)
        self._onInitDone()
        #The initialisation chain return the initialized object on success
        return self
    
    def __ebInitializationFailed(self, failure):
        #FIXME: Better Error Handling
        self.log("%s initialization failed: %s",
                 self.__class__.__name__,
                 log.getFailureMessage(failure))
        self._onInitFailed(failure)
        #Propagate failures
        return failure
    
    def __ebEventAborted(self, failure, event):
        self.log("Event %s aborted", event)
        return

    def __cbParentActivated(self, parent):
        self._doFinishActivation()
        self._failure= None
        self.log("%s successfully activated", self.__class__.__name__)
        self._active = True
        self._activeWaiters.fireCallbacks(self)
        self._onActivated()
        self._activeChildWaiters.fireCallbacks(self)
        if self._parent:
            self._parent._childElementActivated()
                
    def __ebParentAborted(self, failure):
        self._failure = failure
        self._active = False
        self.log("%s activation failed: %s",
                 self.__class__.__name__,
                 log.getFailureMessage(failure))
        self._activeWaiters.fireErrbacks(failure)
        self._onAborted(failure)
        self._activeChildWaiters.fireErrbacks(failure)
        if self._parent:
            self._parent._childElementAborted()
