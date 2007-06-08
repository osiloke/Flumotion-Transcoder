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


class IAdminTask(Interface):

    def getLabel(self):
        pass
    
    def getProperties(self):
        pass
    
    def addComponent(self, component):
        pass
    
    def removeComponent(self, component):
        pass
    
    def getActiveComponent(self):
        pass
    
    def start(self):
        pass
    
    def pause(self):
        pass
    
    def resume(self):
        pass
    
    def stop(self):
        """
        Returns the list of components previously managed by this task.
        """
    
    def abort(self):
        pass
    
    def suggestWorker(self, worker):
        pass
    
    def getActiveWorker(self):
        pass
    

class AdminTask(object):
    
    implements(IAdminTask)

    def getLabel(self):
        pass
    
    def getProperties(self):
        pass
    
    def addComponent(self, component):
        pass
    
    def removeComponent(self, component):
        pass
    
    def getActiveComponent(self):
        pass
    
    def start(self):
        pass
    
    def pause(self):
        pass
    
    def resume(self):
        pass
    
    def stop(self):
        pass
    
    def abort(self):
        pass
    
    def suggestWorker(self, worker):
        pass
    
    def getActiveWorker(self):
        pass
