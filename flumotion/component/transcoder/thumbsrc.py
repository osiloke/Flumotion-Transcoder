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
