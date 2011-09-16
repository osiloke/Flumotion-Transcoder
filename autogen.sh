#!/bin/sh
set -x

# Make sure we have common
if test ! -f common/flumotion-trial;
  then
  echo "+ Setting up common submodule"
  git submodule init
fi
git submodule update

# source helper functions
if test ! -f common/flumotion-trial;
  then
  echo There is something wrong with your source tree.
  echo You are missing common/flumotion-trial
  exit 1
fi

aclocal -I common || exit 1
# libtoolize --force || exit 1
# autoheader || exit 1
autoconf || exit 1
automake -a || exit 1
echo "./autogen.sh $@" > autoregen.sh
chmod +x autoregen.sh
./configure $@
