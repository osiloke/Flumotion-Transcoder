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


class TargetMedium(api.IdentifiedMedium):

    implements(interfaces.IConfigMedium)

    api.register_medium(interfaces.IConfigMedium,
                        target.ITargetStore)

    api.readonly_property("name")
    api.readonly_property("subdir")
    api.readonly_property("outputDir")
    api.readonly_property("linkDir")
    api.readonly_property("workDir")
    api.readonly_property("extension")
    api.readonly_property("outputFileTemplate")
    api.readonly_property("linkFileTemplate")
    api.readonly_property("linkTemplate")
    api.readonly_property("linkURLPrefix")
    api.readonly_property("enablePostprocessing")
    api.readonly_property("enableLinkFiles")
    api.readonly_property("postprocessCommand")
    api.readonly_property("postprocessTimeout")

    def __init__(self, targStore):
        api.IdentifiedMedium.__init__(self, targStore)


    ## ITargetsMedium Methodes ##

    @api.make_remote()
    def getConfig(self):
        return self.reference.getConfigStore()
