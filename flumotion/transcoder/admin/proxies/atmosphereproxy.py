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

from flumotion.transcoder.enums import ComponentDomainEnum
from flumotion.transcoder.admin.proxies import groupproxy


def instantiate(logger, parent, identifier, manager, 
                atmosphereContext, state, *args, **kwargs):
    return AtmosphereProxy(logger, parent, identifier,  manager, 
                           atmosphereContext, state, *args, **kwargs)


class IAtmosphereListener(Interface):

    def onAtmosphereComponentAdded(self, atmosphere, component):
        pass
    
    def onAtmosphereComponentRemoved(self, atmosphere, component):
        pass


class AtmosphereListener(object):
    
    implements(IAtmosphereListener)
    
    def onAtmosphereComponentAdded(self, atmosphere, component):
        pass
    
    def onAtmosphereComponentRemoved(self, atmosphere, component):
        pass


class AtmosphereProxy(groupproxy.ComponentGroupProxy):
    
    _componentAddedEvent = "AtmosphereComponentAdded"
    _componentRemovedEvent = "AtmosphereComponentRemoved"
    _componentDomain = ComponentDomainEnum.atmosphere
    
    def __init__(self, logger, parent, identifier, manager, 
                 atmosphereContext, atmosphereState):
        groupproxy.ComponentGroupProxy.__init__(self, logger, parent, 
                                                identifier, manager,
                                                atmosphereContext,
                                                atmosphereState,
                                                IAtmosphereListener)

