include $(top_srcdir)/common/python.mk

pythondir = $(libdir)/flumotion/python/flumotion/transcoder/admin/context

python_PYTHON = __init__.py base.py admin.py manager.py worker.py \
                store.py customer.py profile.py target.py config.py \
                notification.py state.py activity.py api.py \
                notifier.py scheduler.py
python_DATA =

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(python_DATA)
