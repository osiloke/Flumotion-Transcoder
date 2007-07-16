# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import Interface, implements
from twisted.internet import reactor, defer

from flumotion.transcoder import log
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.enums import ActivityTypeEnum
from flumotion.transcoder.admin.enums import ActivityStateEnum
from flumotion.transcoder.admin.eventsource import EventSource


## Notification Function ###

def notifyEmergency(msg, failure=None):
    """
    This function can be used from anywere to notify
    emergency situations when no Notifier reference
    is available.
    """
    pass

def notifyDebug(msg, failure=None):
    """
    This function can be used from anywere to notify
    debug information (like traceback) when no 
    Notifier reference is available.
    """
    pass


class INotifierListener(Interface):
    pass
        

class NotifierListener(object):
    
    implements(INotifierListener)
    

class Notifier(log.Loggable, 
               EventSource):
    
    logCategory = adminconsts.NOTIFIER_LOG_CATEGORY
    
    def __init__(self, notifierConfig, activityStore):
        self._store = activityStore
        self._config = notifierConfig


    ## Public Methods ##
    
    def addNotifications(self, notifications):
        pass
    
    