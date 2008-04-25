# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import Attribute, implements

from flumotion.inhouse import log, defer, utils, annotate, waiters

from flumotion.transcoder.admin import adminconsts, interfaces, adminelement
from flumotion.transcoder.admin.enums import NotificationTriggerEnum
from flumotion.transcoder.admin.datasource import datasource


class IBaseStore(interfaces.IAdminInterface):
    
    identifier = Attribute("Unique identifier of the store element")
    label = Attribute("Label of the store element")
    
    def getAdminStore(self):
        pass


class IStoreElement(interfaces.IAdminInterface):
    pass


class INotificationProvider(interfaces.IAdminInterface):
    
    def getNotificationStores(self, trigger):
        pass
    
    def iterNotificationStores(self, trigger):
        pass


## Class Annotations ##

def readonly_proxy(propertyName, fieldName=None, default=None,
                   getterName=None, getterFactory=None):
    if fieldName is None:
        fieldName = propertyName 
    if getterName is None:
        getterName = "get" + propertyName[0].upper() + propertyName[1:]
    
    if getterFactory is None:
        def getter(self):
            value = getattr(self._data, fieldName, None)
            if value == None: value = default
            return utils.deepCopy(value)
        getter.__name__ = getterName
    else:
        getter = getterFactory(getterName, propertyName, fieldName, default)
    
    annotate.injectAttribute("readonly_proxy", getterName, getter)
    prop = property(getter)
    annotate.injectAttribute("readonly_proxy", propertyName, prop)

def readwrite_proxy(propertyName, fieldName=None, default=None,
                    getterName=None, setterName=None,
                    getterFactory=None, setterFactory=None):
    if fieldName is None:
        fieldName = propertyName 
    if getterName is None:
        getterName = "get" + propertyName[0].upper() + propertyName[1:]
    if setterName is None:
        setterName = "set" + propertyName[0].upper() + propertyName[1:]
    
    if getterFactory is None:
        def getter(self):
            value = getattr(self._data, fieldName, None)
            if value == None: value = default
            return utils.deepCopy(value)
        getter.__name__ = getterName
    else:
        getter = getterFactory(getterName, propertyName, fieldName, default)

    if setterFactory is None:
        def setter(self, value):
            setattr(self._data, fieldName, utils.deepCopy(value))
        setter.__name__ = setterName
    else:
        setter = setterFactory(setterName, propertyName, fieldName)
    
    annotate.injectAttribute("readwrite_proxy", getterName, getter)
    annotate.injectAttribute("readwrite_proxy", setterName, setter)
    prop = property(getter, setter)
    annotate.injectAttribute("readwrite_proxy", propertyName, prop)


class SimpleStore(annotate.Annotable):
    implements(IBaseStore)
    
    identifier = None
    label = None
    
    def __init__(self, parentStore, identifier=None, label=None):
        self.parent = parentStore
        if identifier is not None:
            self.identifier = identifier
        if label is not None:
            self.label = label


class DataStore(SimpleStore):
    
    def __init__(self, parentStore, data, identifier=None, label=None):
        SimpleStore.__init__(self, parentStore, identifier or data.identifier, label)
        self._data = data


class StoreElement(adminelement.AdminElement, annotate.Annotable):
    implements(IBaseStore, IStoreElement)
    
    def __init__(self, logger, parentStore, data, identifier=None, label=None):
        adminelement.AdminElement.__init__(self, logger, parentStore,
                                           identifier or data.identifier, label)
        self._data = data


class NotifyStore(StoreElement):
    implements(INotificationProvider)
    
    def __init__(self, logger, parentStore, dataSource, data, identifier=None, label=None):
        assert datasource.IDataSource.providedBy(dataSource)
        StoreElement.__init__(self, logger, parentStore, data, identifier, label)
        self._dataSource = dataSource
        self._notifications = {} # {NotificationTriggerEnum: {identifier: NotificationStore}}


    ## Public Methods ##
    
    def getNotificationStores(self, trigger):
        assert isinstance(trigger, NotificationTriggerEnum)
        return self._notifications[trigger].values()
    
    def iterNotificationStores(self, trigger):
        assert isinstance(trigger, NotificationTriggerEnum)
        return self._notifications[trigger].itervalues()


    ## Protected Virtual Methods ##
    
    def _doRetrieveNotifications(self):
        return defer.succeed([])
    
    def _doWrapNotification(self, notifData):
        raise NotImplementedError()


    ## Protectyed Methods ##

    def _retrievalFailed(self, failure):
        """
        Can be used by child class as retrieval errorback.
        """
        #FIXME: Better Error Handling ?
        log.notifyFailure(self, failure,
                          "Data retrieval failed for %s '%s'",
                          self.__class__.__name__, self.label)
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
        
    def __cbWrapNotifications(self, notifDataList):
        return [self._doWrapNotification(n) for n in notifDataList]
        
    def __cbNotificationsReceived(self, notifStores, oldResult):
        self.log("Store %s '%s' received %d notifications",
                 self.__class__.__name__, self.label, len(notifStores))
        bag = dict([(t, dict()) for t in NotificationTriggerEnum])
        for notifStore in notifStores:
            for t in notifStore.triggers:
                bag[t][notifStore.identifier] = notifStore
        self._notifications = bag
        return oldResult

    def __ebDataSourceError(self, failure):
        #FIXME: Error Handling
        log.notifyFailure(self, failure,
                          "Store %s '%s' data source error",
                          self.__class__.__name__, self.label)
        return failure
        
