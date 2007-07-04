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

from twisted.python.reflect import qual
from twisted.spread import jelly

from flumotion.transcoder import utils
from flumotion.transcoder import constants
from flumotion.transcoder.errors import VirtualPathError


_rootPattern = re.compile("(\w*):(.*)")

class VirtualPath(object, jelly.Jellyable, jelly.Unjellyable):
    
    @classmethod
    def transpose(cls, path, fromLocal, toLocal):
        vp = cls.virtualize(path, fromLocal)
        return vp.localize(toLocal)
    
    @classmethod
    def virtualize(cls, path, local):
        """
        From a path and local, it creates a VirtualPath instance.
        """
        path = utils.cleanupPath(path)
        for name, value in local.iterVirtualRoots():
            value = utils.cleanupPath(value)
            if path.startswith(value):
                path = utils.ensureAbsPath(path[len(value):])
                return VirtualPath(path, name)
        raise VirtualPathError("Cannot virtualize local path '%s', "
                               "no compatible virtual root found" % path)
    
    def __init__(self, path, rootName=None):
        if isinstance(path, str):
            root2 = None
            m = _rootPattern.match(path)
            if m:
                root2, path = m.groups()
            if rootName and root2 and (rootName != root2):
                raise VirtualPathError("Virtual root conflict: '%s' '%s'"
                                       % (rootName, root2))
            self._path = path
            self._root = rootName or root2 or constants.DEFAULT_ROOT
        elif isinstance(path, VirtualPath):
            self._path = path._path
            self._root = path._root
        else:
            raise TypeError()

    def getPath(self):
        return self._path
    
    def getRoot(self):
        return self._root
    
    def localize(self, local):
        """
        The parameters are a local with virtual roots.
        Return a path constructed with the first value in the
        specified local's roots that match the root name and the path.
        """
        roots = local.getVirtualRoots()
        if self._root in roots:
            return utils.joinPath(roots[self._root], self._path)
        raise VirtualPathError("Cannot localize virtual path '%s', "
                               " virtual root not found for this local" % self)
    
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
    
    def __add__(self, path):
        if not isinstance(path, str):
            raise TypeError("cannot concatenate '%s' to VirtualPath"
                            % path.__class__.__name__)
        return VirtualPath(self).append(path)
        
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


    ## Jellyable Overriden Methods ##

    def jellyFor(self, jellier):
        sxp = jellier.prepare(self)
        sxp.extend([
            qual(self.__class__),
            self._root, self._path])
        return jellier.preserve(self, sxp)
    
    
    ## Unjellyable Overriden Methods ##
    
    def unjellyFor(self, unjellier, jellyList):
        self._root, self._path = jellyList[1:]
        return self


jelly.setUnjellyableForClass(qual(VirtualPath), VirtualPath)