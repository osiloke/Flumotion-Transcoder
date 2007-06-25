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
import gtk
import gobject

from flumotion.common import errors, common

from flumotion.component.base.admin_gtk import BaseAdminGtk, BaseAdminGtkNode
from flumotion.transcoder import enums
from flumotion.transcoder.enums import JobStateEnum
from flumotion.transcoder.enums import TargetStateEnum

_ = common.gettexter('flumotion-transcoder')

DEFAULT_VALUE = "<i>Unknown</i>"
#DEFAULT_VALUE = "Unknown"

_fmt = "<span weight='bold' foreground='%s'>%s</span>"
def _error(text):
    return _fmt % ("red", text)

def _warning(text):
    return _fmt % ("brown", text)

def _normal(text):
    return _fmt % ("blue", text)
    

class FileTranscoderAdminGtkNode(BaseAdminGtkNode):

    glade_file = os.path.join('flumotion', 'component', 
                              'transcoder', 'filetranscoder.glade')
    
    gettext_domain = "flumotion-transcoder"

    def __init__(self, *args, **kwargs):
        BaseAdminGtkNode.__init__(self, *args, **kwargs)
        self._progress = None
        self._model = gtk.TreeStore(str, str, str, int)
        self._view = None
        self._errorText = None
        self._uiInitialized = False
        self._fields = {}
        self._valFormats = {}
        self._lblFormats = {}
        self._labels = {}
        self._iterIndex = {}
        self._targetsWarnings = {}
        self._targetsError = {}
        self._jobWarnings = []
        self._jobError = None
        self._status = None

    def error_dialog(self, message):
        # FIXME: dialogize
        print 'ERROR:', message
        
    def addField(self, type, key, comp):
        self._fields[(type, key)] = comp
        
    def getField(self, type, key):
        return self._fields.get((type, key), None)
        
    def addValFormat(self, key, format, default=DEFAULT_VALUE):
        self._valFormats[key] = (format, default)
        
    def addLblFormat(self, key, format, default=DEFAULT_VALUE):
        self._lblFormats[key] = (format, default)
        
    def _format(self, value, format, default):
        if value == None:
            return default
        elif isinstance(format, str):
            return format % value
        elif callable(format):
            return format(value)
        else:
            return str(value)
        
    def formatValue(self, key, value):
        format, default = self._valFormats.get(key, (None, DEFAULT_VALUE))
        return self._format(value, format, default)
        
    def addLabel(self, key, priority, label):
        self._labels[key] = (priority, _(label))
        
    def formatLabel(self, key):
        priority, label = self._labels.get(key, (0, key))
        format, default = self._lblFormats.get(key, (None, DEFAULT_VALUE))
        return (key, priority, self._format(_(label), format, default))
    
    def keepLabel(self, key, priority=0):
        return (key, priority, key)
        
    def haveWidgetTree(self):
        self.widget = self.getWidget('transcoding-widget')      
        self._progress = self.getWidget("progress-bar")
        self._errorText = self.getWidget("error-text")
        self.setView(self.getWidget("info-tree"))
        
        self._errorText.hide()
        
        self.addField("job-data", "customer-name", 
                      self.getWidget("customer-name"))
        self.addField("job-data", "profile-label", 
                      self.getWidget("profile-label"))
        self.addField("job-data", "job-state", 
                      self.getWidget("transcoding-status"))
        self.addField("source-data", "input-file", 
                      self.getWidget("source-input-file"))
        self.addField("job-data", "transcoding-report", 
                      self.getWidget("transcoding-report"))
        
        self.addLblFormat("source", "<big>%s</big>")
        self.addLblFormat("targets", "<big>%s</big>")
        self.addLblFormat("job-error", _error)
        self.addLblFormat("job-warning", _warning)
        self.addLblFormat("target-error", _error)
        self.addLblFormat("target-warning", _warning)
        
        
        self.addValFormat("job-error", _error)
        self.addValFormat("job-warning", _warning)
        self.addValFormat("target-error", _error)
        self.addValFormat("target-warning", _warning)
        self.addValFormat("customer-name", "<big>%s</big>")
        self.addValFormat("duration", "%.2f s")
        self.addValFormat("video-size", lambda v: "%dx%d" % v)
        self.addValFormat("video-rate", lambda v: "%d/%d" % v)
        self.addValFormat("audio-rate", "%d Hz")
        self.addValFormat("job-state", self.formatJobState)
        self.addValFormat("target-state", lambda v: v.nick)
        self.addValFormat("file-size", 
                          lambda v: "%.2f MB" % (int(v) / 1024.0**2))
        self.addValFormat("file-count", "%d") 
        self.addValFormat("type", lambda v: {'audio': "Audio",
                                             'video': "Video",
                                             'audiovideo': "Audio/Video",
                                             'thumbnails': "Thumbnails"
                                             }.get(v, v))
        
        self.addLabel("source", 100, "Source")
        self.addLabel("targets", 90, "Targets")
        self.addLabel("job-error", 2000, "Error:")
        self.addLabel("job-warning", 1000, "Warning:")
        self.addLabel("target-error", 2000, "Error:")
        self.addLabel("target-warning", 1000, "Warning:")
        self.addLabel("type", 100, "Type:")
        self.addLabel("output-file", 90, "Output File:")
        self.addLabel("file-size", 85, "File Size:")
        self.addLabel("file-count", 85, "File Count:")
        self.addLabel("duration", 80, "Duration:")
        self.addLabel("video-size", 70, "Video Size:")
        self.addLabel("video-rate", 60, "Video Rate:")
        self.addLabel("video-encoder", 50, "Video Encoder:")
        self.addLabel("audio-rate", 40, "Audio Rate:")
        self.addLabel("audio-encoder", 30, "Audio Encoder:")
        self.addLabel("mime-type", 20, "Mime Type:")
        
        
        if not self._uiInitialized:
            self.refreshUIState()

    def setUIState(self, state):
        BaseAdminGtkNode.setUIState(self, state)
        self.refreshUIState()
        self._uiInitialized = True

    def setView(self, view):
        self._view = view
        renderer = gtk.CellRendererText()
        nameCol = gtk.TreeViewColumn()
        nameCol.pack_start(renderer, True)
        nameCol.add_attribute(renderer, "markup", 0)
        valueCol = gtk.TreeViewColumn()
        valueCol.pack_start(renderer, True)
        valueCol.add_attribute(renderer, "markup", 1)
        view.append_column(nameCol)
        view.append_column(valueCol)
        self._view.set_model(self._model)

    def refreshUIState(self):
        if not self.uiState:
            return
        for name, field in self._fields.iteritems():
            field.set_markup(self.formatValue(name, None))
        for key, value in self.uiState.get("job-data").iteritems():
            self.stateSetitem(self.state, "job-data", key, value)
        for key, value in self.uiState.get("source-data").iteritems():
            self.stateSetitem(self.state, "source-data", key, value)
        for key, value in self.uiState.get("targets-data").iteritems():
            self.stateSetitem(self.state, "targets-data", key, value)

    def updateJobErrors(self):
        lines = []
        if self._jobError != None:
            text = self.formatValue("job-error", self._jobError)
            label = self.formatLabel("job-error")
            lines.append(label[-1] + " " + text)
        for w in self._jobWarnings:
            text = self.formatValue("job-warning", w)
            label = self.formatLabel("job-warning")
            lines.append(label[-1] + " " + text)
        self._errorText.set_markup("\n".join(lines))
        self._errorText.show()

    def updateStates(self):
        for key, value in self.uiState.get("job-data").iteritems():
            if key == "job-state":
                self.stateSetitem(self.state, "job-data", key, value)
        for key, value in self.uiState.get("targets-data").iteritems():
            if key[1] == "target-state":
                self.stateSetitem(self.state, "targets-data", key, value)
        

    def setTreeValue(self, value, *path):
        """
        path is a list of list containing a key, a priority and a label.
        Like: [["source", 20, "Source"], ["video-size", 10, "Video Size:"]]
        """
        iterKey = tuple([p[0] for p in path])
        iter = self._iterIndex.get(iterKey, None)
        if iter == None:
            for part in path:
                parent = iter
                key, priority, text = part
                child = self._model.iter_children(parent)
                #search for existing node
                while child != None:
                    childKey = self._model.get(child, 2)[0]
                    if childKey == key:
                        iter = child
                        break
                    child = self._model.iter_next(child)
                if child == None:
                    child = self._model.iter_children(parent)
                    #search for position by priority value
                    while child != None :
                        p = self._model.get(child, 3)[0]
                        if p < priority:
                            break
                        child = self._model.iter_next(child)
                    iter = self._model.insert_before(parent, child)
                    self._model.set(iter, 0, text, 1, "", 2, key, 3, priority)
                if parent == None:
                    iterPath = self._model.get_path(iter)
                    self._view.expand_row(iterPath, False)
            self._iterIndex[iterKey] = iter
        self._model.set(iter, 0, path[-1][-1], 1, value)
    
    def delTreeValue(self, *path):
        raise NotImplementedError()

    def stateSet(self, state, key, value):
        self.refreshUIState()

    def _jobStatusEvent(self, value):
        self._status = value
        self.updateStates()
        return False
    
    def _jobProgressEvent(self, value):
        if value != None:
            self._progress.set_fraction(value / 100.0)
        else:
            self._progress.set_fraction(0)
            self._progress.set_text(_("No Progression Information"))
        return False

    def _jobErrorEvent(self, value):
        self._jobError = _(value)
        self.updateJobErrors()
        self.updateStates()
        return False
    
    def _jobWarningEvent(self, value):
        self._jobWarning.append(_(value))
        self.updateJobErrors()
        self.updateStates()
        return False
    
    def _targetStateEvent(self, targetName, value):
        root = self.formatLabel("targets")
        target = self.keepLabel(targetName)
        text = self.getTargetStateText(targetName, value)
        self.setTreeValue(text, root, target)
        return False
    
    def _targetErrorEvent(self, targetName, value):
        root = self.formatLabel("targets")
        target = self.keepLabel(targetName)
        msg = _(value)
        self._targetsError[targetName] = msg
        error = self.formatLabel("target-error")
        text = self.formatValue("target-error", msg)
        self.setTreeValue(text, root, target, error)
        self.updateStates()
        return False
    
    def _targetWarningEvent(self, targetName, value):
        root = self.formatLabel("targets")
        target = self.keepLabel(targetName)
        msg = _(value)
        if not (targetName in self._targetsWarnings):
            self._targetsWarnings[targetName] = list()
        warnings = self._targetsWarnings[targetName]
        warnings.append(msg)
        warning = self.formatLabel("target-warning")
        text = self.formatValue("target-warning", msg)
        self.setTreeValue(text, root, target, warning)
        self.updateStates()
        return
    
    _jobEventHandlers = {"status": _jobStatusEvent,
                         "progress": _jobProgressEvent,
                         "job-error": _jobErrorEvent,
                         "job-warning": _jobWarningEvent}

    _targetEventHandlers = {"target-state": _targetStateEvent,
                            "target-error": _targetErrorEvent,
                            "target-warning": _targetWarningEvent}

    def stateSetitem(self, state, key, subkey, value):
        if (key == "job-data"):
            handler = self._jobEventHandlers.get(subkey, None)
            if handler and not handler(self, value):
                return
        field = self.getField(key, subkey)
        if field:
            text = self.formatValue(subkey, value)
            field.set_markup(text)
        elif key == "source-data":
            root = self.formatLabel("source")
            label = self.formatLabel(subkey)            
            text = self.formatValue(subkey, value)
            self.setTreeValue(text, root, label)
        elif key == "targets-data":
            targetName, subkey = subkey
            handler = self._targetEventHandlers.get(subkey, None)
            if handler and not handler(self, targetName, value):
                return
            root = self.formatLabel("targets")
            target = self.keepLabel(targetName)
            text = self.formatValue(subkey, value)
            label = self.formatLabel(subkey)
            self.setTreeValue(text, root, target, label)
    
    def stateDelitem(self, state, key, subkey, value):
        field = self._fields.get((key, subkey))
        if field:
            field.set_markup(self.formatValue(subkey, None))
        elif key == "source-data":
            label = self.formatLabel(subkey)
            root = self.formatLabel("source")
            self.delTreeValue(root, label)
        elif key == "targets-data":
            targetName, subkey = subkey
            root = self.formatLabel("targets")
            target = self.keepLabel(targetName)
            self.delTreeValue(root, target, label)

    def formatJobState(self, state):
        text = state.nick
        if self._jobError != None:
            return _error(_("Transcoding Failed"))
        if len(self._jobWarnings) > 0:
            return _warning(_("%s (Warnings)" % text))
        return _normal(text)    

    def getTargetStateText(self, target, state):
        text = self.formatValue("target-state", state)
        error = self._targetsError.get(target, None)
        warnings = self._targetsWarnings.get(target, [])
        if error != None:
            return _error(_("Error during %s" % text))
        if len(warnings) > 0:
            return _warning(_("%s (Warnings)" % text))
        return _normal(text)
    

class FileTranscoderAdminGtk(BaseAdminGtk):
    gettext_domain = 'flumotion-transcoder'

    def setup(self):
        d = BaseAdminGtk.setup(self)
        transcoding = FileTranscoderAdminGtkNode(self.state, self.admin,
                                                 title=_('Transcoding'))
        self.nodes['Transcoding'] = transcoding
        return d


GUIClass = FileTranscoderAdminGtk
