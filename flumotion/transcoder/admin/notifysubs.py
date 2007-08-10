# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.transcoder.admin.substitution import Variables
from flumotion.transcoder.admin.enums import NotificationTriggerEnum

class NotificationVariables(Variables):
    
    def __init__(self, parent, prefix, analyseReport):
        Variables.__init__(self, parent)
        self._addAnalyseResult(prefix, analyseReport)

    ## Protected Methods ##
            
    def _addAnalyseResult(self, p, a):
        mimeType = ""
        hasVideo = 0
        hasAudio = 0
        videoWidth = 0
        videoHeight = 0
        duration = 0.0
        length = 0
        hours = 0
        minutes = 0
        seconds = 0
        
        if a:
            mimeType = a.mimeType or ""
            hasVideo = (a.hasVideo and 1) or 0
            hasAudio = (a.hasAudio and 1) or 0
            if a.hasVideo:
                videoWidth = a.videoWidth or 0
                videoHeight = a.videoHeight or 0
        
            if (a.videoDuration == None) and (a.audioDuration == None):
                duration = 0.0
            elif a.videoDuration and a.audioDuration:
                duration = max(a.videoDuration, a.audioDuration)
            elif a.videoDuration:
                duration = a.videoDuration
            else:
                duration = a.audioDuration or 0.0

            if (a.videoLength == None) and (a.audioLength == None):
                length = 0
            elif a.videoLength and a.audioLength:
                length = max(a.videoLength, a.audioLength)
            elif a.videoLength:
                length = a.videoLength
            else:
                length = a.audioLength or 0

            # PyChecker isn't smart enough to see I first convert to int
            __pychecker__ = "no-intdivide"
            seconds = int(round(duration))
            minutes = seconds / 60
            seconds -= minutes * 60
            hours = minutes / 60
            minutes -= hours * 60        

        self.addVar(p + "Mime", mimeType)
        self.addVar(p + "HasAudio", hasAudio)
        self.addVar(p + "HasVideo", hasVideo)
        self.addVar(p + "VideoWidth", videoWidth)
        self.addVar(p + "VideoHeight", videoHeight)
        self.addVar(p + 'Duration', duration)
        self.addVar(p + 'Length', length)
        self.addVar(p + 'Hours', hours)
        self.addVar(p + 'Minutes', minutes)
        self.addVar(p + 'Seconds', seconds)


class SourceNotificationVariables(NotificationVariables):
    
    def __init__(self, profCtx, trigger, report):
        analyseReport = report and report.source.analyse
        NotificationVariables.__init__(self, None,
                                       "source", analyseReport)
        success = ((trigger == NotificationTriggerEnum.done) and 1) or 0
        self.addVar("success", success)
        self.addVar("trigger", trigger.name)
        self.addVar("inputFile", profCtx.getInputFile())
        self.addVar("inputRelPath", profCtx.getInputRelPath())
        self.addVar("customerName", profCtx.customer.store.getName())
        self.addVar("profileName", profCtx.store.getName())
        self.addVar("errorMessage", (report and report.fatalError) or "")
        self._targets = {}
        for targCtx in profCtx.iterTargetContexts():
            key = targCtx.store.getName()
            targReport = report and report.targets[key]
            vars = TargetNotificationVariables(self, targCtx, 
                                               trigger, targReport)
            self._targets[key] = vars
        if self["sourceDuration"] <= 0:
            for vars in self._targets.values():
                if vars['targetDuration'] > 0:
                    self.addVar('mediaDuration', vars["targetDuration"])
                    self.addVar('mediaLength', vars["targetLength"])
                    self.addVar('mediaHours', vars["targetHours"])
                    self.addVar('mediaMinutes', vars["targetMinutes"])
                    self.addVar('mediaSeconds', vars["targetSeconds"])
                    break
        if not ('mediaDuration' in self):
            self.addVar('mediaDuration', self["sourceDuration"])
            self.addVar('mediaLength', self["sourceLength"])
            self.addVar('mediaHours', self["sourceHours"])
            self.addVar('mediaMinutes', self["sourceMinutes"])
            self.addVar('mediaSeconds', self["sourceSeconds"])
         
    def getTargetVariables(self, targCtx):
        key = targCtx.store.getName()
        return self._targets[key]


class TargetNotificationVariables(NotificationVariables):
    
    def __init__(self, sourceVars, targCtx, trigger, targetReport):
        analyseReport = targetReport and targetReport.analyse
        NotificationVariables.__init__(self, sourceVars,
                                       "target", analyseReport)
        success = ((trigger == NotificationTriggerEnum.done) and 1) or 0
        self.addVar("success", success)
        self.addVar("trigger", trigger.name)
        self.addVar("outputFile", targCtx.getOutputFile())
        self.addVar("outputRelPath", targCtx.getOutputRelPath())
        self.addVar("linkFile", targCtx.getLinkFile())
        self.addVar("linkRelPath", targCtx.getLinkRelPath())
        self.addVar("targetName", targCtx.store.getName())
            
        if self["targetDuration"] > 0:
            self.addVar('mediaDuration', self["targetDuration"])
            self.addVar('mediaLength', self["targetLength"])
            self.addVar('mediaHours', self["targetHours"])
            self.addVar('mediaMinutes', self["targetMinutes"])
            self.addVar('mediaSeconds', self["targetSeconds"])
        else:
            self.addVar('mediaDuration', self["sourceDuration"])
            self.addVar('mediaLength', self["sourceLength"])
            self.addVar('mediaHours', self["sourceHours"])
            self.addVar('mediaMinutes', self["sourceMinutes"])
            self.addVar('mediaSeconds', self["sourceSeconds"])
