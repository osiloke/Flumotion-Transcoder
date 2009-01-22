# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.transcoder import local
from flumotion.transcoder.admin.context import base


class WorkerContext(base.BaseContext):

    def __init__(self, adminCtx, label, workerConfig, workerDefault):
        base.BaseContext.__init__(self, adminCtx)
        self.config = workerConfig
        self.label = label
        self._default = workerDefault

    def getAdminContext(self):
        return self.parent

    def getLocal(self):
        roots = dict(self._default.roots)
        if self.config:
            roots.update(self.config.roots)
        return local.Local(self.label, roots)

    def getMaxTask(self):
        if self.config and (self.config.maxTask != None):
            return self.config.maxTask
        return self._default.maxTask

    def getMaxKeepFailed(self):
        if self.config and (self.config.maxKeepFailed != None):
            return self.config.maxKeepFailed
        return self._default.maxKeepFailed