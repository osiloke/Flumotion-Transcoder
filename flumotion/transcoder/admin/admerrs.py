# -*- Mode: Python -*-
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

from flumotion.inhouse import errors as iherrors

from flumotion.transcoder import errors


class StoreError(errors.TranscoderError):
    def __init__(self, *args, **kwargs):
        errors.TranscoderError.__init__(self, *args, **kwargs)


class PropertiesError(errors.TranscoderError):
    def __init__(self, *args, **kwargs):
        errors.TranscoderError.__init__(self, *args, **kwargs)


class APIError(errors.TranscoderError):
    def __init__(self, *args, **kwargs):
        errors.TranscoderError.__init__(self, *args, **kwargs)


class OperationTimedOutError(iherrors.TimeoutError):
    """
    An asynchronous operation timed out.
    """
    def __init__(self, *args, **kwargs):
        iherrors.TimeoutError.__init__(self, *args, **kwargs)


class OperationAbortedError(errors.TranscoderError):
    """
    An asynchronous operation couldn't be done.
    """
    def __init__(self, *args, **kwargs):
        errors.TranscoderError.__init__(self, *args, **kwargs)


class ComponentRejectedError(errors.TranscoderError):
    """
    A component set rejected the component.
    Doesn't mean the component doesn't exist.
    """
    def __init__(self, *args, **kwargs):
        errors.TranscoderError.__init__(self, *args, **kwargs)


class OrphanComponentError(errors.TranscoderError):
    """
    An operation couldn't be done because the
    component is orphan (its worker is not running).
    """
    def __init__(self, *args, **kwargs):
        errors.TranscoderError.__init__(self, *args, **kwargs)


class NotificationError(errors.TranscoderError):
    """
    A Notification couldn't be performed.
    """
    def __init__(self, *args, **kwargs):
        errors.TranscoderError.__init__(self, *args, **kwargs)


class DocumentError(errors.TranscoderError):
    """
    A documetn related error.
    """
    def __init__(self, *args, **kwargs):
        errors.TranscoderError.__init__(self, *args, **kwargs)
