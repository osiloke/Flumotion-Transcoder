include $(top_srcdir)/common/python.mk

pythondir = $(libdir)/flumotion/python/flumotion/transcoder/admin/context

python_PYTHON = __init__.py admincontext.py managercontext.py workercontext.py \
                customercontext.py profilecontext.py targetcontext.py \
                transcontext.py notifiercontext.py apicontext.py
python_DATA =

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(python_DATA)
