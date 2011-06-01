import cgi
import os
import shutil
from datetime import datetime

from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor, threads
from twisted.internet.interfaces import IReactorThreads, IReactorTCP

from flumotion.common.i18n import gettexter
from flumotion.component import component
from flumotion.common import log

from flumotion.inhouse import fileutils

from flumotion.component.transcoder.filemonitor import MonitorMixin
from flumotion.transcoder.virtualpath import VirtualPath
from flumotion.transcoder.local import Local
from flumotion.component.transcoder import compconsts
from flumotion.transcoder.enums import MonitorFileStateEnum

T_ = gettexter('flumotion-transcoder')
# prevents from computing too many md5 at the same time
IReactorThreads(reactor).suggestThreadPoolSize(2)

class HttpMonitorMedium(component.BaseComponentMedium):

    def remote_setFileState(self, virtBase, relFile, status):
        self.comp.setFileState(virtBase, relFile, status)

    def remote_setFilesState(self, states):
        for virtBase, relFile, status in states:
            self.comp.setFileState(virtBase, relFile, status)

    # called when a file is moved to the failed directory
    def remote_moveFiles(self, virtSrcBase, virtDestBase, relFiles):
        self.comp.moveFiles(virtSrcBase, virtDestBase, relFiles)


class RequestHandler(Resource, log.Loggable):
    logCategory = compconsts.HTTP_MONITOR_LOG_CATEGORY

    def __init__(self, monitor, virt_dir):
        self.monitor = monitor
        self.virt_dir = virt_dir
        Resource.__init__(self)

    def render_GET(self, request):
        answer = ("<html><body>"
                  "<p>Please use a Post request.<p>"
                  "</html></body>")
        request.setResponseCode(500)
        return answer

    def render_POST(self, request):
        file_path = cgi.escape(request.args.get("file", [None])[0])

        if file_path is None:
            answer = ("<html><body>"
                      "<p>Please specify a file path.</p>"
                      "</body></html>")
            request.setResponseCode(500)
            return answer

        if not os.path.isfile(file_path):
            answer = ("<html><body>"
                      "<p>Cannot access file %s.</p>"
                      "</body></html>") % file_path
            request.setResponseCode(500)
            return answer

        cue_points = request.args.get("cue-points", [None])[0]
        cue_string = ""
        if cue_points is not None:
            cue_points = cgi.escape(cue_points)
            cue_string = ("The following cue points will be used:"
                          " %s") % cue_points

        params = {"cue-points": cue_points}
        now = datetime.utcnow()

        file_name = os.path.basename(file_path)
        vir_file = self.virt_dir.append(file_name)
        incoming_file = vir_file.localize(self.monitor._local)

        if (file_path == incoming_file):
            # FIXME: check that the file size isn't changing?
            self.debug("Reusing already existing file: %r" % file_path)
            d = threads.deferToThread(self.monitor._file_added, None,
                                      incoming_file, file_name,
                                      None, now, self.virt_dir, params)
        else:
            self.debug("Copying %r to %r", file_path, incoming_file)
            d = threads.deferToThread(shutil.copy, file_path, incoming_file)
            d.addCallback(self.monitor._file_added, incoming_file, file_name,
                          None, now, self.virt_dir, params)

        answer = ("<html><body>"
                  "<p>%s was queued for transcoding.</p>%s"
                  "</body></html>") % (file_path, cue_string)
        return answer


class HttpMonitor(component.BaseComponent, MonitorMixin):
    """
    Launch a transcoding task based on an HTTP post request.
    """

    componentMediumClass = HttpMonitorMedium
    logCategory = compconsts.HTTP_MONITOR_LOG_CATEGORY

    def init(self):
        self.port = None
        self.uiState.addListKey('monitored-profiles', [])
        self.uiState.addDictKey('pending-files', {})
        self._local = None
        self._profiles = []
        self._uiItemDelta = {}
        self._uiItemDelay = None
        self._pathAttr = None

    def do_check(self):

        def monitor_checks(result):
            props = self.config["properties"]
            self._local = Local.createFromComponentProperties(props)
            return result

        try:
            d = component.BaseComponent.do_check(self)
            d.addCallback(monitor_checks)
            d.addErrback(self._ebErrorFilter, "component checking")
            return d
        except:
            self._unexpectedError(task="component checking")

    def do_setup(self):
        props = self.config["properties"]
        strDirs = props.get("profile", [])
        self._profiles = map(VirtualPath, strDirs)
        self.uiState.set('monitored-profiles', self._profiles)

        root = Resource()
        for virt_dir in self._profiles:
            path = virt_dir.getPath().replace("/", "_")
            root.putChild(path, RequestHandler(self, virt_dir))
            local_dir = virt_dir.localize(self._local)
            fileutils.ensureDirExists(local_dir, "monitored")
        factory = Site(root)
        iface = ""
        self.port = props.get("port", 7680)
        self._twisted_port = IReactorTCP(reactor).listenTCP(self.port, factory, interface=iface)
        # in case port is 0 - ie. we asked for a random port.
        self.port = self._twisted_port.getHost().port

    def do_stop(self):
        self._twisted_port.stopListening()

     ## Public Methods ##

    def setFileState(self, virtBase, relFile, status):
        key = (virtBase, relFile)
        state = self.uiState.get('pending-files')
        substate = state.get(key)
        # substate can be None, probably because it has already been
        # added to the internal dictionaries, but has not been updated
        # in the UIState. In that case don't bother with updating the
        # UIState - we don't want to overwrite the file state in the
        # smooth update structure.
        if substate is None:
            return

        # add here the parameters that were added in _file_added
        state, fileinfo, detection_time, mime_type, checksum, params = substate
        substate = (status, fileinfo, detection_time, mime_type, checksum,
                    params)
        self._updateUIItem('pending-files', key, substate)

    ## Signal Handler Methods ##

    # a new request was received
    def _file_added(self, _, file_path, file, fileinfo, detection_time, virt_base, params):
        local_file = virt_base.append(file).localize(self._local)
        self.debug("File added : '%s'", local_file)
        # detection_time = detection_time.replace(tzinfo=None)
        incoming_folder = os.path.dirname(file_path) + '/'
        # Set what we know in the UI. We'll set the rest after computing
        # the checksum
        self._setUIItem('pending-files', (virt_base, file),
                        (MonitorFileStateEnum.downloading, fileinfo,
                         detection_time, None, None, params))


        d = threads.deferToThread(self._getFileInfo, file, incoming_folder,
                                  virt_base, params=params)
        d.addCallbacks(self._updateChecksumState, self._failedChecksum,
                       callbackArgs = (fileinfo, local_file),
                       errbackArgs = (fileinfo, file, virt_base, incoming_folder))
