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
import mimetypes
from cStringIO import StringIO


from zope.interface import Interface, implements, Attribute

from flumotion.transcoder.admin import admerrs
from flumotion.transcoder.admin.enums import DocumentTypeEnum


class IDocument(Interface):

    label = Attribute("Document label")

    def getType(self):
        pass

    def getMimeType(self):
        pass

    def __str__(self):
        pass

    def asString(self):
        pass

    def asFile(self):
        pass


class StringDocument(object):

    implements(IDocument)

    def __init__(self, type, label, data, mimeType='text/plain'):
        assert isinstance(type, DocumentTypeEnum)
        self._type = type
        self.label = label
        self._data = data
        self._mime = mimeType

    def getType(self):
        return self._type

    def getMimeType(self):
        return self._mime

    def __str__(self):
        return self._data

    def asString(self):
        return self._data

    def asFile(self):
        return StringIO(self._data)


class FileDocument(object):

    implements(IDocument)

    def __init__(self, type, label, path, mimeType=None):
        assert isinstance(type, DocumentTypeEnum)
        if not os.path.exists(path):
            raise admerrs.DocumentError("File document '%s' not found", path)
        self.label = label or os.path.basename(self._path)
        self._type = type
        self._path = path
        self._mime = mimeType or  mimetypes.guess_type(path)[0]
        if not self._mime:
            self._mime = 'application/octet-stream'

    def getType(self):
        return self._type

    def getMimeType(self):
        return self._mime

    def __str__(self):
        return self.asString()

    def asString(self):
        f = open(self._path)
        try:
            return f.read()
        finally:
            f.close()

    def asFile(self):
        return open(self._path)
