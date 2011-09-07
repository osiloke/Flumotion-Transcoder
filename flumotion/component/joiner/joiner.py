# -*- Mode: Python -*-
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


import os
import os.path as path
import time
import commands
import pipes
from urllib import urlencode
from xml.dom import minidom
from xml.dom.minidom import Node

from twisted.internet import threads
from twisted.web import client

import gio
import gst

from flumotion.common import log, messages
from flumotion.common.common import strToBool
from flumotion.component import component
from flumotion.component.component import moods
from flumotion.component.consumers.disker.disker import Index
from flumotion.common.i18n import N_, gettexter

__all__ = ['Joiner']
__version__ = "$Rev$"

T_ = gettexter()


class JoinerMedium(component.BaseComponentMedium):

    logCategory = 'joinermedium'

    def remote_loadProjectFile(self, projectFile):
        """
        Loads the configuration file for a new project

        @param file:  A string containing the xml file of the project
        @type  file:  str
        """
        return self.comp.loadProject(projectFile)


class Joiner(component.BaseComponent):
    """
    """
    componentMediumClass = JoinerMedium
    logCategory = 'joiner'
    DEFAULT_SCAN_PERIOD = 10
    DEFAULT_MAX_WINDOW = 3 * 3600
    REMUX_TEMPLATE = "ffmpeg -y -i %s -acodec copy -vcodec copy -f %s %s"
    REMUX_FORMATS = {'avi': ('avi', 'avi'),
                     'mpegps': ('vob', 'mpeg')}

    ## Subclass method ##

    def init(self):
        self._outputDirectory = None
        self._inputDirectory = None
        self._projectsWatchDirectory = None
        self._remuxFormat = None
        self._URLCallback = None
        self._scanPeriod = None
        self._indexMaxWindow = None
        self._scanIndexAtInit = None
        self._stripGaps = None
        self._projectsGroup = None
        self._indexes = {}
        self._olderIndexEntry = None
        self._monitors = []

    def do_setup(self):
        props = self.config['properties']

        # Required properties
        self._outputDirectory =\
            path.abspath(props['output-directory'])
        self._diskerDirectory =\
            path.abspath(props['disker-directory'])
        self._projectsWatchDirectory =\
            path.abspath(props['projects-watch-directory'])
        self._checkDirectories()

        # Optional properties
        self._URLCallback = props.get('callback', None)
        self._scanIndexAtInit = props.get('index-scan', False)
        self._indexMaxWindow = props.get('index-max-window',
                                         self.DEFAULT_MAX_WINDOW)
        self._scanPeriod = props.get('scan-interval', self.DEFAULT_SCAN_PERIOD)
        self._stripGaps = props.get('strip-gaps', False)
        rmf = props.get('remux-format', None)
        self._remuxFormat = self.REMUX_FORMATS.get(rmf, None)


        self._projectsGroup = ProjectsGroup()
        self._projectsGroup.connectProjectCompleted(self._on_project_completed)

        # Scan the index folder and build the internal chace of indexes
        if self._scanIndexAtInit:
            self._scanIndexFolder()

        # Connect a monitor for the projects directory
        self.info("Monitoring %s for new projects",
                  self._projectsWatchDirectory)
        self._connectMonitor(self._projectsWatchDirectory,
                             self._on_projects_directory_changed)

        # Connect a monitor for the indexes directory
        self.info("Monitoring %s for new indexes", self._diskerDirectory)
        self._connectMonitor(self._diskerDirectory,
            self._on_disker_directory_changed)

        # This element is in the atmosphere so change the mood to happy now
        self.setMood(moods.happy)

    def do_stop(self, *args, **kwargs):
        # Disconnect all the monitors when the component is stopped
        for monitor in self._monitors:
            monitor.cancel()
        self._monitors = []

    ## Callbacks ##

    def _on_disker_directory_changed(self, filemonitor, file1, file2,
                                     event_type):
        '''
        This callback is triggered when the disker directory has been modified.
        If and index file has been removed and the index is in our internal
        indexes cache, we remove it. If a new index file has been created or
        modified, we parse it and we add it to the internal indexes cache.
        '''
        if event_type == gio.FILE_MONITOR_EVENT_DELETED:
            # A file has been deleted, check if it's one of the indexes we have
            # in the cache and remove it
            if file1 and file1.get_path() in self._indexes:
                del self._indexes[file1.get_path()]

        elif event_type == gio.FILE_MONITOR_EVENT_CHANGES_DONE_HINT:
            # A file has been created or modified. Check if it's and index
            # file, parse it and add to the internal cache
            if not file1 or\
                        not file1.get_path().endswith(Index.INDEX_EXTENSION):
                return
            index = Index()
            if index.loadIndexFile(file1.get_path()):
                self._addIndex(file1.get_path(), index)

    def _on_projects_directory_changed(self, filemonitor, file1, file2,
                                       event_type):
        '''
        This callback is triggered when the projects directory has been
        modified.
        We only care about new project files added to this directory
        '''
        if event_type != gio.FILE_MONITOR_EVENT_CREATED:
            return
        self.debug("Found new file in the projects directory: %s",
                   file1.get_path())
        self._processProjectFile(file1.get_path())

    def _on_project_completed(self, project):
        '''
        This callback is triggered when a project is complete.
        A project will have a set of cue points (pairs of start and stop time)
        for which we need to find the matching entries in the index, extract
        the chunks from the corresponding files and merge them into a new file
        with a new set of cue points relatives to this file, passed to
        the transcoder with a callback.
        '''
        filename =   project.getProgramID().replace('/', '_').encode('ascii',
                                                                     'ignore')
        outputFile = path.join(self._outputDirectory, filename)
        cuePoints = project.getCuePoints()
        if len(cuePoints) == 0:
            self.warning("This project doesn't not contain any recordable "
                    "chunk")
            return
        fileChunks, transCuePointsList = self._intersectIndex(cuePoints)
        # Create the file first and do the transcoder callback with the
        # results. This need to be done in a thread because it's an I/O
        # blocking operation.
        d = threads.deferToThread(self._createResultFile, outputFile,
                                  fileChunks)
        d.addCallback(self._doRemux, outputFile)
        d.addCallback(self._doTranscoderCallback, transCuePointsList)
        d.addErrback(self._onError)

    ## Private methods ##

    def _scanIndexFolder(self):
        '''
        Scan the index directory and rebuild the index cache
        '''
        files = sorted([path.join(self._diskerDirectory, x)\
                  for x in os.listdir(self._diskerDirectory)\
                  if x.endswith(Index.INDEX_EXTENSION)])
        for f in [x for x in files if path.isfile(x)]:
            index = Index()
            if index.loadIndexFile(f):
                self._addIndex(f, index)

    def _checkDirectories(self):
        '''
        Check if all the directories passed in the configuration exists and add
        an error message in the element if some of them doesn't exists
        '''
        for d in [self._outputDirectory, self._diskerDirectory,\
                  self._projectsWatchDirectory]:
            if d and not path.exists(d) or not path.isdir(d):
                self.error("The directory %s, doesn't exists", d)
                m = messages.Error(T_(N_(
                    "The directory '%s' doesn't exists."
                    "Check your configuration properties."), d))
                self.addMessage(m)

    def _connectMonitor(self, path, callback):
        monitor = gio.File(path).monitor_directory()
        monitor.set_rate_limit(self._scanPeriod * 1000)
        monitor.connect("changed", callback)
        self._monitors.append(monitor)

    def _addIndex(self, filePath, index):
        '''
        Adds a new index to the internal cache and removes old indexes that are
        fall aoutside the window
        '''
        first = index.getFirstTDT()
        # If it's the first index or the first entry is older than the current
        # oldest one we update the reference of the oldest entry
        if self._olderIndexEntry is None or first < self._olderIndexEntry:
            self._olderIndexEntry = first

        # Add the index to the dictionary
        self._indexes[filePath] = index
        self.info("Added index %s", filePath)

        # If the window is not full, don't do anything else
        if first - self._olderIndexEntry <= self._indexMaxWindow:
            return

        # If we filled the window, sort the indexes and start removing old
        # entries until we are in the window limits again
        sortedIndexes = sorted(self._indexes.items(), key=lambda k:
                                k[1].getFirstTDT())
        lastEntryTS = sortedIndexes[-1][1].getFirstTDT()
        for key, index in sortedIndexes:
            if index.getFirstTDT() < lastEntryTS - self._indexMaxWindow:
                self.info("Removing old index %s", key)
                del self._indexes[key]
            else:
                # We are in the limits again, update the reference
                # to the oldest entry
                self._olderIndexEntry = index.getFirstTDT()
                break

    def _processProjectFile(self, filePath):
        '''
        Read the project file and parses it
        '''
        self.info("Start processing project file %s", filePath)
        try:
            f = open(filePath, 'r')
            fileString = f.read()
            f.close()
        except IOError, e:
            self.warning("I/O Error reading project file %s: %r", filePath, e)
            return False
        return self._projectsGroup.parseProjectFile(fileString)

    def _clipCuePoints(self, sortedIndexes, start, stop, needHeaders):
        '''
        Brainfuck
        FIXME: draw me!
        '''

        def addHeaders():
            headers = index.getHeaders()
            if headers is None:
                return
            fileChunks.append({'path': path.splitext(filePath)[0],
                               'offset-start': headers['offset'],
                               'offset-stop': headers['offset'] +\
                                              headers['length']})

        def getStartStop(entries, key1, key2):
            return (entries[0][key1], entries[-1][key1] + entries[-1][key2])

        indexStart = start
        fileChunks = []
        transCuePoints = None

        for filePath, index in sortedIndexes:
            self.debug("Checking index %s with start=%s stop=%s", filePath,
                        indexStart, stop)
            if needHeaders:
                addHeaders()
            entries = index.clipTDT(indexStart, stop)
            if not entries:
                continue
            offsetStart, offsetStop = getStartStop(entries, 'offset', 'length')
            tdtStart, tdtStop = getStartStop(entries, 'tdt', 'tdt-duration')
            fileChunks.append({'path': path.splitext(filePath)[0],
                               'offset-start': offsetStart,
                               'offset-stop': offsetStop,
                               'ts-start': tdtStart,
                               'ts-stop': tdtStop})
            self.debug("Entries  %r - %r", entries[0]['tdt'],
                        entries[-1]['tdt'])
            self.debug("Added new chunk %r", fileChunks[-1])
            # Indexes can be overlapped, so we need to update the start time
            # here in order to avoid adding duplicated chunks.
            indexStart = tdtStop

        if len(fileChunks) == 0:
            self.info("Couldn't clip any of the indexes to %s - %s", start,
                      stop)
            fileChunks = None
        else:
            fileChunkStart = start - fileChunks[0]['ts-start']
            fileChunkStop = fileChunkStart + stop - start
            transCuePoints = (fileChunkStart, fileChunkStop)
        return (fileChunks, transCuePoints)

    def _intersectIndexWithGaps(self, cuePoints):
        transCuePointsList = []
         # Sort indexes using the first TDT
        sortedIndexes = sorted(self._indexes.items(),
                                key=lambda k: k[1].getFirstTDT())

        start = cuePoints[0]['start']
        stop = cuePoints[-1]['stop']
        chunks, transCuePoints = self._clipCuePoints(sortedIndexes,
                                                     start, stop,
                                                     True)
        offset = start - transCuePoints[0]

        for cuePoint in cuePoints:
            transCuePointsList.append((cuePoint["start"] - offset, cuePoint["stop"] - offset))

        return (chunks, transCuePointsList)

    def _intersectIndexStripGaps(self, cuePoints):
        fileChunks = []
        transCuePointsList = []
        needHeaders = True
        tsOffset = 0

        # Sort indexes using the first TDT
        sortedIndexes = sorted(self._indexes.items(),
                                key=lambda k: k[1].getFirstTDT())
        for cuePoint in cuePoints:
            start = cuePoint['start']
            stop = cuePoint['stop']
            chunks, transCuePoints = self._clipCuePoints(sortedIndexes,
                                                         start, stop,
                                                         needHeaders)
            needHeaders = False
            if chunks is not None:
                fileChunks.extend(chunks)
                transCuePoints = (transCuePoints[0] + tsOffset,
                                  transCuePoints[1] + tsOffset)
                transCuePointsList.append(transCuePoints)
                tsOffset += chunks[-1]['ts-stop'] - chunks[0]['ts-start']
        return (fileChunks, transCuePointsList)

    def _intersectIndex(self, cuePoints):
        if self._stripGaps:
            return self._intersectIndexStripGaps(cuePoints)
        else:
            return self._intersectIndexWithGaps(cuePoints)

    def _createResultFile(self, location, fileChunks):
        '''
        Extracts chunks from different files and merge them into
        the output file.
        '''

        try:
            outputFile = open(location, 'w')
        except Exception, e:
            raise Exception("Failed to open output file '%s' for writing: %s"
                            % (outputFile, e))

        blockSize = 1024 * 1024
        for fileChunk in fileChunks:
            remaining = fileChunk['offset-stop'] - fileChunk['offset-start']
            self.debug('Copying %s bytes from %s to %s', remaining,
                       fileChunk['path'], location)
            try:
                inputFile = open(fileChunk['path'], 'r')
                inputFile.seek(fileChunk['offset-start'])
                while remaining > blockSize:
                    outputFile.write(inputFile.read(blockSize))
                    remaining -= blockSize
                outputFile.write(inputFile.read(remaining))
            except IOError, e:
                raise Exception("Error copying file '%s': %s"
                            % (outputFile, e))

    def _doRemux(self, _, outputFile):
        if self._remuxFormat is None:
            return outputFile
        aviOutput = "%s.%s" % (outputFile, self._remuxFormat[1])
        cmd = self.REMUX_TEMPLATE % (pipes.quote(outputFile), self._remuxFormat[0],
                                     pipes.quote(aviOutput))
        self.info("remuxing: %s", cmd)
        res, out = commands.getstatusoutput(cmd)
        if res != 0:
            raise Exception("Error remuxing file: %s" % out)
        return aviOutput

    def _doTranscoderCallback(self, outputFile, transCuePointsList):
        def onError(failure):
            raise Exception("Error sending callback: %s" %
                    failure.getErrorMessage())

        if not self._URLCallback or not transCuePointsList:
            return

        l = map(lambda x: '-'.join([str(int(x[0] * gst.SECOND)), str(int(x[1] *
                gst.SECOND))]), transCuePointsList)
        cuePointsString = ';'.join(l)
        lib = urlencode({
                        'cue-points': cuePointsString,
                        'file': outputFile
                        })
        uri = '?'.join([self._URLCallback, lib])

        self.info("sending callback: %s", uri)
        d = client.getPage(uri, method='POST')
        d.addErrback(onError)
        return d

    def _onError(self, failure):
        self.warning("%s", failure.getErrorMessage())
        m = messages.Warning(T_(N_("%s"), failure.getErrorMessage()))
        self.addMessage(m)


class ProjectsGroup(log.Loggable):
    """
    Hanldles a group of projects that are pending to be finished.
    Emits a project-finished signal when a project has been finished.
    """

    ELEMENTS = ['program', 'chapter', 'chunk', 'start', 'stop',\
                'record', 'complete']

    def __init__(self):
        self._projects = {}
        self._callbacks = []

    def connectProjectCompleted(self, callback, *args):
        self._callbacks.append((callback, args))

    def parseProjectFile(self, fileString):
        try:
            doc = minidom.parseString(fileString)
        except Exception, e:
            self.warning("Error parsing XML document: %r", e)
            return

        projectID = None
        self._recordings = []
        for node in doc.getElementsByTagName('recording'):
            recordingChunk = self._parseNode(node)
            if recordingChunk is None:
                continue

            # Get the project ID of this chunk
            curProjectID = Project.makeID(recordingChunk['program'],
                                          recordingChunk['chapter'])

            # Check that all the recording chunks in the document have the same
            # project ID
            if projectID is None:
                projectID = curProjectID
            elif projectID != curProjectID:
                self.warning("'Program' and 'Chapter' doesn't match for this "
                             "recording chunk, skipping")
                continue

            # Try to get a project from the projects list or create a new one
            # if none of them matches with the 'projectID'
            project = self._projects.get(projectID, Project(projectID))
            if project not in self._projects:
                self._projects[projectID] = project
            project.addRecordingChunk(recordingChunk)
            self._processProjectComplete(project)

    def _parseNode(self, node):

        recordingChunk = {}
        try:
            for name in self.ELEMENTS:
                # Raises and IndexError if the element is missing
                element = node.getElementsByTagName(name)[0]
                # Get all the child nodes for the element,
                # theoretically only one containing the value we need
                childNodes = [x for x in element.childNodes\
                    if x.nodeType == Node.TEXT_NODE]
                if  name in ['start', 'stop']:
                    # the time must be represented in iso 8601 format,
                    # with a second-precision and in utc (,000+0000) and
                    # we transform it in a unix timestamp
                    recordingChunk[name] = time.mktime(time.strptime(
                        str(childNodes[0].nodeValue),
                        '%Y-%m-%dT%H:%M:%S,000+0000'))
                elif  name in ['record', 'complete']:
                    recordingChunk[name] = strToBool(childNodes[0].nodeValue)
                else:
                    recordingChunk[name] = childNodes[0].nodeValue
        except IndexError:
            self.warning("The mandatory element '%s' is missing.", name)
            return None
        except ValueError:
            self.warning("Could not parse element '%s'.", name)
            return None
        return recordingChunk

    def _processProjectComplete(self, project):
        if not project.isComplete():
            return

        for c, args in self._callbacks:
            try:
                c(project, *args)
            except Exception, e:
                self.warning("%r", e)
        del self._projects[project.getProgramID()]


class Project(log.Loggable):
    """
    Live recording project.
    A project is uniquely identified with the 'program' and 'chapter'
    attributes.
    """

    def __init__(self, programID):
        # A list of dictionaries containng the recordings
        self._programID = programID
        self._complete = False
        self._recordingChunks = []

    @staticmethod
    def makeID(program, chapter):
        return "%s_%s" % (program, chapter)

    def getProgramID(self):
        return self._programID

    def isComplete(self):
        return self._complete

    def getCuePoints(self):
        if not self._complete:
            return None
        cuePoints = []
        for recording in self._recordingChunks:
            if not recording['record']:
                continue
            cuePoint = {}
            cuePoint['start'] = recording['start']
            cuePoint['stop'] = recording['stop']
            cuePoints.append(cuePoint)
        return cuePoints

    def addRecordingChunk(self, recordingChunk):
        '''
        Adds a new recording chunk to the Project.
        Returns 'True' if it was added correctly.
        '''
        if self._complete:
            self.warning("The project is already complete, you can't add more "
                "recording chunks.")
            return False

        chunkID = Project.makeID(recordingChunk['program'],
                                 recordingChunk['chapter'])
        if self._programID != chunkID:
            self.warning("Trying to add a chunk with a different program ID.")
            return False

        if recordingChunk['stop'] <= recordingChunk['start']:
            self.warning("Start time is smaller then stop time. start=%s "
                "stop=%s", recordingChunk['stop'], recordingChunk['start'])
            return False

        if len(self._recordingChunks) != 0:
            if recordingChunk['start'] < self._recordingChunks[-1]['stop']:
                self.warning("This chunk overlaps the last added chunk. "
                    "start=%s < last_stop=%s", recordingChunk['start'],
                   self._recordingChunks[-1]['stop'])
                return False

        self.info("Added new recording chunk. %s", str(recordingChunk))
        self._recordingChunks.append(recordingChunk)
        self._complete = recordingChunk['complete']
        return True
