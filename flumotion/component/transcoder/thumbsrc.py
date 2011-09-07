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

import gst
import gobject

from flumotion.common import common

from flumotion.inhouse import log, utils, fileutils


class ThumbSrc(gst.BaseSrc):

    __gsttemplates__ = (
        gst.PadTemplate("src",
                        gst.PAD_SRC,
                        gst.PAD_ALWAYS,
                        gst.caps_new_any()),
        )

    def __init__(self, name=None, push=True):
        gst.BaseSrc.__init__(self)
        if name:
            self.set_name(name)
        self._buffers = []

    def addBuffer(self, buffer):
        self._buffers.append(buffer)

    def do_create(self, offset, size):
        if self._buffers:
            buffer = self._buffers.pop(0)
            return gst.FLOW_OK, buffer
        return gst.FLOW_UNEXPECTED, None


gobject.type_register(ThumbSrc)
