# -*- Mode: Python; test-case-name: flumotion.test.test_enum -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# This file may be distributed and/or modified under the terms of
# the GNU General Public License version 2 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.GPL" in the source distribution for more information.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import os
import sys

from twisted.internet import gtk2reactor
HAVE_GTK2REACTOR = True
try:
    gtk2reactor.install(useGtk=False)
except AssertionError:
    if not isinstance(sys.modules['twisted.internet.reactor'],
                      gtk2reactor.Gtk2Reactor):
        HAVE_GTK2REACTOR = False

import gobject
gobject.threads_init()

import pygst
pygst.require('0.10')
import gst

import tempfile

from twisted.internet import defer
from twisted.python.failure import Failure

from flumotion.component.transcoder import gstutils

class GstreamerUnitTestMixin:
    if not HAVE_GTK2REACTOR:
        skip = 'gtk2reactor is required for this test case'


class MediaGenerator(object):

    def __init__(self, path=None, videoCodec=None, audioCodec=None, muxer=None,
                 duration=1, videoWidth=320, videoHeight=240, videoRate=25,
                 videoPAR=(1,1), audioRate=44100, audioChannels=2):
        assert videoCodec or audioCodec
        assert not (videoCodec and audioCodec and not muxer)
        self.path = path
        self.videoCodec = videoCodec
        self.audioCodec = audioCodec
        self.muxer = muxer
        self.duration = duration
        self.videoWidth = videoWidth
        self.videoHeight = videoHeight
        self.videoRate = videoRate
        self.videoPAR = videoPAR
        self.audioRate = audioRate
        self.audioChannels = audioChannels
        self._deferred = None
        self._pipeline = None
        self._bus = None

    def generate(self):
        if self._deferred:
            return self._deferred
        self._deferred = defer.Deferred()
        self._deferred.addBoth(self.__bbShutdownPipeline)
        try:
            if not self.path:
                handle, self.path =  tempfile.mkstemp()
                os.close(handle)
                self._deferred.addErrback(self.__ebRemoveTempFile)

            if self.videoCodec:
                if isinstance(self.videoRate, (int, long)):
                    videoRate = (self.videoRate, 1)
                    vRate = float(self.videoRate)
                elif isinstance(self.videoRate, (list, tuple)):
                    videoRate = self.videoRate
                    vRate = float(videoRate[0]) / float(videoRate[1])
                aBlockSize = int(round(self.audioRate / vRate))
                buffCount = int(round(vRate * self.duration)) + 1
            else:
                aBlockSize = int(round(self.audioRate / 10))
                buffCount = int(round(10 * self.duration)) + 1
            self._pipeline = gst.Pipeline("GenMediaFile")

            filesink = gst.element_factory_make("filesink")
            filesink.props.location = self.path
            self._pipeline.add(filesink)
            if self.muxer:
                muxer = gst.parse_launch(self.muxer)
                self._pipeline.add(muxer)
                muxer.link(filesink)
            else:
                muxer = filesink

            if self.videoCodec:
                vCaps = ("width=(int)%d, height=(int)%d, framerate=(fraction)%d/%d, "
                         "pixel-aspect-ratio=(fraction)%d/%d"
                         % (self.videoWidth, self.videoHeight, videoRate[0],
                            videoRate[1], self.videoPAR[0], self.videoPAR[1]))
                vCaps = "video/x-raw-rgb, %s;video/x-raw-yuv, %s" % (vCaps, vCaps)
                videotestsrc = gst.element_factory_make("videotestsrc")
                videotestsrc.props.num_buffers = buffCount
                videocaps = gst.element_factory_make("capsfilter")
                videocaps.props.caps = gst.caps_from_string(vCaps)
                videoencoder = gstutils.parse_bin_from_description(self.videoCodec, True)
                videoqueue = gst.element_factory_make("queue")
                self._pipeline.add(videotestsrc, videocaps, videoencoder, videoqueue)
                gst.element_link_many(videotestsrc, videocaps, videoencoder,
                                      videoqueue, muxer)

            if self.audioCodec:
                aCaps = ("rate=(int)%d, channels=(int)%d"
                         % (self.audioRate, self.audioChannels))
                aCaps = "audio/x-raw-int, %s;audio/x-raw-float, %s" % (aCaps, aCaps)
                audiotestsrc = gst.element_factory_make("audiotestsrc")
                audiotestsrc.props.num_buffers = buffCount
                audiotestsrc.props.samplesperbuffer = aBlockSize
                audioconvert = gst.element_factory_make("audioconvert")
                audiocaps = gst.element_factory_make("capsfilter")
                audiocaps.props.caps = gst.caps_from_string(aCaps)
                audioencoder = gstutils.parse_bin_from_description(self.audioCodec, True)
                audioqueue = gst.element_factory_make("queue")
                self._pipeline.add(audiotestsrc, audioconvert, audiocaps,
                                   audioencoder, audioqueue)
                gst.element_link_many(audiotestsrc, audioconvert, audiocaps,
                                      audioencoder, audioqueue, muxer)

            d = defer.Deferred()
            self._bus = self._pipeline.get_bus()
            self._bus.add_signal_watch()
            self._bus.connect("message", self._bus_message_callback)
            ret = self._pipeline.set_state(gst.STATE_PLAYING)
            if ret == gst.STATE_CHANGE_FAILURE:
                raise Exception("Fail to change pipeline state to PLAYING")
            return self._deferred
        except:
            self._deferred.errback(Failure())
            return self._deferred


    ## Private Methods ##

    def __ebRemoveTempFile(self, failure):
        if os.path.isfile(self.path):
            os.remove(self.path)
        return failure

    def __bbShutdownPipeline(self, result):
        if self._bus:
            self._bus.remove_signal_watch()
        self._bus = None
        if self._pipeline:
            self._pipeline.set_state(gst.STATE_NULL)
        self._pipeline = None
        return result

    def _bus_message_callback(self, bus, message):
        if message.type == gst.MESSAGE_STATE_CHANGED:
            if (message.src == self._pipeline):
                new = message.parse_state_changed()[1]
                if new == gst.STATE_PLAYING:
                    # Add a timeout
                    pass
            return
        if message.type == gst.MESSAGE_EOS:
            self._deferred.callback(self)
            return
        if message.type == gst.MESSAGE_ERROR:
            gstgerror, debug = message.parse_error()
            self._deferred.errback(Exception(gsterror))
            return
