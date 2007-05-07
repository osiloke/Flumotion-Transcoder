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

import os
import pygst
import gst
import gobject

from flumotion.common import common
from flumotion.transcoder import log

class ThumbnailSink(gst.BaseSink):
    """
    Saves each buffer it receive in a different file.
    The image encoder used MUST encode a full frame by buffer.
    The specified file template can have the following
    variables:
            %(index)d  => index of the thumbnail (starting at 1)
            %(timestamp)d => timestamp of the thumbnail
            %(time)s => composed time of the thumbnail, 
                        like %(hours)02d:%(minutes)02d:%(seconds)02d
            %(hours)d => hours from start
            %(minutes)d => minutes from start
            %(seconds)d => seconds from start
    """

    __gsttemplates__ = (
        gst.PadTemplate("sink",
                        gst.PAD_SINK,
                        gst.PAD_ALWAYS,
                        gst.caps_new_any()),
        )

    def __init__(self, filePathTemplate, name=None):
        gst.BaseSink.__init__(self)
        self.set_sync(False)
        self._filePathTemplate = filePathTemplate
        self._firstTimestamp = 0
        self._index = 0
        self._files = []
        if name:
            self.props.name = name

    def getFiles(self):
        return self._files

    def _getFilePath(self, timestamp, index):
        seconds = timestamp / gst.SECOND
        minutes = seconds / 60
        hours = minutes / 60
        seconds = seconds % 60
        minutes = minutes % 60
        time = "%02d:%02d:%02d" % (hours, minutes, seconds)
        vars = {"seconds": seconds,
                "minutes": minutes,
                "hours": hours,
                "index": index,
                "time": time,
                "timestamp": timestamp}
        return self._filePathTemplate % vars        

    def do_render(self, buffer):
        self._index += 1
        filePath = None
        try:
            filePath = self._getFilePath(buffer.timestamp, self._index)
            common.ensureDir(os.path.dirname(filePath), "thumbnail output")
            f = open(filePath, "w")
            try:
                f.write(buffer.data)
                self._files.append(filePath)
            finally:
                f.close()
            return gst.FLOW_OK
        except Exception, e:
            msg = "Failed to save thumbnail"
            if filePath:
                msg += " '%s'" % filePath
            msg += ": %s" % str(e)
            error = gst.GError(gst.STREAM_ERROR, 
                               gst.STREAM_ERROR_FAILED, msg)
            message = gst.message_new_error(self, error, log.getExceptionMessage(e))
            self.post_message(message)
            return gst.FLOW_ERROR


gobject.type_register(ThumbnailSink)
