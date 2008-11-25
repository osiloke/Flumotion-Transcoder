================================
Flumotion Transcoder Instalation
================================

Running an Installed Transcoder
===============================

Install the Transcoder
----------------------

On the admin machine and the manager machine (could be the same machine),
the transcoder should be installed. For this you could:

Install from source::

  $ make install
  
Or install from packages::

  $ yum install flumotion-transcoder

This is only needed for the manager and admin machin, but could be usfull
on workers' machine too to be able to use flumotion-launch during dignostics.

Transcoding Manager
-------------------

Edit the file ``/etc/flumotion/managers/transcoder/planet.xml`` if needed to:

  - Restrict the network interfaces to listen to.
  - Change/Set the debug level.
  - Change default credentials to log in the manager.
  
Example of manager configuration file::

	<planet>
	    <manager name="transcoder">
	        <!-- host>localhost</host -->
	        <debug>4</debug>
	        <port>7632</port>
	        <transport>ssl</transport>
	        <!-- certificate>default.pem</certificate -->
	        <component name="manager-bouncer" type="htpasswdcrypt-bouncer">
	            <property name="data"><![CDATA[user:PSfNpHTkpTx1M]]></property>
	        </component>
	        <plugs>
	            <plug socket="flumotion.component.plugs.lifecycle.ManagerLifecycle"
	                type="transcoder-environment">
	            </plug>
	        </plugs>
	    </manager>
	</planet>

Start the transcoding manager with the standard flumotion service script::

  $ service flumotion start manager transcoder

Transcoding Workers
-------------------

On each machines where a transcoding worker should run, copy the configuration
file example ``/usr/share/doc/flumotion-transcoder-X.X.X.X/examples/workers/transcoder.xml``
to ``/etc/flumotion/workers''.

Edit the copied file:

  - Set the debug level.
  - Set the transcoding manager host and port.
  - Set the credentials to use to log in the manager.

Example of worker configuration file::

	<worker name="trans-worker">
	    <!-- debug>4</debug -->
        <manager>
            <host>manager.dev.fluendo.lan</host>
            <port>7632</port>
            <transport>ssl</transport>
            <!-- certificate>default.pem</certificate -->
        </manager>
        <authentication type="plaintext">
            <username>user</username>
            <password>test</password>
        </authentication>
        <!-- feederports></feederports -->
	</worker>


Start the transcoding workers with the standard flumotion service script::

  $ service flumotion start worker transcoder

Transcoder Administration
-------------------------

First, :trac:`wiki:Transcoder/Documentation/Configuration/AdminConfig configure the transcoder administration`.

Modify the *sysconfig* file ``/etc/sysconfig/flumotion-transcoder-admin`` if needed.

Start the transcoder administration::

  $ service flumotion-transcoder-admin start
  
