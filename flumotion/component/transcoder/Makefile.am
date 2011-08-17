include $(top_srcdir)/common/python.mk

component_PYTHON = __init__.py binmaker.py gstutils.py videosize.py \
                   cuepointsfilesrc.py \
                   job.py transcoder.py basetargets.py reporter.py context.py \
                   thumbsink.py filetranscoder_admin_gtk.py \
                   compconsts.py analyst.py disco2.py varsets.py \
                   transtargets.py thumbtargets.py thumbsamplers.py thumbsrc.py \
                   watcher.py filetranscoder.py



componentdir = $(libdir)/flumotion/python/flumotion/component/transcoder
component_DATA = base.xml filetranscoder.xml filetranscoder.glade

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(component_DATA)
