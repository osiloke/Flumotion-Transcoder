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

from flumotion.inhouse import properties

from flumotion.transcoder.admin import enums


class BouncerConfig(properties.PropertyBag):
    type = properties.Enum("type", enums.APIBouncerEnum, enums.APIBouncerEnum.saltedsha256)
    users = properties.Dict(properties.String("users"))


class APIConfig(properties.PropertyBag):
    bouncer = properties.Child("bouncer", BouncerConfig)
    host = properties.String('host', "localhost", False)
    port = properties.Integer('port', 7667, False)
    useSSL = properties.Boolean('use-ssl', True)
    certificate = properties.String('certificate', "default.pem")    
