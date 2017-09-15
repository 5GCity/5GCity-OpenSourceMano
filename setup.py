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

__author__ = "Prithiv Mohan"
__date__   = "14/Sep/2017"

#!/usr/bin/env python

from setuptools import setup
from os import system

_name = 'mon'
_version = '1.0'
_description = 'OSM Monitoring Module'
_author = 'Prithiv Mohan'
_author_email = 'prithiv.mohan@intel.com'
_maintainer = 'Adrian Hoban'
_maintainer_email = 'adrian.hoban@intel.com'
_license = 'Apache 2.0'
_copyright = 'Intel Research and Development Ireland'
_url = 'https://osm.etsi.org/gitweb/?p=osm/MON.git;a=tree'
_requirements = [
    "MySQL-python",
    "requests",
    "loguitls",
    "cherrypy",
    "jsmin",
    "jsonschema",
    "python-openstackclient",
    "python-novaclient",
    "python-keystoneclient",
    "python-neutronclient",
    "python-aodhclient",
    "python-gnocchi client",
    "boto==2.8",
    "python-cloudwatchlogs-logging",
    "py-cloudwatch",
    "pyvcloud",
    "pyopenssl",
    "python-requests",
    "cherrypy",
    "python-bottle",
]

setup(name=_name,
      version = _version,
      description = _description,
      long_description = open('README.rst').read(),
      author = _author,
      author_email = _author_email,
      maintainer = _maintainer,
      maintainer_email = _maintainer_email,
      url = _url,
      license = _license,
      copyright = _copyright,
      packages = [_name],
      package_dir = {_name: _name},
      package_data = {_name: ['core/message_bus/*.py', 'core/models/*.json',
                      'plugins/OpenStack/Aodh/*.py', 'plugins/OpenStack/Gnocchi/*.py',
                      'plugins/vRealiseOps/*', 'plugins/CloudWatch/*']},
      install_requires = _requirements,
      include_package_data=True,
      )
