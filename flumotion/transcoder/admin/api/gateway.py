# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import classProvides

from flumotion.inhouse.spread import avatars


class Avatar(avatars.Avatar):
    
    classProvides(avatars.IAvatarFactory)
    
    def __init__(self, service, avatarId, mind):
        avatars.Avatar.__init__(self, service, avatarId, mind)
        self._admin = service.getServer().getAdmin()
