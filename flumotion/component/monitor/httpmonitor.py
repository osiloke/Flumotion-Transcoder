import os

from socket import gethostname

from twisted.web.client import getPage
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor
from twisted.internet.defer import fail
from twisted.internet.interfaces import IReactorTCP

from flumotion.component.transcoder import compconsts
from flumotion.transcoder.enums import MonitorFileStateEnum
from flumotion.ovp.utils import safe_mkdirs
from flumotion.component.monitor.base import MonitorBase
from flumotion.component.monitor.resource import RequestHandler
from flumotion.component.transcoder.watcher import DirectoryWatcher


class HttpMonitor(MonitorBase):
    """
    Launch a transcoding task based on an HTTP post request.
    """

    logCategory = compconsts.HTTP_MONITOR_LOG_CATEGORY

    def init(self):
        self.watchers = []
        self._scanPeriod = None
        self._directories = []
        self.port = None
        self._listener = None

    def do_setup(self):
        try:
            properties = self.config['properties']
            # setup the passive profiles
            if self.http_profiles:
                root = Resource()
                for p in self.http_profiles:
                    vdir = self.profiles_virtualbase[p]
                    root.putChild(p, RequestHandler(self, vdir, callback=self._file_added_http, profile_name=p))
                    local_dir = vdir.localize(self._local)
                    safe_mkdirs(local_dir, "monitored")
                factory = Site(root)
                self.port = properties.get("port", 7680)
                self._listener = IReactorTCP(reactor).listenTCP(self.port, factory)
                if not self.port:
                    # setting port to 0 means random port, read and store.
                    self.port = self._listener.getHost().port
            # setup the active profiles
            self._scanPeriod = properties.get("scan-period", 10)
            for p in self.active_profiles:
                vdir = self.profiles_virtualbase[p]
                local_dir = vdir.localize(self._local)
                safe_mkdirs(local_dir, "monitored", self._pathAttr)
                watcher = DirectoryWatcher(self, local_dir, p, timeout=self._scanPeriod)
                watcher.connect('file-added', self._file_added, vdir, p)
                watcher.connect('file-completed', self._file_completed, vdir, p)
                watcher.connect('file-removed', self._file_removed, vdir, p)
                watcher.start()
                self.watchers.append(watcher)
            setup_callback = properties.get('setup-callback')
            if setup_callback:
                data = {'hostname': gethostname(), 'port': self.port}
                url = setup_callback % data
                getPage(url, method='POST')
                
                

            # htpp://sdfsdkfjlsdjfklsdf/?host=%(host)s&myport=%(port)s
            # htpp://sdfsdkfjlsdjfklsdf/?myip=123.123.123.123&myport=1234
            # TODO: make the http call to register.
        except:
            return fail(self._unexpected_error(task="component setup"))

    def do_stop(self):
        if self._listener:
            self._listener.stopListening()
        for w in self.watchers:
            w.stop()
        self.watchers[:] = []


    ## Signal Handler Methods ##
    def _file_added(self, watcher, file, fileinfo, detection_time, virt_base, profile_name):
        localFile = virt_base.append(file).localize(self._local)
        self.debug("File added : '%s'", localFile)

        # put here the parameters
        self._set_ui_item('pending-files', (profile_name, file),
                         (MonitorFileStateEnum.downloading, fileinfo,
                          detection_time, None, None, None))

    def _file_completed(self, watcher, file, fileinfo, virt_base, profile_name):
        self.get_file_info(file, fileinfo, watcher.path, virt_base,
            profile_name=profile_name, params={})
        

    def _file_removed(self, watcher, file, virtBase):
        localFile = virtBase.append(file).localize(self._local)
        self.debug("File removed '%s'", localFile)
        self._del_ui_item('pending-files', (virtBase, file))



    # a new request was received
    def _file_added_http(self, _, file_path, file, fileinfo, detection_time,
            virt_base, profile_name, params):
        local_file = virt_base.append(file).localize(self._local)
        self.debug("File added : '%s'", local_file)
        incoming_folder = os.path.dirname(file_path) + '/'
        # Set what we know in the UI. We'll set the rest after computing
        # the checksum
        self._set_ui_item('pending-files', (profile_name, file),
            (MonitorFileStateEnum.downloading, fileinfo, detection_time, None, None, params))

        self.get_file_info(file, fileinfo, incoming_folder, virt_base,
            profile_name=profile_name, params=params)
