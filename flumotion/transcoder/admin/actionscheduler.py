# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import time

from twisted.internet import reactor

from flumotion.common import enum


class Action(object):
    
    def __init__(self, identifier, 
                 callback, *args, **kwargs):
        self._scheduler = None
        self._delayed = None
        self._identifier = identifier
        self._callback = callback
        self._args = args
        self._kwargs = kwargs
        
    def cancel(self):
        if self._scheduler:
            self._scheduler.cancelActions(self)
            
    def _setup(self, scheduler, delayed):
        self._scheduler = scheduler
        self._delayed = delayed
            
    def _perform(self):
        self._callback(*self._args, **self._kwargs)
        
    def _cancel(self):
        if self._delayed:
            self._delayed.cancel()
        self._scheduler = None
        self._delayed = None
        

class ActionScheduler(object):
    """
    The action scheduler managed delayed actions.
    Each actions are identified by a callback and an identifier.
    The scheduler ensure there is only one pending (identifier,callback)
    action. If more than one action are added with the same
    (identifier,callback) only the earliest one is keeped.
    """
    
    def __init__(self):
        self._actions = {} # {identifier: {callback: Action}}
        
    def cancelActions(self, *actions):
        for action in actions:
            assert isinstance(action, Action)
            assert action._scheduler == self, "Action not scheduled by me"
            action._cancel()
            self.__removeActions(action)
            return action
    
    def getActions(self, identifier, callback=None):
        """
        Retrieve the actions with specified identifier and callback.
        """
        tmp = self._actions.get(identifier, None)
        if tmp:
            if callback:
                if callback in tmp:
                    return [tmp[callback]]
            else:
                return [a for a in tmp.itervalues()]
        return []
    
    def cancelByIdentifier(self, identifier, callback=None):
        actions = self.getActions(identifier, callback)
        self.cancelActions(*actions)
        
    def addAction(self, delay, action):
        """
        Add an action to be sheduled if another action with 
        identical identifier and callback and smaller delay.
        """
        assert isinstance(action, Action)
        assert action._scheduler == None, "Action already scheduled"
        old = self.__getAction(action._identifier, action._callback)
        if old:
            if old._delayed.getTime() < (time.time() + delay):
                return old
            else:
                self.cancelActions(old)
        delayed = reactor.callLater(delay, self.__performAction, action)
        action._setup(self, delayed)
        return action
    
    def __getAction(self, identifier, callback):
        tmp = self._actions.get(identifier, None)
        if tmp:
            return tmp.get(callback, None)
        return None
    
    def __addAction(self, action):
        i = action._identifier
        self._actions.setdefault(i, {})[action._callback] = action
    
    def __removeActions(self, *actions):
        for action in actions:
            if action._identifier in self._actions:
                tmp = self._actions[action._identifier]
                if action._callback in tmp:
                    del self._actions[action._identifier][action._callback]
                    if not self._actions[action._identifier]:
                        del self._actions[action._identifier]
    
    def __performAction(self, action):
        self.__removeActions(action)
        action._perform()
            
    
