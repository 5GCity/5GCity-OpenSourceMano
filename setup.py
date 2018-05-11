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
__date__ = "14/Sep/2017"
from setuptools import setup


def parse_requirements(requirements):
    with open(requirements) as f:
        return [l.strip('\n') for l in f if l.strip('\n') and not l.startswith('#') and '://' not in l]


_name = 'osm_mon'
_version = '1.0'
_description = 'OSM Monitoring Module'
_author = 'Prithiv Mohan'
_author_email = 'prithiv.mohan@intel.com'
_maintainer = 'Adrian Hoban'
_maintainer_email = 'adrian.hoban@intel.com'
_license = 'Apache 2.0'
_url = 'https://osm.etsi.org/gitweb/?p=osm/MON.git;a=tree'
setup(name="osm_mon",
      version=_version,
      description=_description,
      long_description=open('README.rst').read(),
      author=_author,
      author_email=_author_email,
      maintainer=_maintainer,
      maintainer_email=_maintainer_email,
      url=_url,
      license=_license,
      packages=[_name],
      package_dir={_name: _name},
      package_data={_name: ['osm_mon/core/message_bus/*.py', 'osm_mon/core/models/*.json',
                            'osm_mon/plugins/OpenStack/Aodh/*.py', 'osm_mon/plugins/OpenStack/Gnocchi/*.py',
                            'osm_mon/plugins/vRealiseOps/*', 'osm_mon/plugins/CloudWatch/*']},
      scripts=['osm_mon/plugins/vRealiseOps/vROPs_Webservice/vrops_webservice',
               'osm_mon/core/message_bus/common_consumer.py'],
      install_requires=parse_requirements('requirements.txt'),
      include_package_data=True,
      dependency_links=[
          'git+https://osm.etsi.org/gerrit/osm/common.git@857731b#egg=osm-common'
      ]
      )
