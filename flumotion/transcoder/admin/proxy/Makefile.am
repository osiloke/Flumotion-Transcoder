include $(top_srcdir)/common/python.mk

pythondir = $(libdir)/flumotion/python/flumotion/transcoder/admin/proxies

python_PYTHON = __init__.py base.py managerset.py workerset.py \
                manager.py worker.py atmosphere.py \
                flow.py component.py componentset.py \
                monitorset.py monitor.py group.py \
                transcoderset.py transcoder.py

python_DATA =

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(python_DATA)
