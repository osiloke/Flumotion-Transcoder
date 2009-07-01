===============================================
Flumotion Transcoder Nagios Alert Configuration
===============================================

Requirements
------------

 * <customer> : Customer name as show in /home/file/
 * <subdirectory> : The transcodification subdirectory inside the incoming directory of the customer
 * <encoder_name> : The name of the encoder in which the transcoder is running
 * <alert_time> : Minutes before a file is considered out of transcodification time (normally 120)

Nagios 3.x
==========

 1. Log into monitor01.bcn.fluendo.net
 2. Edit the file ``/etc/nagios/objects/integration/services/services.cfg``
 3. Add an entry such as the one below::

    define service{
        use                     support-service
        service_description     transcoder <customer> <subdirectory>
        host_name               <encoder_name>
        check_command           check_recursive_age!/home/file/<customer>/files/incoming/<subdirectory>!<alert_time>
    }


 Example::

    define service{
        use                     support-service
        service_description     transcoder cope transcode32
        host_name               encoder026.p4.bt.bcn
        check_command           check_recursive_age!/home/file/cope/files/incoming/transcode32!120
    }


Nagios 2.x
==========

 1. Log into se01.bcn.fluendo.net
 2. Edit the file ``/etc/nagios/services.cfg``
 3. Add an entry such as the one below::

    define service{
        use                     support-service
        service_description     transcoder <customer> <subdirectory>
        host_name               <encoder_name>
        check_command           check_recursive_age!/home/file/<customer>/files/incoming/<subdirectory>!<alert_time>
    }


 Example::

    define service{
        use                     support-service
        service_description     transcoder cope transcode32
        host_name               ^encoder026.p4$
        check_command           check_recursive_age!/home/file/cope/files/incoming/transcode32!120
    }


