include $(top_srcdir)/common/python.mk

pythondir = $(libdir)/flumotion/python/flumotion/transcoder/admin

python_PYTHON = __init__.py main.py admin.py adminconfig.py adminelement.py \
                errors.py transprops.py monitorprops.py eventsource.py \
                actionscheduler.py compprops.py constants.py eventsource.py \
                monitoringtask.py substitution.py taskbalancer.py utils.py \
                virtualpath.py waiters.py
python_DATA =

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(python_DATA)
