# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.


from flumotion.component.component import moods

from flumotion.inhouse import log, defer, utils
from flumotion.inhouse.ringbuffer import RingBuffer

from flumotion.transcoder.admin import adminconsts


class Janitor(log.Loggable):
    
    logCategory = adminconsts.JANITOR_LOG_CATEGORY
    
    def __init__(self, adminCtx, components):
        self._adminCtx = adminCtx
        self._components = components
        # The component with bad moods are keeped but limited
        self._badMoods = set([moods.sad, moods.lost])
        self._neutralMoods = set([moods.sleeping, moods.waking])
        self._bags = {} # {workername: RingBuffer}
        self._deleted = set()
        
    def initialize(self):
        self._components.connect("component-added",
                                 self, self.onComponentAddedToSet)
        self._components.connect("component-removed",
                                 self, self.onComponentRemovedFromSet)
        self._components.update(self)
        return defer.succeed(self)


    ## ComponentSet Event Listeners ##

    def onComponentAddedToSet(self, componentset, component):
        component.connect("mood-changed", self, self.onComponentMoodChanged)    
        component.update(self)
    
    def onComponentRemovedFromSet(self, componentset, component):
        bag = self.__getComponentBag(component)
        if bag and (component in bag):
            bag.remove(component)
        if component in self._deleted:
            self._deleted.remove(component)
        component.disconnect("mood-changed", self)


    ## Component Event Listeners ##

    def onComponentMoodChanged(self, component, mood):
        if mood == None: return
        if mood in self._neutralMoods: return
        if component in self._deleted: return
        bag = self.__getComponentBag(component)
        if bag == None: return
        workerName = component.getRequestedWorkerName()
        if component in bag:
            if not (mood in self._badMoods):
                bag.remove(component)
                self.log("Component '%s' not in a bad mood anymore (%s); "
                         "take out of the bag (worker '%s' bag contains %d components)",
                         component.getLabel(), mood.name, workerName, len(bag))
        else:
            if mood in self._badMoods:
                old = bag.push(component)
                self.log("Component '%s' goes in a bad mood (%s); "
                         "keeping it (worker '%s' bag contains %d components)",
                         component.getLabel(), mood.name, workerName, len(bag))
                if old:
                    self.debug("Worker '%s' disposal bag is full; dumping "
                               "component '%s'", workerName, component.getLabel())
                    self._deleted.add(old)
                    d = old.forceDelete()
                    # Catch all failures
                    d.addErrback(defer.resolveFailure)
    

    ## Private Methods ##
    
    def __getComponentBag(self, component):
        workerName = component.getRequestedWorkerName()
        if not workerName: return None
        if workerName in self._bags:
            return self._bags[workerName]
        workerCtx = self._adminCtx.getWorkerContext(workerName)
        capacity = workerCtx.getMaxKeepFailed()
        self.debug("Create disposal bag of %d components for worker '%s'",
                   capacity, workerName)
        bag = RingBuffer(capacity)
        self._bags[workerName] = bag
        return bag
