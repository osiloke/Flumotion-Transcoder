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

from flumotion.inhouse import utils
from flumotion.inhouse.fileutils import PathAttributes

from flumotion.transcoder.admin.property import base
from flumotion.ovp.utils import a_better_digest


class BaseMonitorProperties(base.ComponentPropertiesMixin):
    implements(base.IComponentProperties)

    @classmethod
    def createFromComponentDict(cls, workerCtx, props, **kwargs):
        named_profiles = props.get('named-profile', list())
        named_profiles = map(lambda s: s.split('!'), named_profiles)
        profiles = props.get("profile", list())
        name = props.get("admin-id", "")
        return cls(name, profiles=profiles, named_profiles=named_profiles, **kwargs)

    @classmethod
    def createFromContext(cls, custCtx, **kwargs):
        profiles = []
        named_profiles = []
        for profCtx in custCtx.iterUnboundProfileContexts():
            profiles.append(profCtx.inputBase)
            if int(profCtx.active):
                named_profiles.append((profCtx.name, profCtx.inputBase, 1))
            else:            
                named_profiles.append((profCtx.name, profCtx.inputBase, 0))
        return cls(custCtx.name, profiles=profiles, named_profiles=named_profiles, **kwargs)


    def __init__(self, name, profiles, named_profiles=None, **kwargs):
        assert isinstance(profiles, (list, tuple))
        self._name = name
        self._profiles = tuple(profiles)
        self._digest = a_better_digest((name, profiles, named_profiles, kwargs))
        self._named_profiles = named_profiles
        

    def asComponentProperties(self, workerCtx):
        props = []
        local = workerCtx.getLocal()
        for p in self._profiles:
            props.append(("profile", str(p)))
        for np in self._named_profiles:
            props.append(("named-profile", '!'.join(map(str, np))))
        props.append(("admin-id", self._name))
        props.extend(local.asComponentProperties())
        return props

    #==========================================================================
    # base.IComponentProperties Implementation
    #==========================================================================
    
    def getDigest(self):
        return self._digest

    def prepare(self, workerCtx):
        pass


class MonitorProperties(BaseMonitorProperties):

    implements(base.IComponentProperties)

    @classmethod
    def createFromComponentDict(cls, workerCtx, props):
        return super(MonitorProperties, cls).createFromComponentDict(
            workerCtx, props,
            scanPeriod=props.get("scan-period", None),
            setup_callback = props.get("setup-callback", None),
            pathAttr=PathAttributes.createFromComponentProperties(props)
        )

    @classmethod
    def createFromContext(cls, custCtx):
        return super(MonitorProperties, cls).createFromContext(
            custCtx,
            scanPeriod=custCtx.monitoringPeriod,
            setup_callback=custCtx.setup_callback,
            pathAttr=custCtx.pathAttributes
        )

    def __init__(self, name, scanPeriod=None, setup_callback=None, pathAttr=None, **kwargs):
        super(MonitorProperties, self).__init__(name, **kwargs)
        self._directories = self._profiles # old name
        self._scanPeriod = scanPeriod
        self._setup_callback = setup_callback
        self._pathAttr = pathAttr


    def asComponentProperties(self, workerCtx):
        props = super(MonitorProperties, self).asComponentProperties(workerCtx)
        if self._scanPeriod:
            props.append(("scan-period", self._scanPeriod))
        if self._setup_callback:
            props.append(("setup-callback", self._setup_callback))
        if self._pathAttr:
            props.extend(self._pathAttr.asComponentProperties())
        return props

    def asLaunchArguments(self, workerCtx):
        args = []
        local = workerCtx.getLocal()
        for d in self._profiles:
            args.append(utils.mkCmdArg(str(d), "profile="))
        if self._scanPeriod:
            args.append(utils.mkCmdArg(str(self._scanPeriod), "scan-period="))
        if self._setup_callback:
            args.append(utils.mkCmdArg(str(self._setup_callback), "setup-callback="))
        if self._pathAttr:
            args.extend(self._pathAttr.asLaunchArguments())
        args.extend(local.asLaunchArguments())
        return args


class HttpMonitorProperties(BaseMonitorProperties):

    implements(base.IComponentProperties)

    @classmethod
    def createFromComponentDict(cls, workerCtx, props):
        return super(HttpMonitorProperties, cls).createFromComponentDict(
            workerCtx, props,
            scanPeriod=props.get("scan-period", None),
            setup_callback = props.get("setup-callback", None),
            port=props.get("port", 7680),
            pathAttr=PathAttributes.createFromComponentProperties(props)
        )

    @classmethod
    def createFromContext(cls, custCtx):
        try:
            port = custCtx.monitorPort
        except:
            port = 7680
        return super(HttpMonitorProperties, cls).createFromContext(
            custCtx,
            scanPeriod=custCtx.monitoringPeriod,
            setup_callback=custCtx.setup_callback,
            pathAttr=custCtx.pathAttributes,
            port=port
        )

    def __init__(self, name, port, scanPeriod=None, setup_callback=None, pathAttr=None, **kwargs):
        super(HttpMonitorProperties, self).__init__(name, **kwargs)
        self._scanPeriod = scanPeriod
        self._setup_callback = setup_callback
        self._pathAttr = pathAttr
        self._port = port

    def asComponentProperties(self, workerCtx):
        props = super(HttpMonitorProperties, self).asComponentProperties(workerCtx)
        if self._scanPeriod:
            props.append(("scan-period", self._scanPeriod))
        if self._setup_callback:
            props.append(("setup-callback", self._setup_callback))
        if self._pathAttr:
            props.extend(self._pathAttr.asComponentProperties())
        props.append(("port", self._port))
        return props

    def asLaunchArguments(self, workerCtx):
        args = []
        local = workerCtx.getLocal()
        args.append(utils.mkCmdArg(str(self._profiles), "profile="))
        if self._scanPeriod:
            args.append(utils.mkCmdArg(str(self._scanPeriod), "scan-period="))
        if self._setup_callback:
            args.append(utils.mkCmdArg(str(self._setup_callback), "setup-callback="))
        if self._pathAttr:
            args.extend(self._pathAttr.asLaunchArguments())
        args.append(utils.mkCmdArg(str(self._port), "port="))
        args.extend(local.asLaunchArguments())
        return args

