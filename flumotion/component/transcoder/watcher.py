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

import gobject
import os
import stat
from datetime import datetime

from twisted.internet import threads, defer, reactor
from twisted.internet.interfaces import IReactorTime

from flumotion.inhouse import log

FILE_PROCESSING_BLOCK = 20


class Watcher(gobject.GObject, log.LoggerProxy):
    """
    Watches for changes in a directory

    Signals:
    _ file-completed : The given filename is new and hasn't
                        changed size between
    _file-added : A new file has appeared
    _ file-removed : A file has been deleted
    _ file-not-present : The given filename does not exist
                            iterations
    """
    __gsignals__ = {
        "file-completed" : (gobject.SIGNAL_RUN_LAST,
                            gobject.TYPE_NONE,
                            (gobject.TYPE_STRING,
                             gobject.TYPE_PYOBJECT)),
        "file-added" : (gobject.SIGNAL_RUN_LAST,
                        gobject.TYPE_NONE,
                        (gobject.TYPE_STRING,
                         gobject.TYPE_PYOBJECT,
                         gobject.TYPE_PYOBJECT)),
        "file-removed" : (gobject.SIGNAL_RUN_LAST,
                          gobject.TYPE_NONE,
                          (gobject.TYPE_STRING, )),
        "file-not-present" : (gobject.SIGNAL_RUN_LAST,
                              gobject.TYPE_NONE,
                              (gobject.TYPE_STRING, ))
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


class PeriodicalWatcher(Watcher):
    """
    Periodically scan for changes.
    """
    def __init__(self, logger, timeout=30, *args, **kwargs):
        Watcher.__init__(self, logger, *args, **kwargs)
        self.timeout = timeout
        self._sigid = None
        self._files = {}

    def start(self, reset=False):
        self._stopChecking()
        if reset:
            self._files = {}
        self._scheduleCheck()

    def stop(self):
        self._stopChecking()

    def _stopChecking(self):
        if self._sigid:
            self._sigid.cancel()
            self._sigid = None

    def _scheduleCheck(self):
        if self._sigid is None:
            self._sigid = IReactorTime(reactor).callLater(self.timeout, self._checkForChanges)

    def _checkForChanges(self):
        self.log("Watching...")
        self._sigid = None
        d = self._listFiles()
        if isinstance(d, defer.Deferred):
            d.addCallbacks(self.__cbGotFiles, self.__ebListFileFailed)
            return d
        return self.__cbGotFiles(d)

    def __ebListFileFailed(self, failure):
        log.notifyFailure(self, failure, "Failure during file listing")
        # Continue anyway
        self._scheduleCheck()

    def __fileProcessingGenerator(self, currFiles, newFiles):
        for f in currFiles.keys():
            if f in newFiles:
                continue
            yield None
            self.log("File '%s' removed", f)
            self.emit('file-removed', f)
            del currFiles[f]
        for f, s in newFiles.iteritems():
            yield None
            oldfilesize = None
            if f in currFiles and currFiles[f]:
                oldfilesize = currFiles[f][stat.ST_SIZE]
            self.log("File '%s' size change from %s to %s",
                     f, str(oldfilesize), str(s[stat.ST_SIZE]))
            #new file
            if not (f in currFiles):
                self.log("File '%s' added", f)
                now = datetime.utcnow()
                self.emit('file-added', f, s, now)
                currFiles[f] = s
                continue
            #Checked file
            if currFiles[f] == None:
                continue
            #Completed file
            if s[stat.ST_SIZE] == currFiles[f][stat.ST_SIZE]:
                self.log("File '%s' completed", f)
                self.emit('file-completed', f, s)
                currFiles[f] = None
                continue
            currFiles[f] = s

    def __cbGotFiles(self, newfiles):
        self.log("Comparing new files (%d) to old files (%d)",
                 len(newfiles), len(self._files))
        processor = self.__fileProcessingGenerator(self._files, newfiles)
        self.__processFiles(processor)

    def __processFiles(self, processor):
        try:
            for i in range(FILE_PROCESSING_BLOCK):
                processor.next()
            IReactorTime(reactor).callLater(0.01, self.__processFiles, processor)
        except StopIteration, e:
            self._sigid = None
            self._scheduleCheck()

    def _listFiles(self):
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
    def __init__(self, logger, path, *args, **kwargs):
        PeriodicalWatcher.__init__(self, logger, *args, **kwargs)
        self.path = path

    def _listFiles(self):
        result = {}
        d = threads.deferToThread(os.path.walk, self.path, self._step, result)
        d.addCallback(lambda x: result)
        return d

    def _step(self, results, dirname, content):
        abs_content = [os.path.join(dirname, f)
                       for f in content]
        file_stat = [f for f in abs_content if os.path.isfile(f)]
        for file in file_stat:
            try:
                stat = tuple(os.stat(file))
            except OSError:
                continue
            results[file[len(self.path):]] = stat


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

    def _listFiles(self):
        results = {}
        for filename in self.files:
            if not os.path.exists(filename):
                self.emit('file-not-present', filename)
                continue
            results[filename] = tuple(os.stat(filename))
        return results
