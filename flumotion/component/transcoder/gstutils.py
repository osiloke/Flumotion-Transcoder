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
from gst.extend import discoverer

from flumotion.transcoder import defer
from flumotion.component.transcoder import compconsts, videosize


class Discoverer(discoverer.Discoverer):
    """
    A deferred version of the discoverer.
    """
    def __init__(self, filePath):
        discoverer.Discoverer.__init__(self, filePath, 
                                       max_interleave=compconsts.MAX_INTERLEAVE)
        self.filePath = filePath
        
    def discover(self):
        d = defer.Deferred()
        self.connect('discovered', self._discoverer_callback, d)
        discoverer.Discoverer.discover(self)
        return d
                  
    
    def _discoverer_callback(self, discoverer, is_media, deferred):
        if is_media:
            deferred.callback(discoverer)
        else:
            error = Exception(("Discoverer does not think "
                               + "'%s' is a media file")
                              % self.filePath)
            deferred.errback(error)
    

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
