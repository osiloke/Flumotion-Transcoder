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

from twisted.python import failure

from flumotion.inhouse import errors as iherrors


class TranscoderError(iherrors.FlumotionError):
    def __init__(self, *args, **kwargs):
        iherrors.FlumotionError.__init__(self, *args, **kwargs)


class TranscoderConfigError(TranscoderError):
    def __init__(self, *args, **kwargs):
        TranscoderError.__init__(self, *args, **kwargs)


class LocalizationError(TranscoderError):
    def __init__(self, *args, **kwargs):
        TranscoderError.__init__(self, *args, **kwargs)


class VirtualPathError(LocalizationError):
    def __init__(self, *args, **kwargs):
        TranscoderError.__init__(self, *args, **kwargs)


class HandledTranscoderError(TranscoderError):
    def __init__(self, *args, **kwargs):
        TranscoderError.__init__(self, *args, **kwargs)


class TranscoderFailure(failure.Failure):
    def __init__(self, *args, **kwargs):
        failure.Failure.__init__(self, *args, **kwargs)


class HandledTranscoderFailure(TranscoderFailure):
    def __init__(self, *args, **kwargs):
        TranscoderFailure.__init__(self, *args, **kwargs)


