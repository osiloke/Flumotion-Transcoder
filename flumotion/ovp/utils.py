'''
Created on Jun 1, 2011

@author: joseph
'''
import os
from itertools import chain

from flumotion.inhouse import log
from flumotion.ovp import hashlib


def _flattening_generator(arg):
    if isinstance(arg, (list, tuple)):
        for item in chain(*map(_flattening_generator, arg)):
            yield item
    elif isinstance(arg, dict):
        for item in _flattening_generator(zip(*sorted(arg.items()))):
            yield item
    else:
        yield str(arg)


def a_better_digest(*args, **kwargs):
    """ Digest using a generator instead of recursion """
    digester = hashlib.md5()
    digester.update("/")
    digester.update("/".join(_flattening_generator(args)))
    return digester.digest()


def safe_mkdirs(dir, description, attr=None):
    """
    Ensure the given directory exists, creating it if not.
    Raises a SystemError if this fails, including the given description.
    If mkdir fail, verify the directory hasn't been created by another process.
    """
    dir = os.path.abspath(dir)
    try:
        os.makedirs(dir, 0755)
    except OSError, e:
        if not os.path.isdir(dir):
            if e.errno == 17:
                raise SystemError("Could not create %s directory '%s': "
                                  "it exists but it's not a directory"
                                  % (description, dir))
            else:
                raise SystemError("Could not create %s directory '%s': %s"
                                  % (description, dir, log.getExceptionMessage(e)),
                                  cause=e)
    if attr:
        attr.apply(dir)




