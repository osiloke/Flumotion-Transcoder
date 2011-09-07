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


from flumotion.component.component import moods

from flumotion.inhouse import log, defer, utils, ringbuffer

from flumotion.transcoder.admin import adminconsts


class Janitor(log.Loggable):

    logCategory = adminconsts.JANITOR_LOG_CATEGORY

    def __init__(self, adminCtx, compPxySet):
        self._adminCtx = adminCtx
        self._compPxySet = compPxySet
        # The compPxy with bad moods are keeped but limited
        self._badMoods = set([moods.sad, moods.lost])
        self._neutralMoods = set([moods.sleeping, moods.waking])
        self._bags = {} # {workername: ringbuffer.RingBuffer}
        self._deleted = set()

    def initialize(self):
        self._compPxySet.connectListener("component-added", self,
                                         self.__onComponentAddedToSet)
        self._compPxySet.connectListener("component-removed", self,
                                         self.__onComponentRemovedFromSet)
        self._compPxySet.refreshListener(self)
        return defer.succeed(self)


    ## ComponentSet Event Listeners ##

    def __onComponentAddedToSet(self, compPxySet, compPxy):
        compPxy.connectListener("mood-changed", self,
                                self.__onComponentMoodChanged)
        compPxy.refreshListener(self)

    def __onComponentRemovedFromSet(self, compPxySet, compPxy):
        compPxy.disconnectListener("mood-changed", self)
        bag = self.__getComponentBag(compPxy)
        if bag and (compPxy in bag):
            bag.remove(compPxy)
        if compPxy in self._deleted:
            self._deleted.remove(compPxy)


    ## Component Event Listeners ##

    def __onComponentMoodChanged(self, compPxy, mood):
        if mood == None: return
        if mood in self._neutralMoods: return
        if compPxy in self._deleted: return
        bag = self.__getComponentBag(compPxy)
        if bag == None: return
        workerName = compPxy.getRequestedWorkerName()
        if compPxy in bag:
            if not (mood in self._badMoods):
                bag.remove(compPxy)
                self.log("Component '%s' not in a bad mood anymore (%s); "
                         "take out of the bag (worker '%s' bag contains %d components)",
                         compPxy.label, mood.name, workerName, len(bag))
        else:
            if mood in self._badMoods:
                old = bag.push(compPxy)
                self.log("Component '%s' goes in a bad mood (%s); "
                         "keeping it (worker '%s' bag contains %d components)",
                         compPxy.label, mood.name, workerName, len(bag))
                if old:
                    self.debug("Worker '%s' disposal bag is full; dumping "
                               "component '%s'", workerName, old.label)
                    self._deleted.add(old)
                    # Let the opportunity to components managers to cleanup,
                    # but fix a maximum time after which the deletion will be forced
                    utils.createTimeout(adminconsts.JANITOR_WAIT_FOR_DELETE,
                                        self.__forceComponentDeletion, old)
                    d = old.forceStop()
                    # Catch all failures
                    d.addErrback(defer.resolveFailure)


    ## Private Methods ##

    def __getComponentBag(self, compPxy):
        workerName = compPxy.getRequestedWorkerName()
        if not workerName: return None
        if workerName in self._bags:
            return self._bags[workerName]
        workerCtx = self._adminCtx.getWorkerContextByName(workerName)
        capacity = workerCtx.getMaxKeepFailed()
        self.debug("Create disposal bag of %d components for worker '%s'",
                   capacity, workerName)
        bag = ringbuffer.RingBuffer(capacity)
        self._bags[workerName] = bag
        return bag

    def __forceComponentDeletion(self, compPxy):
        if compPxy not in self._deleted:
            # Already deleted by the components managers.
            return
        self.warning("Component '%s' still not deleted, force deletion",
                     compPxy.label)
        d = compPxy.forceDelete()
        # Catch all failures
        d.addErrback(defer.resolveFailure)
