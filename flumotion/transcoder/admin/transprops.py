# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import implements

from flumotion.common import log

from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.admin.compprops import IComponentProperties
from flumotion.transcoder.admin.compprops import ComponentPropertiesMixin
from flumotion.transcoder.admin.utils import digestParameters
from flumotion.transcoder.admin.virtualpath import VirtualPath

class TranscoderProperties(ComponentPropertiesMixin):
    
    implements(IComponentProperties)
    
    @classmethod
    def createFromWorkerDict(cls, workerContext, props):
        config = props.get("config", None)
        niceLevel = props.get("nice-level", None)
        name = props.get("admin-id", "")
        return cls(name, config, niceLevel)
    
    @classmethod
    def createFromContext(cls, customerCtx):
        #return cls(customerCtx.store.getName(), folders, period)
        raise NotImplementedError()
    
    def __init__(self, name, config, niceLevel=None):
        assert config != None
        self._name = name
        self._config = config
        self._niceLevel = niceLevel
        self._digest = digestParameters(self._name, 
                                        self._config, 
                                        self._niceLevel)

    ## IComponentProperties Implementation ##
        
    def getDigest(self):
        return self._digest
        
    def getComponentProperties(self, workerContext):
        props = {}
        props["config"] = self._config
        if self._niceLevel:
            props["nice-level"] = self._niceLevel
        props.append(("admin-id", self._name))
        return props
