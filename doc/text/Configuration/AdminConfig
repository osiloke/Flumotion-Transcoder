================================
Flumotion Transcoder Instalation
================================

Configure the Transcoder Administration
=======================================

System Configuration
--------------------

Edit the file ``/etc/flumotion/transcoder/transcoder-admin.ini``:

 - Set the filesystem roots for the admin.
 - Set the notification email addresses and recipients.
 - Set the manager host and port.
 - Set the manager credentials.
 - Set the default worker file system roots, 
   max concurent task count and max failed job.
 - Set specific worker overrides.
   
Example of *transcoder-admin.ini* file::

  [HEADER]
  version = 1.0
  
  [global]
  
  [admin]
  roots#default = /home/file
  
  [admin:data-source]
  data-file = /etc/flumotion/transcoder/transcoder-data.ini
  
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

Transcoding Configuration
-------------------------

The transcoding configuration can come from different sources:

File Data Source
................
  
  The file datasource have a main configuration file *transcoder-data.ini*,
  and a list of customer configuration files usualy in a sub-directory named *customers*.
  
  `Global configuration file`_.

  `Customer configuration files`_.

Database Data Source
....................

  Not implemented yet.

.. _`Global configuration file`: TransFileConfig
.. _`Customer configuration files`: CustomerFileConfig
