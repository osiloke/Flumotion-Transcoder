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

import copy

from zope.interface import implements

from flumotion.common import log

from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.admin.compprops import IComponentProperties
from flumotion.transcoder.admin.compprops import ComponentPropertiesMixin
from flumotion.transcoder.admin.utils import digestParameters
from flumotion.transcoder.admin.virtualpath import VirtualPath

class MonitorProperties(ComponentPropertiesMixin):
    
    implements(IComponentProperties)
    
    @classmethod
    def createFromWorkerDict(cls, workerContext, props):
        scanPeriod = props.get("scan-period", None)
        absPathList = props.get("directory", list())
        name = props.get("admin-id", "")
        roots = workerContext.getRoots()
        directories = [VirtualPath.fromPath(p, roots) for p in absPathList]
        return cls(name, directories, scanPeriod)
    
    def __init__(self, name, virtDirs, scanPeriod=None):
        assert isinstance(virtDirs, list) or isinstance(virtDirs, tuple)
        self._name = name
        self._directories = tuple(virtDirs)
        self._scanPeriod = scanPeriod
        self._digest = digestParameters(self._name, self._directories, 
                                        self._scanPeriod)
        

    ## IComponentProperties Implementation ##
        
    def getDigest(self):
        return self._digest
        
    def getComponentProperties(self, workerContext):
        props = []
        roots = workerContext.getRoots()
        for d in self._directories:
            path = d.toPath(roots)
            if not path:
                log.warning("Failed to resolve path '%s' for worker '%s'",
                            str(d), workerContext.getLabel())
            else:
                props.append(("directory", path))
        if self._scanPeriod:
            props.append(("scan-period", self._scanPeriod))
        props.append(("admin-id", self._name))
        return props
