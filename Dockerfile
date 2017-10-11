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
# License for the specific language governing permissions and limitations
# under the License.

# For those usages not covered by the Apache License, Version 2.0 please
# contact: prithiv.mohan@intel.com or adrian.hoban@intel.com

#__author__ = "Prithiv Mohan"
#__date__   = "25/Sep/2017"

FROM ubuntu:16.04
RUN  apt-get update && \
  DEBIAN_FRONTEND=noninteractive apt-get --yes install git tox make python python-pip debhelper && \
  DEBIAN_FRONTEND=noninteractive apt-get --yes install wget python-dev python-software-properties python-stdeb&& \
  DEBIAN_FRONTEND=noninteractive pip install -U pip && \
  DEBIAN_FRONTENT=noninteractive pip install -U requests logutils jsonschema lxml && \
  DEBIAN_FRONTEND=noninteractive pip install -U setuptools setuptools-version-command stdeb jsmin && \
  DEBIAN_FRONTEND=noninteractive pip install -U six pyvcloud bottle cherrypy pyopenssl && \
  DEBIAN_FRONTEND=noninteractive apt-get --yes install default-jre libmysqlclient-dev && \
  DEBIAN_FRONTEND=noninteractive apt-get --yes install libmysqlclient-dev libxml2 && \
  DEBIAN_FRONTEND=noninteractive pip install -U MySQL-python \
                                                python-openstackclient \
                                                python-keystoneclient \
                                                aodhclient \
                                                gnocchiclient \
                                                boto==2.48 \
                                                python-cloudwatchlogs-logging \
                                                py-cloudwatch
