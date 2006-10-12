AC_INIT(README)

AS_VERSION(flumotion-transcoder, FLUTRANS, 0, 0, 1, 1)
AC_SUBST(RELEASE, $FLUTRANS_RELEASE)

AC_SUBST_FILE(AUTHORS)
AUTHORS=$srcdir/AUTHORS

AC_SUBST(PYGTK_010_REQ, 2.6.3)
AC_SUBST(PYGST_010_REQ, 0.10.0)
AC_SUBST(GST_010_REQ, 0.10.0.1)
AC_SUBST(FLUMOTION_REQ, 0.3.1)

AM_INIT_AUTOMAKE($PACKAGE, $VERSION)

dnl Add parameters for aclocal
AC_SUBST(ACLOCAL_AMFLAGS, "-I m4 -I common")

AS_AC_EXPAND(LIBDIR, $libdir)
AC_MSG_NOTICE(Storing library files in $LIBDIR)

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

dnl checks for gst-python
if test $GST_010_SUPPORTED = "yes"; then
  PKG_CHECK_MODULES(PYGST_010, gst-python-0.10 >= $PYGST_010_REQ,
      [PYGST_010_DIR="`$PKG_CONFIG --variable=pyexecdir gst-python-0.10`"
       AC_SUBST(PYGST_010_DIR)
       AC_MSG_NOTICE(Using gstreamer-python 0.10 installed in $PYGST_010_DIR)],
      [AC_MSG_RESULT([$PYGST_010_PKG_ERRORS])
       GST_010_SUPPORTED=no])

  if test $GST_010_SUPPORTED = "yes"; then
    saved_PYTHONPATH=$PYTHONPATH
    export PYTHONPATH=$PYGST_010_DIR:$PYTHONPATH
    AS_PYTHON_IMPORT([gst],,
                     [AC_MSG_NOTICE([Unable to import gst-python 0.10 -- check your PYTHONPATH?])
                      GST_010_SUPPORTED=no],
                     [import pygst; pygst.require('0.10')],
                     [assert gst.pygst_version[[1]] == 10 or (gst.pygst_version[[1]] == 9 and gst.pygst_version[[2]] >= 7)])

  fi
fi

if test $GST_010_SUPPORTED = "no"; then
  AC_MSG_ERROR([No suitable gstreamer-python versions found. Correct the above
errors and try again.])
fi  

AC_SUBST(GST_010_SUPPORTED)

FLU_PKG_CONFIG_REQUIRES="gstreamer-0.10 >= $GST_010_REQ"
AC_SUBST(FLU_PKG_CONFIG_REQUIRES)

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

AC_CONFIG_FILES([bin/flumotion-transcoder], [chmod +x bin/flumotion-transcoder])
AC_OUTPUT(
Makefile
bin/Makefile
common/Makefile
conf/Makefile
misc/Makefile
transcoder/Makefile
flumotion/Makefile
flumotion/transcoder/Makefile
flumotion-transcoder.spec
)
