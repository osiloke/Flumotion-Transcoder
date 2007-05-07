# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.
# Headers in this file shall remain intact.

from twisted.internet import reactor, defer
from twisted.python import failure

from flumotion.twisted.compat import implements
from flumotion.common.log import Loggable
from flumotion.transcoder import inifile
from flumotion.transcoder.admin.datasource import dataprops
from flumotion.transcoder.admin.datasource import datasource


class DataWrapper(object):
    
    def __init__(self, data, hidden=[], readonly=[]):
        self.__dict__['_data'] = data
        self.__dict__['_hidden'] = set(hidden)
        self.__dict__['_readonly'] = set(readonly)        
        
    def __getattr__(self, attr):
        hidden = self.__dict__['_hidden']
        if attr in hidden:
            raise AttributeError, attr
        data = self.__dict__['_data']
        return getattr(data, attr)
    
    def __setattr__(self, attr, value):
        hidden = self.__dict__['_hidden']
        readonly = self.__dict__['_hidden']
        if (attr in hidden) or (attr in readonly):
            raise AttributeError, attr
        data = self.__dict__['_data']
        setattr(data, attr, value)
        
    def _getData(self):
        return self.__dict__['_data']


class FileDataSource(Loggable):
    
    logCategory = 'data-source'
    
    implements(datasource.IDataSource)
    
    def __init__(self, filePath):
        self._filePath = filePath
        self._data = dataprops.AdminData()
        self._loader = inifile.IniFile();
    
    def initialize(self):
        try:
            self._loader.loadFromFile(self._data, self._filePath)
            return defer.succeed(self)
        except Exception, e:
            msg = "Failed to initialize file data-source"
            ex = datasource.InitializationError(msg, cause=e)
            f = failure.Failure(ex)
            return defer.fail(f)

    def waitReady(self):
        return defer.succeed(self)

    def retrieveDefaults(self):
        try:
            result = DataWrapper(self._data, ['customers'])
            return defer.succeed(result)
        except Exception, e:
            msg = "Failed to retrieve default data"
            ex = datasource.RetrievalError(msg, cause=e)
            f = failure.Failure(ex)
            return defer.fail(f)
        
    def retrieveCustomers(self):
        try:
            result = [DataWrapper(c, ['info', 'profiles']) 
                      for c in self._data.customers
                      if c != None]
            return defer.succeed(result)
        except Exception, e:
            msg = "Failed to retrieve customers data"
            ex = datasource.RetrievalError(msg, cause=e)
            f = failure.Failure(ex)
            return defer.fail(failure)
        
    def retrieveCustomerInfo(self, customerData):
        try:
            assert isinstance(customerData, DataWrapper)
            result = DataWrapper(customerData._getData().info)
            return defer.succeed(result)
        except Exception, e:
            msg = "Failed to retrieve customer info data"
            ex = datasource.RetrievalError(msg, cause=e)
            f = failure.Failure(ex)
            return defer.fail(f)
        
    def retrieveProfiles(self, customerData):
        try:
            assert isinstance(customerData, DataWrapper)
            result = [DataWrapper(p, ['targets']) 
                      for p in customerData._getData().profiles
                      if p != None]
            return defer.succeed(result)
        except Exception, e:
            msg = "Failed to retrieve profiles data"
            ex = datasource.RetrievalError(msg, cause=e)
            f = failure.Failure(ex)
            return defer.fail(f)
        
    def retrieveNotifications(self, withGlobal, customerData, 
                              profileData, targetData):
        raise NotImplementedError()
        
    def retrieveTargets(self, profileData):
        try:
            assert isinstance(profileData, DataWrapper)
            result = [DataWrapper(t, ['config', 'type']) 
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
            assert isinstance(targetData, DataWrapper)
            result = DataWrapper(targetData._getData().config, [], ['type'])
            return defer.succeed(result)
        except Exception, e:
            msg = "Failed to retrieve target config data"
            ex = datasource.RetrievalError(msg, cause=e)
            f = failure.Failure(ex)
            return defer.fail(f)

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
        raise NotImplementedError()
    
    def delete(self, *data):
        raise NotImplementedError()
