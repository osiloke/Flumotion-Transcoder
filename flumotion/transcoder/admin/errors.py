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


class StoreError(TranscoderError):
    def __init__(self, *args, **kwargs):
        TranscoderError.__init__(self, *args, **kwargs)


class PropertiesError(TranscoderError):
    def __init__(self, *args, **kwargs):
        TranscoderError.__init__(self, *args, **kwargs)


class ComponentRejectedError(TranscoderError):
    """
    A component set rejected the component.
    Doesn't mean the component doesn't exist.
    """
    def __init__(self, *args, **kwargs):
        TranscoderError.__init__(self, *args, **kwargs)


class OrphanComponentError(TranscoderError):
    """
    An operation couldn't be done because the
    component is orphan (its worker is not running).
    """
    def __init__(self, *args, **kwargs):
        TranscoderError.__init__(self, *args, **kwargs)


class WaiterError(TranscoderError):
    """
    A wait operation couldn't be completed.
    """
    def __init__(self, *args, **kwargs):
        TranscoderError.__init__(self, *args, **kwargs)


class NotificationError(TranscoderError):
    """
    A Notification couldn't be performed.
    """
    def __init__(self, *args, **kwargs):
        TranscoderError.__init__(self, *args, **kwargs)


class DocumentError(TranscoderError):
    """
    A documetn related error.
    """
    def __init__(self, *args, **kwargs):
        TranscoderError.__init__(self, *args, **kwargs)
