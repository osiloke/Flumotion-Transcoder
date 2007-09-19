# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import re
import md5
import time
import random
import datetime
import commands
import string
from email.Utils import parseaddr, formataddr

from twisted.internet import reactor

from flumotion.common import enum

from flumotion.transcoder import constants, log, defer
from flumotion.transcoder.errors import OperationTimedOutError


class LazyEncapsulationIterator(object):
    
    def __init__(self, cls, iterator, *args, **kwargs):
        self._cls = cls
        self._iterator = iterator
        self._args = args
        self._kwargs = kwargs
    
    def __iter__(self):
        return self
        
    def next(self):
        nextValue = self._iterator.next()        
        return self._cls(nextValue, *self._args, **self._kwargs)
    

def digestParameters(*args, **kwargs):
    
    def internalDigestParams(digester, *args, **kwargs):
        for e in args:
            if isinstance(e, list) or isinstance(e, tuple):
                internalDigestParams(digester, *e)
            elif isinstance(e, dict):
                internalDigestParams(digester, **e)
            else:
                digester.update("/")
                digester.update(str(e))
        if len(kwargs) > 0:
            keys = map(str, kwargs.keys())
            keys.sort()
            digester.update("/".join(keys))
            values = [kwargs[k] for k in keys]
            internalDigestParams(digester, *values)
    digester = md5.new()
    internalDigestParams(digester, *args, **kwargs)
    return digester.digest()


def genUniqueBinaryIdentifier():
    return digestParameters(time.time(), time.clock(), random.random())


def genUniqueIdentifier():    
    return genUniqueBinaryIdentifier().encode("HEX").upper()


## String and Path Utility Functions ##

_notKeyedVarPattern = re.compile('%(?!\()')
_keyedVarPattern = re.compile('%(?=\()')
_varNamePattern = re.compile('\(([a-zA-Z0-9_]*)\).*')

def filterFormat(format, vars):
    """
    Escape a format string to only let the variable in
    the specified dict. The values of the dict are not used and not changed.
    Ex:
        format = "%(toto)satest%(tata)sta%%ta%(pim)tutu%d%(titi)spam%%%spam%"
        vars = {"toto": None, "tata": None, "titi": None}
        result = "%(toto)satest%(tata)sta%%%%ta%%(pim)tutu%%d%(titi)spam%%%%%%spam%%"
    """
    escaped = '%%'.join(_notKeyedVarPattern.split(format))
    parts = _keyedVarPattern.split(escaped)
    result = parts[:1]
    for i, p in enumerate(parts[1:]):
        m = _varNamePattern.match(p)
        if m:
            if m.group(1) in vars:
                result.append(p)
                continue
        result.append('')
        result.append(p)
    return '%'.join(result)        

_safeChars = set(string.letters + string.digits
                 + '!#$%*+,-./:<=>?@[\\]^_{}~')

def mkCmdArg(*args):
    base = ''.join(args)
    # Check if the ' chars are necessaries
    # to prevent ugly looking command lines
    if reduce(bool.__and__, map(_safeChars.__contains__, base)):
        return " " + base
    return commands.mkarg(base)

def splitEscaped(regex, s):
    """
    It should be a faaaar better way to do it...
    See test_utils.py
    """
    result = []
    temp = []
    regex = '(?<!\\\\)' + regex
    parts = s.split("\\\\")
    for p in parts:
        sub = re.split(regex, p)
        temp.append(sub[0])
        if len(sub) == 1:
            continue
        result.append('\\\\'.join(temp))
        del temp[:]
        if len(sub) > 2:
            result.extend(sub[1:-1])
        temp.append(sub[-1])
    result.append('\\\\'.join(temp))
    return result

def stripEscaped(s):
    """
    See test_utils.py
    """
    j = 0
    for j, c in enumerate(reversed(s)):
        if c != ' ':
            if c == '\\':
                j -= 1
            break
    return s[:len(s)-j].lstrip()

def splitCommandFields(s):
    """
    See test_utils.py
    """
    result = []
    quoted = splitEscaped('["\']', s)
    for odd, chunk in enumerate(quoted):
        if (odd % 2) == 0:
            spaced = splitEscaped(' ', chunk)
            for part in spaced:
                part = stripEscaped(part)
                if not part: continue
                part = part.replace('\\ ', ' ')
                part = part.replace('\\"', '"')
                part = part.replace('\\\'', '\'')
                part = part.replace('\\\\', '\\')
                result.append(part)
        else:
            chunk = chunk.replace('\\"', '"')
            chunk = chunk.replace('\\\'', '\'')
            chunk = chunk.replace('\\\\', '\\')
            result.append(chunk)
    return result

def escapeField(s):
    e = s.replace('\\', '\\\\')
    if not s:
        return '""'
    if (' ' in s) or ('"' in s):
        return '"' + e.replace('"', '\\"') + '"'
    return e

def joinCommandFields(l):
    """
    See test_utils.py
    """
    return ' '.join([escapeField(str(s)) for s in l])


## Mail Utilitiy Fiunctions ##

def splitMailRecipients(line):
    """
    See test_utils.py
    """
    result = [parseaddr(f) for f in line.split(", ")]
    if result == [('', '')]:
        return []
    return result

def joinMailRecipients(recipients):
    """
    See test_utils.py
    """
    return ", ".join([formataddr(r) for r in recipients])

def splitMailAddress(address):
    return parseaddr(address)

def joinMailAddress(fields):
    return formataddr(fields)


## Structures Utility Functions ##

def deepCopy(value):
    """
    Do a safe deep copy of the specified value.
    Do not mess up the enums.
    Only work for the basic types:
        str, int, float, long, dict, list and enums.
    All instances of subclasses of these base types
    will be replaced by instances of the base type.
    """
    if value == None:
        return None
    if isinstance(value, (str, int, float, long, enum.Enum, datetime.datetime)):
        return value
    if isinstance(value, dict):
        return dict([(deepCopy(k), deepCopy(v)) 
                     for k, v in value.items()])
    if isinstance(value, list):
        return [deepCopy(v) for v in value]
    if isinstance(value, tuple):
        return tuple([deepCopy(v) for v in value])
    if isinstance(value, set):
        return set([deepCopy(v) for v in value])
    raise TypeError("Value type unsuported by deepCopy: \"%s\" (%s)" 
                    % (str(value), value.__class__.__name__))


## Timeout and Delay Utility Functions ##

def callNext(callable, *args, **kwargs):
    return reactor.callLater(constants.CALL_NEXT_DELAY,
                             callable, *args, **kwargs)

def callWithTimeout(timeout, callable, *args, **kwargs):
    d = callable(*args, **kwargs)
    if not timeout: return d
    result = defer.Deferred()
    to = createTimeout(timeout, __asyncCallTimeout, result)
    args = (result, to)
    d.addCallbacks(__cbForwardCallback, __ebForwardErrback, 
                   callbackArgs=args, errbackArgs=args)
    return result

def __asyncCallTimeout(d):
    error = OperationTimedOutError("Asynchronous Call Timed Out")
    d.errback(error)

def __ebForwardErrback(failure, d, to):
    if hasTimedOut(to):
        log.warning("Received failure for a timed out call: %s",
                    log.getFailureMessage(failure))
        return
    cancelTimeout(to)
    d.errback(failure)

def __cbForwardCallback(result, d, to):
    if hasTimedOut(to):
        log.warning("Received result for a timed out call: %s",
                    str(result))
        return
    cancelTimeout(to)
    d.callback(result)

def createTimeout(timeout, callback, *args, **kwargs):
    if timeout == None:
        return None
    return reactor.callLater(timeout, __callTimeout,
                             callback, *args, **kwargs)

def cancelTimeout(timeout):
    if timeout and timeout.active():
        timeout.cancel()

def hasTimedOut(timeout):
    return timeout and not timeout.active()

def __callTimeout(callable, *args, **kwargs):
    try:
        callable(*args, **kwargs)
    except Exception, e:
        log.notifyException(log, e, "Timeout call raise an exception")
