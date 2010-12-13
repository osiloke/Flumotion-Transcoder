include $(top_srcdir)/common/python.mk

component_PYTHON = __init__.py joiner.py

componentdir = $(libdir)/flumotion/python/flumotion/component/joiner
component_DATA = joiner.xml

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(component_DATA)
