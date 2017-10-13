..
       # Copyright 2017 Intel Research and Development Ireland Limited
       # *************************************************************
       # This file is part of OSM Monitoring module
       # All Rights Reserved to Intel Corporation
       #
       # Licensed under the Apache License, Version 2.0 (the "License"); you
       # may not use this file except in compliance with the License. You may
       # obtain a copy of the License at
       #
       #         http://www.apache.org/licenses/LICENSE-2.0
       #
       # Unless required by applicable law or agreed to in writing, software
       # distributed under the License is distributed on an "AS IS" BASIS,
       # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
       # implied. See the License for the specific language governing
       # permissions and limitations under the License.
       #
       # For those usages not covered by the Apache License, Version 2.0 please
       # contact: helena.mcgough@intel.com or adrian.hoban@intel.com

OSM MON module
**************
This is a guide for using the OSM MON module source code to create a container
for monitoring. It will allow the use of the three plugins available to the
module; CloudWatch, OpenStack and vROPs.


At the moment this process requires a number of steps, but in the future the
process will become automated as it will become part of the osm installation
script which is contained within the devops repo.
: `</devops/installers/install_mon.sh>`


For information on how to use this module refer to this usage guide:
: `</MON/doc/MON_usage_guide.rst>`


You can find the source code for MON by following the link below:
https://osm.etsi.org/gitweb/?p=osm/MON.git;a=tree


Requirements
------------
* lxc setup
* OSM deployment


Creating a MON Container
------------------------
To create a MON container and utilize the supported functionality, clone the
MON repo and then run the provided script for container creation and
installation:

    ::

        git clone https://osm.etsi.org/gerrit/osm/MON.git
        cd MON/scripts
        . install_mon.sh

This script will create a MON container, install all of the required packages,
as well as initializing the Apache Kafka and the vROPs web service.


Plugin Utilization
------------------
There are three plugins supported by this monitoring module; CloudWatch,
OpenStack and vROPs.

vROPs plugin
~~~~~~~~~~~~
The vROPs plugin will automatically be installed after you have run the above
installation script.

OpenStack Plugin
~~~~~~~~~~~~~~~~
There are two OpenStack services supported within this module monitoring and
alarming, which are supported by the Gnocchi and Aodh plugins respectively.

For more information on what metrics and alarms that these plugins support
please refer to the following documentation:
: `</MON/doc/OpenStack/>`.

These documents will also describe what alarming and monitoring functionality
the plugins support.

* To run the Gnocchi plugin run the following command:

      ::

          lxc exec MON - python /root/MON/plugins/OpenStack/Gnocchi/plugin_instance.py

* To run the Aodh plugin run the following command:

      ::

          lxc exec MON - python /root/MON/plugins/OpenStack/Aodh/plugin_instance.py

CloudWatch
~~~~~~~~~~
The MON container supports a CloudWatch plugin as well.


Verification
------------
* To confirm that you have created your MON container, run the following command
  and confirm that your container is in a RUNNING state:

    ::

        lxc list | grep MON

* Confirm that the kafka service is installed and running within the container:

    ::

        lxc exec MON -- service kafka status
