# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import os
import stat
from datetime import datetime
import gobject

from twisted.internet import reactor
from twisted.internet.defer import maybeDeferred
from twisted.internet.interfaces import IReactorTime
from twisted.internet.task import LoopingCall, Cooperator
from twisted.internet.threads import deferToThread

from flumotion.inhouse import log


class Watcher(gobject.GObject, log.LoggerProxy):
    """
    Watches for changes in a directory

    Signals:
    _ file-completed : The given filename is new and hasn't
                        changed size between
    _ file-added : A new file has appeared
    _ file-removed : A file has been deleted
    _ file-not-present : The given filename does not exist
                            iterations
    """
    __gsignals__ = {
        "file-completed" : (
            gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            (gobject.TYPE_STRING, gobject.TYPE_PYOBJECT)),
        "file-added" : (
            gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            (gobject.TYPE_STRING, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        "file-removed" : (
            gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            (gobject.TYPE_STRING,)),
        "file-not-present" : (
            gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            (gobject.TYPE_STRING,))
        }

    def __init__(self, logger):
        gobject.GObject.__init__(self)
        log.LoggerProxy.__init__(self, logger)

    def start(self):
        """
        Start the watcher.
        """

    def stop(self):
        """
        Stop the watcher.
        """

def scheduler(x):
    """ Schedule the iterations for the cooperator """
    return IReactorTime(reactor).callLater(0.02, x)


class PeriodicalWatcher(Watcher):
    """
    Periodically scan for changes.
    """
    def __init__(self, logger, timeout=5, *args, **kwargs):
        Watcher.__init__(self, logger, *args, **kwargs)
        self.timeout = timeout
        self._sigid = None
        self._files = {}
        self.looping_check = LoopingCall(self.check_for_changes)

    def start(self, reset=False):
        if not self.looping_check.running:
            self.looping_check.start(self.timeout, True)
        if reset:
            self._files = {}

    def stop(self):
        if self.looping_check.running:
            self.looping_check.stop()

    def check_for_changes(self):
        self.log("Watching...")
        d = maybeDeferred(self.list_files)
        d.addCallbacks(
            self.list_files_ok,
            self.list_files_failed
        )
        return d

    def list_files_failed(self, failure):
        log.notifyFailure(self, failure, "Failure during file listing")

    def list_files_ok(self, newfiles):
        self.log("Comparing new files (%d) to old files (%d)",
                 len(newfiles), len(self._files))
        processor = self.process_files(self._files, newfiles)
        # process the file comparison one at a time
        cooperator = Cooperator(scheduler=scheduler)
        cooperator.cooperate(processor)


    def process_files(self, old, new):
        yield None
        added = set(new).difference(old)
        removed = set(old).difference(new)
        changed = set(new).intersection(old)
        for f in removed:
            self.log("File '%s' removed", f)
            self.emit('file-removed', f)
            del old[f]
            yield None
        for f in added:
            self.log("File '%s' added", f)
            self.emit('file-added', f, new[f], datetime.utcnow())
            old[f] = new[f]
            yield None
        for f in changed:
            if old[f] == None:
                pass
            elif old[f][stat.ST_SIZE] != new[f][stat.ST_SIZE]:
                self.log("File '%s' size change from %s to %s", f,
                    str(old[f][stat.ST_SIZE]),
                    str(new[f][stat.ST_SIZE]))
                old[f] = new[f]
            else:
                self.log("File '%s' completed", f)
                self.emit('file-completed', f, new[f])
                old[f] = None
            yield None

    def list_files(self):
        """
        Returns a dict of filename->(stat tuple) mapping.
        """
        raise NotImplementedError


class DirectoryWatcher(PeriodicalWatcher):
    """
    Directory Watcher
    Watches a directory for new files.
    path : path to check for new/removed files
    """
    def __init__(self, logger, path, profile_name, *args, **kwargs):
        PeriodicalWatcher.__init__(self, logger, *args, **kwargs)
        self.path = path

    def list_files(self):
        return deferToThread(self.defer_tree_walk, self.path)

    def defer_tree_walk(self, start):
        file_list = {}
        for root, dirs, files in os.walk(start):
            for file in files:
                abspath = os.path.join(root, file)
                relpath = abspath[len(start):]
                try:
                    file_list[relpath] = tuple(os.stat(abspath))
                except OSError:
                    continue
        return file_list


class FilesWatcher(PeriodicalWatcher):
    """
    Watches a collection of files for modifications.
    """
    def __init__(self, logger, files, *args, **kwargs):
        """
        files : list of absolute filenames
        """
        PeriodicalWatcher.__init__(self, logger, *args, **kwargs)
        self.files = files

    def list_files(self):
        results = {}
        for filename in self.files:
            if not os.path.exists(filename):
                self.emit('file-not-present', filename)
                continue
            results[filename] = tuple(os.stat(filename))
        return results
