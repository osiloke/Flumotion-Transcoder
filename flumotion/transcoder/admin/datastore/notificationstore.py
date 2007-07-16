# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.transcoder import log

from flumotion.transcoder.admin.enums import NotificationTypeEnum


class BaseNotification(object):
    
    def __init__(self, data, admin, customer, profile, target):
        self._data = data
        self._admin = admin
        self._customer = customer
        self._profile = profile
        self._target = target

    def getIdentifier(self):
        return self._data.identifier

    def getCustomer(self):
        return self._customer
    
    def getProfile(self):
        return self._profile
    
    def getTarget(self):
        return self._target
    
    def getType(self):
        return self._data.type
    
    def getTriggers(self):
        return self._data.triggers
    

class EMailNotification(BaseNotification):
    
    def __init__(self, data, admin, customer, profile, target):
        BaseNotification.__init__(self, data, admin, customer, profile, target)
        
    def getSubjectTemplate(self):
        d, a = self._data, self._admin
        return d.subjectTemplate or a.getMailSubjectTemplate()
    
    def getBodyTemplate(self):
        d, a = self._data, self._admin
        return d.bodyTemplate or a.getMailBodyTemplate()

    def getAttachments(self):
        return self._data.attachments or set([])
    
    def getAddresses(self):
        return dict([(k, list(v)) for k, v in self._data.addresses])        

        
class GETRequestNotification(BaseNotification):
    
    def __init__(self, data, admin, customer, profile, target):
        BaseNotification.__init__(self, data, admin, customer, profile, target)

    def getRequestTemplate(self):
        return self._data.requestTemplate
    
    def getRetryTimeout(self):
        d, a = self._data, self._admin
        return d.retryTimeout or a.getGETRequestTimeout()
    
    def getRetryCount(self):
        d, a = self._data, self._admin
        return d.retryCount or a.getGETRequestRetryCount()
    
    def getRetrySleep(self):
        d, a = self._data, self._admin
        return d.retrySleep or a.getGETRequestRetrySleep()
        
        
_notifLookup = {NotificationTypeEnum.get_request: GETRequestNotification,
                NotificationTypeEnum.email: EMailNotification}


def NotificationFactory(data, admin, customer, profile, target):
    assert data.type in _notifLookup
    return _notifLookup[data.type](data, admin, customer, profile, target)
