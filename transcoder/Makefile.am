include $(top_srcdir)/common/python.mk

transcoderdir = $(pyexecdir)/transcoder

transcoder_PYTHON =	\
        __init__.py     \
        setup.py

BUILT_SOURCES = setup.py

CLEANFILES = $(BUILT_SOURCES)

clean-local:
	rm -rf *.pyc *.pyo

