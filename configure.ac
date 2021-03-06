AC_INIT(flumotion-transcoder, m4_esyscmd([ test -z "$VERSION" && VERSION=0.11.0.1;
                              common/version-gen $VERSION .tarball-version]),
   [flumotion-devel@lists.fluendo.com],
   [flumotion-transcoder], [http://www.flumotion.net/])

AM_INIT_AUTOMAKE([-Wno-portability])

AS_VERSION
AC_SUBST(PACKAGE_VERSION_SPEC, `echo $VERSION | tr '-' '_'`)
AS_NANO

AC_SUBST_FILE(AUTHORS)
AUTHORS=$srcdir/AUTHORS

AC_SUBST(FLU_REQ, 0.10.0)
AC_SUBST(INHOUSE_REQ, 0.10.0)

dnl Start commit used to autogenrate ChangeLog from 'git log'
AC_SUBST(GIT_LOG_START_COMMIT, "75f3054ffc9195f7aeed251d09486c2482632656")

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
PKG_CHECK_MODULES(FLUMOTION, flumotion >= $FLU_REQ)
FLUMOTION_DIR="`$PKG_CONFIG --variable=flumotiondir flumotion`"
AC_MSG_NOTICE([Flumotion code base directory is $FLUMOTION_DIR])
AC_SUBST(FLUMOTION_DIR)

dnl check for flumotion-inhouse library
PKG_CHECK_MODULES(INHOUSE, flumotion-inhouse >= $INHOUSE_REQ)
INHOUSE_DIR="`$PKG_CONFIG --variable=flumotioninhousedir flumotion-inhouse`"
AC_MSG_NOTICE([Flumotion in-house library directory is $INHOUSE_DIR])
AC_SUBST(INHOUSE_DIR)

dnl check for MySQL-python
AS_PYTHON_IMPORT(MySQLdb,,AC_MSG_ERROR([MySQL-python not found]),,)

dnl output stuff
PREAMBLE=`cat $srcdir/misc/preamble.py`
FLUMOTION_SETUP(transcoder/setup.py, $FLUMOTION_DIR, $PREAMBLE, "transcoder")
FLUMOTION_SETUP(flumotion/test/setup.py, $FLUMOTION_DIR, $PREAMBLE, "transcoder")
FLUMOTION_SETUP(tests/setup.py, $FLUMOTION_DIR, $PREAMBLE, "transcoder")
FLUMOTION_SETUP(misc/setup.py, $FLUMOTION_DIR, $PREAMBLE, "transcoder")

AC_CONFIG_FILES([env], [chmod +x env])
AC_CONFIG_FILES([bin/flumotion-transcoder-admin], [chmod +x bin/flumotion-transcoder-admin])
AC_CONFIG_FILES([bin/flumotion-transcoder-upgrade], [chmod +x bin/flumotion-transcoder-upgrade])
AC_CONFIG_FILES([bin/flumotion-progressive-move], [chmod +x bin/flumotion-progressive-move])
AC_CONFIG_FILES([bin/flumotion-transcoder-qos], [chmod +x bin/flumotion-transcoder-qos])
AC_CONFIG_FILES([bin/flumotion-transcoder-remux], [chmod +x bin/flumotion-transcoder-remux])

AC_OUTPUT(
Makefile
bin/Makefile
common/Makefile
conf/Makefile
misc/Makefile
doc/Makefile
data/Makefile
data/database/Makefile
data/database/mysql/Makefile
transcoder/Makefile
flumotion/Makefile
flumotion/test/Makefile
flumotion/transcoder/Makefile
flumotion/transcoder/manager/Makefile
flumotion/transcoder/tools/Makefile
flumotion/transcoder/admin/Makefile
flumotion/transcoder/admin/datasource/Makefile
flumotion/transcoder/admin/datastore/Makefile
flumotion/transcoder/admin/property/Makefile
flumotion/transcoder/admin/proxy/Makefile
flumotion/transcoder/admin/context/Makefile
flumotion/transcoder/admin/api/Makefile
flumotion/transcoder/admin/api/mediums/Makefile
flumotion/component/Makefile
flumotion/component/transcoder/Makefile
flumotion/component/monitor/Makefile
flumotion/component/joiner/Makefile
flumotion/ovp/Makefile
flumotion/project/Makefile
flumotion/project/transcoder.py
pkgconfig/Makefile
pkgconfig/flumotion-transcoder.pc
pkgconfig/flumotion-transcoder-uninstalled.pc
tests/Makefile
flumotion-transcoder.spec
)

echo
echo "    $PACKAGE_STRING ($PACKAGE_VERSION_RELEASE)"
echo
echo "    pychecker:              $PYCHECKER"
echo "    epydoc:                 $EPYDOC"
echo
echo "Now type \"make\" to build flumotion"
