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

from flumotion.transcoder import log, utils
from flumotion.transcoder.enums import NotificationTriggerEnum
from flumotion.transcoder.admin import adminconsts, adminelement
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
        self.warning("Data retrieval failed for %s '%s': %s", 
                     self.__class__.__name__, self.getLabel(), 
                     log.getFailureMessage(failure))
        self.debug("Data retrieval traceback:\n%s",
                   log.getFailureTraceback(failure))
        #Propagate failures
        return failure


    ## Overriden Methods ##
    
    def _doPrepareInit(self, chain):
        def waitDatasource(result):
            to = adminconsts.WAIT_DATASOURCE_TIMEOUT
            d = self._dataSource.waitReady(to)
            # Keep the result value
            d.addCallback(utils.overrideResult, result)
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
        self.warning("Store %s '%s' data source error: %s",
                     self.__class__.__name__, self.getLabel(),
                     log.getFailureMessage(failure))
        self.debug("Datasource traceback:\n%s",
                   log.getFailureTraceback(failure))
        return failure
        
