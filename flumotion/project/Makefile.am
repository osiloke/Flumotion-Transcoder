include $(top_srcdir)/common/python.mk
include $(top_srcdir)/common/locale.mk

transcoderdir = $(libdir)/flumotion/python/flumotion/project

transcoder_PYTHON = transcoder.py
noinst_PYTHON = __init__.py

clean-local:
	rm -f *.pyc *.pyo

PROJECT = transcoder

BUILT_SOURCES = transcoder.py
CLEANFILES = $(BUILT_SOURCES)

EXTRA_DIST = $(transcoder_PYTHON)
