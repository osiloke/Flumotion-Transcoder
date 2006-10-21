AUTOMAKE_OPTIONS = dist-bzip2 no-dist-gzip 1.8

ACLOCAL_AMFLAGS = -I common

include $(srcdir)/common/common.mk
include $(srcdir)/common/pychecker.mk

SUBDIRS = common conf misc bin transcoder flumotion tests

PYCHECKER_WHITELIST = \
	flumotion/transcoder/*.py

EXTRA_DIST = \
	LICENSE.Flumotion \
	flumotion-transcoder.spec \
	doc/redhat/flumotion-transcoder.init \
	doc/redhat/flumotion-transcoder.sysconfig
