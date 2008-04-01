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

from flumotion.inhouse.spread import mediums 

from flumotion.transcoder.admin.proxies import fluproxy
from flumotion.transcoder.admin.api import interfaces 


class BaseMedium(mediums.ServerMedium):
    
    implements(interfaces.IBaseMedium)
    
    def __init__(self, ref):
        self.ref = ref
        
    
    ## IBaseMedium Methodes ##
    
    def getIdentifier(self):
        self.ref.getIdentifier()
    
    def getName(self):
        self.ref.getName()

    def getLabel(self):
        self.ref.getLabel()
    
    
    ## Make the Methodes remote ##
    
    remote_getIdentifier = getIdentifier
    remote_getName = getName
    remote_getLabel = getLabel
