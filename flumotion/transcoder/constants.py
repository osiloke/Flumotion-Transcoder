# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

# Log categories
DEFER_LOG_CATEGORY = "defer"

CALL_NEXT_DELAY = 0.01

# Default roots
DEFAULT_ROOT = "default"
TEMP_ROOT = "temp"

LINK_TEMPLATE = ('<iframe src="%(outputURL)s" '
                 'width="%(c-width)s" '
                 'height="%(c-height)s" '
                 'frameborder="0" scrolling="no" '
                 'marginwidth="0" marginheight="0" />\n')
