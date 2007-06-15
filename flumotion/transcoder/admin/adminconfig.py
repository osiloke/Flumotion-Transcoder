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

from flumotion.transcoder import properties
from flumotion.transcoder.admin import adminconsts


class ManagerConfig(properties.PropertyBag):
    host = properties.String('host', None, True)
    port = properties.Integer('port', None, True)
    username = properties.String('username', None, True)
    password = properties.String('password', None, True)
    useSSL = properties.Boolean('use-ssl', False)
    certificate = properties.String('certificate', None)


class WorkerConfig(properties.PropertyBag):
    roots = properties.Dict(properties.String('roots'))
    maxTask = properties.Integer('max-task', 1, False, True)


class DataSourceConfig(properties.PropertyBag):
    file = properties.String('file', None, True)

class AdminConfig(properties.PropertyBag):
    datasource = properties.Child("data-source", DataSourceConfig)
    roots = properties.Dict(properties.String('roots'))

class ClusterConfig(properties.RootPropertyBag):
    debug = properties.String("debug")
    admin = properties.Child("admin", AdminConfig)
    manager = properties.Child("manager", ManagerConfig)
    workerDefaults = properties.Child('worker-defaults', WorkerConfig)
    workers = properties.ChildDict('workers', WorkerConfig)
    transcoderLabelTemplate = properties.String("transcoder-label-template",
                                                adminconsts.TRANSCODER_LABEL_TEMPLATE)
    monitorLabelTemplate = properties.String("monitor-label-template",
                                             adminconsts.MONITOR_LABEL_TEMPLATE)
    