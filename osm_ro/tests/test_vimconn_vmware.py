# -*- coding: utf-8 -*-

##
# Copyright 2016-2017 VMware Inc.
# This file is part of ETSI OSM
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact:  osslegalrouting@vmware.com
##


from osm_ro.vimconn_vmware import vimconnector
from osm_ro.vimconn import vimconnUnexpectedResponse,vimconnNotFoundException
from pyvcloud.vcd.client import Client
from lxml import etree as lxmlElementTree
from pyvcloud.vcd.org import Org
from pyvcloud.vcd.vdc import VDC
from pyvcloud.vcd.vapp import VApp
import unittest
import mock
import test_vimconn_vmware_xml_response as xml_resp

__author__ = "Prakash Kasar"

class TestVimconn_VMware(unittest.TestCase):
    def setUp(self):
        config = { "admin_password": "admin",
                  "admin_username":"user",
                  "nsx_user": "nsx",
                  "nsx_password": "nsx",
                  "nsx_manager":"https://test-nsx" }

        self.client = Client('test', verify_ssl_certs=False)

        # get vcd org object
        org_resp = xml_resp.org_xml_response
        get_org = lxmlElementTree.fromstring(org_resp) 
        self.org = Org(self.client, resource=get_org)

        self.vim = vimconnector(uuid='12354',
                                 name='test',
                         tenant_id='abc1234',
                          tenant_name='test',
                          url='https://test',
                               config=config)


    @mock.patch.object(vimconnector,'get_vdc_details')
    @mock.patch.object(vimconnector,'connect')
    @mock.patch.object(vimconnector,'perform_request')
    def test_get_network_not_found(self, perform_request, connect, get_vdc_details):
        """
        Testcase to get network with invalid network id
        """   
        # created vdc object
        vdc_xml_resp = xml_resp.vdc_xml_response
        vdc = lxmlElementTree.fromstring(vdc_xml_resp)

        # assumed return value from VIM connector
        get_vdc_details.return_value = self.org, vdc
        self.vim.client = self.vim.connect()
        perform_request.return_value.status_code = 200
        perform_request.return_value.content = xml_resp.vdc_xml_response

        # call to VIM connector method with invalid id
        self.assertRaises(vimconnNotFoundException,self.vim.get_network,'mgmt-net')

    @mock.patch.object(vimconnector,'perform_request')
    @mock.patch.object(vimconnector,'get_vdc_details')
    @mock.patch.object(vimconnector,'connect')
    def test_get_network(self, connect, get_vdc_details, perform_request):
        """
        Testcase to get network with valid network id
        """
        net_id = '5c04dc6d-6096-47c6-b72b-68f19013d491'
        # created vdc object
        vdc_xml_resp = xml_resp.vdc_xml_response
        vdc = lxmlElementTree.fromstring(vdc_xml_resp)

        # assumed return value from VIM connector
        get_vdc_details.return_value = self.org, vdc
        self.vim.client = self.vim.connect()
        perform_request.side_effect = [mock.Mock(status_code = 200,
                                       content = xml_resp.vdc_xml_response),
                                       mock.Mock(status_code = 200,
                                       content = xml_resp.network_xml_response)]
        # call to VIM connector method with network_id
        result = self.vim.get_network(net_id)

        # assert verified expected and return result from VIM connector
        self.assertEqual(net_id, result['id'])

    @mock.patch.object(vimconnector,'perform_request')
    @mock.patch.object(vimconnector,'get_vdc_details')
    @mock.patch.object(vimconnector,'connect')
    def test_get_network_list_not_found(self, connect, get_vdc_details, perform_request):
        """
        Testcase to get list of available networks by invalid network id 
        """
        vdc_xml_resp = xml_resp.vdc_xml_response
        network_xml_resp = xml_resp.network_xml_response
        # created vdc object
        vdc = lxmlElementTree.fromstring(vdc_xml_resp)

        # assumed return value from VIM connector
        get_vdc_details.return_value = self.org, vdc
        self.vim.client = self.vim.connect()
        perform_request.return_value.status_code = 200
        perform_request.return_value.content = network_xml_resp

        # call to VIM connector method with network_id
        result = self.vim.get_network_list({'id':'45hdfg-345nb-345'})

        # assert verified expected and return result from VIM connector
        self.assertEqual(list(), result)

    @mock.patch.object(vimconnector,'perform_request')
    @mock.patch.object(vimconnector,'get_vdc_details')
    @mock.patch.object(vimconnector,'connect')
    def test_get_network_list(self, connect, get_vdc_details, perform_request):
        """
        Testcase to get list of available networks by valid network id
        """ 
        #import pdb;pdb.set_trace() ## Not working  
        vdc_xml_resp = xml_resp.vdc_xml_response
        net_id = '5c04dc6d-6096-47c6-b72b-68f19013d491'
        # created vdc object
        vdc = lxmlElementTree.fromstring(vdc_xml_resp)
        # created network object
        network_xml_resp = xml_resp.network_xml_response
        # assumed return value from VIM connector
        get_vdc_details.return_value = self.org, vdc
        self.vim.client = self.vim.connect()
        perform_request.side_effect = [mock.Mock(status_code = 200,
                                       content = xml_resp.vdc_xml_response),
                                       mock.Mock(status_code = 200,
                                       content = network_xml_resp)]
        perform_request.reset_mock()
        perform_request() 

        # call to VIM connector method with network_id
        result = self.vim.get_network_list({'id': net_id})

        # assert verified expected and return result from VIM connector
        for item in result:
            self.assertEqual(item.get('id'), net_id)
            self.assertEqual(item.get('status'), 'ACTIVE')
            self.assertEqual(item.get('shared'), False)

    @mock.patch.object(vimconnector,'create_network_rest')
    def test_new_network(self, create_network_rest):
        """
        Testcase to create new network by passing network name and type
        """
        # create network reposnse 
        create_net_xml_resp = xml_resp.create_network_xml_response
        net_name = 'Test_network'
        net_type = 'bridge'
        # assumed return value from VIM connector
        create_network_rest.return_value = create_net_xml_resp
        # call to VIM connector method with network name and type
        result = self.vim.new_network(net_name, net_type)

        # assert verified expected and return result from VIM connector
        self.assertEqual(result, 'df1956fa-da04-419e-a6a2-427b6f83788f')

    @mock.patch.object(vimconnector, 'create_network_rest')
    def test_new_network_not_created(self, create_network_rest):
        """
        Testcase to create new network by assigning empty xml data  
        """
        # assumed return value from VIM connector
        create_network_rest.return_value = """<?xml version="1.0" encoding="UTF-8"?>
                                              <OrgVdcNetwork></OrgVdcNetwork>"""
                                           

        # assert verified expected and return result from VIM connector
        self.assertRaises(vimconnUnexpectedResponse,self.vim.new_network,
                                                              'test_net',
                                                                'bridge')

    @mock.patch.object(vimconnector, 'connect')
    @mock.patch.object(vimconnector, 'get_network_action')
    @mock.patch.object(vimconnector, 'delete_network_action')
    def test_delete_network(self, delete_network_action, get_network_action, connect):
        """
        Testcase to delete network by network id  
        """
        net_uuid = '0a55e5d1-43a2-4688-bc92-cb304046bf87'
        # delete network response 
        delete_net_xml_resp = xml_resp.delete_network_xml_response

        # assumed return value from VIM connector
        self.vim.client = self.vim.connect()
        get_network_action.return_value = delete_net_xml_resp
        delete_network_action.return_value = True
        # call to VIM connector method with network_id
        result = self.vim.delete_network(net_uuid)

        # assert verified expected and return result from VIM connector
        self.assertEqual(result, net_uuid)

    @mock.patch.object(vimconnector, 'get_vcd_network')
    def test_delete_network_not_found(self, get_vcd_network):
        """
        Testcase to delete network by invalid network id  
        """
        # assumed return value from VIM connector
        get_vcd_network.return_value = False
        # assert verified expected and return result from VIM connector
        self.assertRaises(vimconnNotFoundException,self.vim.delete_network,
                                    '2a23e5d1-42a2-0648-bc92-cb508046bf87')

    def test_get_flavor(self):
        """
        Testcase to get flavor data  
        """
        flavor_data = {'a646eb8a-95bd-4e81-8321-5413ee72b62e': {'disk': 10,
                                                                'vcpus': 1,
                                                               'ram': 1024}}
        vimconnector.flavorlist = flavor_data
        result = self.vim.get_flavor('a646eb8a-95bd-4e81-8321-5413ee72b62e')

        # assert verified expected and return result from VIM connector
        self.assertEqual(result, flavor_data['a646eb8a-95bd-4e81-8321-5413ee72b62e'])

    def test_get_flavor_not_found(self):
        """
        Testcase to get flavor data with invalid id 
        """
        vimconnector.flavorlist = {}
        # assert verified expected and return result from VIM connector
        self.assertRaises(vimconnNotFoundException,self.vim.get_flavor,
                                'a646eb8a-95bd-4e81-8321-5413ee72b62e')

    def test_new_flavor(self):
        """
        Testcase to create new flavor data
        """
        flavor_data = {'disk': 10, 'vcpus': 1, 'ram': 1024}
        result = self.vim.new_flavor(flavor_data)
        # assert verified expected and return result from VIM connector
        self.assertIsNotNone(result)

    def test_delete_flavor(self):
        """
        Testcase to delete flavor data  
        """
        flavor_data = {'2cb3dffb-5c51-4355-8406-28553ead28ac': {'disk': 10,
                                                                'vcpus': 1,
                                                               'ram': 1024}}
        vimconnector.flavorlist = flavor_data
        # return value from VIM connector
        result = self.vim.delete_flavor('2cb3dffb-5c51-4355-8406-28553ead28ac')

        # assert verified expected and return result from VIM connector
        self.assertEqual(result, '2cb3dffb-5c51-4355-8406-28553ead28ac')

    @mock.patch.object(vimconnector,'connect_as_admin')
    @mock.patch.object(vimconnector,'perform_request')
    def test_delete_image_not_found(self, perform_request, connect_as_admin):
        """
        Testcase to delete image by invalid image id  
        """
        # creating conn object
        self.vim.client = self.vim.connect_as_admin()

        # assumed return value from VIM connector
        perform_request.side_effect = [mock.Mock(status_code = 200,
                                       content = xml_resp.delete_catalog_xml_response),
                                       mock.Mock(status_code = 201,
                                       content = xml_resp.delete_catalog_item_xml_response)
                                       ]

        # assert verified expected and return result from VIM connector
        self.assertRaises(vimconnNotFoundException, self.vim.delete_image, 'invali3453')

    @mock.patch.object(vimconnector,'get_vdc_details')
    @mock.patch.object(vimconnector,'connect')
    @mock.patch.object(Org,'list_catalogs')
    def test_get_image_list(self, list_catalogs, connect, get_vdc_details):
        """
        Testcase to get image list by valid image id
        """
        # created vdc object
        vdc_xml_resp = xml_resp.vdc_xml_response
        vdc = lxmlElementTree.fromstring(vdc_xml_resp)
        self.vim.client = self.vim.connect()

        # assumed return value from VIM connector
        get_vdc_details.return_value = self.org, vdc
        list_catalogs.return_value = [{'isShared': 'false', 'numberOfVAppTemplates': '1', 'orgName': 'Org3', 'isPublished': 'false', 'ownerName': 'system', 'numberOfMedia': '0', 'creationDate': '2017-10-15T02:03:59.403-07:00', 'id': '34925a30-0f4a-4018-9759-0d6799063b51', 'name': 'Ubuntu_1nic'}, {'isShared': 'false', 'numberOfVAppTemplates': '1', 'orgName': 'Org3', 'isPublished': 'false', 'ownerName': 'orgadmin', 'numberOfMedia': '1', 'creationDate': '2018-02-15T02:16:58.300-08:00', 'id': '4b94b67e-c2c6-49ec-b46c-3f35ba45ca4a', 'name': 'cirros034'}, {'isShared': 'true', 'numberOfVAppTemplates': '1', 'orgName': 'Org3', 'isPublished': 'true', 'ownerName': 'system', 'numberOfMedia': '0', 'creationDate': '2018-01-26T02:09:12.387-08:00', 'id': 'b139ed82-7ca4-49fb-9882-5f841f59c890', 'name': 'Ubuntu_plugtest-1'}, {'isShared': 'true', 'numberOfVAppTemplates': '1', 'orgName': 'Org2', 'isPublished': 'false', 'ownerName': 'system', 'numberOfMedia': '0', 'creationDate': '2017-06-18T21:33:16.430-07:00', 'id': 'b31e6973-86d2-404b-a522-b16846d099dc', 'name': 'Ubuntu_Cat'}, {'isShared': 'false', 'numberOfVAppTemplates': '1', 'orgName': 'Org3', 'isPublished': 'false', 'ownerName': 'orgadmin', 'numberOfMedia': '0', 'creationDate': '2018-02-15T22:26:28.910-08:00', 'id': 'c3b56180-f980-4256-9109-a93168d73ff2', 'name': 'de4ffcf2ad21f1a5d0714d6b868e2645'}, {'isShared': 'false', 'numberOfVAppTemplates': '0', 'orgName': 'Org3', 'isPublished': 'false', 'ownerName': 'system', 'numberOfMedia': '0', 'creationDate': '2017-08-23T05:54:56.780-07:00', 'id': 'd0eb0b02-718d-42e0-b889-56575000b52d', 'name': 'Test_Cirros'}, {'isShared': 'false', 'numberOfVAppTemplates': '0', 'orgName': 'Org3', 'isPublished': 'false', 'ownerName': 'system', 'numberOfMedia': '0', 'creationDate': '2017-03-08T21:25:05.923-08:00', 'id': 'd3fa3df2-b311-4571-9138-4c66541d7f46', 'name': 'cirros_10'}, {'isShared': 'false', 'numberOfVAppTemplates': '0', 'orgName': 'Org3', 'isPublished': 'false', 'ownerName': 'system', 'numberOfMedia': '0', 'creationDate': '2017-07-12T22:45:20.537-07:00', 'id': 'd64b2617-ea4b-4b90-910b-102c99dd2031', 'name': 'Ubuntu16'}, {'isShared': 'true', 'numberOfVAppTemplates': '1', 'orgName': 'Org3', 'isPublished': 'true', 'ownerName': 'system', 'numberOfMedia': '1', 'creationDate': '2017-10-14T23:52:37.260-07:00', 'id': 'e8d953db-8dc9-46d5-9cab-329774cd2ad9', 'name': 'Ubuntu_no_nic'}]
 
        result = self.vim.get_image_list({'id': '4b94b67e-c2c6-49ec-b46c-3f35ba45ca4a'})

        # assert verified expected and return result from VIM connector
        for item in result:
            self.assertEqual(item['id'], '4b94b67e-c2c6-49ec-b46c-3f35ba45ca4a')

    @mock.patch.object(vimconnector,'get_vapp_details_rest')
    @mock.patch.object(vimconnector,'get_vdc_details')
    def test_get_vminstance(self, get_vdc_details, get_vapp_details_rest):
        """
        Testcase to get vminstance by valid vm id
        """
        vapp_info = {'status': '4',
                   'acquireMksTicket': {'href': 'https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/screen/action/acquireMksTicket',
                   'type': 'application/vnd.vmware.vcloud.mksTicket+xml', 'rel': 'screen:acquireMksTicket'},
                   'vm_virtual_hardware': {'disk_edit_href': 'https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/virtualHardwareSection/disks', 'disk_size': '40960'},
                   'name': 'Test1_vm-69a18104-8413-4cb8-bad7-b5afaec6f9fa',
                   'created': '2017-09-21T01:15:31.627-07:00',
                    'IsEnabled': 'true',
                   'EndAddress': '12.16.24.199',
                   'interfaces': [{'MACAddress': '00:50:56:01:12:a2',
                                   'NetworkConnectionIndex': '0',
                                   'network': 'testing_T6nODiW4-68f68d93-0350-4d86-b40b-6e74dedf994d',
                                   'IpAddressAllocationMode': 'DHCP',
                                   'IsConnected': 'true',
                                   'IpAddress': '12.16.24.200'}],
                   'ovfDescriptorUploaded': 'true',
                   'nestedHypervisorEnabled': 'false',
                   'Gateway': '12.16.24.1',
                   'acquireTicket': {'href': 'https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/screen/action/acquireTicket',
                   'rel': 'screen:acquireTicket'},
                   'vmuuid': '47d12505-5968-4e16-95a7-18743edb0c8b',
                   'Netmask': '255.255.255.0',
                   'StartAddress': '12.16.24.100',
                   'primarynetwork': '0',
                   'networkname': 'External-Network-1074',
                   'IsInherited': 'false',
                   'deployed': 'true'} 
        # created vdc object
        vdc_xml_resp = xml_resp.vdc_xml_response
        vdc = lxmlElementTree.fromstring(vdc_xml_resp)
        # assumed return value from VIM connector
        get_vdc_details.return_value = self.org, vdc
        get_vapp_details_rest.return_value = vapp_info

        result = self.vim.get_vminstance('47d12505-5968-4e16-95a7-18743edb0c8b')
        # assert verified expected and return result from VIM connector
        self.assertEqual(result['status'], 'ACTIVE')
        self.assertEqual(result['hostId'], '47d12505-5968-4e16-95a7-18743edb0c8b')


    @mock.patch.object(vimconnector,'connect')
    @mock.patch.object(vimconnector,'get_namebyvappid')
    @mock.patch.object(vimconnector,'get_vdc_details')
    @mock.patch.object(VDC,'get_vapp')
    @mock.patch.object(VApp,'power_off')
    @mock.patch.object(VApp,'undeploy')
    @mock.patch.object(VDC,'delete_vapp')
    @mock.patch.object(Client,'get_task_monitor')
    def test_delete_vminstance(self, get_task_monitor, delete_vapp,
                                               undeploy, poweroff,
                                         get_vapp, get_vdc_details,
                                        get_namebyvappid, connect):
        """
        Testcase to delete vminstance by valid vm id
        """
        vm_id = '4f6a9b49-e92d-4935-87a1-0e4dc9c3a069'
        vm_name = 'Test1_vm-69a18104-8413-4cb8-bad7-b5afaec6f9fa'
        # created vdc object
        vdc_xml_resp = xml_resp.vdc_xml_response
        vdc = lxmlElementTree.fromstring(vdc_xml_resp)

        # assumed return value from VIM connector
        self.vim.client = self.vim.connect()
        get_vdc_details.return_value = self.org, vdc 
        get_namebyvappid.return_name = vm_name

        vapp_resp = xml_resp.vapp_xml_response
        vapp = lxmlElementTree.fromstring(vapp_resp) 
        get_vapp.return_value = vapp
        
        power_off_resp = xml_resp.poweroff_task_xml
        power_off = lxmlElementTree.fromstring(power_off_resp)
        poweroff.return_value = power_off

        status_resp = xml_resp.status_task_xml 
        status = lxmlElementTree.fromstring(status_resp)
        self.vim.connect.return_value.get_task_monitor.return_value.wait_for_success.return_value = status

        # call to VIM connector method
        result = self.vim.delete_vminstance(vm_id)

        # assert verified expected and return result from VIM connector
        self.assertEqual(result, vm_id)

    @mock.patch.object(vimconnector,'get_network_id_by_name')
    @mock.patch.object(vimconnector,'get_vm_pci_details')
    @mock.patch.object(VDC,'get_vapp')
    @mock.patch.object(vimconnector,'connect')
    @mock.patch.object(vimconnector,'get_namebyvappid')
    @mock.patch.object(vimconnector,'get_vdc_details')
    @mock.patch.object(vimconnector,'perform_request')
    @mock.patch.object(VApp,'get_all_vms')
    def test_refresh_vms_status(self, get_all_vms, perform_request, get_vdc_details,
                                                          get_namebyvappid, connect,
                                                       get_vapp, get_vm_pci_details,
                                                            get_network_id_by_name):
        """
        Testcase to refresh vms status by valid vm id
        """ 
        vm_id = '53a529b2-10d8-4d56-a7ad-8182acdbe71c'

        # created vdc object
        vdc_xml_resp = xml_resp.vdc_xml_response
        vdc = lxmlElementTree.fromstring(vdc_xml_resp)    
        # assumed return value from VIM connector
        self.vim.client = self.vim.connect()
        get_vdc_details.return_value = self.org, vdc

        get_namebyvappid.return_value = 'Test1_vm-69a18104-8413-4cb8-bad7-b5afaec6f9fa'
        get_vm_pci_details.return_value = {'host_name': 'test-esx-1.corp.local', 'host_ip': '12.19.24.31'}
        vapp_resp = xml_resp.vapp_xml_response
        vapp = lxmlElementTree.fromstring(vapp_resp)
        get_vapp.return_value = vapp 
        get_network_id_by_name.return_value = '47d12505-5968-4e16-95a7-18743edb0c8b'

        vm_resp = xml_resp.vm_xml_response
        vm_list = lxmlElementTree.fromstring(vm_resp)
        get_all_vms.return_value = vm_list
          
        perform_request.return_value.status_code = 200
        perform_request.return_value.content = vm_resp
        # call to VIM connector method
        result = self.vim.refresh_vms_status([vm_id])
        for attr in result[vm_id]:
            if attr == 'status':
                # assert verified expected and return result from VIM connector
                self.assertEqual(result[vm_id][attr], 'ACTIVE')

    @mock.patch.object(vimconnector,'get_vcd_network')
    def test_refresh_nets_status(self, get_vcd_network):
        net_id = 'c2d0f28f-d38b-4588-aecc-88af3d4af58b'
        network_dict = {'status': '1','isShared': 'false','IpScope': '',
                        'EndAddress':'12.19.21.15',
                        'name': 'testing_gwyRXlvWYL1-9ebb6d7b-5c74-472f-be77-963ed050d44d',
                        'Dns1': '12.19.21.10', 'IpRanges': '',
                        'Gateway': '12.19.21.23', 'Netmask': '255.255.255.0',
                        'RetainNetInfoAcrossDeployments': 'false',
                        'IpScopes': '', 'IsEnabled': 'true', 'DnsSuffix': 'corp.local',
                        'StartAddress': '12.19.21.11', 'IpRange': '',
                        'Configuration': '', 'FenceMode': 'bridged',
                        'IsInherited': 'true', 'uuid': 'c2d0f28f-d38b-4588-aecc-88af3d4af58b'}
        # assumed return value from VIM connector
        get_vcd_network.return_value = network_dict
        result = self.vim.refresh_nets_status([net_id])
        # assert verified expected and return result from VIM connector
        for attr in result[net_id]:
            if attr == 'status':
                self.assertEqual(result[net_id][attr], 'ACTIVE')

    @mock.patch.object(VDC,'get_vapp')
    @mock.patch.object(vimconnector,'connect')
    @mock.patch.object(vimconnector,'get_namebyvappid')
    @mock.patch.object(vimconnector,'get_vdc_details')
    def test_action_vminstance(self, get_vdc_details, get_namebyvappid,
                                                               connect,
                                                             get_vapp):
        """
        Testcase for action vm instance by vm id
        """
        task_resp = xml_resp.poweroff_task_xml
        vm_id = '05e6047b-6938-4275-8940-22d1ea7245b8'
        # created vdc object
        vdc_xml_resp = xml_resp.vdc_xml_response
        vdc = lxmlElementTree.fromstring(vdc_xml_resp)
        # assumed return value from VIM connector
        get_vdc_details.return_value = self.org, vdc
        get_namebyvappid.return_value = 'Test1_vm-69a18104-8413-4cb8-bad7-b5afaec6f9fa'
        self.vim.client = self.vim.connect()
        power_off_resp = xml_resp.poweroff_task_xml
        power_off = lxmlElementTree.fromstring(power_off_resp) 
        get_vapp.return_value.undeploy.return_value = power_off

        status_resp = xml_resp.status_task_xml
        status = lxmlElementTree.fromstring(status_resp)
        self.vim.connect.return_value.get_task_monitor.return_value.wait_for_success.return_value = status

        # call to VIM connector method
        result = self.vim.action_vminstance(vm_id,{'shutdown': None})

        # assert verified expected and return result from VIM connector
        self.assertEqual(result, vm_id)

    @mock.patch.object(vimconnector,'get_org')
    def test_get_tenant_list(self, get_org):
        """
        Test case for get tenant list     
        """
        org_dict = {'catalogs': {'4c4fdb5d-0c7d-4fee-9efd-cb061f327a01': '80d8488f67ba1de98b7f485fba6abbd2', '1b98ca02-b0a6-4ca7-babe-eadc0ae59677': 'Ubuntu', 'e7f27dfe-14b7-49e1-918e-173bda02683a': '834bdd1f28fd15dcbe830456ec58fbca', '9441ee69-0486-4438-ac62-8d8082c51302': 'centos', 'e660cce0-47a6-4315-a5b9-97a39299a374': 'cirros01', '0fd96c61-c3d1-4abf-9a34-0dff8fb65743': 'cirros034', '1c703be3-9bd2-46a2-854c-3e678d5cdda8': 'Ubuntu_plugtest-1', 'bc4e342b-f84c-41bd-a93a-480f35bacf69': 'Cirros', '8a206fb5-3ef9-4571-9bcc-137615f4d930': '255eb079a62ac155e7f942489f14b0c4'}, 'vdcs': {'e6436c6a-d922-4b39-9c1c-b48e766fce5e': 'osm', '3852f762-18ae-4833-a229-42684b6e7373': 'cloud-1-vdc'}, 'networks': {'e203cacd-9320-4422-9be0-12c7def3ab56': 'testing_lNejr37B-38e4ca67-1e26-486f-ad2f-f14bb099e068', 'a6623349-2bef-4367-9fda-d33f9ab927f8': 'Vlan_3151', 'adf780cb-358c-47c2-858d-ae5778ccaf17': 'testing_xwBultc-99b8a2ae-c091-4dd3-bbf7-762a51612385', '721f9efc-11fe-4c13-936d-252ba0ed93c8': 'testing_tLljy8WB5e-a898cb28-e75b-4867-a22e-f2bad285c144', '1512d97a-929d-4b06-b8af-cf5ac42a2aee': 'Managment', 'd9167301-28af-4b89-b9e0-09f612e962fa': 'testing_prMW1VThk-063cb428-eaee-44b8-9d0d-df5fb77a5b4d', '004ae853-f899-43fd-8981-7513a3b40d6b': 'testing_RTtKVi09rld-fab00b16-7996-49af-8249-369c6bbfa02d'}}
        tenant_name = 'osm'
        get_org.return_value = org_dict

        # call to VIM connector method  
        results = self.vim.get_tenant_list({'name' : tenant_name})
        # assert verified expected and return result from VIM connector  
        for result in results: 
            self.assertEqual(tenant_name,result['name'])

    @mock.patch.object(vimconnector,'get_org')
    def test_get_tenant_list_negative(self, get_org):
        """
        Test case for get tenant list negative
        """
        org_dict = {'vdcs': {}}
        tenant_name = 'testosm'
        get_org.return_value = org_dict

        # call to VIM connector method
        results = self.vim.get_tenant_list({'name' : tenant_name})
        # assert verified expected and return result from VIM connector
        self.assertEqual(results, [])
