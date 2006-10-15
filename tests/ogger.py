#!/usr/bin/env python
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.
# Flumotion Transcoder

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import os
import sys

import gobject
gobject.threads_init()

import pygst
pygst.require('0.10')

import setup
setup.setup()

from flumotion.transcoder import trans

if len(sys.argv) < 3:
    print "Usage: %s [infile] [outfile]" % sys.argv[0]
    sys.exit(1)

mainloop = gobject.MainLoop()

def _done_callback(mt):
    print "Done."
    mainloop.quit()

def _error_callback(mt, reason):
    print "ERROR: %s" % reason
    mainloop.quit()

mt = trans.MultiTranscoder('ogger', sys.argv[1])
# we make it very small because we just want to be make sure we can transcode
profile = trans.Profile('ogg', 'vorbisenc', 'theoraenc', 'oggmux',
    videowidth=32)
mt.addOutput(sys.argv[2], profile)
mt.connect('done', _done_callback)
mt.connect('error', _error_callback)

# we idle_add becaust mt.start() could error immediately before we go in
# the main loop
gobject.idle_add(mt.start)
mainloop.run()
