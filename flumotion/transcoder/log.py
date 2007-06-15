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
import sys
import traceback
import StringIO

from twisted.python import failure
from flumotion.common import log as flog
from flumotion.transcoder.errors import TranscoderError


# Proxy some flumotion.comon.log class, functions and constants
Loggable = flog.Loggable

setFluDebug = flog.setFluDebug
getCategoryLevel = flog.getCategoryLevel

LOG = flog.LOG
DEBUG = flog.DEBUG
INFO = flog.INFO
WARNING = flog.WARNING
ERROR = flog.ERROR


_DEFAULT_CATEGORY = ""

def setDefaultCategory(category):
    _DEFAULT_CATEGORY = category

def getExceptionMessage(exception):
    msg = flog.getExceptionMessage(exception)
    if isinstance(exception, TranscoderError):
        details = exception.causeDetails
        if details:
            msg += "; CAUSED BY " + details
    return msg

def getFailureMessage(failure):
    msg = flog.getFailureMessage(failure)
    exception = failure.value
    if isinstance(exception, TranscoderError):
        details = exception.causeDetails
        if details:
            msg += "; CAUSED BY " + details
    return msg

def getExceptionTraceback(exception):
    f = failure.Failure()
    if f.value != exception:
        return "Not Traceback information available"
    io = StringIO.StringIO()
    print >> io, f.getTraceback()
    if isinstance(f.value, TranscoderError):
        if f.value.causeTraceback:
            print >> io, "\n\nCAUSED BY:\n\n"
            print >> io, f.value.causeTraceback
    return io.getvalue()


def getFailureTraceback(failure):
    io = StringIO.StringIO()
    print >> io, failure.getTraceback()
    exception = failure.value
    if exception and isinstance(exception, TranscoderError):
        if exception.causeTraceback:
            print >> io, "\n\nCAUSED BY:\n\n"
            print >> io, exception.causeTraceback
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
        if attr in ("logName", "name"):
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

def log(self, *args, **kwargs):
    flog.log(_DEFAULT_CATEGORY, *args, **kwargs)

def debug(self, *args, **kwargs):
    flog.debug(_DEFAULT_CATEGORY, *args, **kwargs)

def info(self, *args, **kwargs):
    flog.info(_DEFAULT_CATEGORY, *args, **kwargs)

def warning(self, *args, **kwargs):
    flog.warning(_DEFAULT_CATEGORY, *args, **kwargs)

def error(self, *args, **kwargs):
    flog.error(_DEFAULT_CATEGORY, *args, **kwargs)

