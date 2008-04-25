# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import Interface, implements, Attribute

from flumotion.inhouse import annotate

from flumotion.transcoder import substitution
from flumotion.transcoder.admin import interfaces


class IBaseContext(interfaces.IAdminInterface):
    
    parent = Attribute("Parent context")
    
    def getAdminContext(self):
        pass


class IBaseStoreContext(IBaseContext):
    
    identifier = Attribute("Context identifier")
    label = Attribute("Context label")
    store = Attribute("context store reference")
        

class LazyContextIterator(object):
    
    def __init__(self, parent, cls, iterator, *args, **kwargs):
        self.parent = parent
        self._cls = cls
        self._iterator = iterator
        self._args = args
        self._kwargs = kwargs
    
    def __iter__(self):
        return self
        
    def next(self):
        nextValue = self._iterator.next()        
        return self._cls(self.parent, nextValue, *self._args, **self._kwargs)


## Class Annotations ##

def store_proxy(propertyName, storePropertyName=None, getterName=None, default=None):
    if storePropertyName is None:
        storePropertyName = propertyName
    if getterName is None:
        getterName = "get" + propertyName[0].upper() + propertyName[1:] 
    
    def getter(self):
        value = getattr(self.store, storePropertyName)
        if value == None:
            return default
        return value
    
    getter.__name__ = getterName
    annotate.injectAttribute("store_proxy", getterName, getter)
    prop = property(getter)
    annotate.injectAttribute("store_proxy", propertyName, prop)

def store_parent_proxy(propertyName, parentPropertyName=None,
                       storePropertyName=None, getterName=None):
    if parentPropertyName is None:
        parentPropertyName = propertyName
    if storePropertyName is None:
        storePropertyName = propertyName
    if getterName is None:
        getterName = "get" + propertyName[0].upper() + propertyName[1:]
    
    def getter(self):
        value = getattr(self.store, storePropertyName)
        if value != None: return value
        if self.parent is None:
            raise AttributeError("Attribute %s of class %s not properly setup, "
                                 "parent not found" % (propertyName, self))
        return getattr(self.parent, parentPropertyName)
    
    getter.__name__ = getterName
    annotate.injectAttribute("store_parent_proxy", getterName, getter)
    prop = property(getter)
    annotate.injectAttribute("store_parent_proxy", propertyName, prop)

def store_admin_proxy(propertyName, adminPropertyName=None,
                      storePropertyName=None, getterName=None):
    if adminPropertyName is None:
        adminPropertyName = propertyName
    if storePropertyName is None:
        storePropertyName = propertyName
    if getterName is None:
        getterName = "get" + propertyName[0].upper() + propertyName[1:]
    
    def getter(self):
        value = getattr(self.store, storePropertyName)
        if value != None: return value
        storeCtx = self.getStoreContext()
        if storeCtx is None:
            raise AttributeError("Attribute %s of class %s not properly setup, "
                                 "store context not found" % (propertyName, self))
        return getattr(storeCtx, adminPropertyName)
    
    getter.__name__ = getterName
    annotate.injectAttribute("store_admin_proxy", getterName, getter)
    prop = property(getter)
    annotate.injectAttribute("store_admin_proxy", propertyName, prop)

def property_getter(propertyName):
    def decorator(func):
        prop = property(func)
        annotate.injectAttribute("property_getter", propertyName, prop)
        return func
    return decorator


class BaseContext(object):
    implements(IBaseContext)
    
    def __init__(self, parent):
        self.parent = parent
        self._variables = substitution.Variables(getattr(parent, "_variables", None))
        
    def getAdminContext(self):
        raise NotImplementedError()
    

class BaseStoreContext(BaseContext, annotate.Annotable):
    implements(IBaseStoreContext)
    
    def __init__(self, parent, store, identifier=None, label=None):
        BaseContext.__init__(self, parent)
        self.store = store
        self.identifier = identifier or store.identifier
        self.label = label or store.label
