# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.transcoder import log, defer, utils
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.waiters import CounterWaiters
from flumotion.transcoder.admin.enums import NotificationTriggerEnum
from flumotion.transcoder.admin.adminelement import AdminElement
from flumotion.transcoder.admin.datasource import datasource


def _basic_getter_builder(getterName, propertyName, default):
    def getter(self):
        value = getattr(self._data, propertyName, None)
        if value == None: value = default
        return utils.deepCopy(value)
    return getter

def _parent_overridable_getter_builder(getterName, propertyName, funcName=None):
    def getter(self):
        value = getattr(self._data, propertyName, None)
        if value != None: return utils.deepCopy(value)
        parentGetterName = funcName or getterName
        if hasattr(self._parent, parentGetterName):
            return getattr(self._parent, parentGetterName)()
        return None
    return getter

_getter_builders = {"basic": _basic_getter_builder,
                    "parent_overridable": _parent_overridable_getter_builder}

_setter_builders = {}


class MetaStore(type):

    def __init__(cls, name, bases, dct):

        def createGetters(tag, props):
            getterBuilderName = "_%s_getter_builder" % tag
            defaultGetterBuilder = _getter_builders.get(tag, None)
            getterBuilder = getattr(cls, getterBuilderName, defaultGetterBuilder)
            if getterBuilder:
                for getterName, params in props.items():
                    if not hasattr(cls, getterName) :
                        getter = getterBuilder(getterName, *params)
                        if getter:
                            setattr(cls, getterName, getter)

        def createSetters(tag, props):
            setterBuilderName = "_%s_setter_builder" % tag
            defaultSetterBuilder = _setter_builders.get(tag, None)
            setterBuilder = getattr(cls, setterBuilderName, defaultSetterBuilder)
            if setterBuilder:
                for setterName, params in props.items():
                    if not hasattr(cls, setterName) :
                        setter = setterBuilder(setterName, *params)
                        if setter:
                            setattr(cls, setterName, setter)
        
        super(MetaStore, cls).__init__(name, bases, dct)
        
        properties = getattr(cls, "__getters__", {})
        for tag, definition in properties.items():
            createGetters(tag, definition)
        properties = getattr(cls, "__setters__", {})
        for tag, definition in properties.items():
            createSetters(tag, definition)


class BaseStore(AdminElement):
    
    __metaclass__ = MetaStore
    
    def __init__(self, logger, parent, dataSource, data, listenerInterface):
        assert datasource.IDataSource.providedBy(dataSource)
        AdminElement.__init__(self, logger, parent, 
                                           listenerInterface)
        self._data = data
        self._dataSource = dataSource
        self._notifications = {} # {NotificationTriggerEnum: {identifier: BaseNotification}}


    ## Public Methods ##
    
    def getNotifications(self, trigger):
        assert isinstance(trigger, NotificationTriggerEnum)
        return self._notifications[trigger].values()
    
    def iterNotifications(self, trigger):
        assert isinstance(trigger, NotificationTriggerEnum)
        return self._notifications[trigger].itervalues()

    ## Protected Virtual Methods ##
    
    def _doRetrieveNotifications(self):
        return defer.succeed([])
    
    def _doWrapNotification(self, notificationData):
        raise NotImplementedError()


    ## Protectyed Methods ##

    def _retrievalFailed(self, failure):
        """
        Can be used by child class as retrieval errorback.
        """
        #FIXME: Better Error Handling ?
        log.notifyFailure(self, failure,
                          "Data retrieval failed for %s '%s'",
                          self.__class__.__name__, self.getLabel())
        #Propagate failures
        return failure


    ## Overriden Methods ##
    
    def _doPrepareInit(self, chain):
        def waitDatasource(result):
            to = adminconsts.WAIT_DATASOURCE_TIMEOUT
            d = self._dataSource.waitReady(to)
            # Keep the result value
            d.addCallback(defer.overrideResult, result)
            return d
        chain.addCallback(waitDatasource)
        chain.addErrback(self.__ebDataSourceError)
        # Retrieve and initialize the notifications
        chain.addCallback(self.__cbRetrieveNotifications)        

    def _doPrepareActivation(self, chain):
        pass


    ## Private Methods ##

    def __cbRetrieveNotifications(self, result):
        d = self._doRetrieveNotifications()
        d.addCallback(self.__cbWrapNotifications)
        d.addCallbacks(self.__cbNotificationsReceived, 
                       self._retrievalFailed,
                       callbackArgs=(result,))
        return d
        
    def __cbWrapNotifications(self, notifications):
        return [self._doWrapNotification(n) for n in notifications]
        
    def __cbNotificationsReceived(self, notifications, oldResult):
        self.log("Store %s '%s' received %d notifications",
                 self.__class__.__name__, self.getLabel(), len(notifications))
        bag = dict([(t, dict()) for t in NotificationTriggerEnum])
        for n in notifications:
            for t in n.getTriggers():
                bag[t][n.getIdentifier()] = n
        self._notifications = bag
        return oldResult

    def __ebDataSourceError(self, failure):
        #FIXME: Error Handling
        log.notifyFailure(self, failure,
                          "Store %s '%s' data source error",
                          self.__class__.__name__, self.getLabel())
        return failure
        
