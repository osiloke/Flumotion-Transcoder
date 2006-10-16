# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.
# Flumotion Transcoder

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

import gobject
import os

from flumotion.common import log

class Watcher(gobject.GObject, log.Loggable):
    """
    Watches for changes in a directory

    Signals:
    _ complete-file : The given filename is new and hasn't changed size between
        iterations
    """
    __gsignals__ = {
        "complete-file" : (gobject.SIGNAL_RUN_LAST,
                          gobject.TYPE_NONE,
                          (gobject.TYPE_STRING, ))
        }

    def __init__(self, timeout=30):
        """
        path : path to check for new/removed files
        timeout : timeout between checks, in seconds
        ignorefiles : List of files to consider as already processed
        specificfiles : List of the only files to be watched
        """
        gobject.GObject.__init__(self)
        self.timeout = timeout
        self._sigid = None
        self._files = {}

    def start(self, checknow=False):
        """
        Start the watcher. If checknow is True, the watcher will scan the
        directory once immediatly.
        """
        if self._sigid:
            gobject.source_remove(self._sigid)
        if checknow:
            self._files = self._scanDir()
        else:
            self._files = {}
        self._sigid = gobject.timeout_add(self.timeout * 1000, self._timeoutCb)

    def stop(self):
        """
        Stop the watcher, and flush the internal list of files.
        """
        if self._sigid:
            gobject.source_remove(self._sigid)
            self._sigid = None
        # reset the watched files
        self._files = {}

    def _timeoutCb(self):
        self.log("watching...")
        newfiles = self._getData()
        oldfiles = self._files.keys()
        for newf in newfiles.keys():
            newsize = newfiles[newf]
            if (newf in oldfiles) and newsize == self._files[newf]:
                self.emit('complete-file', newf)
                self._checked.append(newf)
                del newfiles[newf]
        self._files = newfiles
        return True

    def _getData(self):
        """
        Return a dictionnary of filename -> file size
        """
        raise NotImplementedError

class DirectoryWatcher(Watcher):
    """
    Directory Watcher
    Watches a directory for new files.
    """
    
    def __init__(self, path, ignorefiles=[], *args, **kwargs):
        Watcher.__init__(self, *args, **kwargs)
        self.path = path
        self._checked = ignorefiles

    def _getData(self):
        # Scan the directory for non-complete files
        # returns a dict of filename->size mapping
        newfiles = [x for x in os.listdir(self.path) if not x in self._checked]
        newsize = [os.path.getsize(os.path.join(self.path, x)) for x in newfiles]
        return dict(zip(newfiles, newsize))
        

class FilesWatcher(Watcher):
    """
    Watches a collection of files for modifications.

    Signals:
    _ file-not-present : The given filename does not exist
    """

    
    __gsignals__ = {
        "file-not-present" : (gobject.SIGNAL_RUN_LAST,
                              gobject.TYPE_NONE,
                              (gobject.TYPE_STRING, ))
        }

    def __init__(self, files, *args, **kwargs):
        """
        files : list of absolute filenames
        """
        Watcher.__init__(self, *args, **kwargs)
        self.files = files

    def _getData(self):
        # Get the file sizes. If a file doesn't exist, raise an error
        res = {}
        for filename in self.files:
            if not os.path.exists(filename):
                self.emit('file-not-present', filename)
                break
            res[filename] = os.path.getsize(filename)
        return res
