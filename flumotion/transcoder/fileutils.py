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

import os
import grp
import pwd
import re

from flumotion.transcoder import utils, log
from flumotion.transcoder.errors import SystemError


class PathAttributes(object):
    
    @classmethod
    def createFromComponentProperties(cls, props):
        forceUser = props.get("force-user", None)
        forceGroup = props.get("force-group", None)
        forceDirMode = None
        forceFileMode = None
        dirMode = props.get("force-dir-mode", None)
        fileMode = props.get("force-file-mode", None)
        try:
            forceDirMode = dirMode and int(dirMode, 8)
        except ValueError, e:
            log.warning("Invalid directory mode '%s' specified: %s",
                        dirMode, log.getExceptionMessage(e))
        try:
            forceFileMode = fileMode and int(fileMode, 8)
        except ValueError, e:
            log.warning("Invalid file mode '%s' specified: %s",
                        fileMode, log.getExceptionMessage(e))
        return cls(forceUser, forceGroup, forceDirMode, forceFileMode)
    
    def __init__(self, userName=None, groupName=None,
                       dirMode=None, fileMode=None):
        self._userName = userName
        self._groupName = groupName
        self._userId = lookupUserId(userName)
        self._groupId = lookupGroupId(groupName)
        self._dirMode = dirMode
        self._fileMode = fileMode
        
    def apply(self, path):
        if os.path.isdir(path):
            mode = self._dirMode
        else:
            mode = self._fileMode
        applyPathAttributes(path, self._userId, self._groupId, mode)
        
    def __str__(self):
        dm = None
        fm = None
        if self._dirMode != None:
            dm = oct(self._dirMode)
        if self._fileMode != None:
            fm = oct(self._fileMode)
        return "%s:%s %s|%s" % (self._userName, self._groupName, dm, fm)

    def asComponentProperties(self):
        result = []
        if self._userName:
            result.append(("force-user", self._userName))
        if self._groupName:
            result.append(("force-group", self._groupName))
        if self._dirMode != None:
            result.append(("force-dir-mode", oct(self._dirMode)))
        if self._fileMode:
            result.append(("force-file-mode", oct(self._fileMode)))
        return result
    
    def asLaunchArguments(self):
        result = []
        if self._userName:
            result.append(utils.mkCmdArg(str(self._userName), "force-user="))
        if self._groupName:
            result.append(utils.mkCmdArg(str(self._groupName), "force-group="))
        if self._dirMode != None:
            result.append(utils.mkCmdArg(oct(self._dirMode), "force-dir-mode="))
        if self._fileMode:
            result.append(utils.mkCmdArg(oct(self._fileMode), "force-file-mode="))
        return result


def lookupUserId(userName):
    if not userName: return None
    try:
        pwdinfo = pwd.getpwnam(userName)
        return pwdinfo[2]
    except KeyError:
        return None

def lookupGroupId(groupName):
    if not groupName: return None
    try:
        grpinfo = grp.getgrnam(groupName)
        return grpinfo[2]
    except KeyError:
        return None

def applyPathAttributes(path, userid=None, groupid=None, mode=None):
    if mode != None:
        try:
            os.chmod(path, mode)
        except Exception, e:
            msg = ("Could not change mode to %s for path '%s': %s"
                   % (oct(mode), path, log.getExceptionMessage(e)))
            log.warning("%s", msg)
    if userid or groupid:
        try:
            os.chown(path, userid or -1, groupid or -1)
        except Exception, e:
            msg = ("Could not change ownership to %d:%d for path '%s': %s"
                   % (userid or -1, groupid or -1, path,
                      log.getExceptionMessage(e)))
            log.warning("%s", msg)

def ensureDirExists(dir, description, attr=None):
    """
    Ensure the given directory exists, creating it if not.
    Raises a SystemError if this fails, including the given description.
    If mkdir fail, verify the directory hasn't been created by another process.
    """
    dir = os.path.abspath(dir)
    if os.path.exists(dir):
        if os.path.isdir(dir):
            return
        raise SystemError("Could not create %s directory '%s': "
                          "it exists but it's not a directory"
                          % (description, dir))
    parts = dir.split(os.sep)
    for i in range(len(parts) - 1):
        dir = os.sep.join(parts[0:i + 2])
        if os.path.exists(dir):
            if os.path.isdir(dir):
                continue
            raise SystemError("Could not create %s directory '%s': "
                              "it exists but it's not a directory"
                              % (description, dir))
        try:
            os.mkdir(dir, 0755)
        except OSError, e:
            # May have been created at the same time by another process
            #FIXME: Is there a constant for this ?
            if e.errno == 17: continue
            raise SystemError("Could not create %s directory '%s': %s"
                              % (description, dir, log.getExceptionMessage(e)),
                              cause=e)
        if attr:
            attr.apply(dir)

_dumpTransTable = '................................ !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~.................................................................................................................................'

def hexDump(file, lineCount, lineSize=16):
    result = []
    currSize = 0
    maxSize = lineCount * lineSize
    while currSize < maxSize:
        line = file.read(lineSize)
        ascii = line.translate(_dumpTransTable)
        hex = ''
        i = 0
        while i*8 <= len(line):
            hex += ' '.join([c.encode('hex') for c in line[i*8:i*8 + 8]])
            hex += '  '
            i += 1
        hexPad = ' '*((lineSize*3 + (lineSize/8)*2) - len(hex))
        asciiPad = ' '*(lineSize - len(ascii))
        result.append("%s%s|%s%s|" % (hex, hexPad, ascii, asciiPad))
        currSize += len(line)
        if len(line) < lineSize:
            break
    return "\n".join(result)

def str2filename(value):
    """
    Build a valid name for a file or a directory from a specified string.
    Replace all caracteres out of [0-9A-Za-z-()] by '_' and lower the case.
    Ex: "Big Client Corp" => "big_client_corp"
        "OGG-Theora/Vorbis" => "ogg_theora_vorbis"
    """
    return "_".join(re.split("[^0-9A-Za-z-()]", value)).lower()

def splitPath(filePath, withExtention=True):
    """
    From: /toto/ta.ta/tu.tu.foo
    Return: ("/toto/ta.ta/", "tu.tu", ".foo")
    If withExtention is set to false, the extension is not extracted:
    From: /toto/ta.ta/tu.tu.foo
    Return: ("/toto/ta.ta/", "tu.tu.foo", "")
    """
    path = ""
    file = filePath
    ext = ""
    lastSepIndex = filePath.rfind('/') + 1
    if lastSepIndex > 0:
        path = file[:lastSepIndex]
        file = file[lastSepIndex:]
    if withExtention:
        lastDotIndex = file.rfind('.')
        if lastDotIndex >= 0:
            ext = file[lastDotIndex:]
            file = file[:lastDotIndex]
    return (path, file, ext)

def cleanupPath(filePath):
    """
    Simplify a path, but keep the last '/'.
    Ex:   //test/./toto/test.txt/ => /test/toto/test.txt/
    See test_utils.py for more use cases.
    
    FIXME: Too much complicated and special-cased.
    """
    parts = filePath.split('/')
    if len(parts) <= 1:
        return filePath
    result = []
    if parts[0] != '.':
        result.append(parts[0])
    result.extend([p for p in parts[1:-1] if p and p != '.'])
    last = parts[-1]
    if last != '.':
        if last or (not last and result and result[-1]):
            result.append(last)
    elif len(result) > 1:
        result.append('')
    if (parts[0] == '') and ((not result) or (result[0] != '') or (len(result) < 2)):
        result.insert(0, '')
    if (parts[-1] == '') and ((not result) or (result[-1] != '') or (len(result) < 2)):
        result.append('')
    if (parts[0] == '.') and ((not result) or ((result[0] != '.') and (len(result) < 2))):
        result.insert(0, '.')
    return '/'.join(result)

def ensureDirPath(dirPath):
    """
    Ensure the path ends by a '/'.
    """
    if (not dirPath) or dirPath.endswith('/'):
        return dirPath
    return dirPath + '/'

def ensureAbsPath(dirPath):
    """
    Ensure the path starts with a '/'.
    """
    if not dirPath:
        return '/'
    if dirPath.startswith('/'):
        return dirPath
    return '/' + dirPath

_ensureRelPathPattern = re.compile("/*(.*)")
def ensureRelPath(aPath):
    """
    Ensure the path do not starts with a '/'.
    """
    if not aPath:
        return aPath
    return _ensureRelPathPattern.match(aPath).group(1)

def ensureAbsDirPath(dirPath):
    """
    Shortcut to ensureDirPath(ensureAbsPath()) because it's used a lot.
    """
    if not dirPath:
        return '/'
    if not dirPath.endswith('/'):
        dirPath = dirPath + '/'
    if not dirPath.startswith('/'):
        dirPath = '/' + dirPath
    return dirPath

def ensureRelDirPath(dirPath):
    """
    Shortcut to ensureDirPath(ensureRelPath()) because it's used a lot.
    """
    if not dirPath:
        return dirPath
    if not dirPath.endswith('/'):
        dirPath = dirPath + '/'
    return _ensureRelPathPattern.match(dirPath).group(1)

def str2path(value):
    """
    Convert a string to a path.
    Actualy doing nothing.
    "toto/tatat/titi.txt" => "toto/tatat/titi.txt"
    """
    return value

def makeAbsolute(path, base=None):
    """
    If the specified path is not absolute (do not starts with '/')
    it's concatenated to the specified base or the current directory.
    """
    if not base:
        base = os.path.abspath('')
    if path.startswith('/'):
        return os.path.abspath(path)
    return os.path.abspath(ensureAbsDirPath(base) + path)

def joinPath(*parts):
    return cleanupPath("/".join(parts))
