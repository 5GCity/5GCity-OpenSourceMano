# Copyright 2017 Sandvine
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import pytest
import json


def osm_add_options(parser):
    parser.addoption("--osmhost", default="", help="osm hostname")
    parser.addoption("--osm-descriptor-packages", default="", help="location of descriptor packages")
    parser.addoption("--osm-vnfd-descriptor-packages", default="", help="vnfd packages to test")
    parser.addoption("--osm-nsd-descriptor-packages", default="", help="nsd package to test")
    parser.addoption("--osmfile", action="store", default="", help="osm json data file")
    parser.addoption("--osm-ns-name-prefix", action="store", default="", help="ns name prefix to apply")

'''
@pytest.fixture
def osm(request):
    from osmclient.common import OsmAPI
    with open(request.config.getoption("--osm")) as json_data:
        osmdict=json.load(json_data)
        return OsmAPI.OsmAPI(osmdict['ip'])

'''

@pytest.fixture
def osm(request):
    from lib.osm import osm
    osmhost=request.config.getoption("--osmhost")
    descriptors_dir=request.config.getoption("--osm-descriptor-packages")
    vnfd_descriptors_list=request.config.getoption("--osm-vnfd-descriptor-packages").split(',')
    nsd_descriptors_list=request.config.getoption("--osm-nsd-descriptor-packages").split(',')
    ns_name_prefix=request.config.getoption("--osm-ns-name-prefix")
    return osm.Osm(osmhost,
                   descriptors_dir=descriptors_dir,
                   vnfd_descriptors_list=vnfd_descriptors_list,
                   nsd_descriptors_list=nsd_descriptors_list,
                   ns_name_prefix=ns_name_prefix)
