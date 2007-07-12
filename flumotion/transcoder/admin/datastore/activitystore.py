# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import datetime

from flumotion.transcoder.enums import ActivityTypeEnum
from flumotion.transcoder.enums import ActivityStateEnum
from flumotion.transcoder.admin.datastore.profilestore import ProfileStore

class BaseActivity(object):
    
    def __init__(self, parent, data, isNew=True):
        self._parent = parent
        self._data = data
        self._deleted = False
        self._isNew = isNew
        
    def store(self):
        assert not self._deleted
        d = self._parent._storeActivity(self, self._isNew)
        self._new = False
        return d
    
    def reset(self):
        assert not self._deleted
        return self._parent._resetActivity(self)
    
    def delete(self):
        assert not self._deleted
        self._deleted = True
        return self._parent._deleteActivity(self)
        
    def getLabel(self):
        assert not self._deleted
        return self._data.label
    
    def getType(self):
        assert not self._deleted
        return self._data.type
    
    def getState(self):
        assert not self._deleted
        return self._data.state

    def setState(self, state):
        assert not self._deleted
        assert isinstance(state, ActivityStateEnum)
        self._data.state = state
        self._touche()
    
    def getStartTime(self):
        assert not self._deleted
        return self._data.startTime
    
    def getLastTime(self):
        assert not self._deleted
        return self._data.lastTime
            

    ## Protected Methods ##
    
    def _touche(self):
        self._data.lastTime = datetime.datetime.now()
    
    def _getData(self):
        return self._data




class TranscodingActivity(BaseActivity):
    
    def __init__(self, parent, data, isNew=True):
        BaseActivity.__init__(self, parent, data, isNew)
        
    def getInputRelPath(self):
        assert not self._deleted
        return self._data.inputRelPath
    
    def setInputRelPath(self, relPath):
        assert not self._deleted
        assert isinstance(relPath, str)
        self._data.inputRelPath = relPath
    
    def getCustomer(self):
        assert not self._deleted
        return self._parent.getCustomer(self._data.customerName, None)
    
    def getProfile(self):
        assert not self._deleted
        cust = self._parent.getCustomer(self._data.customerName, None)
        if not cust:
            return None
        prof = cust.getProfile(self._data.profileName, None)
        return prof
    
    def setProfile(self, profile):
        assert not self._deleted
        assert isinstance(profile, ProfileStore)
        self._data.customerName = profile._parent.getName()
        self._data.profileName = profile.getName()
    
    
_classLookup = {ActivityTypeEnum.transcoding: TranscodingActivity}


def Activity(parent, data, isNew=True):
    assert data.type in _classLookup
    return _classLookup[data.type](parent, data, isNew)
