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

from flumotion.inhouse import fileutils, properties

from flumotion.transcoder import constants, errors


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
        path = fileutils.cleanupPath(path)
        for name, value in local.iterVirtualRoots():
            value = fileutils.cleanupPath(value)
            if path.startswith(value):
                path = fileutils.ensureAbsPath(path[len(value):])
                return VirtualPath(path, name)
        raise errors.VirtualPathError("Cannot virtualize local path '%s', "
                                      "no compatible virtual root found" % path)

    def __init__(self, path, defaultRoot=None):
        if isinstance(path, str):
            m = _rootPattern.match(path)
            if m:
                self._root, self._path = m.groups()
            else:
                self._root = defaultRoot or constants.DEFAULT_ROOT
                self._path = path
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
            return fileutils.joinPath(roots[self._root], self._path)
        raise errors.VirtualPathError("Cannot localize virtual path '%s', "
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
        return VirtualPath(fileutils.joinPath(self._path, virtPath._path),
                              self._root)

    def append(self, *parts):
        goodparts = [p for p in parts if p]
        if not goodparts: return self
        path = fileutils.joinPath(self._path, fileutils.joinPath(*goodparts))
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


class VirtualPathProperty(properties.ValueProperty):

    def __init__(self, descriptor, default=None, required=False):
        properties.ValueProperty.__init__(self, descriptor, default, required)

    def checkValue(self, value):
        return isinstance(value, VirtualPath)

    def str2val(self, strval):
        return VirtualPath(strval)

    def val2str(self, value):
        return str(value)
