FairShareWaterUsagePiModule
===========================

Prototype for the RaspberryPi Module used to monitor an XBee water usage data network.

This is functioning code for the RaspberryPi to collect data from XBee device nodes attached to water meters. It processes the data to upload corresponding usage information and error messages sent from the devices to a test cloud server.

==========================================================================================================================

Components:

1) serialConnection.py
Imports the PySerial library to create a serial connection between the Raspberry Pi and the water usage monitor node, to allow transmission of data and communication across the two platforms.

2) pymongoClient.py
Imports the PyMongo library to allow access to a test database cloud server using Python. This allows retrieval and uploading of water usage data from and to the cloud server.

3) memcacheClient.py
Imports the Python-Memcached module to allocate local cache memory, which is used to backup important data in the case that Internet connection is temporarily unavailable. The backed up data will be uploaded to the database server once Internet connection is restored.

4) initialSetup.py
Establishes the appropriate environment for the Main Client script to operate. It does so by initializing the default configuration values for this water usage monitoring network, and determining which measurement nodes are part of this particular network, based on its network ID.

5) nodeReplacement.py
Guides the user through the process of replacing a malfunctioning measurement node from an existing water usage monitoring network.

6) networkConfig.py
Manual alternative to changing the configuration settings to the particular water usage network monitored by this RaspberryPi unit. The script guides the user along the way towards completing the desired configuration changes.

7) mainClient.py
The main script which handles all the data collected by the monitor node of a particular water usage monitoring network. It processes all the incoming data and determines where they in the database server. mainClient.py also monitors the status of measurement nodes belonging to its network. If any node ceases to be operational, error data will be uploaded to the database server to notify the user or admin of the error.

========================================================================================================================

Setting Up the Rasberry Pi-Monitor Node environment:

1) Serial Connection

Serial connection needs to be established for successful communication and transmission of data between the monitor XBee device and the Raspberry Pi unit. In order to prevent the Raspberry Pi boot console from occupying the serial port, follow the steps below:

i) Check the content of the command line text file in the boot folder (/boot/cmdline.txt). One may use a built-in text editor such as Nano for the task.

ii) The content command line text file, by default, looks like the following:
dwc_otg.lpm_enable=0 console=ttyAMA0,115200 kgdboc=ttyAMA0,115200 console=tty1 root=/dev/mmcblk0p2 rootfstype=ext4 rootwait
    Check to see that it has been changed to:
dwc_otg.lpm_enable=0 console=tty1 root=/dev/mmcblk0p2 rootfstype=ext4 rootwait

iii) In addition, please check the content of the file /etc/inittab. It should contain the following line:
2:23:respawn:/sbin/getty -L ttyAMA0 115200 vt100
    Please make sure this line is commented out.
    To comment out a line, add a # symbol in front of the line.



2) Installation of required software

Installation of PySerial:
The PySerial module needs to be installed. It provides backends for Python to access the serial port. To check that PySerial has been installed, run the following command at the command line or in LXTerminal:

sudo apt-get install python-serial

You will be notified if this application has been installed or not. Follow the instructions to complete the procedure if PySerial has not been installed yet.


Installation of PyMongo:
The PyMongo module needs to be installed. PyMongo is a Python distribution containing tools for working with MongoDB, the database system the monitoring network employs to store water usage data. To check that PyMongo has been installed, run the following command at the command line or in LXTerminal:

sudo pip install pymongo

You will be notified if this application has been installed or not. Follow the instructions to complete the procedure if PyMongo has not been installed yet.


Installation of Python-memcached:
The Python-memcached module is a Python-based API for communicating with the Memcached distributed memory object cache daemon. This is needed to provide backup storage for crucial data that have failed to upload to the database server due to loss of internet connection or poor connectivity. To check that Python-memcached has been installed, run the following command at the command or in LXTerminal:

sudo apt-get install python-memcache

You will be notified if this application has been installed or not. Follow the instructions to complete the procedure if Python-memcached has not been installed yet.
