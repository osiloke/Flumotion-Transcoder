# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import implements

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


## Annotations ##

def readonly_context_property(propertyName):
    def getter(self):
        return getattr(self.reference, propertyName)
    methodName = "get" + propertyName[0].upper() + propertyName[0]
    getter.__name__ = methodName 
    annotate.injectAttribute("readonly_context_property", methodName, getter)
    annotate.injectClassCallback("readonly_context_property", "_makeRemote", methodName)

def readonly_store_property(propertyName):
    def getter(self):
        return getattr(self.reference.store, propertyName)
    methodName = "get" + propertyName[0].upper() + propertyName[0]
    getter.__name__ = methodName 
    annotate.injectAttribute("readonly_store_property", methodName, getter)
    annotate.injectClassCallback("readonly_store_property", "_makeRemote", methodName)

def readonly_proxy_getter(getterName):
    def getter(self):
        return getattr(self.reference, getterName)()
    methodName = getterName
    getter.__name__ = methodName 
    annotate.injectAttribute("readonly_proxy_getter", methodName, getter)
    annotate.injectClassCallback("readonly_proxy_getter", "_makeRemote", methodName)

def register_medium(mediumIface, objectIface):
    annotate.injectClassCallback("registerMedium", "_registerMedium",
                                 mediumIface, objectIface)


## Decorators ##

def make_remote(prefix=None):
    def decorator(method):
        methodName = method.__name__
        annotate.injectClassCallback("make_remote",
                                     "_makeRemote", methodName, prefix)
        return method
    return decorator


class Medium(mediums.ServerMedium, annotate.Annotable):

    implements(interfaces.IMedium)
    
    @classmethod
    def _makeRemote(cls, methodName, prefix=None):
        method = getattr(cls, methodName)
        def remote(self, *args, **kwargs):
            return adapt(method(self, *args, **kwargs))
        remoteMethodName = (prefix or _DEFAULT_PREFIX) + methodName
        remote.__name__ = remoteMethodName 
        setattr(cls, remoteMethodName, remote)

    @classmethod
    def _registerMedium(cls, mediumIface, objIface):
        components.registerAdapter(cls, objIface, mediumIface)

    def __init__(self, reference):
        self.reference = reference 


class NamedMedium(Medium):
    
    implements(interfaces.INamedMedium)
    
    readonly_context_property("identifier")
    readonly_context_property("name")
    readonly_context_property("label")
    
    def __init__(self, reference):
        Medium.__init__(self, reference)
     

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

