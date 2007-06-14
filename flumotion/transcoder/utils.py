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

from twisted.internet import defer, reactor


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


## String Utility Functions ##

def str2filename(value):
    """
    Build a valid name for a file or a directory from a specified string.
    Replace all caracteres out of [0-9A-Za-z-()] by '_' and lower the case.
    Ex: "Big Client Corp" => "big_client_corp"
        "OGG-Theora/Vorbis" => "ogg_theora_vorbis"
    """
    return "_".join(re.split("[^0-9A-Za-z-()]", value)).lower()

def splitPath(filePath):
    """
    From: /toto/ta.ta/tu.tu.foo
    Return: ("/toto/ta.ta/", "tu.tu", ".foo")
    """
    path = ""
    file = filePath
    ext = ""
    lastSepIndex = filePath.rfind('/') + 1
    if lastSepIndex > 0:
        path = file[:lastSepIndex]
        file = file[lastSepIndex:]
    lastDotIndex = file.rfind('.')
    if lastDotIndex >= 0:
        ext = file[lastDotIndex:]
        file = file[:lastDotIndex]
    return (path, file, ext)

def cleanupPath(filePath):
    """
    Simplify a path, but keep the last '/'.
    Ex:   //test/./toto/test.txt/ => /test/toto/test.txt/
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
        if last or (not last and result[-1]):
            result.append(last)
    else:
        result.append('')
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

def joinPath(*parts):
    return cleanupPath("/".join(parts))


## Deferred Utility Functions ##

def createTimeout(timeout, callback, *args, **kwargs):
    if timeout == None:
        return None
    return reactor.callLater(timeout, callback, *args, **kwargs)

def cancelTimeout(timeout):
    if timeout and timeout.active():
        timeout.cancel()

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

def resolveFailure(failure, result, *args):
    """
    Resolve an errorback.
    If the failure's error type is in the specified
    arguments, the specified result is returned,
    otherwise the received failure is passed down. 
    """
    if failure.check(args):
        return result
    return failure

def overrideResult(result, newResult):
    return newResult
