# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.
# flumotion-platform - Flumotion Streaming Platform

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

# Logging categories
TRANSCODER_LOG_CATEGORY = "file-trans"
MONITOR_LOG_CATEGORY = "file-monitor"

# Discoverer max interleave in seconds
MAX_INTERLEAVE = 2

SMOOTH_UPTDATE_DELAY = 0.2

# Falling back thumbnailing interval in second
FALLING_BACK_THUMBS_PERIOD_VALUE = 1

# Transcoding update period in second
PROGRESS_PERIOD = 1

# Source file analyse timeout
SOURCE_ANALYSE_TIMEOUT = 60
TARGET_ANALYSE_TIMEOUT = 60

# Transcoder timeouts
PLAY_ERROR_TIMEOUT = 8
TRANSCODER_PLAYING_TIMEOUT = 20
TRANSCODER_PREPARE_TIMEOUT = 60
TRANSCODER_UPDATE_TIMEOUT = 60
TRANSCODER_FINALIZE_TIMEOUT = 60
TRANSCODER_ABORT_TIMEOUT = 60

# Thumbnailer timeouts
PLAY_ERROR_TIMEOUT = 5
THUMBNAILER_PLAYING_TIMEOUT = 8