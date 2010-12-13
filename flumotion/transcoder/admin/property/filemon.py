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

from flumotion.inhouse import utils, fileutils

from flumotion.transcoder.admin.property import base


class MonitorProperties(base.ComponentPropertiesMixin):

    implements(base.IComponentProperties)

    @classmethod
    def createFromComponentDict(cls, workerCtx, props):
        scanPeriod = props.get("scan-period", None)
        directories = props.get("directory", list())
        pathAttr = fileutils.PathAttributes.createFromComponentProperties(props)
        name = props.get("admin-id", "")
        return cls(name, directories, scanPeriod, pathAttr)

    @classmethod
    def createFromContext(cls, custCtx):
        folders = []
        for profCtx in custCtx.iterUnboundProfileContexts():
            folders.append(profCtx.inputBase)
        period = custCtx.monitoringPeriod
        pathAttr = custCtx.pathAttributes
        return cls(custCtx.name, folders, period, pathAttr)

    def __init__(self, name, virtDirs, scanPeriod=None, pathAttr=None):
        assert isinstance(virtDirs, list) or isinstance(virtDirs, tuple)
        self._name = name
        self._directories = tuple(virtDirs)
        self._scanPeriod = scanPeriod
        self._pathAttr = pathAttr
        self._digest = utils.digestParameters(self._name, self._directories,
                                              self._scanPeriod, self._pathAttr)

    ## base.IComponentProperties Implementation ##

    def getDigest(self):
        return self._digest

    def prepare(self, workerCtx):
        pass

    def asComponentProperties(self, workerCtx):
        props = []
        local = workerCtx.getLocal()
        for d in self._directories:
            props.append(("directory", str(d)))
        if self._scanPeriod:
            props.append(("scan-period", self._scanPeriod))
        if self._pathAttr:
            props.extend(self._pathAttr.asComponentProperties())
        props.append(("admin-id", self._name))
        props.extend(local.asComponentProperties())
        return props

    def asLaunchArguments(self, workerCtx):
        args = []
        local = workerCtx.getLocal()
        for d in self._directories:
            args.append(utils.mkCmdArg(str(d), "directory="))
        if self._scanPeriod:
            args.append(utils.mkCmdArg(str(self._scanPeriod), "scan-period="))
        if self._pathAttr:
            args.extend(self._pathAttr.asLaunchArguments())
        args.extend(local.asLaunchArguments())
        return args


class HttpMonitorProperties(base.ComponentPropertiesMixin, log.Loggable):

    implements(base.IComponentProperties)

    @classmethod
    def createFromComponentDict(cls, workerCtx, props):
        port = props.get("port", 7680)
        profiles = props.get("profile", list())
        name = props.get("admin-id", "")
        return cls(name, profiles, port)

    @classmethod
    def createFromContext(cls, custCtx):
        profiles = []
        for profCtx in custCtx.iterUnboundProfileContexts():
            profiles.append(profCtx.inputBase)

        try:
            port = custCtx.monitorPort
        except:
            port = 7680
        return cls(custCtx.name, profiles, port)

    def prepare(self, workerCtx):
        pass

    def getDigest(self):
        return self._digest

    def __init__(self, name, profiles, port):
        self._name = name
        self._port = port
        self._profiles = tuple(profiles)
        self._digest = utils.digestParameters(self._name, self._profiles,
                                              self._port)

    def asComponentProperties(self, workerCtx):
        props = []
        local = workerCtx.getLocal()
        for p in self._profiles:
            props.append(("profile", str(p)))
        props.append(("port", self._port))
        props.append(("admin-id", self._name))
        props.extend(local.asComponentProperties())
        return props

    def asLaunchArguments(self, workerCtx):
        args = []
        local = workerCtx.getLocal()
        args.append(utils.mkCmdArg(str(self._profiles), "profile="))
        args.append(utils.mkCmdArg(str(self._port), "port="))
        args.extend(local.asLaunchArguments())
        return args

