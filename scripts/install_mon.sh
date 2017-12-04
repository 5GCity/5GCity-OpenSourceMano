#!/bin/sh
# Copyright 2017 Intel Research and Development Ireland Limited
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Intel Corporation

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at

#         http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitation

# under the License.

# For those usages not covered by the Apache License, Version 2.0 please
# contact: prithiv.mohan@intel.com or adrian.hoban@intel.com

#__author__ = "Prithiv Mohan"
#__date__   = "13/Oct/2017"

#This is a temporary installation script for the MON Module. From the next
#point release, MON will be a part of the OSM Module and can be installed
#through the install_osm.sh script, just like any other modules.

lxc launch ubuntu:16.04 MON
lxc exec MON -- apt-get --yes update
lxc exec MON -- apt-get --yes install git python python-pip libmysqlclient-dev
lxc exec MON -- git clone https://osm.etsi.org/gerrit/osm/MON.git
lxc exec MON -- pip install -r /root/MON/requirements.txt
lxc exec MON -- python /root/MON/kafkad
lxc exec MON -- . /root/MON/scripts/kafka.sh
lxc exec MON -- . /root/MON/osm_mon/plugins/vRealiseOps/vROPs_Webservice/install.sh
