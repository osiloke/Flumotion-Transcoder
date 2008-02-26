# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from twisted.spread import flavors
from twisted.python.reflect import qual

from flumotion.inhouse.spread import mediums 


class ITranscoderGateway(mediums.IServerMedium):
    pass


class Identity(flavors.Copyable, flavors.RemoteCopy):
    
    def __init__(self, identifier):
        self._identifier = identifier
    
    def getStateToCopyFor(self, perspective):
        print "#"*40, "getStateToCopyFor", perspective
        return {"identifier": self._identifier}

    def setCopyableState(self, state):
        self._identifier = state["identifier"]


## Private ##

from twisted.spread import jelly

jelly.setUnjellyableForClass(qual(Identity), Identity)