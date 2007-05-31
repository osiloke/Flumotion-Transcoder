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
                flowContext, state, *args, **kwargs):
    return FlowProxy(logger, parent, identifier, manager, 
                     flowContext, state, *args, **kwargs)


class IFlowListener(Interface):
    def onFlowComponentAdded(self, flow, component):
        pass
    
    def onFlowComponentRemoved(self, flow, component):
        pass


class FlowListener(object):
    
    implements(IFlowListener)
    
    def onFlowComponentAdded(self, flow, component):
        pass
    
    def onFlowComponentRemoved(self, flow, component):
        pass


class FlowProxy(groupproxy.ComponentGroupProxy):
    
    _componentAddedEvent = "FlowComponentAdded"
    _componentRemovedEvent = "FlowComponentRemoved"
    _componentDomain = ComponentDomainEnum.flow
    
    def __init__(self, logger, parent, identifier, manager, 
                 flowContext, flowState):
        groupproxy.ComponentGroupProxy.__init__(self, logger, parent, 
                                                identifier, manager,
                                                flowContext,
                                                flowState,
                                                IFlowListener)
