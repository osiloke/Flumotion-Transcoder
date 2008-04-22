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

from flumotion.transcoder.admin.datastore import target
from flumotion.transcoder.admin.api import interfaces, api
from flumotion.transcoder.admin.api.mediums import named  


class TargetMedium(named.NamedMedium):
    implements(interfaces.IConfigMedium)
    api.registerMedium(interfaces.IConfigMedium,
                       target.ITargetStore)
    
    
    def __init__(self, target):
        named.NamedMedium.__init__(self, target)
    
    
    ## ITargetsMedium Methodes ##

    @api.remote()
    def getConfig(self):
        return self._reference.getConfigStore()