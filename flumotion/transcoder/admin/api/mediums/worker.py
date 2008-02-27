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

from flumotion.transcoder.api import interfaces 


class WorkerMedium(mediums.ServerMedium):
    
    implements(interfaces.IWorkerMEdium)
    
    
    def __init__(self, worker):
        self._worker = worker
        
    
    ## IWorkerMedium Methodes ##
    
    def getIdentifier(self):
        self._worker.getIdentifier()
    
    def getName(self):
        self._worker.getName()
    
    def getHost(self):
        self._worker.getHost()
    
    
    ## Make the Methodes remote ##
    
    remote_getIdentifier = getIdentifier
    remote_getName = getName
    remote_getHost = getHost