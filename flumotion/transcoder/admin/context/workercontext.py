# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.transcoder.local import Local


class WorkerContext(object):
    
    def __init__(self, adminCtx, label, workerConfig, workerDefault):
        self.admin = adminCtx
        self._label = label
        self.config = workerConfig
        self._default = workerDefault
    
    def getLabel(self):
        return self._label
    
    def getLocal(self):
        roots = dict(self._default.roots)
        if self.config:
            roots.update(self.config.roots)
        return Local(self._label, roots)

    def getMaxTask(self):
        if self.config and (self.config.maxTask != None):
            return self.config.maxTask
        return self._default.maxTask
    
    def getMaxKeepFailed(self):
        if self.config and (self.config.maxKeepFailed != None):
            return self.config.maxKeepFailed
        return self._default.maxKeepFailed