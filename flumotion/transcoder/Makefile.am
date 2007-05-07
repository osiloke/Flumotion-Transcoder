include $(top_srcdir)/common/python.mk

pythondir = $(libdir)/flumotion/python/flumotion/transcoder

python_PYTHON = __init__.py inifile.py properties.py \
                jobconfig.py jobreport.py \
                process.py pipelinecrawler.py \
                log.py errors.py enums.py eventsource.py
python_DATA =

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(python_DATA)
