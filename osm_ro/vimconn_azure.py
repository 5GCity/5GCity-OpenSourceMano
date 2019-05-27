# -*- coding: utf-8 -*-

__author__='Sergio Gonzalez'
__date__ ='$18-apr-2019 23:59:59$'

import vimconn
import logging

from os import getenv
from uuid import uuid4

from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.compute import ComputeManagementClient


class vimconnector(vimconn.vimconnector):

    def __init__(self, uuid, name, tenant_id, tenant_name, url, url_admin=None, user=None, passwd=None, log_level=None,
                 config={}, persistent_info={}):

        vimconn.vimconnector.__init__(self, uuid, name, tenant_id, tenant_name, url, url_admin, user, passwd, log_level,
                                      config, persistent_info)

        # LOGGER
        self.logger = logging.getLogger('openmano.vim.azure')
        if log_level:
            logging.basicConfig()
            self.logger.setLevel(getattr(logging, log_level))

        # CREDENTIALS 
        self.credentials = ServicePrincipalCredentials(
            client_id=user,
            secret=passwd,
            tenant=(tenant_id or tenant_name)
        )

        # SUBSCRIPTION
        if 'subscription_id' in config:
            self.subscription_id = config.get('subscription_id')
            self.logger.debug('Setting subscription '+str(self.subscription_id))
        else:
            raise vimconn.vimconnException('Subscription not specified')
        # REGION
        if 'region_name' in config:
            self.region = config.get('region_name')
        else:
            raise vimconn.vimconnException('Azure region_name is not specified at config')
        # RESOURCE_GROUP
        if 'resource_group' in config:
            self.resource_group = config.get('resource_group')
        else:
            raise vimconn.vimconnException('Azure resource_group is not specified at config')
        # VNET_NAME
        if 'vnet_name' in config:
            self.vnet_name = config["vnet_name"]
            
        # public ssh key
        self.pub_key = config.get('pub_key')
            
    def _reload_connection(self):
        """
        Sets connections to work with Azure service APIs
        :return:
        """
        self.logger.debug('Reloading API Connection')
        try:
            self.conn = ResourceManagementClient(self.credentials, self.subscription_id)
            self.conn_compute = ComputeManagementClient(self.credentials, self.subscription_id)
            self.conn_vnet = NetworkManagementClient(self.credentials, self.subscription_id)
            self._check_or_create_resource_group()
            self._check_or_create_vnet()
        except Exception as e:
            self.format_vimconn_exception(e)            

    def _get_resource_name_from_resource_id(self, resource_id):
        return str(resource_id.split('/')[-1])

    def _get_location_from_resource_group(self, resource_group_name):
        return self.conn.resource_groups.get(resource_group_name).location
        
    def _get_resource_group_name_from_resource_id(self, resource_id):
        return str(resource_id.split('/')[4])

    def _check_subnets_for_vm(self, net_list):
        # All subnets must belong to the same resource group and vnet
        if len(set(self._get_resource_group_name_from_resource_id(net['id']) +
                   self._get_resource_name_from_resource_id(net['id']) for net in net_list)) != 1:
            raise self.format_vimconn_exception('Azure VMs can only attach to subnets in same VNET')

    def format_vimconn_exception(self, e):
        """
        Params: an Exception object
        :param e:
        :return: Raises the proper vimconnException
        """
        self.conn = None
        self.conn_vnet = None
        raise vimconn.vimconnConnectionException(type(e).__name__ + ': ' + str(e))        

    def _check_or_create_resource_group(self):
        """
        Creates a resource group in indicated region
        :return: None
        """
        self.logger.debug('Creating RG {} in location {}'.format(self.resource_group, self.region))
        self.conn.resource_groups.create_or_update(self.resource_group, {'location': self.region})

    def _check_or_create_vnet(self):
        try:
            vnet_params = {
                'location': self.region,
                'address_space': {
                    'address_prefixes': "10.0.0.0/8"
                },
            }
            self.conn_vnet.virtual_networks.create_or_update(self.resource_group, self.vnet_name, vnet_params)
        except Exception as e:
            self.format_vimconn_exception(e)

    def new_network(self, net_name, net_type, ip_profile=None, shared=False, vlan=None):
        """
        Adds a tenant network to VIM
        :param net_name: name of the network
        :param net_type:
        :param ip_profile: is a dict containing the IP parameters of the network (Currently only IPv4 is implemented)
                'ip-version': can be one of ['IPv4','IPv6']
                'subnet-address': ip_prefix_schema, that is X.X.X.X/Y
                'gateway-address': (Optional) ip_schema, that is X.X.X.X
                'dns-address': (Optional) ip_schema,
                'dhcp': (Optional) dict containing
                    'enabled': {'type': 'boolean'},
                    'start-address': ip_schema, first IP to grant
                    'count': number of IPs to grant.
        :param shared:
        :param vlan:
        :return: a tuple with the network identifier and created_items, or raises an exception on error
            created_items can be None or a dictionary where this method can include key-values that will be passed to
            the method delete_network. Can be used to store created segments, created l2gw connections, etc.
            Format is vimconnector dependent, but do not use nested dictionaries and a value of None should be the same
            as not present.
        """

        return self._new_subnet(net_name, ip_profile)

    def _new_subnet(self, net_name, ip_profile):
        """
        Adds a tenant network to VIM. It creates a new VNET with a single subnet
        :param net_name:
        :param ip_profile:
        :return:
        """
        self.logger.debug('Adding a subnet to VNET '+self.vnet_name)
        self._reload_connection()

        if ip_profile is None:
            # TODO get a non used vnet ip range /24 and allocate automatically
            raise vimconn.vimconnException('Azure cannot create VNET with no CIDR')

        try:
            vnet_params= {
                'location': self.region,
                'address_space': {
                    'address_prefixes': [ip_profile['subnet_address']]
                },
                'subnets': [
                    {
                        'name': "{}-{}".format(net_name[:24], uuid4()),
                        'address_prefix': ip_profile['subnet_address']
                    }
                ]
            }
            self.conn_vnet.virtual_networks.create_or_update(self.resource_group, self.vnet_name, vnet_params)
            # TODO return a tuple (subnet-ID, None)
        except Exception as e:
            self.format_vimconn_exception(e)

    def _create_nic(self, subnet_id, nic_name, static_ip=None):
        self._reload_connection()
        
        resource_group_name=self._get_resource_group_name_from_resource_id(subnet_id)
        location = self._get_location_from_resource_group(resource_group_name)
            
        if static_ip:
            async_nic_creation = self.conn_vnet.network_interfaces.create_or_update(
                resource_group_name,
                nic_name,
                {
                    'location': location,
                    'ip_configurations': [{
                        'name': nic_name + 'ipconfiguration',
                        'privateIPAddress': static_ip,
                        'privateIPAllocationMethod': 'Static',
                        'subnet': {
                            'id': subnet_id
                        }
                    }]
                }
            )
        else:
            async_nic_creation = self.conn_vnet.network_interfaces.create_or_update(
                resource_group_name,
                nic_name,
                {
                    'location': location,
                    'ip_configurations': [{
                        'name': nic_name + 'ipconfiguration',
                        'subnet': {
                            'id': subnet_id
                        }
                    }]
                }
            )

        return async_nic_creation.result()

    def get_image_list(self, filter_dict={}):
        """
        The urn contains for marketplace  'publisher:offer:sku:version'

        :param filter_dict:
        :return:
        """
        image_list = []

        self._reload_connection()
        if filter_dict.get("name"):
            params = filter_dict["name"].split(":")
            if len(params) >= 3:
                publisher = params[0]
                offer = params[1]
                sku = params[2]
                version = None
                if len(params) == 4:
                    version = params[3]
                images = self.conn_compute.virtual_machine_images.list(self.region, publisher, offer, sku)
                for image in images:
                    if version:
                        image_version = str(image.id).split("/")[-1]
                        if image_version != version:
                            continue
                    image_list.append({
                        'id': str(image.id),
                        'name': self._get_resource_name_from_resource_id(image.id)
                    })
                return image_list

        images = self.conn_compute.virtual_machine_images.list()

        for image in images:
            # TODO implement filter_dict
            if filter_dict:
                if filter_dict.get("id") and str(image.id) != filter_dict["id"]:
                    continue
                if filter_dict.get("name") and \
                        self._get_resource_name_from_resource_id(image.id) != filter_dict["name"]:
                    continue
                # TODO add checksum
            image_list.append({
                'id': str(image.id),
                'name': self._get_resource_name_from_resource_id(image.id),
            })
        return image_list

    def get_network_list(self, filter_dict={}):
        """Obtain tenant networks of VIM
        Filter_dict can be:
            name: network name
            id: network uuid
            shared: boolean
            tenant_id: tenant
            admin_state_up: boolean
            status: 'ACTIVE'
        Returns the network list of dictionaries
        """
        self.logger.debug('Getting all subnets from VIM')
        try:
            self._reload_connection()
            vnet = self.conn_vnet.virtual_networks.get(self.config["resource_group"], self.vnet_name)
            subnet_list = []
            
            for subnet in vnet.subnets:
                # TODO implement filter_dict
                if filter_dict:
                    if filter_dict.get("id") and str(subnet.id) != filter_dict["id"]:
                        continue
                    if filter_dict.get("name") and \
                            self._get_resource_name_from_resource_id(subnet.id) != filter_dict["name"]:
                        continue

                subnet_list.append({
                    'id': str(subnet.id),
                     'name': self._get_resource_name_from_resource_id(subnet.id),
                     'status': str(vnet.provisioning_state),  # TODO Does subnet contains status???
                     'cidr_block': str(subnet.address_prefix)
                    }
                )
            return subnet_list
        except Exception as e:
            self.format_vimconn_exception(e)

    def new_vminstance(self, vm_name, description, start, image_id, flavor_id, net_list, cloud_config=None,
                       disk_list=None, availability_zone_index=None, availability_zone_list=None):

        return self._new_vminstance(vm_name, image_id, flavor_id, net_list)
        
    def _new_vminstance(self, vm_name, image_id, flavor_id, net_list, cloud_config=None, disk_list=None,
                        availability_zone_index=None, availability_zone_list=None):
        #Create NICs
        self._check_subnets_for_vm(net_list)
        vm_nics = []
        for idx, net in enumerate(net_list):
            subnet_id=net['subnet_id']
            nic_name = vm_name + '-nic-'+str(idx)
            vm_nic = self._create_nic(subnet_id, nic_name)
            vm_nics.append({ 'id': str(vm_nic.id)})

        try:
            vm_parameters = {
                'location': self.region,
                'os_profile': {
                    'computer_name': vm_name,  # TODO if vm_name cannot be repeated add uuid4() suffix
                    'admin_username': 'sergio',  # TODO is it mandatory???
                    'linuxConfiguration': {
                        'disablePasswordAuthentication': 'true',
                        'ssh': {
                          'publicKeys': [
                            {
                              'path': '/home/sergio/.ssh/authorized_keys',
                              'keyData': self.pub_key
                            }
                          ]
                        }
                    }                    
                    
                },
                'hardware_profile': {
                    'vm_size':flavor_id
                },
                'storage_profile': {
                    'image_reference': image_id
                },
                'network_profile': {
                    'network_interfaces': [
                        vm_nics[0]
                    ]
                }
            }
            creation_result = self.conn_compute.virtual_machines.create_or_update(
                self.resource_group, 
                vm_name, 
                vm_parameters
            )
            
            run_command_parameters = {
                'command_id': 'RunShellScript', # For linux, don't change it
                'script': [
                'date > /home/sergio/test.txt'
                ]
            }
            poller = self.conn_compute.virtual_machines.run_command(
                self.resource_group, 
                vm_name, 
                run_command_parameters
            )
            # TODO return a tuple (vm-ID, None)
        except Exception as e:
            self.format_vimconn_exception(e)

    def get_flavor_id_from_data(self, flavor_dict):
        self.logger.debug("Getting flavor id from data")
        self._reload_connection()
        vm_sizes_list = [vm_size.serialize() for vm_size in self.conn_compute.virtual_machine_sizes.list(self.region)]

        cpus = flavor_dict['vcpus']
        memMB = flavor_dict['ram']

        filteredSizes = [size for size in vm_sizes_list if size['numberOfCores'] > cpus and size['memoryInMB'] > memMB]
        listedFilteredSizes = sorted(filteredSizes, key=lambda k: k['numberOfCores'])

        return listedFilteredSizes[0]['name']

    def check_vim_connectivity(self):
        try:
            self._reload_connection()
            return True
        except Exception as e:
            raise vimconn.vimconnException("Connectivity issue with Azure API: {}".format(e))

    def get_network(self, net_id):
        resGroup = self._get_resource_group_name_from_resource_id(net_id)
        resName = self._get_resource_name_from_resource_id(net_id)
        
        self._reload_connection()
        vnet = self.conn_vnet.virtual_networks.get(resGroup, resName)

        return vnet

    def delete_network(self, net_id):
        resGroup = self._get_resource_group_name_from_resource_id(net_id)
        resName = self._get_resource_name_from_resource_id(net_id)
        
        self._reload_connection()
        self.conn_vnet.virtual_networks.delete(resGroup, resName)

    def delete_vminstance(self, vm_id):
        resGroup = self._get_resource_group_name_from_resource_id(net_id)
        resName = self._get_resource_name_from_resource_id(net_id)
        
        self._reload_connection()
        self.conn_compute.virtual_machines.delete(resGroup, resName)

    def get_vminstance(self, vm_id):
        resGroup = self._get_resource_group_name_from_resource_id(net_id)
        resName = self._get_resource_name_from_resource_id(net_id)
        
        self._reload_connection()
        vm=self.conn_compute.virtual_machines.get(resGroup, resName)

        return vm

    def get_flavor(self, flavor_id):
        self._reload_connection()
        for vm_size in self.conn_compute.virtual_machine_sizes.list(self.region):
            if vm_size.name == flavor_id :
                return vm_size


# TODO refresh_nets_status ver estado activo
# TODO refresh_vms_status  ver estado activo
# TODO get_vminstance_console  for getting console

if __name__ == "__main__":

    # Making some basic test
    vim_id='azure'
    vim_name='azure'
    needed_test_params = {
        "client_id": "AZURE_CLIENT_ID",
        "secret": "AZURE_SECRET",
        "tenant": "AZURE_TENANT",
        "resource_group": "AZURE_RESOURCE_GROUP",
        "subscription_id": "AZURE_SUBSCRIPTION_ID",
        "vnet_name": "AZURE_VNET_NAME",
    }
    test_params = {}

    for param, env_var in needed_test_params.items():
        value = getenv(env_var)
        if not value:
            raise Exception("Provide a valid value for env '{}'".format(env_var))
        test_params[param] = value

    config = {
            'region_name': getenv("AZURE_REGION_NAME", 'westeurope'),
            'resource_group': getenv("AZURE_RESOURCE_GROUP"),
            'subscription_id': getenv("AZURE_SUBSCRIPTION_ID"),
            'pub_key': getenv("AZURE_PUB_KEY", None),
            'vnet_name': getenv("AZURE_VNET_NAME", 'myNetwork'),
    }

    virtualMachine = {
        'name': 'sergio',
        'description': 'new VM',
        'status': 'running',
        'image': {
            'publisher': 'Canonical',
            'offer': 'UbuntuServer',
            'sku': '16.04.0-LTS',
            'version': 'latest'
        },
        'hardware_profile': {
            'vm_size': 'Standard_DS1_v2'
        },
        'networks': [
            'sergio'
        ]
    }

    vnet_config = {
        'subnet_address': '10.1.2.0/24',
        #'subnet_name': 'subnet-oam'
    }
    ###########################

    azure = vimconnector(vim_id, vim_name, tenant_id=test_params["tenant"], tenant_name=None, url=None, url_admin=None,
                         user=test_params["client_id"], passwd=test_params["secret"], log_level=None, config=config)

    # azure.get_flavor_id_from_data("here")
    # subnets=azure.get_network_list()
    # azure.new_vminstance(virtualMachine['name'], virtualMachine['description'], virtualMachine['status'],
    #                      virtualMachine['image'], virtualMachine['hardware_profile']['vm_size'], subnets)

    azure.get_flavor("Standard_A11")