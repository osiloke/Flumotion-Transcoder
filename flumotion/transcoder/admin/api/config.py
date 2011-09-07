# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007,2008,2009 Fluendo, S.L.
# Copyright (C) 2010,2011 Flumotion Services, S.A.
# All rights reserved.
#
# This file may be distributed and/or modified under the terms of
# the GNU Lesser General Public License version 2.1 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.LGPL" in the source distribution for more information.
#
# Headers in this file shall remain intact.

from flumotion.inhouse import properties

from flumotion.transcoder.admin import enums


class BouncerConfig(properties.PropertyBag):
    type = properties.Enum("type", enums.APIBouncerEnum, enums.APIBouncerEnum.saltedsha256)
    users = properties.Dict(properties.String("users"))


class APIConfig(properties.PropertyBag):
    bouncer = properties.Child("bouncer", BouncerConfig)
    host = properties.String('host', "localhost", False)
    port = properties.Integer('port', 7600, False)
    useSSL = properties.Boolean('use-ssl', True)
    certificate = properties.String('certificate', "default.pem")
