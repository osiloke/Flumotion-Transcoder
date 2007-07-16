include $(top_srcdir)/common/python.mk

pythondir = $(libdir)/flumotion/python/flumotion/transcoder/admin/datasource

python_PYTHON = __init__.py basestore.py adminstore.py customerstore.py \
                profilestore.py targetstore.py configstore.py activitystore.py \
                notificationstore.py
python_DATA =

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(python_DATA)
