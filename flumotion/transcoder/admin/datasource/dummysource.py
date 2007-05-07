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
from flumotion.transcoder.enums import TargetTypeEnum
from flumotion.transcoder.enums import IntervalUnitEnum
from flumotion.transcoder.enums import ThumbOutputTypeEnum
from flumotion.transcoder.enums import VideoScaleMethodEnum
from flumotion.transcoder.admin.datasource import datasource


DEFAULTS_DATA = {'monitorInterval': 2,
                 'transcodingTimeout': 4,
                 'postprocessTimeout': 60,
                 'preprocessTimeout': 60,
                 'outputFileTemplate': "%(inputFileBase)s.%(outputFileExt)",
                 'linkFileTemplate': "%(inputFile)s.link",
                 'configFileTemplate': "%(inputFile)s.ini",
                 'reportFileTemplate': "%(inputFile)s.rep",
                 'mailSubjectTemplate': "Transcoding Error",
                 'mailBodyTemplate': "Errorrrrr",
                 'GETRequestTimeout': 60,
                 'GETRequestRetryCount': 3,
                 'GETRequestRetrySleep': 60}

CUSTOMER_DATA = {'label': "Fluendo",
                 'subdir': None,
                 'inputDir': None,
                 'outputDir': None,
                 'failedDir': None,
                 'doneDir': None,
                 'linkDir': None,
                 'workDir': None,
                 'configDir': None,
                 'failedRepDir': None,
                 'doneRepDir': None,
                 'outputFileTemplate': None,
                 'linkFileTemplate': None,
                 'configFileTemplate': None,
                 'reportFileTemplate': None,
                 'linkTemplate': None,
                 'linkURLPrefix': None,
                 'enablePostprocessing': None,
                 'enablePreprocessing': None,
                 'enableLinkFiles': None,
                 'transcodingPriority': None,
                 'processPriority': None,
                 'preprocessCommand': None,
                 'postprocessCommand': None,
                 'preprocesstimeout': None,
                 'postprocessTimeout': None,
                 'transcodingTimeout': None}

CUSTOMER_INFO = {'name': None,
                 'contact': None,
                 'addresses': [],
                 'phone': None,
                 'email': None}

PROFILE_DATA = {'label': None,
                'subdir': None,
                'inputDir': None,
                'outputDir': None,
                'failedDir': None,
                'doneDir': None,
                'linkDir': None,
                'workDir': None,
                'configDir': None,
                'failedRepDir': None,
                'doneRepDir': None,
                'outputFileTemplate': None,
                'linkFileTemplate': None,
                'configFileTemplate': None,
                'reportFileTemplate': None,
                'linkTemplate': None,
                'linkURLPrefix': None,
                'enablePostprocessing': None,
                'enablePreprocessing': None,
                'enableLinkFiles': None,
                'transcodingPriority': None,
                'processPriority': None,
                'preprocessCommand': None,
                'postprocessCommand': None,
                'preprocesstimeout': None,
                'postprocessTimeout': None,
                'transcodingTimeout': None}

TARGET_DATA = {'label': None,
               'extension': None,
               'subdir': None,
               'outputFileTemplate': None,
               'linkFileTemplate': None,
               'linkTemplate': None,
               'linkURLPrefix': None,
               'enablePostprocessing': None,
               'enableLinkFiles': None,
               'postprocessCommand': None,
               'postprocessTimeout': None}

AUDIO_CONFIG = {'type': TargetTypeEnum.audio,
                'muxer': None,
                'audioEncoder': None,
                'audioRate': None,
                'audioChannels': None}

VIDEO_CONFIG = {'type': TargetTypeEnum.video,
                'muxer': None,
                'videoEncoder': None,
                'videoWidth': None,
                'videoHeight': None,
                'videoMaxWidth': None,
                'videoMaxHeight': None,
                'videoPAR': None,
                'videoFramerate': None,
                'scaleMethod': None}

AUDIOVIDEO_CONFIG = {'type': TargetTypeEnum.audiovideo,
                     'muxer': None,
                     'audioEncoder': None,
                     'audioRate': None,
                     'audioChannels': None,
                     'videoEncoder': None,
                     'videoWidth': None,
                     'videoHeight': None,
                     'videoMaxWidth': None,
                     'videoMaxHeight': None,
                     'videoPAR': None,
                     'videoFramerate': None,
                     'scaleMethod': None}

THUMBNAILS_CONFIG = {'type': TargetTypeEnum.thumbnails,
                     'thumbsWidth': None,
                     'thumbsHeight': None,
                     'intervalValue': None,
                     'intervalUnit': None,
                     'maxCount': None,
                     'format': None}

REPORT_DATA = {}

TARGET_REPORT_DATA = {}


def fail(failure):
    return defer.fail(failure)
    d = defer.Deferred()
    reactor.callLater(0.2, d.errback, failure)
    return d

def succeed(result):
    #return defer.succeed(result)
    d = defer.Deferred()
    reactor.callLater(0.2, d.callback, result)
    return d


class DummyData(object):
    def __init__(self, writeable, key, template, **delta):
        data = dict(template)
        for k, v in delta.iteritems():
            assert k in template
            data[k] = v
        self.__dict__['_writeable'] = writeable
        self.__dict__['_data'] = data
        self.__dict__['_key'] = key
        self.__dict__['_source'] = None
    
    def __eq__(self, data):
        return (isinstance(data, DummyData) 
                and (self.__dict__['_key'] == data.__dict__['_key']))
    
    def _getKey(self):
        return self.__dict__['_key']
    
    def __getattr__(self, attr):
        data = self.__dict__['_data']
        if attr in data:
            return data[attr]
        if not (attr in self.__dict__):
            raise AttributeError, attr
        return self.__dict__[attr]
    
    def __setattr__(self, attr, value):
        data = self.__dict__['_data']
        if attr in data:
            if not self.__dict__['_writeable']:
                raise datasource.ReadOnlyDataError("Attribute %s is read only"
                                                   % attr)
            data[attr] = value
        else:
            self.__dict__[attr] = value

    def _clone(self):
        new = self.__class__(self.__dict__['_writeable'],
                             self.__dict__['_key'],
                             self.__dict__['_data'])
        source = self.__dict__['_source']
        if source:
            new.__dict__['_source'] = source
        else:
            new.__dict__['_source'] = self
        return new
        
    def _apply(self, other):
        assert self.__class__ == other.__class__
        assert self.__dict__['_key'] == other.__dict__['_key']
        if not self.__dict__['_writeable']:
            raise datasource.ReadOnlyDataError("Data read only")
        dest = self.__dict__['_data']
        src = other.__dict__['_data']
        for k, v in dest.iteritems():
            dest[k] = src.get(k, v)
            
    def _getSource(self):
        return self.__dict__['_source']
            
    def _store(self):
        source = self.__dict__['_source']
        assert source
        source._apply(self)
    
    
class DummyDataSource(Loggable):
    
    implements(datasource.IDataSource)
    
    def __init__(self):
        self.defaults = DummyData(True, (), DEFAULTS_DATA)
        
        cust1data = DummyData(True, (1,0), CUSTOMER_DATA,
                              label="Fluendo")
        cust1info = DummyData(False, (1,1), CUSTOMER_INFO,
                              name="Fluendo S.A.",
                              contact="Thomas")
        cust1prof1 = DummyData(True, (1,2,1,0), PROFILE_DATA,
                               label="OGG/Theora-Vorbis")
        cust1prof1targ1data = DummyData(True, (1,2,1,1,1,0), TARGET_DATA,
                                        label="low",
                                        extension="ogg")
        cust1prof1targ1conf = DummyData(True, (1,2,1,1,1,1), AUDIOVIDEO_CONFIG,
                                        muxer="oggmux",
                                        videoEncoder="theoraenc bitrate=128",
                                        audioEncoder="vorbisenc bitrate=64000")
        cust1prof1targ2data = DummyData(True, (1,2,1,1,2,0), TARGET_DATA,
                                        label="high",
                                        extension="ogg")
        cust1prof1targ2conf = DummyData(True, (1,2,1,1,2,1), AUDIOVIDEO_CONFIG,
                                        muxer="oggmux",
                                        videoEncoder="theoraenc bitrate=500",
                                        audioEncoder="vorbisenc bitrate=128000")
        cust1prof1targ3data = DummyData(True, (1,2,1,1,3,0), TARGET_DATA,
                                        label="thumbs",
                                        extension="jpg")
        cust1prof1targ3conf = DummyData(True, (1,2,1,1,3,1), THUMBNAILS_CONFIG,
                                        intervalValue=10,
                                        intervalUnit=IntervalUnitEnum.percent,
                                        maxCount=0)
        cust1prof2 = DummyData(True, (1,2,2,0), PROFILE_DATA,
                               label="Flash Video",
                               subdir= "flv")
        cust1prof2targ1data = DummyData(True, (1,2,2,1,1,0), TARGET_DATA,
                                        label="video",
                                        extension="flv")
        cust1prof2targ1conf = DummyData(True, (1,2,2,1,1,1), AUDIOVIDEO_CONFIG,
                                        muxer="fluflvmux",
                                        videoEncoder="fenc_flv bitrate=128000",
                                        audioEncoder="lame ! mp3parse")
        cust1prof2targ2data = DummyData(True, (1,2,2,1,2,0), TARGET_DATA,
                                        label="thumbs",
                                        extension="png")
        cust1prof2targ2conf = DummyData(True, (1,2,2,1,2,1), THUMBNAILS_CONFIG,
                                        intervalValue=1,
                                        intervalUnit=IntervalUnitEnum.seconds,
                                        maxCount=5)
        
        cust2data = DummyData(True, (2,0), CUSTOMER_DATA,
                              label="Big Client",
                              subdir="big/client")
        cust2info = DummyData(False, (2,1), CUSTOMER_INFO,
                              name="The Big Company")
        cust2prof1 = DummyData(True, (2,1,1,0), PROFILE_DATA,
                               label="Test")
        cust2prof1targ1data = DummyData(True, (2,1,1,1,1,0), TARGET_DATA,
                                        label="normal",
                                        extension="ogg")
        cust2prof1targ1conf = DummyData(True, (2,1,1,1,1,1), AUDIOVIDEO_CONFIG,
                                        muxer="oggmux",
                                        videoEncoder="theoraenc bitrate=500",
                                        audioEncoder="vorbisenc bitrate=128000")
        
        self._nextid = 10
        self.customers = {(1,): (cust1data,
                                 cust1info,
                                 {(1,1): (cust1prof1,
                                          {(1,1,1): (cust1prof1targ1data,
                                                     cust1prof1targ1conf),
                                           (1,1,2): (cust1prof1targ2data,
                                                     cust1prof1targ2conf),
                                           (1,1,3): (cust1prof1targ3data,
                                                     cust1prof1targ3conf)
                                           }
                                          ),
                                  (1,2): (cust1prof2,
                                          {(1,2,1): (cust1prof2targ1data,
                                                     cust1prof2targ1conf),
                                           (1,2,2): (cust1prof2targ2data,
                                                     cust1prof2targ2conf)
                                           }
                                          )
                                  }
                                 ),
                          (2,): (cust2data,
                                 cust2info,
                                 {(2,1): (cust2prof1,
                                          {(2,1,1): (cust2prof1targ1data,
                                                     cust2prof1targ1conf)
                                           }
                                          )
                                  }
                                 )
                          }
    
    def _getCustomer(self, key):
        assert len(key) >= 2
        assert (key[1] >= 0) and (key[1] <= 2)
        k = (key[0],)
        if not (k in self.customers):
            raise datasource.DataNotFoundError("Customer %s not found"
                                               % repr(k))
        return self.customers[k]
        
    def _getProfile(self, key):
        profiles = self._getCustomer(key)[-1]
        assert len(key) >= 4
        assert (key[3] >= 0) and (key[3] <= 1)
        k = (key[0],key[2])
        if not (k in profiles):
            raise datasource.DataNotFoundError("Profile %s not found"
                                               % repr(k))
        return profiles[k]
        
    def _getTarget(self, key):
        targets = self._getProfile(key)[-1]
        assert len(key) >= 6
        assert (key[5] >= 0) and (key[5] <= 1)
        k = (key[0],key[2], key[4])
        if not (k in targets):
            raise datasource.DataNotFoundError("Target %s not found"
                                               % repr(k))
        return targets[k]
    
    def initialize(self):
        self.log("Initializing the Dummy Data Source")
        return succeed(self)
    
    def waitReady(self):
        return succeed(self)
    
    def retrieveDefaults(self):
        try:
            return succeed(self.defaults._clone())
        except datasource.DataSourceError, e:
            return fail(failure.Failure(e))
        except Exception, e:
            e = datasource.RetrievalError("Defaults retrieval error",
                                          cause=e) 
            return fail(failure.Failure(e))
        
    def retrieveCustomers(self):
        try:
            res = [v[0]._clone() for v in self.customers.values() if v[0] != None]
            return succeed(res)
        except datasource.DataSourceError, e:
            return fail(failure.Failure(e))
        except Exception, e:
            e = datasource.RetrievalError("Customers retrieval error",
                                          cause=e) 
            return fail(failure.Failure(e))
        
    def retrieveCustomerInfo(self, customerData):
        try:
            assert isinstance(customerData, DummyData)
            key = customerData._getKey()
            cust = self._getCustomer(key)
            res = cust[1] and cust[1]._clone()
            return succeed(res)
        except datasource.DataSourceError, e:
            return fail(failure.Failure(e))
        except Exception, e:
            e = datasource.RetrievalError("Customer Info retrieval error",
                                          cause=e) 
            return fail(failure.Failure(e))
        
    def retrieveProfiles(self, customerData):
        try:
            assert isinstance(customerData, DummyData)
            key = customerData._getKey()
            cust = self._getCustomer(key)
            res = [p[0]._clone() for p in cust[-1].values() if p[0] != None]
            return succeed(res)
        except datasource.DataSourceError, e:
            return fail(failure.Failure(e))
        except Exception, e:
            e = datasource.RetrievalError("Profiles retrieval error",
                                          cause=e) 
            return fail(failure.Failure(e))
        
    def retrieveNotifications(self, withGlobal, customerData, 
                              profileData, targetData):
        return succeed([])
    
    def retrieveTargets(self, profileData):
        try:
            assert isinstance(profileData, DummyData)
            key = profileData._getKey()
            prof = self._getProfile(key)
            res = [t[0]._clone() for t in prof[1].values() if t[0] != None]
            return succeed(res)
        except datasource.DataSourceError, e:
            return fail(failure.Failure(e))
        except Exception, e:
            e = datasource.RetrievalError("Target retrieval error",
                                          cause=e) 
            return fail(failure.Failure(e))
       
    def retrieveTargetConfig(self, targetData):
        try:
            assert isinstance(targetData, DummyData)
            key = targetData._getKey()
            target = self._getTarget(key)
            res = target[1] and target[1]._clone()
            return succeed(res)
        except datasource.DataSourceError, e:
            return fail(failure.Failure(e))
        except Exception, e:
            e = datasource.RetrievalError("Target config retrieval fail",
                                          cause=e) 
            return fail(failure.Failure(e))
    
    def newCustomer(self, cusomerId):
        res = DummyData(True, (self._nextid,0), CUSTOMER_DATA)
        self._nextid += 1
        return res
        
    def newProfile(self, customerData):
        assert isinstance(customerData, DummyData)
        key = customerData._getKey()
        assert len(key) == 2
        res = DummyData(True, key+(self._nextid,0), PROFILE_DATA)
        self._nextid += 1
        return res

    def newNotification(self, type, data):
        raise NotImplementedError()

    def newTarget(self, profileData):
        assert isinstance(profileData, DummyData)
        key = profileData._getKey()
        assert len(key) == 4
        res = DummyData(True, key + (self._nextid,0), TARGET_DATA)
        self._nextid += 1
        return res
    
    def newTargetConfig(self, targetData):
        assert isinstance(targetData, DummyData)
        key = targetData._getKey()
        assert len(key) == 6
        assert targetData.type in TargetTypeEnum
        if targetData.type == TargetTypeEnum.audio:
            tmpl = AUDIO_CONFIG
        elif targetData.type == TargetTypeEnum.video:
            tmpl = VIDEO_CONFIG
        elif targetData.type == TargetTypeEnum.audiovideo:
            tmpl = AUDIOVIDEO_CONFIG
        elif targetData.type == TargetTypeEnum.thumbnails:
            tmpl = THUMBNAILS_CONFIG
        res = DummyData(True, key + (self._nextid,1), tmpl)
        self._nextid += 1
        return res
        
    def newReport(self, profileData):
        assert isinstance(profileData, DummyData)
        key = profileData._getKey()
        assert len(key) == 4
        return DummyData(True, None, REPORT_DATA)
        
    def newTargetReport(self, reportData):
        assert isinstance(reportData, DummyData)
        key = reportData._getKey()
        assert len(key) == 6
        return DummyData(True, None, TARGET_REPORT_DATA)
        
    def newNotificationReport(self, reportData, notificationData):
        raise NotImplementedError()
        
    def store(self, *data):
        try:
            count = 0
            customers = self.customers
            for o in data:
                count += 1
                source = o._getSource()
                if source:
                    o._store()
                    continue
                key = o._getKey()
                if key == None:
                    #Ignore the reports
                    continue
                assert len(key) > 1
                assert (len(key) % 2) == 0
                cust = customers.get(key[0], None)
                if len(key) == 2:
                    if cust == None:
                        cust = [None, None, {}]
                        customers[key[0]] = cust
                    if cust[key[1]] != None:
                        raise datasource.DuplicatedDataError(
                                     "Customer already exists")
                    cust[key[1]] = o
                    continue
                
                if cust == None:
                    raise datasource.DataDependencyError(
                             "Profile dependency not found")
                profiles = cust[key[0]][-1]
                prof = profiles.get(key[2], None)
                if len(key) == 4:
                    if prof == None:
                        prof = [None, {}]
                        profiles[key[2]] = prof
                    if prof[key[3]] != None:
                        raise datasource.DuplicatedDataError(
                                 "Profile already exists")
                    prof[key[3]] = o
                    continue
                
                if prof == None:
                    raise datasource.DataDependencyError(
                             "Target dependency not found")
                targets = prof[key[2]][-1]
                targ = targets.get(key[4], None)
                if len(key) == 6:
                    if targ == None:
                        targ = [None, None]
                        targets[key[4]] = targ
                    if targ[key[5]] != None:
                        raise datasource.DuplicatedDataError(
                                     "Target already exists")
                    targ[key[5]] = o
                    continue
            return succeed(count)
        except datasource.DataSourceError, e:
            return fail(failure.Failure(e))
        except Exception, e:
            e = datasource.StoringError(cause=e) 
            return fail(failure.Failure(e))
            
    def delete(self, *data):
        raise NotImplementedError()