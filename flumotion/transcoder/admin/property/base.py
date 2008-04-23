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

import copy

from zope.interface import Interface, implements

from flumotion.inhouse import utils

    
    
class IComponentProperties(Interface):

    def getDigest(self):
        pass

    def prepare(self, workerCtx):
        pass

    def asComponentProperties(self, workerCtx):
        pass

    def asLaunchArguments(self, workerCtx):
        pass
    

class ComponentPropertiesMixin(object):
    
    def __hash__(self):
        return hash(self.getDigest())
    
    def __eq__(self, props):
        return (IComponentProperties.providedBy(props)
                and (props.getDigest() == self.getDigest()))
        
    def __ne__(self, props):
        return not self.__eq__(props)

    def getDigest(self):
        pass


class GenericComponentProperties(ComponentPropertiesMixin):
    
    implements(IComponentProperties)
    
    @classmethod
    def createFromComponentDict(cls, workerCtx, props):
        return GenericComponentProperties(props)
    
    def __init__(self, props):
        self._properties = copy.deepcopy(props)
        self._digest = utils.digestParameters(self._properties)
        
    
    ## IComponentProperties Implemenetation ##
    
    def getDigest(self):
        return self._digest
    
    def prepare(self, workerCtx):
        pass
    
    def asComponentProperties(self, workerCtx):
        raise NotImplementedError()
    
    def asLaunchArguments(self, workerCtx):
        raise NotImplementedError()
