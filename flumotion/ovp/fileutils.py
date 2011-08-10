'''
Created on Jun 7, 2011

@author: strioni
'''
from flumotion.ovp import hashlib
from flumotion.inhouse.utils import mkCmdArg
import commands

def checksum(path):
    """ Computes the md5 checksum of the file """
    if not path: 
        raise ValueError("'path' must be an absolute path.")
    #read the file in chunks for performance reasons
    h = hashlib.md5()
    SIZE = 1 << 16
    fd = open(path, "rb")
    for chunk in iter(lambda: fd.read(SIZE), ""):
        h.update(chunk)
    return h.hexdigest()
    fd.close()

def magic_mimetype(path):
    try:
        arg = mkCmdArg(path)
        mime_type = commands.getoutput("file -biL" + arg)
    except Exception, e:
        mime_type = "ERROR: %s" % str(e)
    return mime_type
