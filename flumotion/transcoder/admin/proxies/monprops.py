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

from flumotion.transcoder import utils, fileutils
from flumotion.transcoder.virtualpath import VirtualPath
from flumotion.transcoder.utils import digestParameters
from flumotion.transcoder.admin.errors import PropertiesError
from flumotion.transcoder.admin.proxies.compprops import IComponentProperties
from flumotion.transcoder.admin.proxies.compprops import ComponentPropertiesMixin


class MonitorProperties(ComponentPropertiesMixin):
    
    implements(IComponentProperties)
    
    @classmethod
    def createFromComponentDict(cls, workerContext, props):
        scanPeriod = props.get("scan-period", None)
        directories = props.get("directory", list())
        pathAttr = fileutils.PathAttributes.createFromComponentProperties(props)
        name = props.get("admin-id", "")
        return cls(name, directories, scanPeriod, pathAttr)
    
    @classmethod
    def createFromContext(cls, customerCtx):
        folders = []
        for p in customerCtx.iterUnboundProfileContexts():
            folders.append(p.getInputBase())
        period = customerCtx.store.getMonitoringPeriod()
        pathAttr = customerCtx.getPathAttributes()
        return cls(customerCtx.store.getName(), folders, period, pathAttr)
    
    def __init__(self, name, virtDirs, scanPeriod=None, pathAttr=None):
        assert isinstance(virtDirs, list) or isinstance(virtDirs, tuple)
        self._name = name
        self._directories = tuple(virtDirs)
        self._scanPeriod = scanPeriod
        self._pathAttr = pathAttr
        self._digest = digestParameters(self._name, self._directories, 
                                        self._scanPeriod, self._pathAttr)
        

    ## IComponentProperties Implementation ##
        
    def getDigest(self):
        return self._digest
        
    def prepare(self, workerContext):
        pass
        
    def asComponentProperties(self, workerContext):
        props = []
        local = workerContext.getLocal()
        for d in self._directories:
            props.append(("directory", str(d)))
        if self._scanPeriod:
            props.append(("scan-period", self._scanPeriod))
        if self._pathAttr:
            props.extend(self._pathAttr.asComponentProperties())
        props.append(("admin-id", self._name))
        props.extend(local.asComponentProperties())
        return props
    
    def asLaunchArguments(self, workerContext):
        args = []
        local = workerContext.getLocal()
        for d in self._directories:
            args.append(utils.mkCmdArg(str(d), "directory="))
        if self._scanPeriod:
            args.append(utils.mkCmdArg(str(self._scanPeriod), "scan-period="))
        if self._pathAttr:
            args.extend(self._pathAttr.asLaunchArguments())
        args.extend(local.asLaunchArguments())
        return args
