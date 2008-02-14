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

import gobject
import gst

from zope.interface import Interface

from flumotion.inhouse import log


class IThumbnailSampler(Interface):
    
    def prepare(self, startTime):
        pass
        
    def update(self, streamTime, buffer):
        pass

    def finalize(self):
        pass


class ThumbSink(gst.BaseSink):

    __gsttemplates__ = (
        gst.PadTemplate("sink",
                        gst.PAD_SINK,
                        gst.PAD_ALWAYS,
                        gst.caps_new_any()),
        )

    def __init__(self, sampler, name=None):
        gst.BaseSink.__init__(self)
        assert IThumbnailSampler.providedBy(sampler)
        self._sampler = sampler
        if name: self.props.name = name
        self.set_sync(False)
        self._error = False
        self._prepared = False
        self._segment = None


    ## Public Methods ##
    
    def postError(self, msg, debug=None):
        error = gst.GError(gst.STREAM_ERROR,
                           gst.STREAM_ERROR_FAILED, msg)
        message = gst.message_new_error(self, error, debug or "")
        self.post_message(message)
        self._error = True

    
    ## Overriden Methods ##

    def do_event(self, event):
        if event.type == gst.EVENT_NEWSEGMENT:
            segInfo = gst.Event.parse_new_segment(event)
            if not self._segment:
                self._segment = gst.Segment()
                startTime = None
                if segInfo[2] == gst.FORMAT_TIME:
                    startTime = segInfo[3]
                self._sampler.prepare(startTime)
            self._segment.set_newsegment(*segInfo)
        elif event.type == gst.EVENT_EOS:
            self._sampler.finalize()
        return True

    def do_render(self, buffer):
        if self._error or not self._segment:
            return gst.FLOW_ERROR
        try:
            streamTime = self._segment.to_stream_time(gst.FORMAT_TIME,
                                                      buffer.timestamp)
            self._sampler.update(streamTime, buffer)
            return gst.FLOW_OK
        except Exception, e:
            msg = "Failure during thumbnail sampling: " + str(e)
            debug = log.getExceptionMessage(e)
            self.postError(msg, debug)
            return gst.FLOW_ERROR


gobject.type_register(ThumbSink)
