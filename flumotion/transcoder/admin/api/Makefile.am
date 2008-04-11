include $(top_srcdir)/common/python.mk

SUBDIRS = mediums 

pythondir = $(libdir)/flumotion/python/flumotion/transcoder/admin/api

python_PYTHON = __init__.py config.py server.py api.py gateway.py \
                apiserver.py interfaces.py types.py

python_DATA =

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(python_DATA)
