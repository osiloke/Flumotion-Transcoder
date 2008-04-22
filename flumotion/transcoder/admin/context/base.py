# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.inhouse import annotate

from flumotion.transcoder.substitution import Variables


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


def genStoreProxy(getterName, default=None):
    def getter(self):
        method = getattr(self.store, getterName, None)
        if method is None:
            raise ValueError("Context element %s do not have method %s"
                             % (self.store, getterName))
        value = method()
        if value == None: value = default
        return value
    annotate.addAnnotationMethod("genStoreProxy", getterName, getter)

def genParentOverridingStoreProxy(getterName, parentGetterName=None):
    def getter(self):
        method = getattr(self.store, getterName, None)
        if method is None:
            raise ValueError("Context element %s do not have method %s"
                             % (self.store, getterName))
        value = method()
        if value != None:
            return value
        pGetterName = parentGetterName or getterName
        if self.parent is None:
            raise ValueError("Context element %s without parent" % self)
        parentGetter = getattr(self.parent, pGetterName, None)
        if parentGetter is None:
            raise ValueError("Context element %s do not have method %s"
                             % (self.parent, pGetterName))
        return  parentGetter()
    annotate.addAnnotationMethod("genParentOverridingStoreProxy", getterName, getter)

def genStoreOverridingStoreProxy(getterName, storeGetterName=None):
    def getter(self):
        method = getattr(self.store, getterName, None)
        if method is None:
            raise ValueError("Context element %s do not have method %s"
                             % (self.store, getterName))
        value = method()
        if value != None: return value
        sGetterName = storeGetterName or getterName
        storeCtx = self.getStoreContext()
        if storeCtx is None:
            raise ValueError("Context element %s without store context" % self)
        storeGetter = getattr(storeCtx, sGetterName, None)
        if storeGetter is None:
            raise ValueError("Context element %s do not have method %s"
                             % (storeCtx, sGetterName))
        return storeGetter()
    annotate.addAnnotationMethod("genStoreOverridingStoreProxy", getterName, getter)


class BaseContext(object):
    
    def __init__(self, parent):
        self.parent = parent
        self._variables = Variables(getattr(parent, "_variables", None))
    

class BaseStoreContext(BaseContext):
    
    def __init__(self, parent, store):
        BaseContext.__init__(self, parent)
        self.store = store
