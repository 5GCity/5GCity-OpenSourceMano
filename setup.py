#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2018 Telefonica S.A.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from setuptools import setup, find_packages

_name = "osm_nbi"
# version is at first line of osm_nbi/html_public/version
here = os.path.abspath(os.path.dirname(__file__))
# with open(os.path.join(here, 'osm_nbi/html_public/version')) as version_file:
#     VERSION = version_file.readline().strip()
with open(os.path.join(here, 'README.rst')) as readme_file:
    README = readme_file.read()

setup(
    name=_name,
    description='OSM North Bound Interface',
    long_description=README,
    version_command=('git describe --match v* --tags --long --dirty', 'pep440-git-full'),
    # version=VERSION,
    # python_requires='>3.5.0',
    author='ETSI OSM',
    author_email='alfonso.tiernosepulveda@telefonica.com',
    maintainer='Alfonso Tierno',
    maintainer_email='alfonso.tiernosepulveda@telefonica.com',
    url='https://osm.etsi.org/gitweb/?p=osm/NBI.git;a=summary',
    license='Apache 2.0',

    packages=find_packages(exclude=["temp", "local"]),
    include_package_data=True,
    # exclude_package_data={'': ['osm_nbi/local', 'temp']},
    # data_files=[('/etc/osm/', ['osm_nbi/nbi.cfg']),
    #             ('/etc/systemd/system/', ['osm_nbi/osm-nbi.service']),
    #             ],
    dependency_links=[
        "git+https://osm.etsi.org/gerrit/osm/IM.git#egg=osm-im",
        'git+https://osm.etsi.org/gerrit/osm/common.git#egg=osm-common'
    ],
    install_requires=[
        'CherryPy==18.0.0',
        'osm-common',
        'jsonschema',
        'PyYAML',
        'osm-im',
        'python-keystoneclient'
    ],
    setup_requires=['setuptools-version-command'],
)
