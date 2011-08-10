include $(top_srcdir)/common/python.mk

component_PYTHON = __init__.py \
                   base.py resource.py \
                   filemonitor.py filemonitor_admin_gtk.py watcher.py \
                   httpmonitor.py httpmonitor_admin_gtk.py

componentdir = $(libdir)/flumotion/python/flumotion/component/monitor
component_DATA = filemonitor.xml filemonitor.glade httpmonitor.glade

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(component_DATA)
