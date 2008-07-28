include $(top_srcdir)/common/python.mk

SUBDIRS = admin manager tools

pythondir = $(libdir)/flumotion/python/flumotion/transcoder

python_PYTHON = __init__.py transconfig.py transreport.py \
                pipelinecrawler.py substitution.py \
                errors.py enums.py i18n.py \
                virtualpath.py local.py constants.py
                 

python_DATA =

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(python_DATA)
