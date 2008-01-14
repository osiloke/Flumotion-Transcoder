AC_INIT(README)

AS_VERSION(flumotion-transcoder, FLUTRANS, 0, 1, 2, 1)
AC_SUBST(RELEASE, $FLUTRANS_RELEASE)

AC_SUBST_FILE(AUTHORS)
AUTHORS=$srcdir/AUTHORS

AC_SUBST(FLUMOTION_REQ, 0.5.0.1)

AM_INIT_AUTOMAKE($PACKAGE, $VERSION)

dnl Add parameters for aclocal
AC_SUBST(ACLOCAL_AMFLAGS, "-I common")

AS_AC_EXPAND(LIBDIR, $libdir)
AC_MSG_NOTICE(Storing library files in $LIBDIR)

AS_AC_EXPAND(DATADIR, $datadir)
AC_MSG_NOTICE(Storing data files in $DATADIR)

AS_AC_EXPAND(SYSCONFDIR, $sysconfdir)
AC_MSG_NOTICE(Storing configuration files in $SYSCONFDIR)

AS_AC_EXPAND(LOCALSTATEDIR, $localstatedir)
AC_MSG_NOTICE(Using localstatedir $LOCALSTATEDIR)


dnl check for python
AS_PATH_PYTHON(2.4.0)
dnl useful when we compile our own python modules
dnl AM_CHECK_PYTHON_HEADERS(,[AC_MSG_ERROR(could not find Python headers)])

dnl check for epydoc
AC_CHECK_PROG(EPYDOC, epydoc, yes, no)
AM_CONDITIONAL(HAVE_EPYDOC, test "x$EPYDOC" = "xyes")

dnl check for pychecker
AC_CHECK_PROG(PYCHECKER, pychecker, yes, no)
AM_CONDITIONAL(HAVE_PYCHECKER, test "x$PYCHECKER" = "xyes")

dnl check for flumotion
PKG_CHECK_MODULES(FLUMOTION, flumotion >= $FLUMOTION_REQ)
FLUMOTION_DIR="`$PKG_CONFIG --variable=flumotiondir flumotion`"
AC_MSG_NOTICE([Flumotion code base directory is $FLUMOTION_DIR])
AC_SUBST(FLUMOTION_DIR)

dnl output stuff
PREAMBLE=`cat $srcdir/misc/preamble.py`
FLUMOTION_SETUP(transcoder/setup.py, $FLUMOTION_DIR, $PREAMBLE, "transcoder")
FLUMOTION_SETUP(flumotion/test/setup.py, $FLUMOTION_DIR, $PREAMBLE, "transcoder")
FLUMOTION_SETUP(tests/setup.py, $FLUMOTION_DIR, $PREAMBLE, "transcoder")
FLUMOTION_SETUP(misc/setup.py, $FLUMOTION_DIR, $PREAMBLE, "transcoder")

AC_CONFIG_FILES([env], [chmod +x env])
AC_CONFIG_FILES([bin/flumotion-transcoder-admin], [chmod +x bin/flumotion-transcoder-admin])
AC_CONFIG_FILES([bin/flumotion-transcoder-upgrade], [chmod +x bin/flumotion-transcoder-upgrade])

AC_OUTPUT(
Makefile
bin/Makefile
common/Makefile
conf/Makefile
misc/Makefile
doc/Makefile
transcoder/Makefile
flumotion/Makefile
flumotion/test/Makefile
flumotion/transcoder/Makefile
flumotion/transcoder/manager/Makefile
flumotion/transcoder/tools/Makefile
flumotion/transcoder/admin/Makefile
flumotion/transcoder/admin/datasource/Makefile
flumotion/transcoder/admin/datastore/Makefile
flumotion/transcoder/admin/proxies/Makefile
flumotion/transcoder/admin/context/Makefile
flumotion/component/Makefile
flumotion/component/transcoder/Makefile
flumotion/project/Makefile
flumotion/project/transcoder.py
pkgconfig/Makefile
pkgconfig/flumotion-transcoder.pc
pkgconfig/flumotion-transcoder-uninstalled.pc
tests/Makefile
flumotion-transcoder.spec
)
