# -*- Mode: Python -*-
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
