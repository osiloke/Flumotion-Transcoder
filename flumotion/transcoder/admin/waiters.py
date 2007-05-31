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

from flumotion.transcoder.admin.errors import OperationTimedOutError
from flumotion.transcoder.admin.errors import WaiterError


class BaseWaiter(object):
    
    def __init__(self):
        self._waiters = {} # {Deferred: IDelayedCall}
        
    ## Protected Methods ##
        
    def _wait(self, timeout=None):
        d = defer.Deferred()
        c = None
        if timeout:
            c = reactor.callLater(timeout, self.__waitTimeout, d)
        self._waiters[d] = c
        return d
    
    def _fireCallbacks(self, result=None):
        for d, c in self._waiters.iteritems():
            if c: c.cancel()
            d.callback(result)
        self._waiters.clear()
        
    def _fireErrbacks(self, error):
        for d, c in self._waiters.iteritems():
            if c: c.cancel()
            d.errback(error)
        self._waiters.clear()


    ## Private Methods ##
    
    def __waitTimeout(self, failure, d):
        self._waiter.pop(d)
        d.errback(OperationTimedOutError("Waiter Timeout"))


class SimpleWaiter(BaseWaiter):
    """
    Wait for a value to be not None or empty.
    """

    def __init__(self, value=None):
        BaseWaiter.__init__(self)
        self._value = value
        
    def wait(self, timeout=None):
        if self._value:
            return defer.succeed(self._value)
        return self._wait(timeout)
    
    def setValue(self, value):
        self._value = value
        if self._value:
            self._fireCallbacks(value)
    
    def getValue(self):
        return self._value
    

class CounterWaiter(BaseWaiter):
    """
    This waiter have a counter and a target value.
    The counter can be incremented and decremented,
    and when its value match the target value, 
    the deferred are fired.
    The target value can be changed at any moment.
    """
    
    def __init__(self, target=0, counter=0, result=None):
        BaseWaiter.__init__(self)
        self._target = target
        self._counter = counter
        self._result = result
        
    def wait(self, timeout=None):
        if self._target == self._counter:
            return defer.succeed(self._result)
        return self._wait(timeout)
    
    def inc(self):
        self._counter += 1
        self.__checkCounter()
        
    def dec(self):
        self._counter -= 1
        self.__checkCounter()
        
    def setCounter(self, counter):
        self._counter = counter
        self.__checkCounter()
        
    def getCounter(self):
        return self._counter
    
    def getTarget(self):
        return self._target
    
    def setTarget(self, target):
        self._target = target
        self.__checkCounter()

        
    ## Private Methods ##

    def __checkCounter(self):
        if self._counter == self._target:
            self._fireCallbacks(self._result)


class ValueWaiter(object):
    """
    This class allow others to wait for a value.
    The wait method returns a Deferred wich callback
    and errback will be fired when the value is set to specified 
    list of good and wrong values.
    if values is empty or None, any change will trigger the callback
    if the new value is not in wrongValues.
    """
    
    def __init__(self, value=None):
        self._value = value
        self._any = {} # {Deferred: (IDelayedCall, [goodValues], [wrongValues])}
        self._good = {} # {value: {Deferred: (IDelayedCall, [goodValues], [wrongValues])}}
        self._bad = {} # {value: {Deferred: (IDelayedCall, [goodValues], [wrongValues])}}
      
    ## Public Methods ##  
    
    def wait(self, goodValues=None, wrongValues=None, timeout=None):
        if wrongValues and (self._value in wrongValues):
            error = WaiterError("Unexpected value '%s'" 
                                % str(self._value))
            return defer.fail(error)
        if goodValues and (self._value in goodValues):
            return defer.succeed(self._value)
        d = defer.Deferred()
        to = None
        if timeout:
            to = reactor.callLater(timeout, self.__waitTimeout, d, 
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
        if to:
            to.cancel()
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

    def __waitTimeout(self, failure, d, goodValues, wrongValues):
        self._removeWaiter(d, None, goodValues, wrongValues)
        d.errback(OperationTimedOutError("Waiter Timeout"))
