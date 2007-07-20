# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.transcoder import log, utils
from flumotion.transcoder.admin.enums import NotificationTypeEnum
from flumotion.transcoder.admin.datastore.basestore import MetaStore


class BaseNotification(object):

    __metaclass__ = MetaStore
    
    __getters__ = {"basic":
                       {"getIdentifier": ("identifier", None),
                        "getType":        ("type", None),
                        "getTriggers":    ("triggers", None)}}
                        
    
    @staticmethod
    def _admin_overridable_getter_builder(getterName, propName, funcName):
        def getter(self):
            value = getattr(self._data, propName, None)
            if value != None: return utils.deepCopy(value)
            return utils.deepCopy(getattr(self._admin, funcName)())
        return getter
    
    def __init__(self, data, admin, customer, profile, target):
        self._data = data
        self._admin = admin
        self._customer = customer
        self._profile = profile
        self._target = target

    def getCustomer(self):
        return self._customer
    
    def getProfile(self):
        return self._profile
    
    def getTarget(self):
        return self._target
    

class EMailNotification(BaseNotification):
    
    __getters__ = {"basic":
                       {"getAttachments": ("attachments", set([])),
                        "getRecipients":  ("recipients", dict())},
                   "admin_overridable":
                       {"getSubjectTemplate": ("subjectTemplate", 
                                               "getMailSubjectTemplate"),
                        "getBodyTemplate":    ("bodyTemplate", 
                                               "getMailBodyTemplate"),
                        "getTimeout":         ("timeout", 
                                               "getMailTimeout"),
                        "getRetryMax":        ("retryMax", 
                                               "getMailRetryMax"),
                        "getRetrySleep":      ("retrySleep", 
                                               "getMailRetrySleep")}}
                        
    
    def __init__(self, data, admin, customer, profile, target):
        BaseNotification.__init__(self, data, admin, customer, profile, target)
        
        
class GETRequestNotification(BaseNotification):

    __getters__ = {"basic":
                       {"getRequestTemplate": ("requestTemplate", set([]))},
                   "admin_overridable":
                       {"getTimeout":    ("timeout", 
                                          "getHTTPRequestTimeout"),
                        "getRetryMax":   ("retryMax", 
                                          "getHTTPRequestRetryMax"),
                        "getRetrySleep": ("retrySleep", 
                                          "getHTTPRequestRetrySleep")}}
    
    def __init__(self, data, admin, customer, profile, target):
        BaseNotification.__init__(self, data, admin, customer, profile, target)
        
        
_notifLookup = {NotificationTypeEnum.get_request: GETRequestNotification,
                NotificationTypeEnum.email: EMailNotification}


def NotificationFactory(data, admin, customer, profile, target):
    assert data.type in _notifLookup
    return _notifLookup[data.type](data, admin, customer, profile, target)
