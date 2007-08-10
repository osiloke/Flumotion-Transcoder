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

from flumotion.transcoder import log

#FIXME: Find a way to not having to assume the childs classes
#       will implement logging methods.

class EventSource(object):
    """
    Manage listeners to events.
    Assume the child classes implement ILogger.
    """
    
    def __init__(self, interfaces):        
        self._listeners = {}
        if isinstance(interfaces, list) or isinstance(interfaces, tuple):
            for interface in interfaces:
                self._listeners[interface] = weakref.WeakKeyDictionary()
        else:
            self._listeners[interfaces] = weakref.WeakKeyDictionary()


    ## Public Methods ##

    def addListener(self, listener, *args, **kwargs):
        # PyChecker doesn't like that the logging method are undefined
        __pychecker__ = "no-classattr"
        interfaces = []
        for interface, listeners in self._listeners.items():
            if not interface.providedBy(listener):
                self.log("Interface %s not provided by listener %s",
                         interface.__name__,
                         listener.__class__.__name__)
                continue
            assert not (listener in listeners)
            interfaces.append(interface)
            self._listeners[interface][listener] = (args, kwargs)        
        assert len(interfaces) > 0
        
    def removeListener(self, listener):
        interfaces = []
        for interface, listeners in self._listeners.items():
            if not interface.providedBy(listener):
                continue
            assert listener in listeners
            interfaces.append(interface)
            del self._listeners[interface][listener]
        assert len(interfaces) > 0

    def syncListener(self, listener):
        """
        Send all events to the listener 
        like if it was connected from the begining.
        """
        interfaces = []
        for interface, listeners in self._listeners.items():
            if not interface.providedBy(listener):
                continue            
            assert listener in listeners
            interfaces.append(interface)
        assert len(interfaces) > 0
        self._doSyncListener(listener)


    ## Virtual Methods ##
    
    def _doSyncListener(self, listener):
        """
        Called when a listener want to receive all the events
        like if it was connected from start.
        """
        pass

    
    ## Protected Methods ##
    
    def _fireEventTo(self, payload, listener, event, interface=None):
        """
        Send an event only to the specified listener.
        The strange order of the parameteres are to be able
        to call the method directly has a deferred callback
        that return the payload.
        """
        try:
            if not interface:
                assert len(self._listeners) == 1
                interface = self._listeners.keys()[0]
            assert interface in self._listeners
            method = "on%s" % event
            assert interface.get(method), "%s not found" % event
            assert listener in self._listeners[interface]
            args, kwargs = self._listeners[interface][listener]
            if isinstance(payload, tuple):
                getattr(listener, method)(self, *(payload + args), **kwargs)
            else:
                getattr(listener, method)(self, payload, *args, **kwargs)
        except Exception, e:
            log.notifyException(self, e,  "Error triggering event %s", event)
    
    def _fireEvent(self, payload, event, interface=None):
        """
        The strange order of the parameteres are to be able
        to call the method directly has a deferred callback
        that return the payload.
        if the payload is a tuple, it will be expanded as extra parameteres.
        """
        try:
            if not interface:
                assert len(self._listeners) == 1
                interface = self._listeners.keys()[0]
            assert interface in self._listeners
            method = "on%s" % event
            assert interface.get(method), "%s not found in %s" % (method, interface)
            for listener, (args, kwargs) in self._listeners[interface].items():
                if isinstance(payload, tuple):
                    getattr(listener, method)(self, *(payload + args), **kwargs)
                else:
                    getattr(listener, method)(self, payload, *args, **kwargs)
        except Exception, e:
            log.notifyException(self, e,  "Error triggering event %s", event)
            
    def _fireEventWithoutPayload(self, event, interface=None):
        try:
            if not interface:
                assert len(self._listeners) == 1
                interface = self._listeners.keys()[0]
            assert interface in self._listeners
            method = "on%s" % event
            assert interface.get(method), "%s not found in %s" % (method, interface)
            for listener, (args, kwargs) in self._listeners[interface].items():
                getattr(listener, method)(self, *args, **kwargs)
        except Exception, e:
            log.notifyException(self, e,  "Error triggering event %s", event)

