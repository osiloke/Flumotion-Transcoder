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
from twisted.internet import defer, reactor

from flumotion.transcoder import utils
from flumotion.transcoder.admin.errors import OperationTimedOutError
from flumotion.transcoder.admin.errors import WaiterError


class IWaiters(Interface):
    
    def isWaiting(self):
        pass
    
    def hasWaiter(self):
        pass
    
    def setValue(self, value):
        pass
    
    def getValue(self, value):
        pass
    
    def wait(self, timeout=None):
        pass
    

class BaseWaiters(object):
    
    def __init__(self, message=None):
        self._waiters = {} # {Deferred: IDelayedCall}
        self._timeoutMessage = message
        
    ## Protected Methods ##
        
    def wait(self, timeout=None):
        d = defer.Deferred()
        to = utils.createTimeout(timeout, self.__asyncWaitTimeout, d)
        self._waiters[d] = to
        return d
    
    def hasWaiter(self):
        return len(self._waiters) > 0
    
    def _fireCallbacks(self, result=None):
        for d, to in self._waiters.iteritems():
            utils.cancelTimeout(to)
            d.callback(result)
        self._waiters.clear()
        
    def _fireErrbacks(self, error):
        for d, to in self._waiters.iteritems():
            utils.cancelTimeout(to)
            d.errback(error)
        self._waiters.clear()


    ## Private Methods ##
    
    def __asyncWaitTimeout(self, d):
        self._waiters.pop(d)
        message = self._timeoutMessage or "Waiter Timeout"
        err = OperationTimedOutError(message)
        d.errback(err)


class PassiveWaiters(BaseWaiters):
    
    def __init__(self, message=None):
        BaseWaiters.__init__(self, message)
        self.fireCallbacks = self._fireCallbacks
        self.fireErrbacks = self._fireErrbacks
    

class AssignWaiters(BaseWaiters):
    """
    Wait for a value to be not None or empty.
    """
    
    implements(IWaiters)

    def __init__(self, value=None, message=None):
        BaseWaiters.__init__(self, message)
        self._value = value
        
    def isWaiting(self):
        if self._value:
            return False
        return True
        
    def wait(self, timeout=None):
        if self.isWaiting():
            return BaseWaiters.wait(self, timeout)
        return defer.succeed(self._value)
    
    def setValue(self, value):
        self._value = value
        if self._value:
            self._fireCallbacks(value)
    
    def getValue(self):
        return self._value
    

class CounterWaiters(BaseWaiters):
    """
    This waiter have a counter and a target value.
    The counter can be incremented and decremented,
    and when its value match the target value, 
    the deferred are fired.
    The target value can be changed at any moment.
    """
    
    implements(IWaiters)
    
    def __init__(self, target=0, counter=0, result=None, message=None):
        BaseWaiters.__init__(self, message)
        self._target = target
        self._counter = counter
        self._result = result
        
    def isWaiting(self):
        return self._target != self._counter
        
    def wait(self, timeout=None):
        if self.isWaiting():
            return BaseWaiters.wait(self, timeout)
        return defer.succeed(self._result)
    
    def inc(self):
        self._counter += 1
        self.__checkCounter()
        
    def dec(self):
        self._counter -= 1
        self.__checkCounter()
        
    def incTarget(self):
        self._target += 1
        self.__checkCounter()
        
    def decTarget(self):
        self._target -= 1
        self.__checkCounter()
        
    def setValue(self, counter):
        self._counter = counter
        self.__checkCounter()
        
    def getValue(self):
        return self._counter
    
    def getTarget(self):
        return self._target
    
    def setTarget(self, target):
        self._target = target
        self.__checkCounter()

        
    ## Private Methods ##

    def __checkCounter(self):
        if not self.isWaiting():
            self._fireCallbacks(self._result)


class ValueWaiters(object):
    """
    This class allow others to wait for a value.
    The wait method returns a Deferred wich callback
    and errback will be fired when the value is set to specified 
    list of good and wrong values.
    if values is empty or None, any change will trigger the callback
    if the new value is not in wrongValues.
    """
    
    implements(IWaiters)
    
    def __init__(self, value=None):
        self._value = value
        self._any = {} # {Deferred: (IDelayedCall, [goodValues], [wrongValues])}
        self._good = {} # {value: {Deferred: (IDelayedCall, [goodValues], [wrongValues])}}
        self._bad = {} # {value: {Deferred: (IDelayedCall, [goodValues], [wrongValues])}}
      
    ## Public Methods ##  
    
    def hasWaiter(self):
        return (len(self._any) > 0) or (len(self._good) > 0) or (len(self._bad) > 0)
    
    def isWaiting(self):
        return True
    
    def wait(self, goodValues=None, wrongValues=None, timeout=None):
        if wrongValues and (self._value in wrongValues):
            error = WaiterError("Unexpected value '%s'" 
                                % str(self._value))
            return defer.fail(error)
        if goodValues and (self._value in goodValues):
            return defer.succeed(self._value)
        d = defer.Deferred()
        to = utils.createTimeout(timeout, self.__asyncWaitTimeout, d, 
                                 goodValues, wrongValues)
        self.__addWaiter(d, to, goodValues, wrongValues)
        return d
    
    def setValue(self, value):
        if self._value != value:
            self._value = value
            if value in self._bad:
                items = self._bad[value].items()
                error = WaiterError("Unexpected value '%s'" % str(value))
                for d, (to, good, wrong) in items:
                    self.__removeWaiter(d, to, good, wrong)
                    d.errback(error)
            items = self._any.items()
            for d, (to, good, wrong) in items:
                self.__removeWaiter(d, to, good, wrong)
                d.callback(value)
            if value in self._good:
                items = self._good[value].items()
                for d, (to, good, wrong) in items:
                    self.__removeWaiter(d, to, good, wrong)
                    d.callback(value)
    
    def getValue(self):
        return self._value
    
    ## PRivate Methods ##
    
    def __addWaiter(self, d, to, goodValues, wrongValues):
        data = (to, goodValues, wrongValues)
        if goodValues:
            for v in goodValues:
                self._good.setdefault(v, {})[d] = data
        else:
            self._any[d] = data
        if wrongValues:
            for v in wrongValues:
                self._bad.setdefault(v, {})[d] = data
        
    def __removeWaiter(self, d, to, goodValues, wrongValues):
        utils.cancelTimeout(to)
        if wrongValues:
            for v in wrongValues:
                del self._bad[v][d]
                if not self._bad[v]:
                    del self._bad[v] 
        if goodValues:
            for v in goodValues:
                del self._good[v][d]
                if not self._good[v]:
                    del self._good[v] 
        else:
            del self._any[d]

    def __asyncWaitTimeout(self, d, goodValues, wrongValues):
        self.__removeWaiter(d, None, goodValues, wrongValues)
        d.errback(OperationTimedOutError("Waiter Timeout"))
