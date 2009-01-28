=======================================
Configure the Transcoder Administration
=======================================

.. sectnum::

.. contents::

------------------------------
Transcoder Admin Configuration
------------------------------

Quick Start
~~~~~~~~~~~

Copy and modify one of the files:

 - */etc/flumotion/transcoder/transcoder-admin.ini*
 - */usr/share/flumotion-transcoder-XXX/examples/transcoder-admin.ini*
 - Sub-directory *doc/examples/transcoder-admin.ini*
   of the uninstalled transcoder.

Then:

 - Set the file system roots for the admin.
 - Set the notification email addresses and recipients.
 - Set the manager host and port.
 - Set the manager credentials.
 - Set the default worker file system roots, 
   max concurrent task count and max failed job.
 - Set specific worker overrides.

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

This section contains generic parameters for the transcoder.

Property *debug*
................

Overrides the debug level of the transcoder administration.
It uses the same format as the **-d** command line option.

If not specified, the value will be taken from command line
or service configuration.

Usage example::

  debug = 4,scheduler:5

Property *transcoder-label-template*
....................................

specifies the template used in generating the transcoding components labels.

It's a string that can contains placeholders,
see `Component and Activity Name Template`_.

If not specified, the default value is::

  %(customerName)s/%(profileName)s:%(sourcePath)s

Usage example::

  transcoder-label-template = File %(sourceFile)s for %(customerName)s

Property *monitor-label-template*
.................................

Specifies the template used in generating the monitoring components labels.

It's a string that can contains placeholders,
see `Component and Activity Name Template`_.

If not specified, the default value is::

  Monitor for %(customerName)s

Usage example::

  monitor-label-template = %(customerName)s's Monitor

Property *activity-label-template*
..................................

Specifies the template used in generating the scheduler activities labels.

It's a string that can contains placeholders,
see `Component and Activity Name Template`_.

If not specified, the default value is::

  %(customerName)s/%(profileName)s:%(sourcePath)s

Usage example::

  activity-label-template = %(customername)s's Activity for %(sourceFile)s

Section *admin*
---------------

This section contains the configuration specific to the transcoder
administration.

Properties *roots*
..................

The *roots* properties are use to specify the virtual mount points for
the transcoder admin. The principal root is *default* that specify
the base directory for customer files.

This property does not have default value and is required.

Usage example::

  roots#default = /home/file/

Sub-Section *admin:data-source*
-------------------------------

This sub-section of the transcoder administration configuration
is used to configure the datasource from where the configuration
is retrieved.

For now, only the file datasource is supported.

Property *data-file*
....................

Specifies where the file containing the transcoder data is located.

This property does not have default value, and is required.

Usage example::

  data-file = /etc/flumotion/transcoder/transcoder-data.ini

Sub-Section *admin:reports-data-source*
---------------------------------------

This sub-section of the transcoder administration configuration
is used to configure the datasource in which the transcoder
reports are stored.

For now, only the sql datasource is supported.

Property *connection-info*
..........................

Specifies the database connection string. For now, only MySQL databases are
supported. The connection string should be of the form::

  mysql://<user>:<password>@<host>:<port>/<database>

This property does not have default value, and is required.

Usage example::

  connection-info = mysql://transcoder:transcoderpass@database03.priv:3306/transcoder

Sub-Section *admin:notifier*
............................

This sub-section of the transcoder administration configuration
is used to set notification related properties.

Property *smtp-server*
......................

Specifies the address of the SMTP server used to send emails.

This property doesn't have default values, and is required.

Usage example::

    smtp-server = mail.fluendo.com

Property *smtp-port*
....................

Specifies the IP port number to use with the SMTP server.

If not specified, the default value is::

  25

Usage example::

  smtp-port = 42

Property *smtp-require-tls*
...........................

Specifies if an encrypted channel should be used
to communicate with the SMTP server.

If not specified, the default value is::

  True

Usage example::

  smtp-require-tls = False

Property *smtp-username*
........................

If the SMTP server require authentication,
this property is used to specify the user name.

If not specified, no authentication will be done when using the SMTP server.

Usage example::

  smtp-username = user

Property *smtp-password*
........................

If the SMTP server require authentication,
this property is used to specify the password.

Usage example::

  smtp-password = test

Property *mail-notify-sender*
.............................

Specifies the email address to use for the sender of the notification emails.

The email can be specified on its own, or a human-readable
name followed by the email address in quoted inside **<** and **>**.

This property doesn't have default value and is required.

Usage example::

  mail-notify-sender = Transcoder Notifications <notifications@flumotion.com>

Property *mail-emergency-sender*
................................

Specifies the email address to use for the sender of the emergency emails.

The email can be specified on its own, or a human-readable
name followed by the email address in quoted inside **<** and **>**.

This property doesn't have default value and is required.

Usage example::

  mail-emergency-sender = Transcoder Emergencies <emergencies@flumotion.com>

Property *mail-emergency-recipients*
....................................

Specifies the email addresses the emergency emails have to be send to.

Emails addresses are separated by a commas, and email can be specified
on its own, or as a human-readable name followed by the email address
quoted inside **<** and **>**.

This property does not have default value, and at least one email is required.

Usage example::

  mail-emergency-recipients = Test <test@flumotion.com>, admin@flumotion.com

Property *mail-debug-sender*
............................

Specifies the email address to use for the sender of the debug emails.

The email can be specified on its own, or a human-readable
name can be specified followed by the email address in **< >**.

This property does not have default value and is required.

Usage example::

  mail-debug-sender = Transcoder Debug <debug@flumotion.com>

Property *mail-debug-recipients*
................................

Specifies the email addresses the debug emails have to be send to.

Emails addresses are separated by a commas, and email can be specified
on its own, or as a human-readable name followed by the email address
quoted inside **<** and **>**.

This property doesn't have default value, and at least one email is required.

Usage example::

  mail-debug-recipients = debug <debug@flumotion.com>, admin@flumotion.com

Sub-Section *admin:api*
-----------------------

This section contains the properties to configure the administration API.

Property *host*
...............

Specifies the address to listen for API connections.

If not specified, the default value is::

  localhost

Usage example::

  host = admin1.bcn.flumotion.net

Property *port*
...............

Specifies the IP port number the API is listening for connections.

If not specified, the default value is::

  7600

Usage example::

  port = 7676

Property *use-ssl*
..................

Specifies if SSL should be use to encrypt connections to the API.

If not specified, the default value is::

  True

Usage example::

  use-ssl = False

Property *certificate*
......................

Specifies the SSL certificate to use. The certificate
must contains a private key.

It can be specified as an absolute path, or relative to */etc/flumotion*.

If not specified, the default value is::

  default.pem

Usage example::

  certificate = transcoder.pem


Sub-Section *admin:api:bouncer*
-------------------------------

This sub-section of admin api configuration, is used
to configure the bouncer used to authenticate the API connections.

Property *type*
...............

Specifies the bouncer type. The supported types are:

+--------------------+-------------------------------------------------+
|Bouncer Type        |Description                                      |
+====================+=================================================+
|salted-sha256       |Users are specified as a dictionary of salt/hash |
|                    |pairs where *hash = SHA256(salt+password)*       |
+--------------------+-------------------------------------------------+

If not specified, the default value is::

  salted-sha256

Usage example::

  type = salted-sha256

Properties *users*
..................

For each user, a users property should be added with the user name
as property sub-name, and a bouncer-dependent value.

Value format by bouncer types:

+--------------------+-----------------------------------------------------------------------+
|Bouncer Type        |Value Format                                                           |
+====================+=======================================================================+
|salted-sha256       |*salt + ':' + SHA256(salt + password).encode('hex')*                   |
|                    |For example, for a salt 'spam' and password 'bacon'                    |
|                    |the value would be:                                                    |
|                    |*spam:1f16e7daa5261b78f64e01d4904e7eb5aa78aa09c4e9a8efb33a93913757d96b*|
+--------------------+-----------------------------------------------------------------------+

At least one user must be specified to be able to connect to the API.

Usage example::

  users#beans = spam:1f16e7daa5261b78f64e01d4904e7eb5aa78aa09c4e9a8efb33a93913757d96b
  users#test = salt:1bc1a361f17092bc7af4b2f82bf9194ea9ee2ca49eb2e53e39f555bc1eeaed74

Sub-Section *admin:diagnosis*
-----------------------------

This sub-section of admin configuration is used
to configure the diagnosis file with definitions of files that certainly will
fail the transcoding (e.g. text files, empty files).

Property *diagnosis-file*
.........................

Specifies the diagnosis file. The file should contain information on how to
identify files that certainly will fail when transcoded.

This property doesn't have default value and is required.

Usage example::

  diagnosis-file = /etc/flumotion/transcoder/diagnosis.conf

Section *manager*
-----------------

This section groups the manager related properties.

Property *host*
...............

Specifies the host name of the flumotion manager the admin must connect to.

This property doesn't have default value and is required.

Usage example::

  host = manager.bcn.fluendo.net

Property *port*
...............

Specifies the IP port number the manager is listening to.

This property doesn't have default value and is required.

Usage example::

  port = 7632

Property *username*
...................

Specifies the user name to use for manager authentication.

This property doesn't have default value and is required.

Usage example::

  username = user

Property *password*
...................

Specifies the password to use for manager authentication.

This property doesn't have default value and is required.

Usage example::

  password = test

Property *use-ssl*
..................

Specifies if SSL should be used to encrypt the communication
between the transcoder admin and the flumotion manager.

If not specified, the default value is::

  False

Usage example::

  use-ssl = True

Section *worker-defaults* and *workers* sections
------------------------------------------------

The *worker-defaults* section is used to specify default values
for all workers, and these values can be overridden for each
workers by adding a sub section of section *workers* with the
name of the worker.

for example if the property *max-task* is set to 2 in the section
*worker-defaults*, but there is a section named *workers:mananger.dev*
with a property *max-task* of 1, all workers will start at most 2
simultaneous transcoding minus the worker named *manager.dev* that
will only start at most 1 transcoding component.

The properties are the same for the section *worker-defaults*
and the worker-specific sections.

Properties *roots*
..................

Specifies the virtual directory mount point for a worker.
these mount points will be used when converting between virtual
path and local path, and at least *default* and *temp* roots must be specified.

Usage example::

  roots#default = /home/file/
  roots#temp = /var/tmp/flumotion/transcoder/

Property *max-task*
...................

Specifies the maximum amount of simultaneous transcoding component to be
executed on a worker.

Note that the monitor component and sad transcoder components
are not counted as a running component event if a running process still
exists for that component.

If not specified, the default value is::

 1

Usage example::

 max-task = 3

Property *max-keep-failed*
..........................

Specifies the maximum amount of sad transcoder components to keep on a worker.

This is used to prevent a lots of failure to take too much worker resources
by staying in memory.

When a transcoder goes sad and there already is the maximum amount
of sad component, the oldest one to goes sad is stopped and deleted.

If not specified, the default value is::

  5

Usage example::

 max-keep-failed = 3

Property *gst-debug*
....................

Not yet implemented.


Configuration Example
~~~~~~~~~~~~~~~~~~~~~

Example of *transcoder-admin.ini* file::

  [HEADER]
  version = 1.0

  [global]

  [admin]
  roots#default = /home/file

  [admin:data-source]
  data-file = /etc/flumotion/transcoder/transcoder-data.ini

  [admin:reports-data-source]
  connection-info = mysql://transcoder:transcoderpass@database03.priv:3306/transcoder

  [admin:api]
  host = localhost
  port = 7600
  use-ssl = True
  certificate = default.pem

  [admin:api:bouncer]
  type = salted-sha256
  users#user = salt:1bc1a361f17092bc7af4b2f82bf9194ea9ee2ca49eb2e53e39f555bc1eeaed74

  [admin:notifier]
  mail-debug-recipients = sebastien@fluendo.com
  mail-debug-sender = Transcoder Debug <transcoder-debug@fluendo.com>
  mail-emergency-recipients = sebastien@fluendo.com, transcode@flumotion.com
  mail-emergency-sender = Transcoder Emergency <transcoder-emergency@fluendo.com>
  mail-notify-sender = Transcoder Admin <transcoder-notify@fluendo.com>
  smtp-server = mail.fluendo.com
  smtp-port = 2525
  #smtp-require-tls = True
  #smtp-username =
  #smtp-password =

  [admin:diagnosis]
  diagnosis-file = /etc/flumotion/transcoder/diagnosis.conf

  [manager]
  host = manager.dev
  username = user
  password = test
  port = 7632
  use-ssl = True
  #certificate = 

  [worker-defaults]
  max-task = 2
  max-keep-failed = 4
  roots#default = /home/file/v2/
  roots#temp = /var/tmp/flumotion/transcoder/

  # Specific Worker Overrides
  [workers:repeater.dev]
  max-task = 1
  roots#default = /mnt/transcoder/file

---------------------
Transcoder Admin Data
---------------------

The transcoding configuration data can come from different sources:

File Data Source
~~~~~~~~~~~~~~~~

  The file datasource have a main configuration file *transcoder-data.ini*,
  and a list of customer configuration files usually in a sub-directory named *customers*.

  `Global configuration file`_.

  `Customer configuration files`_.

Database Data Source
~~~~~~~~~~~~~~~~~~~~

  Not implemented yet.

.. _`Global configuration file`: file-source/transcoder-config.rst
.. _`Customer configuration files`: file-source/customer-config.rst
.. _`Component and Activity Name Template`: placeholders.rst#component-and-activity-name-template
