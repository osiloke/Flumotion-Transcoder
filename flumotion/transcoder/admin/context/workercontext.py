# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

class WorkerContext(object):
    
    def __init__(self, label, workerConfig, workerDefault):
        self._label = label
        self._config = workerConfig
        self._default = workerDefault
    
    def getLabel(self):
        return self._label
    
    def getRoots(self):
        d = dict(self._default.roots)
        if self._config:
            d.update(self._config.roots)
        return d
