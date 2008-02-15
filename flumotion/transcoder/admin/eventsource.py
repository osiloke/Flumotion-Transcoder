# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import weakref

from flumotion.inhouse import log

from flumotion.transcoder.admin.errors import EventError


class EventSource(object):
    
    def __init__(self):
        self._handlers = {} # {event: {listener: {callback: (args, kwargs)}]}}


    ## Public Methods ##

    def connect(self, event, listener, callback, *args, **kwargs):
        if event not in self._handlers:
            raise EventError("Unknown event %s, cannot connect %s to %s"
                             % (event, callback, self))
        callbacks = self._handlers[event].setdefault(listener, dict())
        assert not (callback in callbacks)
        callbacks[callback] = (args, kwargs)
        
    def disconnect(self, event, listener, callback=None):
        listeners = self._handlers.get(event, None)
        if listeners: 
            callbacks = listeners.get(listener, None)
            if callbacks:
                if callback is None:
                    del listeners[listener]
                else:
                    if callback in callbacks:
                        del callbacks[callback]

    def emit(self, event, *args, **kwargs):
        listeners = self._handlers.get(event, None)
        if listeners is None:
            raise EventError("Unknown event %s, cannot be emited by %s"
                             % (event, self))
        for callbacks in listeners.values():
            for callback, (cbArgs, cbKWArgs) in callbacks.iteritems():
                self.__callHandler(event, args, kwargs,
                                   callback, cbArgs, cbKWArgs)

    def emitTo(self, event, listener, *args, **kwargs):
        listeners = self._handlers.get(event, None)
        if listeners is None:
            raise EventError("Unknown event %s, cannot be emited by %s"
                             % (event, self))
        callbacks = self._handlers.get(listener, None)
        if callbacks:
            for callback, (cbArgs, cbKWArgs) in callbacks.iteritems():
                self.__callHandler(event, args, kwargs,
                                   callback, cbArgs, cbKWArgs)

    def emitPayload(self, payload, event):
        """
        Special version to be used as a Deferred callback.
        """
        if isinstance(payload, (tuple, list)):
            self.emit(event, *payload)
        else:
            self.emit(event, payload)

    def emitPayloadTo(self, payload, event, listener):
        """
        Special version to be used as a Deferred callback.
        """
        if isinstance(payload, (tuple, list)):
            self.emitTo(event, listener, *payload)
        else:
            self.emit(event, listener, payload)
    
    
    ## Virtual Methods ##
    
    def update(self, listener):
        """
        Send all events to the listener 
        like if it was connected from the begining.
        """

    
    ## Protected Methods ##
    
    def _register(self, event):
        assert event not in self._handlers 
        self._handlers[event] = weakref.WeakKeyDictionary()


    ## Private Methods ##
    
    def __callHandler(self, event, eArgs, eKWArgs, callback, cbArgs, cbKWArgs):
        args = eArgs + cbArgs
        kwargs = dict(eKWArgs)
        kwargs.update(cbKWArgs)
        try:                        
            callback(self, *args, **kwargs)
        except Exception, e:
            log.notifyException(self, e,
                                "Error during event %s", event)
