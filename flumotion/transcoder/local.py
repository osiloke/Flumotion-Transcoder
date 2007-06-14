# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.


class Local(object):
    
    @classmethod
    def createFromComponentProperties(cls, props):
        roots = [prop.split(':', 1) 
                 for prop in props.get("local-root", [])]
        name = props.get("local-name", "")
        return cls(name, roots)
    
    def __init__(self, name, virtualRoots):
        self._name = name
        self._roots = dict(virtualRoots)

    def getName(self):
        return self._name

    def iterVirtualRoots(self):
        return self._roots.iteritems()
    
    def getVirtualRoots(self):
        return self._roots
        
    def asComponentProperties(self):
        result = []
        result.append(("local-name", self._name))
        for root, value in self._roots.iteritems():
            result.append(("local-root", "%s:%s" % (root, value)))
        return result