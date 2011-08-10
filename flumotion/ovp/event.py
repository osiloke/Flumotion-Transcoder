'''
Created on Jun 7, 2011

@author: strioni
'''

from collections import Callable, defaultdict
from weakref import ref

class WeakCallback(object):
    """A Weak Callback object that will keep a reference to
    the connecting object with weakref semantics.

    This allows object A to pass a callback method to object S,
    without object S keeping A alive.
    
    Usage:
    
    weak_call = WeakCallback(self._something_changed)
    long_lived_object.connect("on_change", weak_call)

    See http://stackoverflow.com/questions/1673483/how-to-store-callback-methods
    """
    def __init__(self, mcallback):
        """Create a new Weak Callback calling the method @mcallback"""
        self.observer = ref(mcallback.im_self, self.object_deleted)
        self.method_name = mcallback.im_func.__name__

    def __call__(self, *args, **kwargs):
        observer = self.observer()
        if observer:
            callback = getattr(observer, self.method_name)
            callback(*args, **kwargs)
        else:
            self.default_callback(*args, **kwargs)

    def default_callback(self, *args, **kwargs):
        """Called instead of callback when expired"""
        pass

    def object_deleted(self, wref):
        """Called when callback expires"""
        pass
    


class EventSource(object):
    """ A mixin for the subject part of the observer pattern.
    
    The subclass might declare an __events__ iterable with
    the name of the expected events.
    Any subscriber can register itself using
    Subject.connect and remove from registration
    using Subject.disconnect.
    
    Whenever an event is fired, all the subscribers are
    notified, using the same arguments as in the event
    firing
    
    """
    
    def __init__(self, *args, **kwargs):
        self.__observers = defaultdict(set)
        for ev in getattr(self, '__events__', []):
            self.__register_event_type(ev)

    def __register_event_type(self, ev):
        pass
        
    def emit(self, ev, *args, **kwargs):
        assert ev in self.__events__
        for obs in self.__observers[ev]:
            obs(*args, **kwargs)
    
    def connect(self, ev, observer):
        assert ev in self.__events__
        assert isinstance(observer, Callable)
        self.__observers[ev].add(observer)

    def disconnect(self, ev, observer):
        assert ev in self.__events__
        try:
            self.__observers[ev].remove(observer)
        except KeyError:
            pass

