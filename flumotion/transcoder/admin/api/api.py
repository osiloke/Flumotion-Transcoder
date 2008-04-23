# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from twisted.python import components

from flumotion.inhouse import defer, annotate
from flumotion.inhouse.spread import mediums

from flumotion.transcoder.admin import interfaces as admifaces
from flumotion.transcoder.admin.api import interfaces

_DEFAULT_PREFIX = "remote_"


def adapt(value):
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        d = defer.succeed(list())
        for v in value:
            d.addCallback(_adaptListValue, v)
        return d
    if isinstance(value, dict):
        d = defer.succeed(dict())
        for k, v in value.items():
            d.addCallback(_adaptDictValue, k, v)
        return d
    if defer.isDeferred(value):
        return value.addCallback(adapt)
    if admifaces.IAdminInterface.providedBy(value):
        return mediums.IServerMedium(value)
    return value


class Medium(mediums.ServerMedium, annotate.Annotable):
    
    @classmethod
    def _addRemote(cls, methodName, method):
        def remote(self, *args, **kwargs):
            return adapt(method(self, *args, **kwargs))
        remote.__name__ = methodName
        setattr(cls, methodName, remote)

    @classmethod
    def _registerMedium(cls, mediumIface, objIface):
        components.registerAdapter(cls, objIface, mediumIface)

      

def registerMedium(mediumIface, objectIface):
    annotate.addClassAnnotation(0, "registerMedium", "_registerMedium",
                                mediumIface, objectIface)


def remote(prefix=None):
    def decorator(method):
        methodName = (prefix or _DEFAULT_PREFIX) + method.__name__
        annotate.addMethodAnnotation(0, "remote",
                                     method, "_addRemote",
                                     methodName, method)
        return method
    return decorator


## Private ##

def _adaptListValue(l, v):
    a = adapt(v)
    if defer.isDeferred(a):
        return a.addCallback(_appendListValue, l)
    l.append(a)
    return l

def _appendListValue(v, l):
    l.append(v)
    return l

def _adaptDictValue(d, k, v):
    if admifaces.IAdminInterface.providedBy(k):
        raise ValueError("IAdminInterface is not supported for dictonary keys")
    a = adapt(v)
    if defer.isDeferred(a):
        return a.addCallback(_addDictValue, d, k)
    d[k] = a
    return d

def _addDictValue(v, d, k):
    d[k] = v
    return d

