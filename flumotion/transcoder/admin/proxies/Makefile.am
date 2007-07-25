include $(top_srcdir)/common/python.mk

pythondir = $(libdir)/flumotion/python/flumotion/transcoder/admin/proxies

python_PYTHON = __init__.py fluproxy.py managerset.py workerset.py \
                managerproxy.py workerproxy.py atmosphereproxy.py \
                flowproxy.py componentproxy.py componentset.py \
                monitorset.py monitorproxy.py groupproxy.py \
                transcoderset.py transcoderproxy.py \
                compprops.py monprops.py transprops.py
python_DATA =

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(python_DATA)
