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

from flumotion.common.log import Loggable

class Watcher(gobject.GObject, Loggable):
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
        "file-completed" : (gobject.SIGNAL_RUN_LAST,
                            gobject.TYPE_NONE,
                            (gobject.TYPE_STRING, )),
        "file-added" : (gobject.SIGNAL_RUN_LAST,
                        gobject.TYPE_NONE,
                        (gobject.TYPE_STRING, )),
        "file-removed" : (gobject.SIGNAL_RUN_LAST,
                          gobject.TYPE_NONE,
                          (gobject.TYPE_STRING, )),
        "file-not-present" : (gobject.SIGNAL_RUN_LAST,
                              gobject.TYPE_NONE,
                              (gobject.TYPE_STRING, ))
        }

    def __init__(self):
        gobject.GObject.__init__(self)

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
    def __init__(self, timeout=30, *args, **kwargs):
        Watcher.__init__(self, *args, **kwargs)
        self.timeout = timeout
        self._sigid = None
        self._files = {}
        

    def start(self, reset=False):
        if self._sigid:
            gobject.source_remove(self._sigid)
        if reset:
            self._files = {}
        self._sigid = gobject.timeout_add(self.timeout * 1000, self._checkForChanges)

    def stop(self):
        if self._sigid:
            gobject.source_remove(self._sigid)
            self._sigid = None
        
    def _checkForChanges(self):
        self.log("watching...")
        newfiles = self._listFiles()
        oldfiles = self._files
        self.log("Comparing new files (%d) to old files (%d)",
                 len(newfiles), len(oldfiles))
        for f in [x for x in oldfiles.iterkeys() if not x in newfiles]:
            self.emit('file-removed', f)
            del oldfiles[f]
        for f, s in newfiles.iteritems():
            #new file
            if not f in oldfiles:
                self.emit('file-added', f)
                self._files[f] = s
                continue
            #Checked file
            if oldfiles[f] == None:
                continue
            #Completed file
            if s == oldfiles[f]:
                self.emit('file-completed', f)
                oldfiles[f] = None
        return True

    def _listFiles(self):
        """
        Returns a dict of filename->size mapping.
        """
        raise NotImplementedError        


class DirectoryWatcher(PeriodicalWatcher):
    """
    Directory Watcher
    Watches a directory for new files.
    path : path to check for new/removed files        
    """
    def __init__(self, path, *args, **kwargs):
        PeriodicalWatcher.__init__(self, *args, **kwargs)
        self.path = path

    def _listFiles(self):
        def step(results, dirname, content):
            abs_content = [os.path.join(dirname, f) 
                           for f in content]
            file_size = [f for f in abs_content if os.path.isfile(f)]
            for file in file_size:
                try:
                    size = os.path.getsize(file)
                except OSError:
                    continue
                results[file[len(base):]] = size 
        result = {}
        base = self.path
        os.path.walk(base, step, result)
        return result
        
class FilesWatcher(PeriodicalWatcher):
    """
    Watches a collection of files for modifications.
    """
    def __init__(self, files, *args, **kwargs):
        """
        files : list of absolute filenames
        """
        PeriodicalWatcher.__init__(self, *args, **kwargs)
        self.files = files

    def _listFiles(self):
        results = {}
        for filename in self.files:
            if not os.path.exists(filename):
                self.emit('file-not-present', filename)
                continue
            results[filename] = os.path.getsize(filename)
        return results
