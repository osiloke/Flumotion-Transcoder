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

from flumotion.transcoder import substitution
from flumotion.transcoder.admin import interfaces


class IBaseContext(interfaces.IAdminInterface):
    
    parent = Attribute("Parent context")
    
    def getAdminContext(self):
        pass


class IBaseStoreContext(IBaseContext):
    
    identifier = Attribute("Context identifier")
    label      = Attribute("Context label")
    store      = Attribute("context store reference")
        

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


## Descriptors ##

class StoreProxy(object):
    def __init__(self, propertyName, default=None):
        self._propertyName = propertyName
        self._default = default
    def __get__(self, obj, type=None):
        value = getattr(obj.store, self._propertyName)
        if value == None:
            return self._default
        return value
    def __set__(self, obj, value):
        raise AttributeError("Attribute read-only")
    def __delete__(self, obj):
        raise AttributeError("Attribute cannot be deleted")

class StoreParentProxy(object):
    def __init__(self, propertyName, parentPropertyName=None):
        self._propertyName = propertyName
        self._parentPropertyName = parentPropertyName or propertyName         
    def __get__(self, obj, type=None):
        value = getattr(obj.store, self._propertyName)
        if value != None: return value
        if obj.parent is None:
            raise AttributeError("Instance %s does not have parent" % self)
        return getattr(obj.parent, self._parentPropertyName)
    def __set__(self, obj, value):
        raise AttributeError("Attribute read-only")
    def __delete__(self, obj):
        raise AttributeError("Attribute cannot be deleted")


class StoreAdminProxy(object):
    def __init__(self, propertyName, adminPropertyName=None):
        self._propertyName = propertyName
        self._adminPropertyName = adminPropertyName or propertyName         
    def __get__(self, obj, type=None):
        value = getattr(obj.store, self._propertyName)
        if value != None: return value
        storeCtx = obj.getStoreContext()
        if storeCtx is None:
            raise AttributeError("Instance %s does not have store reference" % self)
        return getattr(storeCtx, self._adminPropertyName)
    def __set__(self, obj, value):
        raise AttributeError("Attribute read-only")
    def __delete__(self, obj):
        raise AttributeError("Attribute cannot be deleted")
        

class BaseContext(object):
    implements(IBaseContext)
    
    def __init__(self, parentContext):
        object.__setattr__(self, "parent", parentContext)
        parentVars = getattr(parentContext, "_variables", None)
        self._variables = substitution.Variables(parentVars)

    def getAdminContext(self):
        raise NotImplementedError()
    

class BaseStoreContext(BaseContext):
    implements(IBaseStoreContext)
    
    def __init__(self, parent, store, identifier=None, label=None):
        BaseContext.__init__(self, parent)
        object.__setattr__(self, "store", store)
        object.__setattr__(self, "identifier", identifier or store.identifier)
        object.__setattr__(self, "label", label or store.label)

    def __setattr__(self, attr, value):
        """
        Prevent adding new attributes.
        Allow early detection of attributes spelling mistakes. 
        """
        if attr.startswith("_") or hasattr(self, attr):
            return object.__setattr__(self, attr, value)
        raise AttributeError("Attribute %s cannot be added to %s" % (attr, self))
