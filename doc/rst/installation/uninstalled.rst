================================
Flumotion Transcoder Instalation
================================

Running an Uninstalled Transcoder
=================================

Uninstalled Environment
-----------------------

If the transcoder is not installed on the admin and manager machine,
the environment should be setup to use an uninstalled version.
This is done sourcing the script ``bin/transcoder-uninstalled-environment``
with the version of the transcoder to use as parameter (default to trunk).
This script will look for the environment variable *TRANSCODER_BASE*
to know where are the differents versions of the transcoder,
if not defined, it will look for the environment variable *WORKSPACE*
and deduce *TRANSCODER_BASE* as ``$WORKSPACE/flumotion/transcoder``,
and if *WORKSPACE* is not define ``$HOME/workspace/flumotion/transcoder``
will be used. The version specified as parameter of the script should be
a sub-directory of *TRANSCODER_BASE*, and if not specified trunk is assumed.
The prompt will be modified to remember the current environment.

**THIS SCRIPT SHOULD BE SOURCED AND WILL NOT START A NEW SHELL.**

To use the uninstalled version in ``$TRANSCODER_BASE/trunk``::

  $ . bin/transcoder-uninstalled-environment
  [TRANS] $
  
To use the uninstalled version in ``$TRANSCODER_BASE/test``::

  $ . bin/transcoder-uninstalled-environment test
  [TRANS test] $

Transcoding Manager
-------------------

The transcoding manager should load the plug *transcoder-environment*.
For an example of configuration see ``conf/managers/transcoder/planet.xml``
The transcoder should be installed on the manager machine,
or an uninstalled environment should be setup (see before).

Start a manager with debug logging::

  $ . bin/transcoder-uninstalled-environment
  [TRANS] $ flumotion-manager -d 4 -T tcp -H manager.dev -P 7632 \
  > -n transcoder conf/managers/transcoder/planet.xml

Transcoding Workers
-------------------

The transcoding workers are independent of the transcoding installation.
The transcoder do not have to be installed on the workers' machines,
and the uninstalled environment is not needed.

**WORKERS MUST HAVE DIFFERENT NAMES.**

Start a worker with debug logging::

  $ flumotion-worker -d 4 -T tcp -H manager.dev -P 7632 -n worker1 \
  > -u user -p test

Transcoder Administration
-------------------------

The transcoder admin machine need the transcoder to be installed,
or the uninstalled environment to be setup properly.
It need a configuration file (typically named *transcoder-admin.ini*).
For an example of configuration see ``conf/transcoder/transcoder-admin.ini``
For more information about transcoder configuration,
see section 3 of ``doc/specification.odt``.

**NOTE THAT THE CONFIGURATION EXAMPLE SHOULD BE MODIFIED TO WORK.**

So first, :trac:`wiki:Transcoder/Documentation/Configuration/AdminConfig configure the transcoder administration`.

Start the transcoder admin with debug logging::

  $ . bin/transcoder-uninstalled-environment
  [TRANS] $ bin/flumotion-transcoder-admin -d 4 conf/transcoder/transcoder-admin.ini
