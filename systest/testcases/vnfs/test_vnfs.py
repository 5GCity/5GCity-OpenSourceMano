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
from osmclient.common import utils


class TestClass(object):

    @pytest.fixture(scope='function')
    def cleanup_test_vnf(self,osm,request):
        vnfd_file_list = osm.vnfd_descriptors_list
        nsd_file_list = osm.nsd_descriptors_list

        # cleanup all ns/packages that might have been left around
        def teardown():

            # first delete all nsd's
            for file in nsd_file_list:
                try:
                    desc = osm.get_api().package.get_descriptor_type_from_pkg(file)
                    ns_name=osm.ns_name_prefix+nsd_desc['name']
                    osm.get_api().ns.delete(ns_name)
                except:
                    pass

            # delete all nsd packages
            for file in nsd_file_list:
                try:
                    desc = osm.get_api().package.get_descriptor_type_from_pkg(file)
                    osm.get_api().nsd.delete(desc['name'])
                except: 
                    pass

            # delete all vnfd packages
            for file in vnfd_file_list:
                try:
                    desc = osm.get_api().package.get_descriptor_type_from_pkg(file)
                    osm.get_api().vnfd.delete(desc['name'])
                except: 
                    pass

        request.addfinalizer(teardown)

    def vnf_test(self,osm, openstack, vim, vnfd_file_list, nsd_file_list):
        vnfd_descriptors=[]
        for file in vnfd_file_list:
            assert not osm.get_api().package.upload(file)
            assert not osm.get_api().package.wait_for_upload(file)
            desc = osm.get_api().package.get_descriptor_type_from_pkg(file)
            assert desc
            vnfd_descriptors.append(desc)

        nsd_descriptors=[]
        for file in nsd_file_list:
            assert not osm.get_api().package.upload(file)
            assert not osm.get_api().package.wait_for_upload(file)
            desc = osm.get_api().package.get_descriptor_type_from_pkg(file)
            assert desc
            nsd_descriptors.append(desc)

        # TODO/HACK: need to figure out why this is necessary. 
        # vnfd/nsd is there (seen on ping_pong), but the ns fails that nsd is not there, 
        # another way to check if the nsd is really ready via API?
        time.sleep(10)

        for nsd_desc in nsd_descriptors:
            ns_name=osm.ns_name_prefix+nsd_desc['name']

            assert not osm.get_api().ns.create(nsd_desc['name'],ns_name,vim.vim_name)

            assert utils.wait_for_value(lambda: osm.get_api().ns.get_field(ns_name,'operational-status'),result='init')

            # make sure ns is running
            assert utils.wait_for_value(lambda: osm.get_api().ns.get_field(ns_name,'operational-status'),result='running',wait_time=120)

            assert not osm.get_api().ns.delete(ns_name)

            assert not osm.get_api().nsd.delete(nsd_desc['name'])

        for vnfd_desc in vnfd_descriptors:

            assert not osm.get_api().vnfd.delete(vnfd_desc['name'])

    @pytest.mark.openstack
    @pytest.mark.vnf
    def test_vnf(self,osm, vim, openstack, cleanup_test_vnf):
        vnfd_file_list = osm.vnfd_descriptors_list
        nsd_file_list = osm.nsd_descriptors_list

        self.vnf_test(osm,openstack, vim, vnfd_file_list, nsd_file_list)
