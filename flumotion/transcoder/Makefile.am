include $(top_srcdir)/common/python.mk

pythondir = $(libdir)/flumotion/python/flumotion/transcoder

python_PYTHON = __init__.py inifile.py properties.py \
                transconfig.py transreport.py \
                process.py pipelinecrawler.py \
                log.py errors.py enums.py utils.py \
                virtualpath.py local.py constants.py
python_DATA =

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(python_DATA)
