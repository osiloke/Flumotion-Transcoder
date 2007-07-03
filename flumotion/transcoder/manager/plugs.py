# -*- Mode: Python; test-case-name: flumotion.test.test_http -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.component.plugs import lifecycle

# Add VirtualPath jellyer and unjellyer to the manager
from flumotion.transcoder import virtualpath


class TranscoderEnvironment(lifecycle.ManagerLifecycle):
    """
    This plug is only used to import transcoder 
    related modules in the manager.
    This permit to add custome jellyable types without
    having to add them directly in the manager.
    """
