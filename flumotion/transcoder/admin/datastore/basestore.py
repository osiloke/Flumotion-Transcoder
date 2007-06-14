# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from twisted.internet import defer

from flumotion.transcoder import log
from flumotion.transcoder.admin import adminelement
from flumotion.transcoder.admin.waiters import CounterWaiters
from flumotion.transcoder.admin.datasource import datasource


def _buildOverridableGetter(getterName, propertyName):
    def getter(self):
        value = getattr(self._data, propertyName, None)
        if value != None: return value
        if hasattr(self._parent, getterName):
            return getattr(self._parent, getterName)()
        return None
    return getter

def _buildDefaultGetter(propertyName, staticValue):
    def getter(self):
        value = getattr(self._data, propertyName, None)
        if value != None: return value
        return staticValue
    return getter

def _buildSimpleGetter(propertyName):
    def getter(self):
        return getattr(self._data, propertyName, None)
    return getter


class MetaStore(type):
    
    def __init__(cls, name, bases, dct):
        super(MetaStore, cls).__init__(name, bases, dct)
        props = getattr(cls, "__simple_properties__", [])
        for propertyName in props:
            getterName = "get" + propertyName[0].upper() + propertyName[1:]
            if not hasattr(cls, getterName) :
                getter = _buildSimpleGetter(propertyName)
                setattr(cls, getterName, getter)
        props = getattr(cls, "__overridable_properties__", [])
        for propertyName in props:
            getterName = "get" + propertyName[0].upper() + propertyName[1:]
            if not hasattr(cls, getterName) :
                getter = _buildOverridableGetter(getterName, propertyName)
                setattr(cls, getterName, getter)
        props = getattr(cls, "__default_properties__", {})
        for propertyName, staticValue in props.iteritems():
            getterName = "get" + propertyName[0].upper() + propertyName[1:]
            if not hasattr(cls, getterName) :
                getter = _buildDefaultGetter(propertyName, staticValue)
                setattr(cls, getterName, getter)


class BaseStore(adminelement.AdminElement):
    
    __metaclass__ = MetaStore
    
    def __init__(self, logger, parent, dataSource, data, listenerInterface):
        assert datasource.IDataSource.providedBy(dataSource)
        adminelement.AdminElement.__init__(self, logger, parent, 
                                           listenerInterface)
        self._data = data
        self._dataSource = dataSource


    ## Public Methods ##


    ## Overriden Methods ##
    
    def _doPrepareInit(self, chain):
        def waitDatasource(result):
            d = self._dataSource.waitReady
            # Keep the result value
            d.addCallback(lambda r, v: v, result)
            return d
        chain.addCallback(waitDatasource)
        chain.addErrback(self.__ebDataSourceError)

    def _doPrepareActivation(self, chain):
        #FIXME: Remove this, its only for testing
        from twisted.internet import reactor, defer
        def async(result):
            d = defer.Deferred()
            reactor.callLater(0.2, d.callback, result)
            return d
        chain.addCallback(async)
            

    ## Private Methods ##

    def __ebDataSourceError(self, failure):
        #FIXME: Error Handling
        self.warning("Store data source error: %s",
                     log.getFailureMessage(failure))
        return failure
        
