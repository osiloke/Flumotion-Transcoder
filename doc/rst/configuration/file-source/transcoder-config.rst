========================
Configure the Transcoder
========================

.. sectnum::

.. contents::

Transcoder Admin Global Data
============================

Quick Start
~~~~~~~~~~~

Copy and modify one of the files:

 - */etc/flumotion/transcoder/transcoder-data.ini*
 - */usr/share/flumotion-transcoder-XXX/examples/transcoder-data.ini*
 - Sub-directory *doc/examples/transcoder-data.ini*
   of the uninstalled transcoder.

Then:

 - Modify the group, and modes for file and directory creation.
 - Modify the activity and customer directories.
 - Modify some default values.


Specifications
~~~~~~~~~~~~~~

Section *HEADER*
----------------

This section contains config file's specific information.

Property *version*
..................

This contains the version of the configuration format.

Must not be modified by hand.

Section *global*
----------------

This section contains global and default values.

Property *customers-dir*
........................

Specifies where the customer definition files are located.

Can be specified as an absolute path or a relative path to the
directory containing the transcoder data file (this one).

This property doesn't have default value and is required.

Usage example::

  customers-dir = /home/file/customers/

Property *activities-dir*
.........................

Specifies the directory where the activity files are stored.

This property doesn't have default value and is required.

Usage example::

  activities-dir = /var/cache/flumotion/transcoder/activities

Property *monitoring-period*
............................

Specifies the default monitoring period in second for all customers.

The monitoring period is the time in second between file system scans.
If a file size do not change between two scans, the file is considered
completely uploaded, and is scheduled to be transcoded.

This mean that the maximum time between a file uploading is finished
and the file is scheduled could be near to two times
the *monitoring-period* value.

If the value is not overridden by a customer configuration,
the specified value will be used or the default value::

  5

Usage example::

  monitoring-period = 60

Property *transcoding-priority*
...............................

Specifies the default priority for transcoding profiles.

The value is an integer between 0 and 999, and define
the relative priority between profiles of a same customer.

If the value is not overridden by a customer configuration,
the specified value will be used or the default value::

  100

Usage example::

  transcoding-priority = 500

Property *transcoding-timeout*
..............................

Specifies the default maximum time in seconds to wait before failing
when the transcoding targets files are not changed and the transcoding
task is not terminated.

This timeout is used to detect when the transcoding sub-system is blocked.

If the value is not overridden by a customer configuration,
the specified value will be used and if not specified
the default value is::

  60

Usage example::

  transcoding-timeout = 120

Property *post-process-timeout*
...............................

Specifies the default maximum time in seconds to wait for a post-processing
to terminate. If this maximum time is reached, the transcoding task fail.

This timeout is used to detect blocked post-processing.

If the value is not overridden by a customer configuration,
the specified value will be used and if not specified
the default value is::

  60

Usage example::

  post-process-timeout = 120

Property *pre-process-timeout*
..............................

Specifies the default maximum time in seconds to wait for a pre-processing
to terminate. If this maximum time is reached, the transcoding task fail.

This timeout is used to detect blocked pre-processing.

If the value is not overridden by a customer configuration,
the specified value will be used and if not specified
the default value is::

  60

Usage example::

  pre-process-timeout = 120

Property *output-media-template*
................................

Specifies the default template to use for generating transcoding targets
output files path, when it's a media target (not a thumbnails target).

The template can contains placeholders that will be substituted.
See `File Path Template`_ for a list of the allowed placeholders.

The result of the substitution will be used as path relative
to profile's outgoing directory.

If the value is not overridden by a customer configuration,
the specified value will be used and if not specified
the default value is::

  %(targetPath)s

Usage example::

  output-media-template = %(targetDir)s%(sourceBasename)s%(targetExtension)s

Property *output-thumb-template*
................................

Specifies the default template to use for generating transcoding targets
output files path, when it's a thumbnail target.

The template can contains placeholders that will be substituted.
See `File Path Template`_ for a list of the allowed placeholders.

The result of the substitution will be used as path relative
to profile's outgoing directory.

If the value is not overridden by a customer configuration,
the specified value will be used and if not specified
the default value is::

  %(targetDir)s%(targetBasename)s.%(index)03d%(targetExtension)s

Usage example::

  output-thumb-template = %(targetDir)s%(sourceBasename)s.%(time)s%(targetExtension)s


Property *link-file-template*
................................

Specifies the default template to use for generating link file path.

The template can contains placeholders that will be substituted.
See `File Path Template`_ for a list of the allowed placeholders.

The result of the substitution will be used as path relative
to profile's outgoing directory.

If the value is not overridden by a customer configuration,
the specified value will be used and if not specified
the default value is::

  %(targetPath)s.link

Usage example::

  link-file-template = links/%(targetPath)s.link

Property *config-file-template*
................................

Specifies the default template to use for generating config file path.

The template can contains placeholders that will be substituted.
See `File Path Template`_ for a list of the allowed placeholders.

The result of the substitution will be used as path relative
to profile's config directory.

If the value is not overridden by a customer configuration,
the specified value will be used and if not specified
the default value is::

  %(sourcePath)s.ini

Usage example::

  config-file-template = %(sourcePath)s.conf

Property *report-file-template*
................................

Specifies the default template to use for generating report file path.

The template can contains placeholders that will be substituted.
See `File Path Template`_ for a list of the allowed placeholders.

The result of the substitution will be used as path relative
to the profile's report directory corresponding to the state
of the transcoding task (*pending*, *done*, *failed*).

If the value is not overridden by a customer configuration,
the specified value will be used and if not specified
the default value is::

  %(sourcePath)s.%(id)s.rep

Usage example::

  report-file-template = %(sourcePath)s.rep

Property *mail-subject-template*
................................

Specifies the default subject template for mail notifications.

The template can contains placeholders that will be substituted.
See `Command and Notification Template`_ for a list of the allowed placeholders.

If the value is not overridden by a customer configuration,
the specified value will be used and if not specified
the default value is::

  %(customerName)s/%(profileName)s transcoding %(trigger)s

Usage example::

  mail-subject-template = Transcodification %(trigger)s

Property *mail-body-template*
.............................

Specifies the default body for notification mails.

The template can contains placeholders that will be substituted.
See `Command and Notification Template`_ for a list of the allowed placeholders.

If the value is not overridden by a customer configuration,
the specified value will be used and if not specified
the default value is::
    
  Transcoding Report
  ==================

  Customer Name: %(customerName)s
  Profile Name:  %(profileName)s
  --------------

    File: '%(inputRelPath)s'
  
    Message: %(errorMessage)s
  
Usage example::

  mail-body-template = 'Report\nFile: %(inputRelPath)s\nMessage: %(errorMessage)s'

Property *mail-timeout*
.......................

Specifies the default maximum time in second to wait for the mail notifications
to succeed. This include the SMTP server name resolving, connection,
and waiting acknowledgment.

If the value is not overridden by a customer configuration,
the specified value will be used and if not specified
the default value is::

  30

Usage example::

  mail-timeout = 60


Property *mail-retry-max*
.........................

Specifies how many times by default the mail-sending process must be
retried before considering it as a failure.

If the value is not overridden by a customer configuration,
the specified value will be used and if not specified
the default value is::

  3

Usage example::

  mail-retry-max = 8

Property *mail-retry-sleep*
...........................

Specifies the default time in second between mail-sending retries.

If the value is not overridden by a customer configuration,
the specified value will be used and if not specified
the default value is::

  60

Usage example::

  mail-retry-sleep = 120


Property *http-request-timeout*
...............................

Specifies the default maximum time in second to wait for
the http request notifications to succeed. This include
the HTTP server name resolution, the connection,
and waiting for the response

If the value is not overridden by a customer configuration,
the specified value will be used and if not specified
the default value is::

  30

Usage example::

  http-request-timeout = 60


Property *http-request-retry-max*
.................................

Specifies how many times by default the http request must be done
before considering it a failure.

If the value is not overridden by a customer configuration,
the specified value will be used and if not specified
the default value is::

  3

Usage example::

  http-request-retry-max = 8

Property *http-request-retry-sleep*
...................................

Specifies the default time in second between http request retries.

If the value is not overridden by a customer configuration,
the specified value will be used and if not specified
the default value is::

  60

Usage example::

  http-request-retry-sleep = 120

Property *sql-timeout*
......................

Specifies the default maximum time in second to wait for
the SQL statement notifications to succeed. 

If the value is not overridden by a customer configuration,
the specified value will be used and if not specified
the default value is::

  30

Usage example::

  sql-timeout = 60


Property *sql-retry-max*
........................

Specifies how many times by default the sql statement notifications
must be tried before considering it a failure.

If the value is not overridden by a customer configuration,
the specified value will be used and if not specified
the default value is::

  3

Usage example::

  sql-retry-max = 8

Property *sql-retry-sleep*
..........................

Specifies the default time in second between SQL statements execution retries.

If the value is not overridden by a customer configuration,
the specified value will be used and if not specified
the default value is::

  60

Usage example::

  sql-retry-sleep = 120

Property *access-force-group*
.............................

Specifies the default group name the files and directories
created by the transcoder must belong to.

If the value is not overridden in customer configuration, 
the specified value will be used, and if not specified,
files and directories' group will not be changed, it will
be left as the system set it by default.

Usage example::

  access-force-group = file

Property *access-force-user*
............................

Specifies the default user name the files and directories
created by the transcoder must belong to.

If the value is not overridden in customer configuration, 
the specified value will be used, and if not specified,
files and directories' user will not be changed, it will
be left as the system set it by default.

Usage example::

  access-force-user = flumotion

Property *access-force-dir-mode*
................................

Specifies the default file mode bits in octal form for
the directories created by the transcoder.

If the value is not overridden in customer configuration,
the specified value will be used, and if not specified,
directories' file mode bits will not be changed, it will
be left as the system set it by default.

Usage example::

  access-force-dir-mode = 0777

Property *access-force-file-mode*
.................................

Specifies the default file mode bits in octal form for
the files created by the transcoder.

If the value is not overridden in customer configuration,
the specified value will be used, and if not specified,
files' file mode bits will not be changed, it will
be left as the system set it by default.

Usage example::

  access-force-file-mode = 0666

Property *discoverer-max-interleave*
....................................

Not used.


Configuration Example
~~~~~~~~~~~~~~~~~~~~~

Example of *transcoder-data.ini* file::

  [HEADER]
  version = 1.1

  [global]
  access-force-group = file
  access-force-dir-mode = 0777
  access-force-file-mode = 0666
  activities-dir = /var/cache/flumotion/transcoder/activities
  customers-dir = customers


.. _`File Path Template`: ../placeholders.rst#file-path-template
.. _`Command and Notification Template`: ../placeholders.rst#command-and-notification-template
