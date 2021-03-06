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

import math

from zope.interface import Interface

from flumotion.transcoder.admin import admintask


class MonitorBalancer(object):
    """
    Handle the distribution of monitoring tasks to a set of worker.
    """

    def __init__(self):
        self._workerTasks = {} # {workerPxy: [task]}
        self._orphanes = []
        self._total = 0

    def clearTasks(self):
        self._total = 0
        del self._orphanes[:]
        for tasks in self._workerTasks.itervalues():
            del tasks[:]

    def addWorker(self, workerPxy):
        assert not (workerPxy in self._workerTasks)
        self._workerTasks[workerPxy] = []

    def removeWorker(self, workerPxy):
        assert workerPxy in self._workerTasks
        self._orphanes.extend(self._workerTasks[workerPxy])
        del self._workerTasks[workerPxy]

    def addTask(self, task, workerPxy=None):
        assert admintask.IAdminTask.providedBy(task)
        assert (workerPxy == None) or (workerPxy in self._workerTasks)
        self._total += 1
        if workerPxy:
            self._workerTasks[workerPxy].append(task)
            task.suggestWorker(workerPxy)
        else:
            self._orphanes.append(task)

    def removeTask(self, task):
        assert admintask.IAdminTask.providedBy(task)
        if task in self._orphanes:
            self._orphanes.remove(task)
            self._total -= 1
            return
        for tasks in self._workerTasks.itervalues():
            if task in tasks:
                tasks.remove(task)
                self._total -= 1
                return

    def balance(self):
        if self._workerTasks:
            max = int(math.ceil(float(self._total) / len(self._workerTasks)))
            workerPxys = self._workerTasks.keys()
            workerPxys.sort(key=lambda w: -len(self._workerTasks[w]))
            for workerPxy in workerPxys:
                tasks = self._workerTasks[workerPxy]
                l = len(tasks)
                if l > max:
                    self._orphanes.extend(tasks[max:])
                    del tasks[max:]
                elif l < max:
                    i = -(max - l)
                    migrated = self._orphanes[i:]
                    del self._orphanes[i:]
                    tasks.extend(migrated)
                    for j in migrated:
                        j.suggestWorker(workerPxy)
        if len(self._orphanes) > 0:
            assert len(self._workerTasks) == 0
            for j in self._orphanes:
                j.suggestWorker(None)

