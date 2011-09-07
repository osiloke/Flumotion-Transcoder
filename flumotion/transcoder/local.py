# vi:si:et:sw=4:sts=4:ts=4

# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007,2008,2009 Fluendo, S.L.
# Copyright (C) 2010,2011 Flumotion Services, S.A.
# All rights reserved.
#
# This file may be distributed and/or modified under the terms of
# the GNU Lesser General Public License version 2.1 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.LGPL" in the source distribution for more information.
#
# Headers in this file shall remain intact.

from flumotion.inhouse import utils


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

    def updateFromComponentProperties(self, props):
        roots = [prop.split(':', 1)
                 for prop in props.get("local-root", [])]
        self._roots.update(dict(roots))
        name = props.get("local-name", "")
        if name:
            self._name = name

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

    def asLaunchArguments(self):
        args = []
        args.append(utils.mkCmdArg(str(self._name), "local-name="))
        for root, value in self._roots.iteritems():
            args.append(utils.mkCmdArg("%s:%s" % (root, value), "local-root="))
        return args
