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

MAX_LIST_INCREMENT = 10

import weakref
import re
import datetime

from flumotion.transcoder import virtualpath


class PropertyError(Exception):

    def __init__(self, msg, locator=None, descriptor=None, cause=None):
        Exception.__init__(self, msg)
        self.cause = cause
        self.locator = locator
        self.descriptor = descriptor
    
    def __str__(self):
        msg = Exception.__str__(self)
        if self.cause:
            msg += " CAUSE: " + str(self.cause)
        return msg


class PropertyRuntimeError(RuntimeError):
    pass


class PropertySourceAdapter:    
    def hasLocation(self, locator):
        raise NotImplementedError
    def listLocations(self):
        raise NotImplementedError
    def addLocation(self, locator):
        raise NotImplementedError
    def hasProperty(self, locator, descriptor):
        raise NotImplementedError
    def listProperties(self, locator):
        raise NotImplementedError
    def getProperty(self, locator, descriptor):
        raise NotImplementedError
    def setProperty(self, locator, descriptor, value):
        raise NotImplementedError


class PropertyList(list):

    def __init__(self, prop, parent):
        list.__init__(self)
        self.prop = prop
        self.parent = parent
    
    def __setitem__(self, index, item):
        self.prop.checkItem(self.parent, item)
        self.prop.bindItem(self.parent, item, index)
        list.__setitem__(self, index, item)
    
    def __add__(self, items):
        raise NotImplementedError

    def append(self, item):
        self.prop.checkItem(self.parent, item)
        self.prop.bindItem(self.parent, item, len(self))
        list.append(self, item)

    def addItem(self):
        item = self.prop.createItem(self.parent)
        self.prop.bindItem(self.parent, item, len(self))
        list.append(self, item)
        return item
    
    def putItemAt(self, index, item):
        if index < 0:
            raise PropertyRuntimeError("Cannot put an item at index %d"
                                       % index,
                                       self.prop.locator)
        if index < len(self):
            if self[index] != None:
                raise PropertyRuntimeError("An item has already been added "
                                           + "at index %d" % index)
        else:
            if index > (len(self) + MAX_LIST_INCREMENT):
                raise PropertyRuntimeError("Item index %d to big"
                                           % index)
            list.extend(self, (None,)*(index + 1 - len(self)))
        self.prop.bindItem(self.parent, item, index)
        list.__setitem__(self, index, item)
        return item
    
    def addItemAt(self, index):
        item = self.prop.createItem(self.parent)
        return self.putItemAt(index, item)


class PropertyDict(dict):

    def __init__(self, prop, parent):
        dict.__init__(self)
        self.prop = prop
        self.parent = parent
    
    def __setitem__(self, name, item):
        self.prop.checkItem(self.parent, item)
        self.prop.bindItem(self.parent, item, name)
        dict.__setitem__(self, name, item)
        
    def update(self, items):
        raise NotImplementedError
    
    def putItem(self, name, item):
        self.prop.bindItem(self.parent, item, name)
        dict.__setitem__(self, name, item)
    
    def addItem(self, name):
        item = self.prop.createItem(self.parent)
        return self.putItem(name, item)

    
class BaseProperty(object):
    
    def __init__(self):
        self.attr = None

    def setup(self, cls, attr):        
        """
        Setup the property, called when the
        class is processed by the mertaclass.
        """
        self.attr = attr
        self.delValue(cls)
        
    def addProperty(self, cls, identifier, prop):
        cls._properties[identifier] = prop
        
    def addChild(self, cls, child):
        cls._childs.append(child)
        
    def addPreChecks(self, cls, attr, setCB, delCB=None):
        """
        Add a check function to be triggered before
        the specified attribute is set.
        """
        if attr in cls._preChecks:
            l = cls._preChecks[attr]
        else:
            l = list()
            cls._preChecks[attr] = l
        l.append((setCB, delCB))
        
    def addPostChecks(self, cls, attr, setCB, delCB=None):
        """
        Add a check function to be triggered after
        the specified attribute is set.
        """
        if attr in cls._postChecks:
            l = cls._postChecks[attr]
        else:
            l = list()
            cls._postChecks[attr] = l
        l.append((setCB, delCB))

    def initAttr(self, obj):
        """
        Initialize the attribute of a specified instance.
        Called at instance initialization time.
        """
        
    def getLocator(self, obj):
        raise NotImplementedError
            
    def reset(self, obj):
        self.setValue(obj, None)

    def isSet(self, obj):
        return hasattr(obj, self.attr) and getattr(obj, self.attr) != None
    
    def setValue(self, obj, value):
        setattr(obj, self.attr, value)

    def setValueWithoutChecks(self, obj, value):
        obj.__dict__[self.attr] = value

    def delValue(self, obj):
        delattr(obj, self.attr)
        
    def getValue(self, obj): 
        return getattr(obj, self.attr)
    
    def visitStrValues(self, obj, callback):
        raise NotImplementedError
    
    def loadFromAdapter(self, obj, adapter, locators, descriptors):
        raise NotImplementedError
    
    def saveToAdapter(self, obj, adapter):
        raise NotImplementedError
    
        
class BaseChildProperty(BaseProperty):

    def __init__(self, locator, root=False):
        BaseProperty.__init__(self)        
        if isinstance(locator, str):
            locator = (locator,)
        self.locator = locator
        self.root = root
        
    def setup(self, cls, attr):
        BaseProperty.setup(self, cls, attr)
        self.addChild(cls, self)
        def setAttrForbidden(obj, attr, value):
            if hasattr(obj, attr):
                raise PropertyRuntimeError(("Cannot modify the attribute '%s' "
                                           + "for property set %s")
                                           % (attr, str(self.locator)))
        def delAttrForbidden(obj, attr):
            raise PropertyRuntimeError(("Cannot delete the attribute '%s' "
                                       + "for property set %s")
                                       % (attr, str(self.locator)))
        self.addPreChecks(cls, attr, setAttrForbidden, delAttrForbidden)
        
    def initAttr(self, obj):
        BaseProperty.initAttr(self, obj)
        child = self.createChild(obj)
        if child:
            child.setupBag(self)
        self.setValue(obj, child)

    def reset(self, obj):
        if self.isSet(obj):
            self.getValue(obj).reset()

    def getLocator(self, obj):
        parent = obj.getParent()
        if self.root or (not parent) or (parent == obj):
            return self.locator
        else:
            return parent.getLocator() + self.locator

    def getBags(self, obj):
        """
        Gives all the property bags managed by the property.
        """
        return (self.getValue(obj),)
        
    def createBags(self, obj, locators):
        """
        Create property bags from a specified property source adapter.
        """
        return (self.getValue(obj),)

    def createChild(self, parent):
        raise NotImplementedError

    def visitStrValues(self, obj, callback):
        for b in self.getBags(obj):
            if b: b.visitStrValues(callback)

    def loadFromAdapter(self, obj, adapter, locators, descriptors):
        for b in self.createBags(obj, locators):
            if b:
                b._loadFromAdapter(adapter, locators)
    
    def saveToAdapter(self, obj, adapter):
        for b in self.getBags(obj):
            if b: b.saveToAdapter(adapter)


class ValueProperty(BaseProperty):
    
    def __init__(self, descriptor, default=None, required=False):
        BaseProperty.__init__(self)
        if isinstance(descriptor, str):
            descriptor = (descriptor,)        
        self.descriptor = descriptor
        self.required = required
        self.default = default

    def setup(self, cls, attr):        
        BaseProperty.setup(self, cls, attr)
        self._checkDefault()
        self.addProperty(cls, self.descriptor, self)
        def delAttrForbidden(obj, attr):
            raise PropertyError("Cannot delete attribute '%s'"
                                % attr, obj.getLocator(), self.descriptor)
        self.addPreChecks(cls, attr, self._checkValue, delAttrForbidden)
        
    def initAttr(self, obj):
        BaseProperty.initAttr(self, obj)
        self.setValue(obj, self.default)
        
    def getLocator(self, obj):
        return obj.getLocator()
        
    def _checkDefault(self):
        if self.default == None:
            return
        if not self.checkValue(self.default):
            raise PropertyRuntimeError(("Invalid default value "
                                        + "'%s' (%s) for property %s")
                                        % (str(self.default), 
                                           type(self.default).__name__,
                                           str(self.descriptor)))
    
    def _checkValue(self, obj, attr, value):
        if value == None:
            return
        if not self.checkValue(value):
            raise PropertyError("Invalid value '%s' (%s)"
                    % (str(value), type(value).__name__)
                    , self.getLocator(obj), self.descriptor)
            
    def _str2val(self, obj, strval):
        try:
            val = self.str2val(strval)
            self._checkValue(obj, None, val)
            return val
        except ValueError, e:
            raise PropertyError("Invalid value '%s' (%s)"
                                % (str(strval), str(e)),
                                self.getLocator(obj), self.descriptor)
            
    def reset(self, obj):
        BaseProperty.reset(self, obj)
        if not self.required:
            self.setValue(obj, self.default)
            
    def setStrValue(self, obj, strval):
        if strval == "":
            self.setValue(obj, None)
        else:
            self.setValue(obj, self._str2val(obj, strval))        

    def getStrValue(self, obj):
        if self.isSet(obj):
            val = self.getValue(obj)
        else:
            val = self.default
        if val == None:
            return ""
        return self.val2str(val)
    
    def visitStrValues(self, obj, callback):
        if not self.isSet(obj):
            if self.required:
                raise PropertyError("Missing required property",
                                    obj.getLocator(), self.descriptor)
        else:
            callback(obj.getLocator(), self.descriptor, self.getStrValue(obj))
    
    def loadFromAdapter(self, obj, adapter, locators, descriptors):
        if not self.descriptor in descriptors:
            if self.required:
                raise PropertyError("Missing required property",
                                    obj.getLocator(), self.descriptor)
        else:
            self.setStrValue(obj, adapter.getProperty(obj.getLocator(), 
                                                      self.descriptor))
            del descriptors[self.descriptor]
        
    
    def saveToAdapter(self, obj, adapter):
        if not self.isSet(obj):
            if self.required:
                raise PropertyError("Missing required property",
                                    obj.getLocator(), self.descriptor)
        else:
            adapter.setProperty(obj.getLocator(), self.descriptor, 
                                self.getStrValue(obj))

    def checkValue(self, value):
        return True

    def str2val(self, strval):
        return strval
    
    def val2str(self, value):
        return value


class List(BaseProperty):
    
    def __init__(self, subprop):
        if not isinstance(subprop, ValueProperty):
            raise PropertyRuntimeError(("Invalid property type specified (%s), "
                                       + "must be a ValueProperty instance")
                                       % subprop.__class__.__name__)
        BaseProperty.__init__(self)
        self.subprop = subprop

    def setup(self, cls, attr):
        BaseProperty.setup(self, cls, attr)
        self.subprop._checkDefault()
        self.addProperty(cls, self.subprop.descriptor, self)
        def setAttrForbidden(obj, attr, value):
            if hasattr(obj, attr):
                raise PropertyError("Cannot modify the list attribute '%s'"
                                     % attr, 
                                     obj.getLocator(), self.subprop.descriptor)
        def delAttrForbidden(obj, attr):
            raise PropertyError("Cannot delete the list attribute '%s'"
                                % attr, 
                                obj.getLocator(), self.subprop.descriptor)
        self.addPreChecks(cls, attr, setAttrForbidden, delAttrForbidden)

    def initAttr(self, obj):
        BaseProperty.initAttr(self, obj)
        self.setValue(obj, PropertyList(self, obj))

    def reset(self, obj):
        del self.getValue(obj)[:]

    def checkItem(self, obj, item):
        if not self.subprop.checkValue(item):
            raise PropertyError("Invalid list value '%s'"
                                % str(item),
                                obj.getLocator(), self.subprop.descriptor)
    
    def createItem(self, parent):
        return self.subprop.default
    
    def bindItem(self, parent, item, index):
        pass
        
    def getDescriptor(self, index):
        return self.subprop.descriptor + ("%04d" % (index + 1),)
    
    def visitStrValues(self, obj, callback):
        if len(self.getValue(obj)) == 0 and self.subprop.required:
            raise PropertyError("Missing required list value",
                                obj.getLocator(), self.subprop.descriptor)
        for i, v in enumerate(self.getValue(obj)):
            if v:
                callback(obj.getLocator(), 
                         self.getDescriptor(i),
                         self.subprop.val2str(v))
    
    def loadFromAdapter(self, obj, adapter, locators, descriptors):
        descriptor = self.subprop.descriptor
        values = self.getValue(obj)
        hadValue = False
        for d in descriptors.keys():
            if d[:-1] == descriptor:
                try:
                    hadValue = True
                    index = int(d[-1]) - 1                 
                    strval = adapter.getProperty(obj.getLocator(), d)
                    value = self.subprop.str2val(strval)
                    values.putItemAt(index, value)
                    del descriptors[d]
                except TypeError:
                    raise PropertyError("Invalid property index '%s'"
                                        % str(d[-1]),
                                        obj.getLocator(), descriptor)
        if not hadValue and self.subprop.required:
            raise PropertyError("Missing required list value",
                                obj.getLocator(), descriptor)
    
    def saveToAdapter(self, obj, adapter):
        if len(self.getValue(obj)) == 0 and self.subprop.required:
            raise PropertyError("Missing required list value",
                                obj.getLocator(), self.subprop.descriptor)
        for i, v in enumerate(self.getValue(obj)):
            if v:
                adapter.setProperty(obj.getLocator(), 
                                    self.getDescriptor(i),
                                    self.subprop.val2str(v))


class Dict(BaseProperty):
    
    def __init__(self, subprop):
        if not isinstance(subprop, ValueProperty):
            raise PropertyRuntimeError(("Invalid property type specified (%s), "
                                       + "must be a ValueProperty instance")
                                       % subprop.__class__.__name__)
        BaseProperty.__init__(self)
        self.subprop = subprop

    def setup(self, cls, attr):
        BaseProperty.setup(self, cls, attr)
        self.subprop._checkDefault()
        self.addProperty(cls, self.subprop.descriptor, self)
        def setAttrForbidden(obj, attr, value):
            if hasattr(obj, attr):
                raise PropertyError("Cannot modify the dict attribute '%s'"
                                     % attr, 
                                     obj.getLocator(), self.subprop.descriptor)
        def delAttrForbidden(obj, attr):
            raise PropertyError("Cannot delete the dict attribute '%s'"
                                % attr, 
                                obj.getLocator(), self.subprop.descriptor)
        self.addPreChecks(cls, attr, setAttrForbidden, delAttrForbidden)

    def initAttr(self, obj):
        BaseProperty.initAttr(self, obj)
        self.setValue(obj, PropertyDict(self, obj))

    def reset(self, obj):
        self.getValue(obj).clear()

    def checkItem(self, obj, item):
        if not self.subprop.checkValue(item):
            raise PropertyError("Invalid dict value '%s'"
                                % str(item),
                                obj.getLocator(), self.subprop.descriptor)
    
    def createItem(self, parent):
        return self.subprop.default
    
    def bindItem(self, parent, item, index):
        pass
        
    def getDescriptor(self, name):
        return self.subprop.descriptor + (name,)
    
    def visitStrValues(self, obj, callback):
        if len(self.getValue(obj)) == 0 and self.subprop.required:
            raise PropertyError("Missing required list value",
                                obj.getLocator(), self.subprop.descriptor)
        for n, v in self.getValue(obj).iteritems():
            callback(obj.getLocator(), 
                     self.getDescriptor(n),
                     self.subprop.val2str(v))
    
    def loadFromAdapter(self, obj, adapter, locators, descriptors):
        descriptor = self.subprop.descriptor
        values = self.getValue(obj)
        hadValue = False
        for d in descriptors.keys():
            if d[:-1] == descriptor:
                try:
                    hadValue = True
                    name = str(d[-1])
                    strval = adapter.getProperty(obj.getLocator(), d)
                    value = self.subprop.str2val(strval)
                    values[name] = value
                    del descriptors[d]
                except TypeError:
                    raise PropertyError("Invalid property name '%s'"
                                        % str(d[-1]),
                                        obj.getLocator(), descriptor)
        if not hadValue and self.subprop.required:
            raise PropertyError("Missing required dict value",
                                obj.getLocator(), descriptor)
    
    def saveToAdapter(self, obj, adapter):
        if len(self.getValue(obj)) == 0 and self.subprop.required:
            raise PropertyError("Missing required dict value",
                                obj.getLocator(), self.subprop.descriptor)
        for n, v in self.getValue(obj).iteritems():
            adapter.setProperty(obj.getLocator(), 
                                self.getDescriptor(n),
                                self.subprop.val2str(v))


class RootBagProperty(BaseChildProperty):
    
    def __init__(self):
        BaseChildProperty.__init__(self, ())

        
class PropertyBag(object):
    """
    The inherited classes used as root property bags can
    change the class variable _root_locator.
    """

    class __metaclass__(type):
        def __init__(cls, name, bases, attrs): 
            props = {}
            childs = {}
            preChecks = {}
            postChecks = {}
            for b in bases[::-1]:
                if hasattr(b, "_properties") and (b._properties != None):
                    props.update(b._properties)
                if hasattr(b, "_childs") and (b._childs != None):
                    childs.update(b._childs)
                if hasattr(b, "_preChecks") and (b._preChecks != None):
                    preChecks.update(b._preChecks)
                if hasattr(b, "_postChecks") and (b._postChecks != None):
                    postChecks.update(b._postChecks)
            setattr(cls, "_properties", props)
            setattr(cls, "_childs", childs.values())
            setattr(cls, "_preChecks", preChecks)
            setattr(cls, "_postChecks", postChecks)
            for a, v in attrs.iteritems():
                if not a.startswith('_') and isinstance(v, BaseProperty):
                    v.setup(cls, a)

    def __init__(self, *args, **kwargs):
        self.setParent(None)
        
    def setupBag(self, property):
        self.__dict__["_property"] = property
        for p in self._properties.itervalues():
            p.initAttr(self)
        for c in self._childs:
            c.initAttr(self)
    
    def __getattr__(self, attr):
        if not self.getParent():
            raise PropertyError("Cannot use a property bag without parent")
        if not (attr in self.__dict__):
            raise AttributeError, attr
        return self.__dict__[attr]
    
    def __setattr__(self, attr, value):
        if not self.getParent():
            raise PropertyError("Cannot use a property bag without parent")
        if attr in self._preChecks:
            for c in self._preChecks[attr]:
                c[0](self, attr, value)
        self.__dict__[attr] = value
        if attr in self._postChecks:
            for c in self._postChecks[attr]:
                c[0](self, attr, value)

    def __delattr__(self, attr):
        if not self.getParent():
            raise PropertyError("Cannot use a property bag without parent")
        if attr in self._preChecks:
            for c in self._preChecks[attr]:
                c[1](self, attr)
        del self.__dict__[attr]        
        if attr in self._postChecks:
            for c in self._postChecks[attr]:
                c[1](self, attr)
        
    def getParent(self):
        parent = self.__dict__.get('_parent', None)
        return parent and parent()
    
    def setParent(self, parent):
        self.__dict__['_parent'] = parent and weakref.ref(parent)
    
    def getProperty(self):
        return self._property
    
    def getLocator(self):
        return self._property.getLocator(self)
    
    def reset(self):
        for p in self._properties.itervalues():
            p.reset(self)
        for c in self._childs:
            c.reset(self)
            
    def visitStrValues(self, callback):
        properties = self._properties
        childs = self._childs
        for p in properties.itervalues():
            p.visitStrValues(self, callback)
        for c in childs:
            c.visitStrValues(self, callback)
    
    def _loadFromAdapter(self, adapter, locators):
        locator = self.getLocator()
        properties = self._properties
        childs = self._childs
        if not locator in locators:
            raise PropertyError("Missing required property group", locator)
        del locators[locator]
        descriptors = dict()
        for d in adapter.listProperties(locator):
            descriptors[d] = None
        for p in properties.itervalues():
            p.reset(self)
            p.loadFromAdapter(self, adapter, locators, descriptors)
        for c in childs:
            c.reset(self)         
            c.loadFromAdapter(self, adapter, locators, descriptors)   
        if len(descriptors) > 0:
            raise PropertyError("Unknown property",
                                locator, descriptors.popitem()[0])
    
    def loadFromAdapter(self, adapter):
        locators = dict()
        for l in adapter.listLocations():
            locators[l] = None
        self._loadFromAdapter(adapter, locators)
        if len(locators) > 0:
            raise PropertyError("Unknown property group",
                                locators.keys()[0])
        
            
    def saveToAdapter(self, adapter):
        locator = self.getLocator()
        properties = self._properties
        childs = self._childs
        adapter.addLocation(locator)
        for p in properties.itervalues():
            p.saveToAdapter(self, adapter)
        for c in childs:
            c.saveToAdapter(self, adapter)
    
    def getStrValues(self):
        results = {}
        def setStrValue(section, name, value):
            if section in results:
                sections = results[section]
            else:
                sections = dict()
                results[section] = sections
            sections[name] = value            
        self.visitStrValues(setStrValue)
        return results


class RootPropertyBag(PropertyBag):
    
    VERSION = None
    _rootProperty = RootBagProperty()
    
    def __init__(self):
        PropertyBag.__init__(self)
        self.setParent(self)
        self.setupBag(self._rootProperty)
        

class Child(BaseChildProperty):

    def __init__(self, locator, bagClass, root=False, *args, **kwargs):
        BaseChildProperty.__init__(self, locator, root)
        if not issubclass(bagClass, PropertyBag):
            raise PropertyRuntimeError(("Invalid class specified (%s), "
                                       + "must be a PropertyBag subclass")
                                       % bagClass.__name__)
        self.bagClass = bagClass
        self.bagArgs = args
        self.bagKWArgs = kwargs

    def createChild(self, parent):
        child = self.bagClass(*self.bagArgs, **self.bagKWArgs)
        child.setParent(parent)
        return child


class DynamicChild(BaseChildProperty):
    
    def __init__(self, locator, linkAttr, getClassCB, root=False,  *args, **kwargs):
        BaseChildProperty.__init__(self, locator, root)
        self.linkAttr = linkAttr
        self.getClassCB = getClassCB
        self.bagArgs = args
        self.bagKWArgs = kwargs
        
    def setup(self, cls, attr):    
        BaseChildProperty.setup(self, cls, attr)        
        self.addPostChecks(cls, self.linkAttr, self._updateChildClass)

    def createChild(self, parent):
        val = self._getLinkValue(parent)
        cls = self.getClassCB(parent, val)
        if not cls:
            return None
        previous = self._getPreviousChild(parent)
        self.bagKWArgs['previous'] = previous
        next = cls(*self.bagArgs, **self.bagKWArgs)
        next.setParent(parent)
        return next

    def _getPreviousChild(self, obj):
        return (self.isSet(obj) or None) and self.getValue(obj)
    
    def _getLinkValue(self, obj):
        return ((hasattr(obj, self.linkAttr) or None) 
                and getattr(obj, self.linkAttr))

    def _updateChildClass(self, parent, attr, value):
        #if not already setup, let the setup do the work...
        if not hasattr(parent, self.attr):
            return
        cls = self.getClassCB(parent, value)
        child = self._getPreviousChild(parent)
        if cls == None and child != None:
            self.setValueWithoutChecks(parent, None)
            return
        if cls != None and (child == None or not child.__class__ == cls):
            self.bagKWArgs['previous'] = child
            child = cls(*self.bagArgs, **self.bagKWArgs)
            child.setParent(parent)
            child.setupBag(self)
            self.setValueWithoutChecks(parent, child)


class ChildList(BaseChildProperty):

    def __init__(self, locator, bagClass, root=False, *args, **kwargs):
        BaseChildProperty.__init__(self, locator, root)
        if not issubclass(bagClass, PropertyBag):
            raise PropertyRuntimeError(("Invalid class specified (%s), "
                                       + "must be a PropertyBag subclass")
                                       % bagClass.__name__)
        self.bagClass = bagClass
        self.bagArgs = args
        self.bagKWArgs = kwargs

    def reset(self, obj):
        del self.getValue(obj)[:]
        
    def getBags(self, obj):
        return self.getValue(obj)
    
    def createBags(self, obj, locators):        
        locator = obj.getLocator() + self.locator
        bags = self.getValue(obj)
        for l in locators:
            if l[:-1] != locator:
                continue
            index = int(l[-1]) - 1
            bags.addItemAt(index)
        return bags
    
    def getLocator(self, obj):
        return BaseChildProperty.getLocator(self, obj) + (str(obj._index + 1),)
    
    def checkItem(self, obj, item):
        if not isinstance(item, self.bagClass):
            raise PropertyError(("Cannot use class %s with "
                                 + "list attribute '%s'")
                                 % (item.__class__.__name__, self.attr),
                                 obj.getLocator(), self.descriptor)
    
    def createItem(self, parent):        
        item = self.bagClass(*self.bagArgs, **self.bagKWArgs)
        item.setParent(parent)
        return item
    
    def bindItem(self, parent, item, index):
        item.setParent(parent)
        item._index = index
        item.setupBag(self)
        
    def createChild(self, parent):
        return PropertyList(self, parent)


class ChildDict(BaseChildProperty):

    def __init__(self, locator, bagClass, root=False, *args, **kwargs):
        BaseChildProperty.__init__(self, locator, root)
        if not issubclass(bagClass, PropertyBag):
            raise PropertyRuntimeError(("Invalid class specified (%s), "
                                       + "must be a PropertyBag subclass")
                                       % bagClass.__name__)
        self.bagClass = bagClass
        self.bagArgs = args
        self.bagKWArgs = kwargs

    def reset(self, obj):
        self.getValue(obj).clear()
        
    def getBags(self, obj):
        return self.getValue(obj).values()
    
    def createBags(self, obj, locators):        
        locator = obj.getLocator() + self.locator
        bags = self.getValue(obj)
        for l in locators:
            if l[:-1] != locator:
                continue
            bags.addItem(l[-1])
        return bags.values()
    
    def getLocator(self, obj):
        return BaseChildProperty.getLocator(self, obj) + (str(obj._name),)
    
    def checkItem(self, obj, item):
        if not isinstance(item, self.bagClass):
            raise PropertyError(("Cannot use class %s with "
                                 + "dict attribute '%s'")
                                 % (item.__class__.__name__, self.attr),
                                 obj.getLocator(), self.descriptor)
    
    def createItem(self, parent):        
        item = self.bagClass(*self.bagArgs, **self.bagKWArgs)
        item.setParent(parent)
        return item
    
    def bindItem(self, parent, item, name):
        item.setParent(parent)
        item._name = name
        item.setupBag(self)
        
    def createChild(self, parent):
        return PropertyDict(self, parent)
    
    
class Integer(ValueProperty):
    
    def __init__(self, descriptor, default=None, required=False, unsigned=False):
        ValueProperty.__init__(self, descriptor, default, required)
        self._unsigned = unsigned
    
    def checkValue(self, value):
        return ((isinstance(value, int) or isinstance(value, long))
                and ((not self._unsigned) or (value >= 0)))
    
    def str2val(self, strval):
        return long(strval)
    
    def val2str(self, value):
        return str(value)

class Float(ValueProperty):
    
    def __init__(self, descriptor, default=None, required=False):
        ValueProperty.__init__(self, descriptor, default, required)
    
    def checkValue(self, value):
        return (isinstance(value, float))
    
    def str2val(self, strval):
        return float(strval)
    
    def val2str(self, value):
        return str(value)


class Boolean(ValueProperty):
    
    def __init__(self, descriptor, default=None, required=False):
        ValueProperty.__init__(self, descriptor, default, required)
    
    def checkValue(self, value):
        return isinstance(value, bool)
    
    def str2val(self, strval):
        if str(strval).upper() in ["TRUE", "ON", "1"]:
            return True
        if str(strval).upper() in ["FALSE", "OFF", "0"]:
            return False
        raise TypeError, "Invalid boolean value '%s'" % str(strval)
    
    def val2str(self, value):
        if value:
            return "True"
        else:
            return "False"


class Fraction(ValueProperty):
    
    def __init__(self, descriptor, default=None, required=False, unsigned=False):
        ValueProperty.__init__(self, descriptor, default, required)
        self._unsigned = unsigned
    
    def checkValue(self, value):
        return (isinstance(value, tuple) 
                and (len(value) == 2)
                and (isinstance(value[0], int) or isinstance(value[0], long))
                and (isinstance(value[1], int) or isinstance(value[1], long))
                and (value[1] > 0)
                and ((not self._unsigned) or (value[0] >= 0)))
    
    def str2val(self, strval):
        num, denom = strval.split('/')
        return int(num), int(denom)
    
    def val2str(self, value):
        num, denom = value
        return str(num) + '/' + str(denom)


class String(ValueProperty):
    
    def __init__(self, descriptor, default=None, required=False):
        ValueProperty.__init__(self, descriptor, default, required)
    
    def checkValue(self, value):
        return isinstance(value, str) or isinstance(value, unicode)


class Enum(ValueProperty):
    """
    The specified enum must be a flumotion.common.enum.EnumClass instance,
    and all its values must be lowercase.
    """
    
    def __init__(self, descriptor, flumotionEnum, default=None, required=False):
        ValueProperty.__init__(self, descriptor, default, required)
        self._enum = flumotionEnum
    
    def checkValue(self, value):      
        #FIXME: Should check the type  
        return value in self._enum
    
    def str2val(self, strval):
        name = strval.lower().strip()
        for val in self._enum:
            if val.nick.lower() == name:
                return val
        raise TypeError, "Invalid enum value '%s'" % strval
    
    def val2str(self, value):
        return value.nick


class DynEnumChild(DynamicChild):
    
    def __init__(self, locator, linkAttr, bagClasses, 
                 root=False, *args, **kwargs):
        DynamicChild.__init__(self, locator, linkAttr, self._getBagClass, 
                              root, *args, **kwargs)
        self.bagClasses = {}
        for k, c in bagClasses.iteritems():
            if not issubclass(c, PropertyBag):
                raise PropertyRuntimeError(("Invalid class specified (%s), "
                                            + "must be a PropertyBag subclass")
                                            % c.__name__)
            self.bagClasses[k] = c
    
    def _getBagClass(self, obj, value):
        if value == None:
            return None
        return self.bagClasses.get(value, None)


class DateTime(ValueProperty):
    
    _template = re.compile("([0-9]{4})[-/]([01][0-9])[-/]([0-3][0-9]) +"
                           "([0-2][0-9]):([0-5][0-9]):([0-5][0-9])")
    
    def __init__(self, descriptor, default=None, required=False):
        ValueProperty.__init__(self, descriptor, default, required)
    
    def checkValue(self, value):
        return isinstance(value, datetime.datetime)
    
    def str2val(self, strval):
        match = self._template.match(strval)
        if not match:
            raise TypeError, "Invalid datetime value '%s'" % str(strval)
        values = map(int, match.groups())
        return datetime.datetime(*values)
    
    def val2str(self, value):
        return ("%04d/%02d/%02d %02d:%02d:%02d" 
                % (value.year, value.month, value.day,
                   value.hour, value.minute, value.second))


class VirtualPath(ValueProperty):
    
    def __init__(self, descriptor, default=None, required=False):
        ValueProperty.__init__(self, descriptor, default, required)
    
    def checkValue(self, value):
        return isinstance(value, virtualpath.VirtualPath)
    
    def str2val(self, strval):
        return virtualpath.VirtualPath(strval)
    
    def val2str(self, value):
        return str(value)
