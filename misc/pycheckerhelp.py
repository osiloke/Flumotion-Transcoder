# lots of little imports done before anything else so that
# we don't get weird stray module errors

import pygtk
pygtk.require('2.0')

import pygst
pygst.require('0.10')

import setup
setup.setup()
