# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.transcoder.admin.contexts.managercontext import ManagerContext
from flumotion.transcoder.admin.datasource import filesource

class AdminContext(object):
    
    def __init__(self, adminConfig):
        self._config = adminConfig

    def getDataSource(self):
        return filesource.FileDataSource(self._config.datasource.file)
        
    def getManagerContext(self):
        return ManagerContext(self._config)
