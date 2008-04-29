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

from flumotion.transcoder.admin.context import profile
from flumotion.transcoder.admin.api import interfaces, api


class ProfileMedium(api.NamedMedium):
    
    implements(interfaces.IProfileMedium)
    
    api.register_medium(interfaces.IProfileMedium,
                        profile.IUnboundProfileContext)

    api.readonly_store_property("name")
    api.readonly_store_property("subdir")
    api.readonly_store_property("inputDir")
    api.readonly_store_property("outputDir")
    api.readonly_store_property("failedDir")
    api.readonly_store_property("doneDir")
    api.readonly_store_property("linkDir")
    api.readonly_store_property("workDir")
    api.readonly_store_property("configDir")
    api.readonly_store_property("tempRepDir")
    api.readonly_store_property("failedRepDir")
    api.readonly_store_property("doneRepDir")
    api.readonly_store_property("outputMediaTemplate")
    api.readonly_store_property("outputThumbTemplate")
    api.readonly_store_property("linkFileTemplate")
    api.readonly_store_property("configFileTemplate")
    api.readonly_store_property("reportFileTemplate")
    api.readonly_store_property("linkTemplate")
    api.readonly_store_property("linkURLPrefix")
    api.readonly_store_property("enablePostprocessing")
    api.readonly_store_property("enablePreprocessing")
    api.readonly_store_property("enableLinkFiles")
    api.readonly_store_property("transcodingPriority")
    api.readonly_store_property("processPriority")
    api.readonly_store_property("preprocessCommand")
    api.readonly_store_property("postprocessCommand")
    api.readonly_store_property("preprocessTimeout")
    api.readonly_store_property("postprocessTimeout")
    api.readonly_store_property("transcodingTimeout")
    api.readonly_store_property("monitoringPeriod")
    
    def __init__(self, profCtx):
        api.NamedMedium.__init__(self, profCtx)
    
    
    ## IProfilesMedium Methodes ##

    @api.make_remote()
    def getTargets(self):
        return self.reference.getTargetContexts()

    @api.make_remote()
    def getTarget(self, identifier):
        return self.reference.getTargetContext(identifier)
