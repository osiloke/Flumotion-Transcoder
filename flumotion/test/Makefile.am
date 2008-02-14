include $(top_srcdir)/common/python.mk
include $(top_srcdir)/common/trial.mk
TRIAL_ENV=$(top_builddir)/env

EXTRA_DIST = 	__init__.py common.py gsttestutils.py \
                test_transcontext.py test_videosize.py \
                test_analyst.py

check-local: trial

CLEANFILES = setup.py
