include $(top_srcdir)/common/python.mk

SUBDIRS = context datasource datastore property proxy api

pythondir = $(libdir)/flumotion/python/flumotion/transcoder/admin

python_PYTHON = __init__.py main.py admin.py adminconfig.py adminelement.py \
                interfaces.py admerrs.py adminconsts.py \
                actionscheduler.py montask.py monbalancer.py \
                admintask.py monitoring.py \
                taskmanager.py transtask.py transbalancer.py \
                transcoding.py scheduler.py enums.py notifier.py \
                document.py notifysubs.py diagnostic.py janitor.py \
                diagutils.py
python_DATA =

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(python_DATA)
