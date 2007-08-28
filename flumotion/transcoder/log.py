# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import re
import StringIO

from zope.interface import Interface, implements

from twisted.python.failure import Failure

from flumotion.common import log as flog
from flumotion.transcoder import constants
from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.properties import PropertyError

## Global parameters setters ##

logCategory = ""
_notifier = None

def setDebugNotifier(notifier):
    global _notifier
    _notifier = notifier

def setDefaultCategory(category):
    global logCategory
    logCategory = category

def setFluDebug(string):
    flog.setFluDebug(string)
    from flumotion.transcoder import defer
    category = constants.DEFER_LOG_CATEGORY
    defer.setDebugging(getCategoryLevel(category) in [LOG, DEBUG])
        

# Proxy some flumotion.comon.log class, functions and constants
getCategoryLevel = flog.getCategoryLevel

LOG = flog.LOG
DEBUG = flog.DEBUG
INFO = flog.INFO
WARN = flog.WARN
ERROR = flog.ERROR


class ILogger(Interface):
    
    def log(self, *args, **kwargs):
        pass

    def debug(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


## Transcoder's Loggable ##

class Loggable(flog.Loggable):
    
    implements(ILogger)

def notifyFailure(logger, failure, template, *args, **kwargs):
    global _notifier
    info = kwargs.get("info", None)
    debug = kwargs.get("debug", None)
    msg = getFailureMessage(failure)
    if getCategoryLevel(logger.logCategory) in [LOG, DEBUG]:
        cleanup = kwargs.get("cleanTraceback", False)
        tb = getFailureTraceback(failure, cleanup)
        logger.warning(template + ": %s\n%s", *(args + (msg, tb)))
    else:
        logger.warning(template + ": %s", *(args + (msg,)))
    if debug:
        logger.debug("Additional Debug Information:\n%s", debug)
    if _notifier:
       _notifier(template % args, failure=failure, info=info, debug=debug)

def notifyException(logger, exception, template, *args, **kwargs):
    global _notifier
    info = kwargs.get("info", None)
    debug = kwargs.get("debug", None)
    msg = getExceptionMessage(exception)
    if getCategoryLevel(logger.logCategory) in [LOG, DEBUG]:
        cleanup = kwargs.get("cleanTraceback", False)
        tb = getExceptionTraceback(exception, cleanup)
        logger.warning(template + ": %s\n%s", *(args + (msg, tb)))
    else:
        logger.warning(template + ": %s", *(args + (msg,)))
    if debug:
        logger.debug("Additional Debug Information:\n%s", debug)
    if _notifier:
       _notifier(template % args, exception=exception, info=info, debug=debug)

def getExceptionMessage(exception):
    msg = flog.getExceptionMessage(exception)
    if isinstance(exception, PropertyError):
        msg += " [%s:%s]" % (exception.locator, exception.descriptor)
    if isinstance(exception, TranscoderError):
        details = exception.causeDetails
        if details:
            msg += "; CAUSED BY " + details
    return msg

def getFailureMessage(failure):
    msg = flog.getFailureMessage(failure)
    exception = failure.value
    if isinstance(exception, PropertyError):
        msg += " [%s:%s]" % (exception.locator, exception.descriptor)
    if isinstance(exception, TranscoderError):
        details = exception.causeDetails
        if details:
            msg += "; CAUSED BY " + details
    return msg

def getExceptionTraceback(exception=None, cleanup=False):
    #FIXME: Only work if the exception was raised in the current context
    f = Failure(exception)
    if exception and (f.value != exception):
        return "Not Traceback information available"
    io = StringIO.StringIO()
    tb = f.getTraceback()
    if cleanup:
        tb = cleanTraceback(tb)
    print >> io, tb
    if isinstance(f.value, TranscoderError):
        if f.value.causeTraceback:
            print >> io, "\n\nCAUSED BY:\n\n"
            tb = f.value.causeTraceback
            if cleanup:
                tb = cleanTraceback(tb)
            print >> io, tb
    return io.getvalue()

def getFailureTraceback(failure, cleanup=False):
    io = StringIO.StringIO()
    tb = failure.getTraceback()
    if cleanup:
        tb = cleanTraceback(tb)
    print >> io, tb
    exception = failure.value
    if exception and isinstance(exception, TranscoderError):
        if exception.causeTraceback:
            print >> io, "\n\nCAUSED BY:\n\n"
            tb = exception.causeTraceback
            if cleanup:
                tb = cleanTraceback(tb)
            print >> io, tb
    return io.getvalue()

def cleanTraceback(tb):
    prefix = __file__[:__file__.find("flumotion/transcoder/log.py")]
    regex = re.compile("(\s*File\s*\")(%s)([a-zA-Z-_\. \\/]*)(\".*)" 
                       % prefix.replace("\\", "\\\\"))
    def cleanup(line):
        m = regex.match(line)
        if m:
            return m.group(1) + ".../" + m.group(3) + m.group(4)
        else:
            return line
    return '\n'.join(map(cleanup, tb.split('\n')))


class LoggerProxy(object):

    implements(ILogger)

    def __init__(self, logger, **kwargs):
        self.setLogger(logger, **kwargs)
    
    def setLogger(self, logger, **kwargs):
        self._logger = logger
        self._kwargs = kwargs
    
    def getLogPrefix(self, kwargs):
        return None
    
    def _updateArgs(self, args, kwargs):
        kwargs.update(self._kwargs)
        prefix = self.getLogPrefix(kwargs)
        if prefix:
            return (prefix + args[0],) + args[1:], kwargs
        return args, kwargs
    
    def __setattr__(self, attr, value):
        if attr in ("logName", "name"):
            setattr(self._logger, attr, value)
        else:
            self.__dict__[attr] = value
            
    def __getattr__(self, attr):
        if attr in ("logName", "name", "logCategory"):
            return getattr(self._logger, attr)
        if not (attr in self.__dict__):
            raise AttributeError, attr
        return self.__dict__[attr]
    
    def log(self, *args, **kwargs):
        args, kwargs = self._updateArgs(args, kwargs)
        self._logger.log(*args, **kwargs)

    def debug(self, *args, **kwargs):
        args, kwargs = self._updateArgs(args, kwargs)
        self._logger.debug(*args, **kwargs)

    def info(self, *args, **kwargs):
        args, kwargs = self._updateArgs(args, kwargs)
        self._logger.info(*args, **kwargs)

    def warning(self, *args, **kwargs):
        args, kwargs = self._updateArgs(args, kwargs)
        self._logger.warning(*args, **kwargs)

    def error(self, *args, **kwargs):
        args, kwargs = self._updateArgs(args, kwargs)
        self._logger.error(*args, **kwargs)


### Helper functions to log without logger ##

def log(*args, **kwargs):
    global logCategory
    category = kwargs.pop("category", logCategory)
    flog.log(category, *args, **kwargs)

def debug(*args, **kwargs):
    global logCategory
    category = kwargs.pop("category", logCategory)
    flog.debug(category, *args, **kwargs)

def info(*args, **kwargs):
    global logCategory
    category = kwargs.pop("category", logCategory)
    flog.info(category, *args, **kwargs)

def warning(*args, **kwargs):
    global logCategory
    category = kwargs.pop("category", logCategory)
    flog.warning(category, *args, **kwargs)

def error(*args, **kwargs):
    global logCategory
    category = kwargs.pop("category", logCategory)
    flog.error(category, *args, **kwargs)
