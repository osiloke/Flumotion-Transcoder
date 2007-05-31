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

from flumotion.transcoder.errors import TranscoderError

class TranscoderProperties(object):
    
    def __init__(self, config, niceLevel=None):
        assert config != None
        self._config = config
        self._niceLevel = niceLevel
        
    def getPropertySet(self, workerContext):
        props = {}
        props["config"] = self._config
        if self._niceLevel:
            props["nice-level"] = self._niceLevel
        return props