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


#FIXME: This class is waaayyyy too much hacky

class TranscoderError(Exception):
    """
    An exception that keep information on the cause of its creation.
    The cause may be other exception or a Failure.
    """
    
    def __init__(self, *args, **kwargs):
        self.data = kwargs.pop('data', None)
        self.cause = kwargs.pop('cause', None)
        Exception.__init__(self, *args, **kwargs)
        self.causeDetails = None
        self.causeTraceback = None
        if self.cause:
            try:
                f = failure.Failure()
                if f.value == self.cause:
                    self.causeTraceback = f.getTraceback()
            except:
                #To ignore failure.NoCurrentExceptionError if there is no current exception
                pass
            from flumotion.transcoder import log
            if isinstance(self.cause, TranscoderError):
                self.causeDetails = log.getExceptionMessage(self.cause)
            if isinstance(self.cause, Exception):
                self.causeDetails = log.getExceptionMessage(self.cause)
            elif isinstance(self.cause, failure.Failure):
                self.causeDetails = log.getFailureMessage(self.cause)
            else:
                self.causeDetails = "Unknown"


class SystemError(TranscoderError):
    def __init__(self, *args, **kwargs):
        TranscoderError.__init__(self, *args, **kwargs)


class TranscoderConfigError(TranscoderError):
    def __init__(self, *args, **kwargs):
        TranscoderError.__init__(self, *args, **kwargs)


class LocalizationError(TranscoderError):
    def __init__(self, *args, **kwargs):
        TranscoderError.__init__(self, *args, **kwargs)


class VirtualPathError(LocalizationError):
    def __init__(self, *args, **kwargs):
        TranscoderError.__init__(self, *args, **kwargs)


class OperationTimedOutError(TranscoderError):
    """
    An asynchronous operation timed out.
    """
    def __init__(self, *args, **kwargs):
        TranscoderError.__init__(self, *args, **kwargs)


class OperationAbortedError(TranscoderError):
    """
    An asynchronous operation couldn't be done.
    """
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


