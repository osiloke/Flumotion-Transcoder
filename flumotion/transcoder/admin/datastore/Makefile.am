include $(top_srcdir)/common/python.mk

pythondir = $(libdir)/flumotion/python/flumotion/transcoder/admin/datastore

python_PYTHON = __init__.py base.py store.py notification.py customer.py \
                profile.py target.py config.py state.py activity.py \
                notification.py
python_DATA =

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(python_DATA)
