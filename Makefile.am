# version first -- they are parsed LTR and later options depend on automake 1.8.
AUTOMAKE_OPTIONS = 1.8 dist-bzip2 no-dist-gzip

ACLOCAL_AMFLAGS = -I common

include $(srcdir)/common/changelog.mk
include $(srcdir)/common/common.mk
include $(srcdir)/common/pychecker.mk
include $(srcdir)/common/deb.mk
include $(srcdir)/common/rpm.mk

SUBDIRS = . common conf misc bin doc data pkgconfig transcoder flumotion tests

PYCHECKER_WHITELIST = \
	flumotion/transcoder/*.py \
	flumotion/transcoder/manager/*.py \
	flumotion/transcoder/tools/*.py \
	flumotion/transcoder/admin/*.py \
	flumotion/transcoder/admin/context/*.py \
	flumotion/transcoder/admin/datasource/*.py \
	flumotion/transcoder/admin/datastore/*.py \
	flumotion/transcoder/admin/proxy/*.py \
	flumotion/transcoder/admin/property/*.py \
	flumotion/transcoder/admin/api/*.py \
	flumotion/transcoder/admin/api/mediums/*.py \
	flumotion/component/transcoder/*.py

PYCHECKER_BLACKLIST = 

EXTRA_DIST = env.in \
	.version \
	RELEASE \
	LICENSE.LGPL \
	flumotion-transcoder.spec.in

BUILT_SOURCES = $(top_srcdir)/.version
$(top_srcdir)/.version:
	echo $(VERSION) > $@-t && mv $@-t $@

dist: changelog
