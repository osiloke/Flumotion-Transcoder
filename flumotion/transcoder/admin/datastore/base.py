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

from flumotion.inhouse import log, defer, utils, annotate, waiters

from flumotion.transcoder.admin import adminconsts, interfaces, adminelement
from flumotion.transcoder.admin.enums import NotificationTriggerEnum
from flumotion.transcoder.admin.datasource import datasource


class IBaseStore(interfaces.IAdminInterface):
    
    def getAdminStore(self):
        pass

    def getIdentifier(self):
        pass
    
    def getLabel(self):
        pass


class IStoreWithNotification(IBaseStore):
    
    def getNotificationStores(self, trigger):
        pass
    
    def iterNotificationStores(self, trigger):
        pass


## Method Generators ##

def genGetter(getterName, propertyName, default=None):
    def getter(self):
        value = getattr(self._data, propertyName, None)
        if value == None: value = default
        return utils.deepCopy(value)
    annotate.addAnnotationMethod("genGetter", getterName, getter)


class BaseStore(adminelement.AdminElement):
    implements(IStoreWithNotification)
    
    def __init__(self, logger, parentStore, dataSource, data):
        assert datasource.IDataSource.providedBy(dataSource)
        adminelement.AdminElement.__init__(self, logger, parentStore)
        self._data = data
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
        
    def __cbWrapNotifications(self, notifDataList):
        return [self._doWrapNotification(n) for n in notifDataList]
        
    def __cbNotificationsReceived(self, notifStores, oldResult):
        self.log("Store %s '%s' received %d notifications",
                 self.__class__.__name__, self.getLabel(), len(notifStores))
        bag = dict([(t, dict()) for t in NotificationTriggerEnum])
        for notifStore in notifStores:
            for t in notifStore.getTriggers():
                bag[t][notifStore.getIdentifier()] = notifStore
        self._notifications = bag
        return oldResult

    def __ebDataSourceError(self, failure):
        #FIXME: Error Handling
        log.notifyFailure(self, failure,
                          "Store %s '%s' data source error",
                          self.__class__.__name__, self.getLabel())
        return failure
        
