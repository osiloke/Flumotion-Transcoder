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


def parse_bin_from_description(description, ghost_unconnected_pads):
    """
    Implement gst_parse_bin_from_description() in pure python, since the
    C function isn't wrapped.
    """
    desc = "bin.( %s )" % description
    bin = gst.parse_launch(desc)
    if not bin:
        return None
    if ghost_unconnected_pads:
        pad = bin.find_unconnected_pad(gst.PAD_SRC)
        if pad:
            bin.add_pad(gst.GhostPad("src", pad))
        pad = bin.find_unconnected_pad(gst.PAD_SINK)
        if pad:
            bin.add_pad(gst.GhostPad("sink", pad))
    return bin
