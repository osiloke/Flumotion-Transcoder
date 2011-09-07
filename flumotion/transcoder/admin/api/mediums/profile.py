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

from zope.interface import implements

from flumotion.transcoder.admin.datastore import profile
from flumotion.transcoder.admin.api import interfaces, api


class ProfileMedium(api.IdentifiedMedium):

    implements(interfaces.IProfileMedium)

    api.register_medium(interfaces.IProfileMedium,
                        profile.IProfileStore)

    api.readonly_property("name")
    api.readonly_property("subdir")
    api.readonly_property("inputDir")
    api.readonly_property("outputDir")
    api.readonly_property("failedDir")
    api.readonly_property("doneDir")
    api.readonly_property("linkDir")
    api.readonly_property("workDir")
    api.readonly_property("configDir")
    api.readonly_property("tempRepDir")
    api.readonly_property("failedRepDir")
    api.readonly_property("doneRepDir")
    api.readonly_property("outputMediaTemplate")
    api.readonly_property("outputThumbTemplate")
    api.readonly_property("linkFileTemplate")
    api.readonly_property("configFileTemplate")
    api.readonly_property("reportFileTemplate")
    api.readonly_property("linkTemplate")
    api.readonly_property("linkURLPrefix")
    api.readonly_property("enablePostprocessing")
    api.readonly_property("enablePreprocessing")
    api.readonly_property("enableLinkFiles")
    api.readonly_property("transcodingPriority")
    api.readonly_property("processPriority")
    api.readonly_property("preprocessCommand")
    api.readonly_property("postprocessCommand")
    api.readonly_property("preprocessTimeout")
    api.readonly_property("postprocessTimeout")
    api.readonly_property("transcodingTimeout")
    api.readonly_property("monitoringPeriod")

    def __init__(self, profStore):
        api.IdentifiedMedium.__init__(self, profStore)


    ## IProfilesMedium Methodes ##

    @api.make_remote()
    def getTargets(self):
        return self.reference.getTargetStores()

    @api.make_remote()
    def getTarget(self, identifier):
        return self.reference.getTargetStore(identifier)
