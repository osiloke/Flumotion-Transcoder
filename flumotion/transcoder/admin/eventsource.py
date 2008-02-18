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
        if callback in callbacks: 
            raise EventError("Callback %s already connected to %s"
                             % (callback, self))
        callbacks[callback] = (args, kwargs)
        
    def disconnect(self, event, listener, callback=None):
        if event not in self._handlers:
            raise EventError("Unknown event %s, cannot disconnect %s from %s"
                             % (event, callback, self))
        listeners = self._handlers[event]
        callbacks = listeners.get(listener, None)
        if callbacks is None:
            raise EventError("No callback connected to %s, cannot disconnect %s"
                             % (self, callback))
        if callback is None:
            del listeners[listener]
            return
        if callback not in callbacks:
            raise EventError("Callback %s not connected to %s, cannot disconnect it"
                             % (callback, self))
        del callbacks[callback]

    def emit(self, event, *args, **kwargs):
        listeners = self._handlers.get(event, None)
        if listeners is None:
            raise EventError("Unknown event %s, cannot be emited by %s"
                             % (event, self))
        for callbacks in listeners.values():
            for callback, (cbArgs, cbKWArgs) in callbacks.items():
                self.__callHandler(event, args, kwargs,
                                   callback, cbArgs, cbKWArgs)

    def emitTo(self, event, listener, *args, **kwargs):
        listeners = self._handlers.get(event, None)
        if listeners is None:
            raise EventError("Unknown event %s, cannot be emited by %s"
                             % (event, self))
        callbacks = self._handlers.get(listener, None)
        if callbacks:
            for callback, (cbArgs, cbKWArgs) in callbacks.items():
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
        if event in self._handlers:
            raise EventError("Event %s already registered by %s"
                             % (event, self)) 
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
