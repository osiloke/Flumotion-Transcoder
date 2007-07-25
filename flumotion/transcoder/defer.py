# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import traceback

from twisted.internet import defer, reactor

from flumotion.transcoder import log
from flumotion.transcoder.errors import OperationTimedOutError


## Global parameters setters ##

_notifier = None

def setDebugNotifier(notifier):
    global _notifier
    _notifier = notifier

def setDebugging(on):
    defer.setDebugging(on)


# Proxy some twisted.internet.defer functions and constants

# Functions:
succeed = defer.succeed
fail = defer.fail

#Classes:
DeferredList = defer.DeferredList


class DebugInfo(defer.DebugInfo):

    def __del__(self):
        defer.DebugInfo.__del__(self)
        global _notifier
        if self.failResult and _notifier:
            _notifier("Unhandled error in Deferred", 
                      failure=self.failResult, 
                      debug=self._getDebugTracebacks())
        

class Deferred(defer.Deferred):
    """
    Dirty hack to retrieve lost tracebacks and notify of them.
    """
    
    def __init__(self):
        # Backup debug flag
        debug = self.debug
        # Unset debug flag for parent to not creats its DebugInfo instance
        self.debug = False
        defer.Deferred.__init__(self)
        self.debug = debug
        # Force our instance of DebugInfo to always notify of lost traceback
        self._debugInfo = DebugInfo()
        if debug:
            self._debugInfo.creator = traceback.format_stack()[:-1]


## Utility Callback Functions ##

def delayedSuccess(result, delay):
    """
    Return a deferred wich callback will be called after a specified
    time in second with the specified result.
    """
    d = defer.Deferred()
    reactor.callLater(delay, d.callback, result)
    return d

def delayedFailure(failure, delay):
    """
    Return a deferred wich errback that will be called after a specified
    time in second with the specified result.
    """
    d = defer.Deferred()
    reactor.callLater(delay, d.errback, failure)
    return d

def dropResult(result, callable, *args, **kwargs):
    """
    Simply call a specified callback with specified
    arguments ignoring the received result.
    """
    return callable(*args, **kwargs)

def bridgeResult(result, callable, *args, **kwargs):
    """
    Simply call the given callable, ignore it's result
    and return the old callback result.
    """
    callable(*args, **kwargs)
    return result

def resolveFailure(failure, result, *args):
    """
    Resolve an errorback.
    If the failure's error type is in the specified
    arguments, the specified result is returned,
    otherwise the received failure is passed down. 
    If no error type are specified, all failure 
    will be resolved.
    """
    if (not args) or failure.check(args):
        return result
    return failure

def overrideResult(result, newResult):
    return newResult

def shiftResult(result, callable, index, *args, **kwargs):
    new = list(args)
    new.insert(index, result)
    return callable(*new, **kwargs)

def logFailures(result, logger, newResult, taskDesc):
    for succeed, failure in result:
        if not succeed:
            log.notifyFailure(logger, failure, "Failure during %s", taskDesc)
    return newResult

