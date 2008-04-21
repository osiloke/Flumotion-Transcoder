include $(top_srcdir)/common/python.mk

SUBDIRS = 

pythondir = $(libdir)/flumotion/python/flumotion/transcoder/admin/api/mediums

python_PYTHON = __init__.py named.py workerset.py worker.py scheduler.py \
                store.py defaults.py customer.py profile.py targets.py config.py

python_DATA =

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(python_DATA)
