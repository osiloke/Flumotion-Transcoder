# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import sys
import os
import re
import optparse
import shutil

from flumotion.transcoder.enums import TargetTypeEnum
from flumotion.transcoder.enums import AudioVideoToleranceEnum
from flumotion.transcoder.enums import PeriodUnitEnum
from flumotion.transcoder.enums import ThumbOutputTypeEnum
from flumotion.transcoder import utils, log, inifile
from flumotion.transcoder.tools import oldconfig
from flumotion.transcoder.admin import adminconfig
from flumotion.transcoder.admin.datasource import dataprops


VERSION = "Flumotion Transcoder Configuration Upgrader v1.0"

DEFAULT_OLD_CONFIG_FILE = "/etc/flumotion-transcoder.ini"
DEFAULT_NEW_CONFIG_DIR = "/etc/flumotion/transcoder/%(tag)s"
DEFAULT_ROOT_DIR = "/home/file"

class Loggable(object):
    
    level = 2
    def __init__(self):
        pass
    
    def _postfix(self):
        return ""
    
    def log(self, template, *args):
        if self.level < 5: return
        print ("%s%%s" % template) % (args + (self._postfix(),))

    def debug(self, template, *args):
        if self.level < 4: return
        print ("%s%%s" % template) % (args + (self._postfix(),))

    def info(self, template, *args):
        if self.level < 3: return
        print ("%s%%s" % template) % (args + (self._postfix(),))
        
    def warning(self, template, *args):
        if self.level < 2: return
        print ("WARNING: %s%%s" % template) % (args + (self._postfix(),))

    def error(self, template, *args):
        if self.level < 1: return
        print ("ERROR: %s%%s" % template) % (args + (self._postfix(),))


class UpgradeConfig(Loggable):
    
    @classmethod
    def checkVersions(cls):
        return ((adminconfig.ClusterConfig.VERSION == (1, 0))
                and (dataprops.AdminData.VERSION == (1, 0))
                and (dataprops.CustomerData.VERSION == (1, 0)))
    
    def __init__(self, tag, oldConfigFile, newConfigDir, rootDir,
                 disableRequests=None, changeMail=None, keepConfig=None,
                 doBackup=True):
        self._tag = tag
        self._oldFile = oldConfigFile
        self._newDir = utils.ensureAbsDirPath(newConfigDir)
        self._rootDir = utils.ensureAbsDirPath(rootDir)
        self._disableRequests = disableRequests or False
        self._changeMail = changeMail
        self._keepConfig = keepConfig or False
        self._doBackup = doBackup
        self._adminConfigPath = self._newDir + "transcoder-admin.ini"
        self._adminDataPath = self._newDir + "transcoder-data.ini"
        self._customerDataDir = self._newDir + "customers/"
        self._customerDataRelDir = "customers"
        if self._tag:
            self._tempDir = "/var/tmp/flumotion/transcoder/%s/" % self._tag
        else:
            self._tempDir = "/var/tmp/flumotion/transcoder/"
        if not os.path.exists(self._customerDataDir):
            os.makedirs(self._customerDataDir)

    def upgrade(self):
        self.info("Loading old configuration '%s'", self._oldFile)
        oldConfig = oldconfig.Config(self, self._oldFile)
        self._backupFiles()
        self.upgradeAdminConfig(oldConfig)
        self.upgradeAdminData(oldConfig)
        self.upgradeCustomers(oldConfig)
        
    def _backupFiles(self):
        
        def renameIfExists(f):
            if os.path.exists(f):
                if not self._doBackup:
                    os.remove(f)
                else:
                    dest = f + '.old'
                    self.info("Renaming current file '%s' to '%s'", f, dest)
                    shutil.move(f, dest)
        
        if not (self._keepConfig and os.path.exists(self._adminConfigPath)):
            renameIfExists(self._adminConfigPath)
        renameIfExists(self._adminDataPath)
        if os.path.exists(self._customerDataDir):
            files = os.listdir(self._customerDataDir)
            for f in files:
                if f.endswith('.ini'):
                    renameIfExists(self._customerDataDir + f)
        
    def upgradeAdminConfig(self, oldConfig):
        if self._keepConfig and os.path.exists(self._adminConfigPath):
            return
        self.debug("Creating data container for transcoder admin configuration")
        adminConfig = adminconfig.ClusterConfig()
        
        # Datasource configuration
        adminConfig.admin.datasource.dataFile = self._adminDataPath
        
        # Notifier configuration
        adminConfig.admin.notifier.smtpServer = "mail.fluendo.com"
        adminConfig.admin.notifier.smtpUsername = None
        adminConfig.admin.notifier.smtpPassword = None
        adminConfig.admin.notifier.mailNotifySender = "Transcoder Admin <transcoder-notify@fluendo.com>"
        adminConfig.admin.notifier.mailEmergencySender = "Transcoder Emergency <transcoder-emergency@fluendo.com>"
        adminConfig.admin.notifier.mailEmergencyRecipients = "sebastien@fluendo.com"
        adminConfig.admin.notifier.mailDebugSender = "Transcoder Debug <transcoder-debug@fluendo.com>"
        adminConfig.admin.notifier.mailDebugRecipients = "sebastien@fluendo.com"
        
        # Admin virtual path roots configuration
        adminConfig.admin.roots["default"] = self._rootDir
        
        # Manager configuration
        adminConfig.manager.host = "localhost"
        adminConfig.manager.port = 7632
        adminConfig.manager.username = "user"
        adminConfig.manager.password = "test"
        adminConfig.manager.useSSL = None
        adminConfig.manager.certificate = None

        # Default worker configuration
        adminConfig.workerDefaults.roots["default"] = self._rootDir
        adminConfig.workerDefaults.roots["temp"] = self._tempDir
        adminConfig.workerDefaults.maxTask = oldConfig.maxJobs
        adminConfig.workerDefaults.gstDebug = oldConfig.gstDebug
        
        self.info("Saving admin configuration to '%s'", self._adminConfigPath)
        saver = inifile.IniFile()
        saver.saveToFile(adminConfig, self._adminConfigPath)
        
    def upgradeAdminData(self, oldConfig):
        self.debug("Creating data container for transcoder global data")
        adminData = dataprops.AdminData()
        
        adminData.accessForceGroup = oldConfig.groupName
        adminData.discovererMaxInterleave = oldConfig.maxInterleave
        adminData.customersDir = self._customerDataRelDir
        base = utils.ensureAbsDirPath("/var/cache/flumotion/transcoder/%s" % self._tag)
        adminData.activitiesDir = base + "activities"

        self.info("Saving transcoder global data to '%s'", self._adminDataPath)
        saver = inifile.IniFile()
        saver.saveToFile(adminData, self._adminDataPath)
    
    def upgradeCustomers(self, oldConfig):
        customers = {} # {name: CustomerData}
        hackLookup = {}
        for oldName, oldCustConf in oldConfig.customers.items():
            nameParts = oldName.split('-', 1)
            custName = nameParts[0]
            profName = ((len(nameParts) > 1) and nameParts[1]) or "default"
            if custName in customers:
                custData = customers[custName]
            else:
                # Check for HACK
                key = oldCustConf.inputDir
                if key in hackLookup:
                    custData = hackLookup[key][0]
                    # Keep the smaller name
                    if oldName < custData.name:
                        del customers[custData.name]
                        customers[custData.name] = custData
                        custData.name = oldName
                else:
                    self.debug("Creating data container for customer '%s'", custName)
                    custData = dataprops.CustomerData()
                    customers[custName] = custData
                    custData.name = custName
            if profName in custData.profiles:
                self.warning("Duplicated profile '%s' for customer '%s'; renaming it '%s'",
                             profName, custData.name, profName + "2")
                profName = profName + "2"
            self.debug("Creating data container of profile '%s'", profName)
            profData = dataprops.ProfileData()
            custData.profiles[profName] = profData
            profData.name = profName
            try:
                self._upgradeProfile(oldCustConf, custData, profData)
                key = oldCustConf.inputDir
                if key in hackLookup:
                    # Ensure the last customer/profile names are smaller
                    lastProf = hackLookup[key][1]
                    newProf = profData
                    if lastProf.name > newProf.name:
                        hackLookup[key] = (custData, newProf)
                        newProf, lastProf = lastProf, newProf
                    self._resolveHack(custData, lastProf, newProf)
                else:
                    hackLookup[key] = custData, profData
            except Exception, e:
                self.warning("Fail to upgrade profile '%s' for customer '%s': %s",
                             profName, custName, str(e))
                del custData.profiles[profName]

        # Cleanup a litle
        for custKey, custData in customers.items():
            if custData.name == custData.subdir:
                custData.subdir = None
            for profKey, profData in custData.profiles.items():
                if profKey == profData.subdir:
                    profData.subdir = None
                if profKey == profData.name:
                    profData.name = None
                for targKey, targData in profData.targets.items():
                    if targKey == targData.name:
                        targData.name = None
        
        for custKey, custData in customers.items():
            path = self._customerDataDir + custKey + ".ini"
            self.info("Saving customer '%s' data to '%s'", custKey, path)
            try:
                saver = inifile.IniFile()
                saver.saveToFile(custData, path)
            except Exception, e:
                self.warning("Fail to save customer '%s' file '%s': %s",
                             custKey, path, str(e))

    def _getInputDir(self, custData, profData):
        if profData.inputDir:
            return profData.inputDir
        if custData.inputDir:
            result = custData.inputDir
        elif custData.subdir:
            result = custData.subdir
        else:
            result = utils.str2filename(custData.name)
        result = utils.ensureRelDirPath(result)
        result = result + "files/incoming/"
        if profData.subdir:
            result = result + profData.subdir
        else:
            result = result + utils.str2filename(profData.name)
        return result

    def _resolveHack(self, custData, lastProfData, newProfData):
        self.info("Trying to upgrade HACK made for customer '%s' profiles '%s' and '%s'",
                  custData.name, lastProfData.name, newProfData.name)
        subdir = utils.str2filename(newProfData.name)
        if utils.ensureRelDirPath(subdir) != utils.ensureRelDirPath(lastProfData.subdir):
            newProfData.subdir = subdir
        else:
            newProfData.subdir = subdir + "2"
        inputDir = self._getInputDir(custData, newProfData)
        lastProfData.outputDir = inputDir
        period = min(lastProfData.monitoringPeriod, newProfData.monitoringPeriod)
        lastProfData.monitoringPeriod, newProfData.monitoringPeriod = period, period

    def _upgradeVariables(self, s):
        s = s.replace("%(workPath)", "%(outputWorkPath)")
        s = s.replace("%(workFile)", "%(outputWorkRelPath)")
        s = s.replace("%(outputFile)", "%(outputRelPath)")
        s = s.replace("%(outputPath)", "%(outputPath)")
        s = s.replace("%(inputFile)", "%(inputRelPath)")
        s = s.replace("%(inputPath)", "%(inputPath)")
        s = s.replace("%(workRoot)", "%(outputWorkBase)")
        s = s.replace("%(inputRoot)", "%(inputBase)")
        s = s.replace("%(outputRoot)", "%(outputBase)")
        s = s.replace("%(errorRoot)", "%(failedBase)")
        s = s.replace("%(linkRoot)", "%(linkBase)")
        s = s.replace("%(message)", "%(errorMessage)")
        s = s.replace("%(hours)", "%(mediaHours)")
        s = s.replace("%(minutes)s", "%(mediaMinutes)")
        s = s.replace("%(seconds)s", "%(mediaSeconds)")
        return s

    def _upgradeProfile(self, oldCustConf, custData, profData):
        # List all subdirs
        subdirs = {}
        for kind, path in (("incoming", oldCustConf.inputDir),
                           ("outgoing", oldCustConf.outputDir),
                           ("links",    oldCustConf.linkDir),
                           ("errors",   oldCustConf.errorDir)):
            if not path: continue
            if not path.startswith(self._rootDir):
                raise Exception("Unsupported %s path '%s'; not a subdirectory of '%s'"
                                % (kind, path, self._rootDir))
            subdirs[kind] = (path,) + self._extractSubdirs(path)
        # Count the used customer and profile subdirs
        custSubdirs = {}
        profSubdirs = {}
        for kind, (path, custSubdir, middle, profSubdir) in subdirs.items():
            custSubdirs[custSubdir] = custSubdirs.setdefault(custSubdir, 0) + 1
            profSubdirs[profSubdir] = profSubdirs.setdefault(profSubdir, 0) + 1
        # Choose the most used subdirs
        k = custSubdirs.keys()
        k.sort(key=custSubdirs.get)
        custSubdir = k[-1]
        k = profSubdirs.keys()
        k.sort(key=profSubdirs.get)
        profSubdir = k[-1]
        
        # Arbitrary use the first profile to set the customer subdir
        if not custData.subdir:
            custData.subdir = custSubdir
        profData.subdir = profSubdir
        
        # Now check every path if they comply with the subdirs
        for kind, attr in (("incoming", "inputDir"),
                           ("outgoing", "outputDir"),
                           ("links",    "linkDir"),
                           ("errors",   "failedDir")):
            if not (kind in subdirs): continue
            path, csd, middle, psd = subdirs[kind]
            if (csd != custSubdir) or (psd != profSubdir) or (middle != kind):
                dir = path[len(self._rootDir):].strip('/')
                override = self._guessOverridenDir(dir)
                setattr(profData, attr, utils.ensureRelDirPath(override))
        
        profData.linkURLPrefix = oldCustConf.urlPrefix
        if oldCustConf.urlPrefix and  oldCustConf.linkDir:
            profData.enableLinkFiles = True
        if oldCustConf.priority != 50:
            profData.transcodingPriority = oldCustConf.priority
        if oldCustConf.timeout != 30:
            profData.monitoringPeriod = oldCustConf.timeout
        if oldCustConf.ppTimeout != 60:
            profData.monitoringPeriod = oldCustConf.ppTimeout
        if oldCustConf.transTimeout != 30:
            profData.transcodingTimeout = oldCustConf.transTimeout
        if oldCustConf.getRequest and not self._disableRequests:
            req = self._upgradeVariables(oldCustConf.getRequest)
            profData.notifyDoneRequests.append(req)
        if oldCustConf.errGetRequest and not self._disableRequests:
            req = self._upgradeVariables(oldCustConf.errGetRequest)
            profData.notifyFailedRequests.append(req)
        if oldCustConf.errMail:
            mail = self._changeMail or oldCustConf.errMail
            profData.notifyFailedMailRecipients = mail
        
        for targName, oldTargConf in oldCustConf.profiles.items():
            if targName in profData.targets:
                self.warning("Duplicated target '%s'", targName)
                continue
            self.debug("Creating data container of target '%s'", targName)
            targData = dataprops.TargetData()
            profData.targets[targName] = targData
            targData.name = targName
            try:
                self._upgradeTarget(oldTargConf, custData, profData, targData)
            except Exception, e:
                self.warning("Fail to upgrade target '%s' for profile '%s' "
                             "of customer '%s': %s",
                             targName, profData.name, custData.name, str(e))
                del profData.targets[targName]

    def _extractSubdirs(self, path):
        if path.startswith(self._rootDir):
            for middle in ['incoming', 'outgoing', 'errors', 'links']:
                try:
                    i = path.rindex(middle)
                    return (path[len(self._rootDir):i].strip('/'),
                            middle, path[i + len(middle):].strip('/'))
                except ValueError:
                    continue
        return (None, None, None)
 
    def _guessOverridenDir(self, dir):
        for middle in ['incoming', 'outgoing', 'errors', 'links']:
            try:
                i = dir.index(middle)
                p1 = dir[:i].strip('/')
                p2 = dir[i + len(middle):].strip('/')
                return  p1 + "/file/" + middle + "/" + p2
            except ValueError:
                pass
        return dir

    def _upgradeAudioConfig(self, oldConfig, configData):
        configData.muxer = oldConfig.muxer
        configData.audioEncoder = oldConfig.audioencoder
        configData.audioRate = oldConfig.audiorate
        configData.audioChannels = oldConfig.audiochannels

    def _upgradeVideoConfig(self, oldConfig, configData):
        configData.muxer = oldConfig.muxer
        configData.videoEncoder = oldConfig.videoencoder
        configData.videoWidth = oldConfig.videowidth
        configData.videoHeight = oldConfig.videoheight
        if oldConfig.sizemultiple != 1:
            configData.videoWidthMultiple = oldConfig.sizemultiple
            configData.videoHeightMultiple = oldConfig.sizemultiple
        configData.videoMaxWidth = oldConfig.maxwidth
        configData.videoMaxHeight = oldConfig.maxheight
        configData.videoPAR = oldConfig.videopar
        configData.videoFramerate = oldConfig.videoframerate

    def _upgradeAudioVideoConfig(self, oldConfig, configData):
        configData.tolerance = AudioVideoToleranceEnum.allow_without_audio

    _thumbnailerCmdPattern = re.compile(".*flumotion-thumbnailer([-a-zA-Z0-9]*)\.sh .*-s *([0-9x]*) .*-o *([/%\(\)a-zA-Z0-9]*) .*")
    _pngOutputPattern = re.compile(".*-x *png.*")

    def _upgradeTarget(self, oldTargConf, custData, profData, targData):
        targData.extension = oldTargConf.extension
        if not oldTargConf.appendExt:
            targData.outputFileTemplate = "%(targetDir)s%(sourceBasename)s%(targetExtension)s"
            if profData.enableLinkFiles:
                targData.linkFileTemplate = "%(targetDir)s%(sourceBasename)s.link"
        if oldTargConf.getRequest and not self._disableRequests:
            req = self._upgradeVariables(oldTargConf.getRequest)
            targData.notifyDoneRequests.append(req)
        if oldTargConf.videoencoder:
            if oldTargConf.audioencoder:
                targData.type = TargetTypeEnum.audiovideo
                self._upgradeAudioConfig(oldTargConf, targData.config)
                self._upgradeVideoConfig(oldTargConf, targData.config)
                self._upgradeAudioVideoConfig(oldTargConf, targData.config)
            else:
                targData.type = TargetTypeEnum.video
                self._upgradeVideoConfig(oldTargConf, targData.config)
        elif oldTargConf.audioencoder:
            targData.type = TargetTypeEnum.audio
            self._upgradeAudioConfig(oldTargConf, targData.config)
        else:
            targData.type = TargetTypeEnum.identity
        if oldTargConf.postprocess:
            m = self._thumbnailerCmdPattern.match(oldTargConf.postprocess)
            if not m:
                cmd = self._upgradeVariables(oldTargConf.postprocess)
                targData.postprocessCommand = cmd
                return
            thumbnailerVersion = m.group(1)
            thumbnailSize = m.group(2)
            outputPath = m.group(3)
            if thumbnailerVersion == '-indexer':
                targData.postprocessCommand = "flvtool2 -U %(workPath)s"
            elif thumbnailerVersion != '':
                self.warning("Unknown thumbnailer version "
                             "'flumotion-thumbnailer%s.sh' "
                             "used for postprocess of customer '%s' "
                             "profile '%s' target '%s'", thumbnailerVersion,
                             custData.name, profData.name, targData.name)
            self.debug("Creating data container of thumbnails target")
            thumbData = dataprops.TargetData()
            profData.targets["thumbnails"] = thumbData
            thumbData.name = "thumbnails"
            thumbData.type = TargetTypeEnum.thumbnails
            if not (outputPath == '%(outputRoot)s'):
                if not outputPath.startswith(self._rootDir):
                    raise Exception("Invalid thumbnail output directory '%s'; "
                                    "not a sub-directory of '%s'"
                                    % (outputPath, self._rootDir))
                thumbData.subdir = outputPath[len(self._rootDir):]
            if oldTargConf.appendExt:
                thumbData.outputFileTemplate = "%(targetPath)s"
            else:
                thumbData.outputFileTemplate = "%(targetDir)s%(sourceBasename)s%(targetExtension)s"
            thumbData.config.periodValue = 30
            thumbData.config.periodUnit = PeriodUnitEnum.percent
            thumbData.config.maxCount = 1
            if 'x' in thumbnailSize:
                width, height = map(int, thumbnailSize.split('x'))
                thumbData.config.thumbsWidth = width
                thumbData.config.thumbsHeight = height
            else:
                thumbData.config.thumbsWidth = int(thumbnailSize)
            if self._pngOutputPattern.match(oldTargConf.postprocess):
                thumbData.extension = "png"
                thumbData.config.format = ThumbOutputTypeEnum.png
            else:
                thumbData.extension = "jpg"
                thumbData.config.format = ThumbOutputTypeEnum.jpg
    
def main(argv):
    if not UpgradeConfig.checkVersions():
        print "ERROR: Configuration files definition changed, please update the upgrade script"
    usage="usage: %prog [-v] bootstrap|upgrade [OPTIONS]"
    parser = optparse.OptionParser(usage=usage, version=VERSION)
    parser.add_option('-v', '--verbose', action="count", dest="verbose", default=0,
                      help="Print more information; use more than one time for even more information")
    parser.add_option('-t', '--tag', action="store", type="string", dest="tag", default="",
                      help="Transcoder version tag; used to be able to install more "
                           "than one version of the transcoder at the same time")
    parser.add_option('-o', '--old-config-file',
                      action="store", type="string", dest="oldConfigFile",
                      metavar="OLD_CONFIG_FILE", default=DEFAULT_OLD_CONFIG_FILE,
                      help="The path to the old configuration file to upgrade from; "
                           "default value: '%s'" % DEFAULT_OLD_CONFIG_FILE)
    parser.add_option('-n', '--new-config-dir',
                      action="store", type="string", dest="newConfigDir",
                      metavar="NEW_CONFIG_DIR", default=None,
                      help="The path to the new configuration directory; "
                           "default value: '%s'" % DEFAULT_NEW_CONFIG_DIR)
    parser.add_option('-r', '--root-dir',
                      action="store", type="string", dest="rootDir",
                      metavar="DEFAULT_ROOT_DIR", default=DEFAULT_ROOT_DIR,
                      help="The path to the root directory of the transcoder files; "
                           "default value: '%s'" % DEFAULT_ROOT_DIR)
    parser.add_option('', '--disable-requests',
                      action="store_true", dest="disableRequests", default=False,
                      help="Disable the GET requests configuration for done and filed transcoding")
    parser.add_option('', '--change-mail',
                      action="store", type="string", dest="changeMail",
                      help="Change the eMail used for notifying the transcoding failures")
    parser.add_option('', '--keep-config',
                      action="store_true", dest="keepConfig", default=False,
                      help="Keep the actual configuration file if it exists (flumotion-transcoder.ini)")
    parser.add_option('', '--disable-backup',
                      action="store_false", dest="doBackup", default=True,
                      help="Do not rename the old files, just delete them.")    
    
    
    options, args = parser.parse_args(argv[1:])
    
    Loggable.level = min(5, options.verbose + 2)
    
    if args == ['bootstrap']:
        oldConfigFile = utils.makeAbsolute(options.oldConfigFile)
        rootDir = utils.makeAbsolute(options.rootDir)
        newConfigDir = options.newConfigDir
        if not newConfigDir:
            newConfigDir = DEFAULT_NEW_CONFIG_DIR % options.tag
        newConfigDir = utils.makeAbsolute(newConfigDir)
        
        if not os.path.exists(oldConfigFile):
            parser.error("Old configuration file '%s' not found" % oldConfigFile)
        if not os.access(oldConfigFile, os.F_OK | os.R_OK):
            parser.error("Cannot read old configuration file '%s'; check permissions"
                         % oldConfigFile)
        if not os.path.exists(newConfigDir):
            try:
                os.makedirs(newConfigDir)
            except Exception, e:
                parser.error("New configuration directory '%s' cannot be created: %s"
                             % (newConfigDir, str(e)))
        if not os.access(newConfigDir, os.F_OK | os.R_OK | os.W_OK | os.X_OK):
            parser.error("Not enough permissions to use directory '%s' as "
                         "the new configuration directory" % newConfigDir)
        if not os.path.exists(rootDir):
            try:
                os.makedirs(rootDir)
            except Exception, e:
                parser.error("Default transcoder root directory '%s' cannot be created: %s"
                             % (rootDir, str(e)))
        
        try:
            upgrader = UpgradeConfig(options.tag, oldConfigFile,
                                     newConfigDir, rootDir,
                                     disableRequests=options.disableRequests,
                                     changeMail=options.changeMail,
                                     keepConfig=options.keepConfig,
                                     doBackup=options.doBackup)
            upgrader.upgrade()
        except Exception, e:
            print
            if options.verbose > 3:
                print "ERROR: %s" % log.getExceptionMessage(e)
            else:
                print "ERROR: %s" % str(e)
            if options.verbose > 4:
                print log.getExceptionTraceback(e)
            print
        
        return
    
    if args == ['upgrade']:
        print
        print "Not implemented yet"
        print
        sys.exit(0)
    
    print
    if len(args) > 0:
        print "Error: Invalid command specified"
    else:
        print "Error: No command specified"
    print
    parser.print_usage()
    sys.exit(1)
