# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import re

from flumotion.transcoder.admin import constants, utils


_rootPattern = re.compile("(\w*):(.*)")

class VirtualPath(object):
    
    @classmethod
    def fromPath(cls, path, *roots):
        """
        From a path and root definitions,
        it creates a VirtualPath instance.
        """
        path = utils.cleanupPath(path)
        for definition in roots:
            for name, value in definition.iteritems():
                value = utils.cleanupPath(value)
                if path.startswith(value):
                    path = utils.ensureAbsPath(path[len(value):])
                    return VirtualPath(path, name)
        return None
    
    def __init__(self, path, rootName=None):
        root2 = None
        m = _rootPattern.match(path)
        if m:
            root2, path = m.groups()
        #FIXME: Maybe better to raise an exception
        assert (not rootName) or (not root2) or (rootName == root2)
        self._path = path
        self._root = rootName or root2 or constants.DEFAULT_root

    def getPath(self):
        return self._path
    
    def getRootName(self):
        return self._root
    
    def toPath(self, *roots):
        """
        The parameters are dicts of {"rootName": "rootPath"}.
        Return a path constructed with the first value in the
        specified dicts that match the root name and the path.
        If root value is found, return None.
        """
        for definition in roots:
            if self._root in definition:
                return utils.joinPath(definition[self._root], self._path)
        return None
    
    def __str__(self):
        return "%s:%s" % (self._root, self._path)
    
    def __hash__(self):
        return hash(self._root) ^ hash(self._path)
    
    def __eq__(self, virtPath):
        return (isinstance(virtPath, VirtualPath) 
                and (virtPath._path == self._path)
                and (virtPath._root == self._root))
        
    def __ne__(self, virtPath):
        return not self.__eq__(virtPath)
    
    def join(self, virtPath):
        #FIXME: Maybe better to raise an exception
        assert virtPath._root == self._root
        return VirtualPath(utils.joinPath(self._path, virtPath._path),
                              self._root)

    def append(self, *parts):
        goodparts = [p for p in parts if p]
        if not goodparts: return self
        path = utils.joinPath(self._path, utils.joinPath(*goodparts))
        return VirtualPath(path, self._root)

