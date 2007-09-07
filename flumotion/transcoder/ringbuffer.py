# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

class RingBuffer(object):
    """
    Currently, all elements must be different objects,
    because a dictionary is used to index them.
    None cannot be used as a value, it will be ignored.
    An element can be removed, but it will not realy free
    space for more push. In other word if the buffer is full,
    even if some elements are removed the next push will return
    the next pop if it wasn't one of the removed elements.
    """
    
    def __init__(self, capacity):
        self._list = [None] * capacity
        self._index = {} # {obj: index}
        self._pushIndex = 0
        self._popIndex = 0
        self._count = 0
        
    def push(self, obj):
        if obj == None: return None
        index = self._pushIndex
        max = len(self._list)
        old = self._list[index]
        if self._popIndex == index:
            self._popIndex = (index + 1) % max
        if old != None:
            del self._index[old]
        else:
            self._count += 1
        self._list[index] = obj
        self._index[obj] = index
        self._pushIndex = (index + 1) % max
        return old
    
    def pop(self):
        result = None
        index = self._popIndex
        stop = self._pushIndex
        max = len(self._list)
        # Handle holes
        while True:
            result = self._list[index]
            self._list[index] = None
            index = (index + 1) % max
            if result or (index == stop): break
        self._popIndex = index
        if result:
            self._count -= 1
            del self._index[result]
        return result
    
    def remove(self, obj):
        index = self._index[obj]
        self._count -= 1
        self._list[index] = None
        del self._index[obj]
        return obj

    def __contains__(self, obj):
        return obj in self._index
    
    def __len__(self):
        return self._count
    
    def values(self):
        result = []
        index = self._popIndex
        stop = self._pushIndex
        max = len(self._list)
        while True:
            val = self._list[index]
            index = (index + 1) % max
            if val: result.append(val)
            if index == stop: break
        return result
