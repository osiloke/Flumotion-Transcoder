include $(top_srcdir)/common/python.mk

SUBDIRS = context datasource datastore proxies

pythondir = $(libdir)/flumotion/python/flumotion/transcoder/admin

python_PYTHON = __init__.py main.py admin.py adminconfig.py adminelement.py \
                errors.py adminconsts.py transprops.py monprops.py eventsource.py \
                actionscheduler.py compprops.py constants.py eventsource.py \
                montask.py substitution.py monbalancer.py \
                waiters.py admintask.py monitoring.py \
                taskmanager.py transtask.py transbalancer.py \
                transcoding.py scheduler.py enums.py notifier.py \
                document.py
python_DATA =

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(python_DATA)
