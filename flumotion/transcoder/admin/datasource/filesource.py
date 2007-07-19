# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import os
import random
import shutil

from zope.interface import implements
from twisted.python import failure
from twisted.internet import defer

from flumotion.transcoder import log, inifile, utils
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.enums import ActivityTypeEnum
from flumotion.transcoder.admin.enums import ActivityStateEnum
from flumotion.transcoder.admin.enums import NotificationTypeEnum
from flumotion.transcoder.admin.enums import NotificationTriggerEnum
from flumotion.transcoder.admin.enums import MailAddressTypeEnum
from flumotion.transcoder.admin.enums import DocumentTypeEnum
from flumotion.transcoder.admin.datasource import dataprops
from flumotion.transcoder.admin.datasource import datasource
from flumotion.transcoder.admin.datasource.datasource import InitializationError


class ImmutableWrapper(object):
    
    def __init__(self, identifier, fields):
        self.__dict__['_identifier'] = identifier
        self.__dict__['_fields'] = fields
        
    def __getattr__(self, attr):
        if attr == 'identifier':
            return self.__dict__['_identifier']
        fields = self.__dict__['_fields']
        if not (attr in fields):
            raise AttributeError, attr
        return fields[attr]
    
    def __setattr__(self, attr, value):
        raise AttributeError, attr


class ImmutableDataWrapper(object):
    
    def __init__(self, data, identifier, hidden=[], readonly=[]):
        self.__dict__['_identifier'] = identifier
        self.__dict__['_data'] = data
        self.__dict__['_hidden'] = set(hidden)
        self.__dict__['_readonly'] = set(readonly)        
        
    def __getattr__(self, attr):
        if attr == 'identifier':
            return self.__dict__['_identifier']
        hidden = self.__dict__['_hidden']
        if attr in hidden:
            raise AttributeError, attr
        data = self.__dict__['_data']
        return getattr(data, attr)
    
    def __setattr__(self, attr, value):
        raise AttributeError, attr
        
    def _getData(self):
        return self.__dict__['_data']


class MutableDataWrapper(object):
    
    def __init__(self, parent, template, identifier=None, 
                 data=None, fields=None):
        self._parent = parent
        self._template = template
        self._identifier = identifier
        self._data = data
        if fields:
            self._fields = utils.deepCopy(fields)
        elif data:
            self._reset()
        else:
            self._fields = utils.deepCopy(template["defaults"])
        
    def _reset(self):
        if not self._data: return
        data = self._data
        fields = dict()
        for key, default in self._template["defaults"].iteritems():
            val = getattr(data, key, default)
            fields[key] = utils.deepCopy(val)
        self._fields = fields

    def _store(self):
        if self.state in set([ActivityStateEnum.done,
                              ActivityStateEnum.failed]):
            # Do not store 'done' and 'failed' activities,
            if self._data:
                # Delete if the activity is terminated
                return self._delete()
            # Simulate the activity has been saved
            self._identifier = utils.genUniqueIdentifier()
            return False
        if not self._data:
            data = self._template['class']()
            key = utils.genUniqueIdentifier()
            self._parent[key] = data
            self._identifier = key
            self._data = data
        assert self._identifier in self._parent
        for attr, value in self._fields.items():
            setattr(self._data, attr, utils.deepCopy(value))
        return True
    
    def _delete(self):
        if self._data:
            assert self._identifier in self._parent
            del self._parent[self._identifier]
            self._data = None
            return True
        return False

    def _clone(self):
        new = self.__class__(self._template, self._data, self._fields)
        new.__dict__["_changed"] = self._changed
        return new
    
    def __getattr__(self, attr):
        if attr.startswith('_'):
            if not attr in self.__dict__:
                raise AttributeError, attr
            return self.__dict__[attr]
        if attr == 'identifier':
            return self.__dict__['_identifier']
        hidden = self.__dict__['_template']['hidden']
        if attr in hidden:
            raise AttributeError, attr
        fields = self.__dict__['_fields']
        if not attr in fields:
            raise AttributeError, attr
        return fields[attr]
    
    def __setattr__(self, attr, value):
        if attr.startswith('_'):
            self.__dict__[attr] = value
            return
        hidden = self._template['hidden']
        readonly = self._template['readonly']
        if (attr in hidden) or (attr in readonly):
            raise AttributeError, attr
        fields = self._fields
        fields[attr] = value


TRANS_ACT_TMPL = {'class': dataprops.TranscodingActivityData,
                  'defaults': {'type': ActivityTypeEnum.transcoding,
                               'state': ActivityStateEnum.unknown,
                               'label': "Unknown",
                               'startTime': None,
                               'lastTime': None,
                               'customerName': None,
                               'profileName': None,
                               'targetName': None,
                               'subtype': None,
                               'inputRelPath': None},
                  'hidden': set([]),
                  'readonly': set(['type'])}

NOT_ACT_TMPL = {'class': dataprops.TranscodingActivityData,
                  'defaults': {'type': ActivityTypeEnum.transcoding,
                               'state': ActivityStateEnum.unknown,
                               'label': None,
                               'startTime': None,
                               'lastTime': None,
                               'customerName': None,
                               'profileName': None,
                               'targetName': None,
                               'subtype': None,
                               'trigger': None,
                               'timeout': None,
                               'retryCount': None,
                               'retryMax': None,
                               'retrySleep': None,
                               'data': None},
                  'hidden': set([]),
                  'readonly': set(['type'])}


EMAIL_NOT_TMPL = {'type': NotificationTypeEnum.email,
                  'triggers': set([]),
                  'timeout': None,
                  'retryMax': None,
                  'retrySleep': None,
                  'subjectTemplate': None,
                  'bodyTemplate': None,
                  'attachments': set([DocumentTypeEnum.trans_report,
                                      DocumentTypeEnum.trans_config,
                                      DocumentTypeEnum.trans_log]),
                  'recipients': {}}


REQ_NOT_TMPL = {'type': NotificationTypeEnum.get_request,
                'triggers': set([]),
                'timeout': None,
                'retryMax': None,
                'retrySleep': None,
                'requestTemplate': None}


def _createReqNotif(wrapper, succeed, reqTmpl):
    if succeed:
        trigger = NotificationTriggerEnum.done
    else:
        trigger = NotificationTriggerEnum.failed
    fields = utils.deepCopy(REQ_NOT_TMPL)
    fields['triggers'] = set([trigger])
    fields['requestTemplate'] = reqTmpl
    ident = (wrapper.identifier, trigger, "req")
    return ImmutableWrapper(ident, fields)

def _createMailNotif(wrapper, succeed, recipients):
    if succeed:
        trigger = NotificationTriggerEnum.done
    else:
        trigger = NotificationTriggerEnum.failed
    fields = utils.deepCopy(EMAIL_NOT_TMPL)
    fields['triggers'] = set([trigger])
    t = MailAddressTypeEnum.to
    fields['recipients'][t] = utils.deepCopy(recipients)
    ident = (wrapper.identifier, trigger, "email")
    return ImmutableWrapper(ident, fields)


class FileDataSource(log.Loggable):
    
    logCategory = adminconsts.DATASOURCE_LOG_CATEGORY
    
    implements(datasource.IDataSource)
    
    def __init__(self, config):
        self._adminDataFile = config.dataFile
        self._activityDataFile = config.activityFile
        self._adminData = None
        self._activityData = None
    
    def initialize(self):
        self.debug("Initializing File Data Source")
        d = defer.Deferred()
        d.addCallback(utils.dropResult, self.__loadAdminData, 
                      self._adminDataFile)
        d.addCallback(self.__cbInitAdminData)
        d.addCallback(utils.dropResult, self.__loadActivityData,
                      self._activityDataFile)
        d.addCallback(self.__cbInitActivityData)
        d.addErrback(self.__ebInitializationFailed)
        d.callback(None)
        return d

    def waitReady(self, timeout=None):
        return defer.succeed(self)

    def retrieveDefaults(self):
        try:
            result = ImmutableDataWrapper(self._adminData, 
                                      "defaults", ['customers'])
            return defer.succeed(result)
        except Exception, e:
            msg = "Failed to retrieve default data"
            ex = datasource.RetrievalError(msg, cause=e)
            f = failure.Failure(ex)
            return defer.fail(f)
        
    def retrieveCustomers(self):
        try:
            result = [ImmutableDataWrapper(c, c.name, ['info', 'profiles'])
                      for c in self._adminData.customers
                      if c != None]
            return defer.succeed(result)
        except Exception, e:
            msg = "Failed to retrieve customers data"
            ex = datasource.RetrievalError(msg, cause=e)
            f = failure.Failure(ex)
            return defer.fail(f)
        
    def retrieveCustomerInfo(self, customerData):
        try:
            assert isinstance(customerData, ImmutableDataWrapper)
            data = customerData._getData()
            result = ImmutableDataWrapper(data.info, (data.name, "info"))
            return defer.succeed(result)
        except Exception, e:
            msg = "Failed to retrieve customer info data"
            ex = datasource.RetrievalError(msg, cause=e)
            f = failure.Failure(ex)
            return defer.fail(f)
        
    def retrieveProfiles(self, customerData):
        try:
            assert isinstance(customerData, ImmutableDataWrapper)
            result = [ImmutableDataWrapper(p, p.name, ['targets']) 
                      for p in customerData._getData().profiles
                      if p != None]
            return defer.succeed(result)
        except Exception, e:
            msg = "Failed to retrieve profiles data"
            ex = datasource.RetrievalError(msg, cause=e)
            f = failure.Failure(ex)
            return defer.fail(f)
        
    def retrieveGlobalNotifications(self):
        return defer.succeed([])
        
    def retrieveCustomerNotifications(self, customerData):
        return defer.succeed([])
        
    def retrieveProfileNotifications(self, profileData):
        try:
            assert isinstance(profileData, ImmutableDataWrapper)
            d = profileData._getData()
            assert isinstance(d, dataprops.ProfileData)
            result = []
            for req in d.notifyFailedRequests:
                if req:
                    result.append(_createReqNotif(profileData, False, req))
            for req in d.notifyDoneRequests:
                if req:
                    result.append(_createReqNotif(profileData, True, req))
            recipientsLine = d.notifyFailedMailRecipients
            if recipientsLine:
                recipients = utils.splitMailRecipients(recipientsLine)
                notification = _createMailNotif(profileData, False, recipients)
                result.append(notification)
            return defer.succeed(result)
        except Exception, e:
            msg = "Failed to retrieve profile notifications data"
            ex = datasource.RetrievalError(msg, cause=e)
            f = failure.Failure(ex)
            return defer.fail(f)
        
    def retrieveTargetNotifications(self, targetData):
        try:
            assert isinstance(targetData, ImmutableDataWrapper)
            d = targetData._getData()
            assert isinstance(d, dataprops.TargetData)
            result = []
            for req in d.notifyFailedRequests:
                if req:
                    result.append(_createReqNotif(targetData, False, req))
            for req in d.notifyDoneRequests:
                if req:
                    result.append(_createReqNotif(targetData, True, req))
            return defer.succeed(result)
        except Exception, e:
            msg = "Failed to retrieve target notifications data"
            ex = datasource.RetrievalError(msg, cause=e)
            f = failure.Failure(ex)
            return defer.fail(f)

    def retrieveTargets(self, profileData):
        try:
            assert isinstance(profileData, ImmutableDataWrapper)
            result = [ImmutableDataWrapper(t, t.name, ['config', 'type'])
                      for t in profileData._getData().targets
                      if t != None]
            return defer.succeed(result)
        except Exception, e:
            msg = "Failed to retrieve targets data"
            ex = datasource.RetrievalError(msg, cause=e)
            f = failure.Failure(ex)
            return defer.fail(f)
       
    def retrieveTargetConfig(self, targetData):
        try:
            assert isinstance(targetData, ImmutableDataWrapper)
            data = targetData._getData()
            result = ImmutableDataWrapper(data.config, (data.name, "config"),
                                      [], ['type'])
            return defer.succeed(result)
        except Exception, e:
            msg = "Failed to retrieve target config data"
            ex = datasource.RetrievalError(msg, cause=e)
            f = failure.Failure(ex)
            return defer.fail(f)

    def retrieveActivities(self, type, states=None):
        try:
            states = states and set(states)
            if type == ActivityTypeEnum.transcoding:
                parent = self._activityData.transcodings
                result = [MutableDataWrapper(parent, TRANS_ACT_TMPL, i, d)
                          for i, d in parent.iteritems()
                          if ((states == None) or (d.state in states))]
                return defer.succeed(result)
            if type == ActivityTypeEnum.notification:
                parent = self._activityData.notifications
                result = [MutableDataWrapper(parent, NOT_ACT_TMPL, i, d)
                          for i, d in parent.iteritems()
                          if ((states == None) or (d.state in states))]
                return defer.succeed(result)
            return defer.succeed([])
        except Exception, e:
            msg = "Failed to retrieve activities data"
            ex = datasource.RetrievalError(msg, cause=e)
            f = failure.Failure(ex)
            return defer.fail(f)

    def newActivity(self, type):
        assert isinstance(type, ActivityTypeEnum)
        if type == ActivityTypeEnum.transcoding:
            return MutableDataWrapper(self._activityData.transcodings, 
                                      TRANS_ACT_TMPL)
        else:
            raise NotImplementedError()

    def newCustomer(self, cusomerId):
        raise NotImplementedError()

    def newProfile(self, customerData):
        raise NotImplementedError()
    
    def newNotification(self, type, data):
        raise NotImplementedError()
    
    def newTarget(self, profileData):
        raise NotImplementedError()

    def newTargetConfig(self, targetData):
        raise NotImplementedError()
        
    def newReport(self, profileData):
        raise NotImplementedError()
        
    def newTargetReport(self, reportData):
        raise NotImplementedError()
        
    def newNotificationReport(self, reportData, notificationData):
        raise NotImplementedError()
        
    def store(self, *data):
        changed = False
        for mutable in data:
            if not isinstance(mutable, MutableDataWrapper):
                raise NotImplementedError()
            changed = changed or mutable._store()
        if not changed:
            return defer.succeed(self)
        d = self.__storeActivities(self._activityDataFile, self._activityData)
        d.addCallbacks(self.__cbActivitiesSaved,
                       self.__ebActivitiesSaveFailed)
        return d
        
    def reset(self, *data):
        for mutable in data:
            if not isinstance(mutable, MutableDataWrapper):
                raise NotImplementedError()
            mutable._reset()
        return defer.succeed(self)
        
    def delete(self, *data):
        changed = False
        for mutable in data:
            if not isinstance(mutable, MutableDataWrapper):
                raise NotImplementedError()
            changed = changed or mutable._delete() 
        if not changed:
            return defer.succeed(self)
        d = self.__storeActivities(self._activityDataFile, self._activityData)
        d.addCallbacks(self.__cbActivitiesSaved,
                       self.__ebActivitiesSaveFailed)
        return d


    ## Private Methods ##
    
    def __loadAdminData(self, filePath):
        self.debug("Loading admin data from '%s'", filePath)
        data = dataprops.AdminData()
        loader = inifile.IniFile();
        loader.loadFromFile(data, filePath)
        return data
        
    def __cbInitAdminData(self, data):
        self.debug("Initializing admin data")
        self._adminData = data
    
    def __loadActivityData(self, filePath):
        if os.path.exists(filePath):
            self.debug("Loading activity data from '%s'", filePath)
            try:
                data = dataprops.ActivitiesData()
                loader = inifile.IniFile();
                loader.loadFromFile(data, filePath)
                return data
            except Exception, e:
                self.warning("Activity file invalide or corrupted: %s",
                             log.getExceptionMessage(e))
                return dataprops.ActivitiesData()
        else:
            self.debug("No activitiy file found ('%s')", filePath)
            return defer.succeed(data)
    
    def __cbInitActivityData(self, data):
        self.debug("Initializing activity data")
        self._activityData = data
        changed = False
        for k, t in data.transcodings.items():
            if t.state in set([ActivityStateEnum.done,
                              ActivityStateEnum.failed]):
                del data.transcodings[k]
                changed = True
        if changed:
            return self.__storeActivities(self._activityDataFile, data)
        
        
    def __ebInitializationFailed(self, failure):
        if failure.check(InitializationError):
            return failure
        msg = "Failed to initialize file data-source"
        raise InitializationError(msg, cause=failure.value)        

    def __storeActivities(self, newFile, data):
        oldFile = newFile + ".old"
        try:
            if os.path.exists(newFile):
                shutil.move(newFile, oldFile)
        except Exception, e:
            msg = "Failed to store file data-source"
            ex = datasource.StoringError(msg, cause=e)
            f = failure.Failure(ex)
            return defer.fail(f)
                
        try:
            saver = inifile.IniFile();
            saver.saveToFile(data, newFile)
        except Exception, e:
            try:
                if os.path.exists(oldFile):
                    shutil.move(oldFile, newFile)
            except Exception, e:
                pass
            msg = "Failed to store file data-source"
            ex = datasource.StoringError(msg, cause=e)
            f = failure.Failure(ex)
            return defer.fail(f)
        
        return defer.succeed(newFile)
    
    def __cbActivitiesSaved(self, file):
        if file: 
            self.log("Activities successfuly stored in file '%s'", file)
        return self
        
    def __ebActivitiesSaveFailed(self, failure):
        self.logFailure(failure, "Fail to save activities")
        return failure

