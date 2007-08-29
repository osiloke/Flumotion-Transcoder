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

import os
import re
import md5
import time
import random
import datetime
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


## File System Utility Functions ##

def ensureDirExists(dir, description):
    """
    Ensure the given directory exists, creating it if not.
    Raises a SystemError if this fails, including the given description.
    If makedirs fail, verify the directory hasn't been 
    created by another process.
    """
    if not os.path.exists(dir):
        try:
            os.makedirs(dir)
        except Exception, e:
            #FIXME: Is there a constant for this ?
            if e.errno == 17:
                return
            from flumotion.transcoder.errors import SystemError
            raise SystemError("Could not create %s directory '%s': %s"
                              % (description, dir, log.getExceptionMessage(e)),
                              cause=e)


## String and Path Utility Functions ##

def str2filename(value):
    """
    Build a valid name for a file or a directory from a specified string.
    Replace all caracteres out of [0-9A-Za-z-()] by '_' and lower the case.
    Ex: "Big Client Corp" => "big_client_corp"
        "OGG-Theora/Vorbis" => "ogg_theora_vorbis"
    """
    return "_".join(re.split("[^0-9A-Za-z-()]", value)).lower()

def splitPath(filePath, withExtention=True):
    """
    From: /toto/ta.ta/tu.tu.foo
    Return: ("/toto/ta.ta/", "tu.tu", ".foo")
    If withExtention is set to false, the extension is not extracted:
    From: /toto/ta.ta/tu.tu.foo
    Return: ("/toto/ta.ta/", "tu.tu.foo", "")
    """
    path = ""
    file = filePath
    ext = ""
    lastSepIndex = filePath.rfind('/') + 1
    if lastSepIndex > 0:
        path = file[:lastSepIndex]
        file = file[lastSepIndex:]
    if withExtention:
        lastDotIndex = file.rfind('.')
        if lastDotIndex >= 0:
            ext = file[lastDotIndex:]
            file = file[:lastDotIndex]
    return (path, file, ext)

def cleanupPath(filePath):
    """
    Simplify a path, but keep the last '/'.
    Ex:   //test/./toto/test.txt/ => /test/toto/test.txt/
    See test_utils.py for more use cases.
    
    FIXME: Too much complicated and special-cased.
    """
    parts = filePath.split('/')
    if len(parts) <= 1:
        return filePath
    result = []
    if parts[0] != '.':
        result.append(parts[0])
    result.extend([p for p in parts[1:-1] if p and p != '.'])
    last = parts[-1]
    if last != '.':
        if last or (not last and result and result[-1]):
            result.append(last)
    elif len(result) > 1:
        result.append('')
    if (parts[0] == '') and ((not result) or (result[0] != '') or (len(result) < 2)):
        result.insert(0, '')
    if (parts[-1] == '') and ((not result) or (result[-1] != '') or (len(result) < 2)):
        result.append('')
    if (parts[0] == '.') and ((not result) or ((result[0] != '.') and (len(result) < 2))):
        result.insert(0, '.')
    return '/'.join(result)

def ensureDirPath(dirPath):
    """
    Ensure the path ends by a '/'.
    """
    if (not dirPath) or dirPath.endswith('/'):
        return dirPath
    return dirPath + '/'

def ensureAbsPath(dirPath):
    """
    Ensure the path starts with a '/'.
    """
    if not dirPath:
        return '/'
    if dirPath.startswith('/'):
        return dirPath
    return '/' + dirPath

_ensureRelPathPattern = re.compile("/*(.*)")
def ensureRelPath(aPath):
    """
    Ensure the path do not starts with a '/'.
    """
    if not aPath:
        return aPath
    return _ensureRelPathPattern.match(aPath).group(1)

def ensureAbsDirPath(dirPath):
    """
    Shortcut to ensureDirPath(ensureAbsPath()) because it's used a lot.
    """
    if not dirPath:
        return '/'
    if not dirPath.endswith('/'):
        dirPath = dirPath + '/'
    if not dirPath.startswith('/'):
        dirPath = '/' + dirPath
    return dirPath

def ensureRelDirPath(dirPath):
    """
    Shortcut to ensureDirPath(ensureRelPath()) because it's used a lot.
    """
    if not dirPath:
        return dirPath
    if not dirPath.endswith('/'):
        dirPath = dirPath + '/'
    return _ensureRelPathPattern.match(dirPath).group(1)

def str2path(value):
    """
    Convert a string to a path.
    Actualy doing nothing.
    "toto/tatat/titi.txt" => "toto/tatat/titi.txt"
    """
    return value

def makeAbsolute(path, base=None):
    """
    If the specified path is not absolute (do not starts with '/')
    it's concatenated to the specified base or the current directory.
    """
    if not base:
        base = os.path.abspath('')
    if path.startswith('/'):
        return os.path.abspath(path)
    return os.path.abspath(ensureAbsDirPath(base) + path)

def joinPath(*parts):
    return cleanupPath("/".join(parts))

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
    """
    if value == None:
        return None
    if isinstance(value, (str, int, float, long, enum.Enum, datetime.datetime)):
        return value
    if isinstance(value, dict):
        return value.__class__([(deepCopy(k), deepCopy(v)) 
                                for k, v in value.items()])
    if isinstance(value, (list, tuple, set)):
        return value.__class__([deepCopy(v) for v in value])
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
