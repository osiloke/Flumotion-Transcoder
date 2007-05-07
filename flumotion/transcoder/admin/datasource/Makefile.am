include $(top_srcdir)/common/python.mk

pythondir = $(libdir)/flumotion/python/flumotion/transcoder/admin/datasource

python_PYTHON = __init__.py datasource.py dummysource.py \
                dataprops.py filesource.py \
                sqlsource.py
python_DATA =

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(python_DATA)
