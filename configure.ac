AC_INIT(README)

AS_VERSION(flumotion-transcoder, FLUTRANS, 0, 0, 2, 1)
AC_SUBST(RELEASE, $FLUTRANS_RELEASE)

AC_SUBST_FILE(AUTHORS)
AUTHORS=$srcdir/AUTHORS

AC_SUBST(PYGTK_010_REQ, 2.6.3)
AC_SUBST(GST_010_REQ, 0.10.0.1)
AC_SUBST(FLUMOTION_REQ, 0.3.1)

AM_INIT_AUTOMAKE($PACKAGE, $VERSION)

dnl Add parameters for aclocal
AC_SUBST(ACLOCAL_AMFLAGS, "-I m4 -I common")

AS_AC_EXPAND(LIBDIR, $libdir)
AC_MSG_NOTICE(Storing library files in $LIBDIR)

AC_PROG_CC

dnl check for python
AS_PATH_PYTHON(2.3)

dnl check for GStreamer
PKG_CHECK_MODULES(GST_010, gstreamer-0.10 >= $GST_010_REQ,
    [GST_010_SUPPORTED=yes], [AC_MSG_RESULT([$GST_010_PKG_ERRORS]); GST_010_SUPPORTED=no])

if test $GST_010_SUPPORTED = "no"; then
  AC_MSG_ERROR([No GStreamer development packages found.
Please install GStreamer development packages for version 0.10.
Also, check your PKG_CONFIG_PATH.])
fi  

dnl check for GLIB
PKG_CHECK_MODULES(GLIB, glib-2.0)

export PYTHONPATH=$PYGTK_DIR:$PYTHONPATH
PKG_CHECK_MODULES(PYGTK, pygtk-2.0 >= $PYGTK_010_REQ)
PYGTK_DIR="`$PKG_CONFIG --variable=pyexecdir pygtk-2.0`"
AC_SUBST(PYGTK_DIR)
AC_MSG_NOTICE(Using pygtk installed in $PYGTK_DIR)
PYGTK_VERSION="`$PKG_CONFIG --modversion pygtk-2.0`"

if test "x$PYGTK_VERSION" = "x2.5.2"
then
  AC_MSG_ERROR([PyGTK 2.5.2 contains known bugs, please install other version])
fi

dnl check for flumotion
PKG_CHECK_MODULES(FLUMOTION, flumotion >= $FLUMOTION_REQ)
FLUMOTION_DIR="`$PKG_CONFIG --variable=flumotiondir flumotion`"
AC_MSG_NOTICE([Flumotion code base directory is $FLUMOTION_DIR])
AC_SUBST(FLUMOTION_DIR)

dnl check for pychecker
AC_CHECK_PROG(PYCHECKER, pychecker, yes, no)
AM_CONDITIONAL(HAVE_PYCHECKER, test "x$PYCHECKER" = "xyes")

dnl output stuff
PREAMBLE=`cat $srcdir/misc/preamble.py`
FLUMOTION_SETUP(transcoder/setup.py, $FLUMOTION_DIR, $PREAMBLE, "transcoder")
FLUMOTION_SETUP(flumotion/test/setup.py, $FLUMOTION_DIR, $PREAMBLE, "transcoder")
FLUMOTION_SETUP(tests/setup.py, $FLUMOTION_DIR, $PREAMBLE, "transcoder")
FLUMOTION_SETUP(misc/setup.py, $FLUMOTION_DIR, $PREAMBLE, "transcoder")

AC_CONFIG_FILES([bin/flumotion-transcoder], [chmod +x bin/flumotion-transcoder])
AC_CONFIG_FILES([bin/flumotion-transcoder-job], [chmod +x bin/flumotion-transcoder-job])
AC_OUTPUT(
Makefile
src/Makefile
bin/Makefile
common/Makefile
conf/Makefile
misc/Makefile
transcoder/Makefile
flumotion/Makefile
flumotion/test/Makefile
flumotion/transcoder/Makefile
tests/Makefile
flumotion-transcoder.spec
)
