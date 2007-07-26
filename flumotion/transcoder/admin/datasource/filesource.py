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
import shutil

from zope.interface import implements
from twisted.python import failure

from flumotion.common import common

from flumotion.transcoder import log, defer, inifile, utils
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
from flumotion.transcoder.admin.datasource.datasource import StoringError
from flumotion.transcoder.admin.datasource.datasource import ResetError
from flumotion.transcoder.admin.datasource.datasource import DeletionError


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
        # Hardcoded hack to allow profiles and targets without name
        # name can be hidden when name shouldn't be seen
        if attr == 'name':
            name = getattr(data, attr, None)
            if not name:
                return self.__dict__['_identifier']
        return getattr(data, attr)
    
    def __setattr__(self, attr, value):
        raise AttributeError, attr
        
    def _getData(self):
        return self.__dict__['_data']


class MutableDataWrapper(object):
    """
    Right now this class make the assumption it's used for activities.
    """
    
    def __init__(self, source, template, path=None, identifier=None,
                 data=None, fields=None, **overrides):
        self._source = source
        self._path = path
        self._template = template
        self._identifier = identifier
        self._data = data
        if fields:
            self._fields = utils.deepCopy(fields)
        elif data:
            self._reset()
        else:
            self._fields = utils.deepCopy(template["defaults"])
        for k, v in overrides.items():
            self._fields[k] = v
        
    def _reset(self):
        if not self._data: return
        data = self._data
        fields = dict()
        for key, default in self._template["defaults"].iteritems():
            val = getattr(data, key, default)
            fields[key] = utils.deepCopy(val)
        self._fields = fields

    def _store(self):
        identifier = self._identifier or self.__newIdentifier()
        data = self._data or self._template['class']()
        newPath = self.__getPath(identifier, self.state)
        newTmpPath = newPath + ".tmp"
        for attr, value in self._fields.items():
            if isinstance(value, list):
                l = getattr(data, attr)
                del l[:]
                for v in value:
                    l.append(utils.deepCopy(v))
            elif isinstance(value, dict):
                d = getattr(data, attr)
                d.clear()
                for k, v in value.items():
                    d[k] = utils.deepCopy(v)
            else:
                setattr(data, attr, utils.deepCopy(value))
        try:
            common.ensureDir(os.path.dirname(newTmpPath), "activities")
            saver = inifile.IniFile()
            saver.saveToFile(data, newTmpPath)
        except Exception, e:
            log.notifyException(self._source, e,
                                "File to save activity data file '%s'",
                                newPath)
            raise e
        if self._path:
            self.__deleteFile(self._path)
        self.__moveFile(newTmpPath, newPath)
        self._identifer = identifier
        self._data = data
        self._path = newPath
        self._source._mutableDataStored(identifier, self._data, self._path)
    
    def _delete(self):
        if self._path:
            self.__deleteFile(self._path)
            self._source._mutableDataDeleted(self, self._identifier,
                                             self._data)
            self._path = None
            self._data = None
            self._identifier = None

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
        
    def __newIdentifier(self):
        ident = utils.genUniqueIdentifier()
        return self._template['file-template'] % ident
        
    def __getPath(self, identifier, state):
        if state == ActivityStateEnum.done:
            return self._source._doneActivitiesDir + identifier
        if state == ActivityStateEnum.failed:
            return self._source._failedActivitiesDir + identifier
        return self._source._activeActivitiesDir + identifier
    
    def __deleteFile(self, file):
        try:
            os.remove(file)
        except Exception, e:
            log.notifyException(self._source, e,
                                "Fail to delete file '%s'", file)
            raise e
        
    def __moveFile(self, sourceFile, destFile):
        try:
            shutil.move(sourceFile, destFile)
        except Exception, e:
            log.notifyException(self._source, e,
                                "Fail to move file from '%s' to '%s'",
                                sourceFile, destFile)
            raise e
            

TRANS_ACT_TMPL = {'class': dataprops.TranscodingActivityData,
                  'file-template': 'transcoding-%s.ini',
                  'defaults': {'type': ActivityTypeEnum.transcoding,
                               'subtype': None,
                               'state': ActivityStateEnum.unknown,
                               'label': "Unknown",
                               'startTime': None,
                               'lastTime': None,
                               'customerName': None,
                               'profileName': None,
                               'targetName': None,
                               'inputRelPath': None},
                  'hidden': set([]),
                  'readonly': set(['type', 'subtype'])}

NOT_ACT_TMPL = {'class': dataprops.NotificationActivityData,
                'file-template': 'notification-%s.ini',
                'defaults': {'type': ActivityTypeEnum.notification,
                             'subtype': None,
                             'state': ActivityStateEnum.unknown,
                             'label': None,
                             'startTime': None,
                             'lastTime': None,
                             'customerName': None,
                             'profileName': None,
                             'targetName': None,
                              'trigger': None,
                             'timeout': None,
                             'retryCount': None,
                             'retryMax': None,
                             'retrySleep': None,
                             'data': {}},
                'hidden': set([]),
                'readonly': set(['type', 'subtype'])}

_activityTemplateLookup = {ActivityTypeEnum.transcoding: TRANS_ACT_TMPL,
                           ActivityTypeEnum.notification: NOT_ACT_TMPL}

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

CUST_INFO_TMPL = {'name': None,
                  'contact': None,
                  'adresses': None,
                  'phone': None,
                  'email': None}


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
        self._adminPath = os.path.abspath(config.dataFile)
        self._adminData = None
        self._customersDir = None
        self._customersData = {} # {filename: RootPropertyBag}
        self._activeActivitiesDir = None
        self._doneActivitiesDir = None
        self._failedActivitiesDir = None
        self._invalidActivitiesDir = None
        self._activitiesData = {} # {filename: (filePath, MutableDataWrapper)}
    
    def initialize(self):
        self.debug("Initializing File Data Source")
        d = defer.Deferred()
        d.addCallback(defer.dropResult, self.__loadAdminData)
        d.addCallback(defer.dropResult, self.__loadActivityData)
        d.addErrback(self.__ebInitializationFailed)
        d.callback(None)
        return d

    def waitReady(self, timeout=None):
        return defer.succeed(self)

    def retrieveDefaults(self):
        try:
            result = ImmutableDataWrapper(self._adminData, "defaults",
                                          hidden=['customersDir',
                                                  'activitiesDir',
                                                  'name'])
            return defer.succeed(result)
        except Exception, e:
            msg = "Failed to retrieve default data"
            ex = datasource.RetrievalError(msg, cause=e)
            f = failure.Failure(ex)
            return defer.fail(f)
        
    def retrieveCustomers(self):
        try:
            result = [ImmutableDataWrapper(c, k, hidden=['profiles'])
                      for k, c in self._customersData.items()
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
            result = ImmutableWrapper((customerData.identifier, "info"), 
                                      CUST_INFO_TMPL)
            return defer.succeed(result)
        except Exception, e:
            msg = "Failed to retrieve customer info data"
            ex = datasource.RetrievalError(msg, cause=e)
            f = failure.Failure(ex)
            return defer.fail(f)
        
    def retrieveProfiles(self, customerData):
        try:
            assert isinstance(customerData, ImmutableDataWrapper)
            result = [ImmutableDataWrapper(p, k, hidden=['targets']) 
                      for k, p in customerData._getData().profiles.items()
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
            result = [ImmutableDataWrapper(t, k, hidden=['config', 'type'])
                      for k, t in profileData._getData().targets.items()
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
                                          readonly=['type'])
            return defer.succeed(result)
        except Exception, e:
            msg = "Failed to retrieve target config data"
            ex = datasource.RetrievalError(msg, cause=e)
            f = failure.Failure(ex)
            return defer.fail(f)

    def retrieveActivities(self, type, states=None):
        try:
            assert type in ActivityTypeEnum
            states = states and set(states)
            result = []
            tmpl = _activityTemplateLookup.get(type)
            result = [MutableDataWrapper(self, tmpl, p, f, a)
                      for f, (p, a) in self._activitiesData.items()
                      if a.type == type]
            return defer.succeed(result)
        except Exception, e:
            msg = "Failed to retrieve activities data"
            ex = datasource.RetrievalError(msg, cause=e)
            f = failure.Failure(ex)
            return defer.fail(f)

    def newActivity(self, type, subtype):
        assert isinstance(type, ActivityTypeEnum)
        tmpl = _activityTemplateLookup.get(type)
        return MutableDataWrapper(self, tmpl, subtype=subtype)

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
        try:
            for mutable in data:
                if not isinstance(mutable, MutableDataWrapper):
                    raise NotImplementedError()
                mutable._store()
            return defer.succeed(self)
        except Exception, e:
            error = StoringError(cause=e)
            return defer.fail(error)
        
    def reset(self, *data):
        try:
            for mutable in data:
                if not isinstance(mutable, MutableDataWrapper):
                    raise NotImplementedError()
                mutable._reset()
            return defer.succeed(self)
        except Exception, e:
            error = ResetError(cause=e)
            return defer.fail(error)
        
    def delete(self, *data):
        try:
            for mutable in data:
                if not isinstance(mutable, MutableDataWrapper):
                    raise NotImplementedError()
                mutable._delete() 
            return defer.succeed(self)
        except Exception, e:
            error = DeletionError(cause=e)
            return defer.fail(error)


    ## Protected Methods ##
    
    _excludedStates = set([ActivityStateEnum.failed,
                           ActivityStateEnum.done])
    
    def _mutableDataStored(self, identifier, data, path):
        if data.state in self._excludedStates:
            self._activitiesData.pop(identifier, None)
            return
        self._activitiesData[identifier] = (path, data)
    
    def _mutableDataDeleted(self, identifier, data):
        self._activitiesData.pop(identifier, None)


    ## Private Methods ##
    
    def __safeMove(self, sourceDir, destDir, file):
        try:
            shutil.move(sourceDir + file, destDir + file)
        except Exception, e:
            log.notifyException(self, e,
                                "Fail to move file '%s' from '%s' to '%s'",
                                file, sourceDir, destDir)
    
    def __loadAdminData(self):
        self.debug("Loading admin data from '%s'", self._adminPath)
        loader = inifile.IniFile()
        adminData = dataprops.AdminData()
        loader.loadFromFile(adminData, self._adminPath)
        self._adminData = adminData
        basePath = os.path.dirname(self._adminPath)
        relDir = self._adminData.customersDir
        absPath = utils.makeAbsolute(relDir, basePath)
        absDir = utils.ensureAbsDirPath(absPath)
        self._customersDir = absDir
        common.ensureDir(self._customersDir, "customers configuration")
        self.debug("Loading customers data from directory '%s'", absDir)
        self._customersData.clear()
        files = os.listdir(absDir)
        for f in files:
            if not f.endswith('.ini'):
                self.log("Ignoring customer data file '%s'", f)
                continue
            self.log("Loading customer data file '%s'", f)
            data = dataprops.CustomerData()
            try:
                loader.loadFromFile(data, absDir + f)
            except Exception, e:
                log.notifyException(self, e,
                                    "Fail to load customer data "
                                    "from file '%s'", absDir + f)
                continue
            self._customersData[f] = data
        
    def __loadActivityData(self):
        basePath = os.path.dirname(self._adminPath)
        relDir = self._adminData.activitiesDir
        absPath = utils.makeAbsolute(relDir, basePath)
        absDir = utils.ensureAbsDirPath(absPath)
        self._activeActivitiesDir = absDir
        self._failedActivitiesDir = utils.ensureAbsDirPath(absDir + "failed")
        self._doneActivitiesDir = utils.ensureAbsDirPath(absDir + "done")
        self._invalidActivitiesDir = utils.ensureAbsDirPath(absDir + "invalid")
        common.ensureDir(self._activeActivitiesDir, "activities data base")
        common.ensureDir(self._failedActivitiesDir, "failed activities")
        common.ensureDir(self._doneActivitiesDir, "done activities")
        common.ensureDir(self._invalidActivitiesDir, "invalid activities")
        self.debug("Loading activities data from directory '%s'", absDir)
        loader = inifile.IniFile()
        self._activitiesData.clear()
        files = os.listdir(absDir)
        for f in files:
            if not f.endswith('.ini'):
                self.log("Ignoring activity data file '%s'", f)
                continue
            if f.startswith("transcoding-"):
                data = dataprops.TranscodingActivityData()
            elif f.startswith("notification-"):
                data = dataprops.NotificationActivityData()
            else:
                self.log("Ignoring activity data file '%s'", f)
                continue
            self.log("Loading activity data file '%s'", f)
            try:
                loader.loadFromFile(data, absDir + f)
            except Exception, e:
                log.notifyException(self, e,
                                    "Fail to load activity data "
                                    "from file '%s'", absDir + f)
                self.__safeMove(absDir, self._invalidActivitiesDir, f)
                continue
            if data.state == ActivityStateEnum.done:
                self.__safeMove(absDir, self._doneActivitiesDir, f)
            elif data.state == ActivityStateEnum.failed:
                self.__safeMove(absDir, self._failedActivitiesDir, f)
            else:
                self._activitiesData[f] = (absDir + f, data)
        
    def __ebInitializationFailed(self, failure):
        if failure.check(InitializationError):
            return failure
        msg = "Failed to initialize file data-source"
        raise InitializationError(msg, cause=failure.value)        
