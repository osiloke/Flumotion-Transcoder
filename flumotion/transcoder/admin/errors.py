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
    pass


class OperationTimedOutError(TranscoderError):
    """
    An asynchronous operation timed out.
    """

class ComponentRejectedError(TranscoderError):
    """
    A component set rejected the component.
    Doesn't mean the component doesn't exist.
    """

class OrphanComponentError(TranscoderError):
    """
    An operation couldn't be done because the
    component is orphan (its worker is not running).
    """
    
class WaiterError(TranscoderError):
    """
    A wait operation couldn't be completed.
    """