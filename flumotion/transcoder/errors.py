# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

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


