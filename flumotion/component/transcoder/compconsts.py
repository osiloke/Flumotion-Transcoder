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

# Logging categories
TRANSCODER_LOG_CATEGORY = "file-trans"
MONITOR_LOG_CATEGORY = "file-monitor"
HTTP_MONITOR_LOG_CATEGORY = "http-monitor"

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

# Maximum time to wait for an error message when changing
# transcoding pipeline state to PLAYING failed
TRANSCODER_PLAY_ERROR_TIMEOUT = 20
# Maximum time to wait for the transcoding pipeline to change to PLAYING state
# It's big to prevent failures when servers are loaded with profiles with
# many transcoding targets
TRANSCODER_PLAYING_TIMEOUT = 120
# Maximum time producers have to prepare the transcoding task
TRANSCODER_PREPARE_TIMEOUT = 60
# Maximum time producers have to update the transcoding pipeline
TRANSCODER_UPDATE_TIMEOUT = 60
# Maximum time producers have to finalize the transcoding task
TRANSCODER_FINALIZE_TIMEOUT = 60
# Maximum time producers have to abort the transcoding task
TRANSCODER_ABORT_TIMEOUT = 60

# Maximum time to wait for an error message when changing
# thumbnailing pipeline state to PLAYING failed
THUMBNAILER_PLAY_ERROR_TIMEOUT = 20
# Maximum time to wait for the thumbnailing pipeline to change to PLAYING state
THUMBNAILER_PLAYING_TIMEOUT = 30
