# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import Interface, implements

from flumotion.transcoder.admin.enums import ComponentDomainEnum
from flumotion.transcoder.admin.proxy import group


class AtmosphereProxy(group.ComponentGroupProxy):

    _componentDomain = ComponentDomainEnum.atmosphere

    def __init__(self, logger, parentPxy, identifier,
                 managerPxy, atmoCtx, atmoState):
        group.ComponentGroupProxy.__init__(self, logger, parentPxy,
                                           identifier, managerPxy,
                                           atmoCtx, atmoState)

    def getAtmosphereContext(self):
        return self._context


def instantiate(logger, parentPxy, identifier, managerPxy,
                atmoCtx, atmoState, *args, **kwargs):
    return AtmosphereProxy(logger, parentPxy, identifier,  managerPxy,
                           atmoCtx, atmoState, *args, **kwargs)
