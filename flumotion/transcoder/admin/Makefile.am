include $(top_srcdir)/common/python.mk

pythondir = $(libdir)/flumotion/python/flumotion/transcoder/admin

python_PYTHON = __init__.py main.py admin.py adminconfig.py adminelement.py \
                errors.py jobprops.py monitorprops.py
python_DATA =

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(python_DATA)
