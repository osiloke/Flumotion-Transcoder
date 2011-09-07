# vi:si:et:sw=4:sts=4:ts=4

# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007,2008,2009 Fluendo, S.L.
# Copyright (C) 2010,2011 Flumotion Services, S.A.
# All rights reserved.
#
# This file may be distributed and/or modified under the terms of
# the GNU Lesser General Public License version 2.1 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.LGPL" in the source distribution for more information.
#
# Headers in this file shall remain intact.

from zope.interface import Attribute, implements

from flumotion.inhouse import log, defer, utils, waiters

from flumotion.transcoder.admin import adminconsts, interfaces, adminelement
from flumotion.transcoder.admin.enums import NotificationTriggerEnum
from flumotion.transcoder.admin.datasource import datasource


class IBaseStore(interfaces.IAdminInterface):

    identifier = Attribute("Unique identifier of the store element")
    label      = Attribute("Label of the store element")

    def getAdminStore(self):
        pass


class IStoreElement(interfaces.IAdminInterface):
    pass


class INotificationProvider(interfaces.IAdminInterface):

    def getNotificationStores(self, trigger):
        pass

    def iterNotificationStores(self, trigger):
        pass


## Proxy Descriptor ##

class ReadOnlyProxy(object):
    def __init__(self, fieldName, default=None):
        self._fieldName = fieldName
        self._default= default
    def __get__(self, obj, type=None):
        value = getattr(obj._data, self._fieldName, None)
        if value == None: value = self._default
        return utils.deepCopy(value)
    def __set__(self, obj, value):
        raise AttributeError("Attribute is read-only")
    def __delete__(self, obj):
        raise AttributeError("Attribute cannot be deleted")


class SimpleStore(object):
    implements(IBaseStore)

    identifier = None
    label = None

    def __init__(self, parentStore, identifier=None, label=None):
        object.__setattr__(self, "parent", parentStore)
        if identifier is not None:
            object.__setattr__(self, "identifier", identifier)
        if label is not None:
            object.__setattr__(self, "label", label)

    def __setattr__(self, attr, value):
        """
        Prevent adding new attributes.
        Allow early detection of attributes spelling mistakes.
        """
        if attr.startswith("_") or hasattr(self, attr):
            return object.__setattr__(self, attr, value)
        raise AttributeError("Attribute %s cannot be added to %s" % (attr, self))


class DataStore(SimpleStore):

    def __init__(self, parentStore, data, identifier=None, label=None):
        SimpleStore.__init__(self, parentStore, identifier or data.identifier, label)
        self._data = data


class StoreElement(adminelement.AdminElement):
    implements(IBaseStore, IStoreElement)

    def __init__(self, logger, parentStore, data, identifier=None, label=None):
        adminelement.AdminElement.__init__(self, logger, parentStore,
                                           identifier or data.identifier, label)
        self._data = data


class NotifyStore(StoreElement):
    implements(INotificationProvider)

    def __init__(self, logger, parentStore, dataSource, data, identifier=None, label=None):
        assert datasource.IInformationSource.providedBy(dataSource)
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

