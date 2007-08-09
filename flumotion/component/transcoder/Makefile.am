include $(top_srcdir)/common/python.mk

component_PYTHON = __init__.py binmaker.py gstutils.py videosize.py \
                   filemonitor.py filemonitor_admin_gtk.py watcher.py \
                   job.py transcoder.py targets.py reporter.py context.py \
                   thumbsink.py filetranscoder.py filetranscoder_admin_gtk.py \
                   compconsts.py
                   

componentdir = $(libdir)/flumotion/python/flumotion/component/transcoder
component_DATA = base.xml filemonitor.xml filemonitor.glade \
                 filetranscoder.xml filetranscoder.glade

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(component_DATA)
