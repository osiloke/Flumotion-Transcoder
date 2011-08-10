'''
Created on Jun 6, 2011

@author: strioni
'''
import cgi
import os
import shutil
from datetime import datetime

from twisted.web.resource import Resource
from twisted.internet.threads import deferToThread

from flumotion.common import log

from flumotion.component.transcoder import compconsts



class RequestHandler(Resource, log.Loggable):
    logCategory = compconsts.HTTP_MONITOR_LOG_CATEGORY

    def __init__(self, monitor, virt_dir, callback, profile_name=None):
        self.monitor = monitor
        self.callback = callback
        self.virt_dir = virt_dir
        self.profile_name = profile_name
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

        if not file_path.startswith('/'):
            #-------------------- Assume that the path is relative to virtDir
            vir_file = self.virt_dir.append(file_path)
            file_path = vir_file.localize(self.monitor._local)

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
            cue_string = ("The following cue points will be used: %s"
                % cue_points)

        params = {"cue-points": cue_points}
        requested_profile = request.args.get("profile", [None])[0]
        requested_profile = self.profile_name or requested_profile
        if requested_profile:
            params.update({"profile-name": requested_profile})

        now = datetime.utcnow()

        file_name = os.path.basename(file_path)
        vir_file = self.virt_dir.append(file_name)
        incoming_file = vir_file.localize(self.monitor._local)

        if (file_path == incoming_file):
            # FIXME: check that the file size isn't changing?
            self.debug("Reusing already existing file: %r" % file_path)
            d = deferToThread(self.callback, None,
                                      incoming_file, file_name,
                                      None, now, self.virt_dir,
                                      self.profile_name, params)
        else:
            self.debug("Copying %r to %r", file_path, incoming_file)
            d = deferToThread(shutil.copy, file_path, incoming_file)
            d.addCallback(self.callback, incoming_file, file_name,
                          None, now, self.virt_dir, self.profile_name, params)

        answer = ("<html><body>"
                  "<p>%s was queued for transcoding.</p>%s"
                  "</body></html>") % (file_path, cue_string)
        return answer
