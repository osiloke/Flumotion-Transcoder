include $(top_srcdir)/common/python.mk

pythondir = $(libdir)/flumotion/python/flumotion/transcoder/manager

python_PYTHON = __init__.py plugs.py
python_DATA = plugs.xml

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(python_DATA)
