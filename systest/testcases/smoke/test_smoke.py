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
import pprint
import time


@pytest.mark.smoke
class TestClass(object):

    def test_empty_vnf(self,osm):
        assert not osm.get_api().vnf.list()

    def test_empty_vnf_catalog(self,osm):
        assert not osm.get_api().vnfd.list()

    def test_empty_ns(self,osm):
        assert not osm.get_api().ns.list()

    def test_empty_ns_catalog(self,osm):
        assert not osm.get_api().nsd.list()

    def vnf_upload_packages(self, osm, descriptor_file_list ):
        for file in descriptor_file_list:
            assert not osm.get_api().package.upload(file)
            assert not osm.get_api().package.wait_for_upload(file)
            desc = osm.get_api().package.get_key_val_from_pkg(file)
            assert desc

    def delete_all_packages(self, osm):
        for nsd in osm.get_api().nsd.list(): 
            assert not osm.get_api().nsd.delete(nsd['name'])

        for vnfd in osm.get_api().vnfd.list(): 
            assert not osm.get_api().vnfd.delete(vnfd['name'])
            
    def test_upload_vnf_package(self, osm):
        vnfd_file_list = osm.vnfd_descriptors_list
        nsd_file_list = osm.nsd_descriptors_list
        # upload vnfd's
        self.vnf_upload_packages(osm, vnfd_file_list )
        # upload nsd's
        self.vnf_upload_packages(osm, nsd_file_list )

        # now delete all packages
        self.delete_all_packages(osm)
