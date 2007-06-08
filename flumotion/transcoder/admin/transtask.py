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

from flumotion.common.log import Loggable

from flumotion.transcoder import log
from flumotion.transcoder import utils
from flumotion.transcoder.admin import constants
from flumotion.transcoder.admin.eventsource import EventSource
from flumotion.transcoder.admin.taskbalancer import ITask
from flumotion.transcoder.admin.transprops import TranscoderProperties
from flumotion.transcoder.admin.proxies.transproxy import TranscoderProxy
from flumotion.transcoder.admin.proxies.transproxy import TranscoderListener


class ITranscodingTaskListener(Interface):
    def onTranscoderElected(self, transcodingtask, transcoder):
        pass
    
    def onTranscoderRelieved(self, transcodingtask, transcoder):
        pass

    
class TranscodingTaskListener(object):
    
    implements(ITranscodingTaskListener)

    def onTranscoderElected(self, transcodingtask, transcoder):
        pass
    
    def onTranscoderRelieved(self, transcodingtask, transcoder):
        pass


class TranscodingTask(Loggable, EventSource, TranscoderListener):
    
    implements(ITask)
    
    logCategory = 'admin-transcoding'
    
    def __init__(self, customerCtx):
        pass
