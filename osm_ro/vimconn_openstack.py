# -*- coding: utf-8 -*-

##
# Copyright 2015 Telefónica Investigación y Desarrollo, S.A.U.
# This file is part of openmano
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
# contact with: nfvlabs@tid.es
##

'''
osconnector implements all the methods to interact with openstack using the python-client.
'''
__author__="Alfonso Tierno, Gerardo Garcia, Pablo Montes, xFlow Research"
__date__ ="$22-jun-2014 11:19:29$"

import vimconn
import json
import yaml
import logging
import netaddr
import time
import yaml
import random

from novaclient import client as nClient, exceptions as nvExceptions
from keystoneauth1.identity import v2, v3
from keystoneauth1 import session
import keystoneclient.exceptions as ksExceptions
import keystoneclient.v3.client as ksClient_v3
import keystoneclient.v2_0.client as ksClient_v2
from glanceclient import client as glClient
import glanceclient.client as gl1Client
import glanceclient.exc as gl1Exceptions
from  cinderclient import client as cClient
from httplib import HTTPException
from neutronclient.neutron import client as neClient
from neutronclient.common import exceptions as neExceptions
from requests.exceptions import ConnectionError

'''contain the openstack virtual machine status to openmano status'''
vmStatus2manoFormat={'ACTIVE':'ACTIVE',
                     'PAUSED':'PAUSED',
                     'SUSPENDED': 'SUSPENDED',
                     'SHUTOFF':'INACTIVE',
                     'BUILD':'BUILD',
                     'ERROR':'ERROR','DELETED':'DELETED'
                     }
netStatus2manoFormat={'ACTIVE':'ACTIVE','PAUSED':'PAUSED','INACTIVE':'INACTIVE','BUILD':'BUILD','ERROR':'ERROR','DELETED':'DELETED'
                     }

#global var to have a timeout creating and deleting volumes
volume_timeout = 60
server_timeout = 60

class vimconnector(vimconn.vimconnector):
    def __init__(self, uuid, name, tenant_id, tenant_name, url, url_admin=None, user=None, passwd=None,
                 log_level=None, config={}, persistent_info={}):
        '''using common constructor parameters. In this case
        'url' is the keystone authorization url,
        'url_admin' is not use
        '''
        api_version = config.get('APIversion')
        if api_version and api_version not in ('v3.3', 'v2.0', '2', '3'):
            raise vimconn.vimconnException("Invalid value '{}' for config:APIversion. "
                                           "Allowed values are 'v3.3', 'v2.0', '2' or '3'".format(api_version))
        vimconn.vimconnector.__init__(self, uuid, name, tenant_id, tenant_name, url, url_admin, user, passwd, log_level,
                                      config)

        self.insecure = self.config.get("insecure", False)
        if not url:
            raise TypeError, 'url param can not be NoneType'
        self.persistent_info = persistent_info
        self.session = persistent_info.get('session', {'reload_client': True})
        self.nova = self.session.get('nova')
        self.neutron = self.session.get('neutron')
        self.cinder = self.session.get('cinder')
        self.glance = self.session.get('glance')
        self.keystone = self.session.get('keystone')
        self.api_version3 = self.session.get('api_version3')

        self.logger = logging.getLogger('openmano.vim.openstack')
        if log_level:
            self.logger.setLevel( getattr(logging, log_level) )

    def __getitem__(self, index):
        """Get individuals parameters.
        Throw KeyError"""
        if index == 'project_domain_id':
            return self.config.get("project_domain_id")
        elif index == 'user_domain_id':
            return self.config.get("user_domain_id")
        else:
            return vimconn.vimconnector.__getitem__(self, index)

    def __setitem__(self, index, value):
        """Set individuals parameters and it is marked as dirty so to force connection reload.
        Throw KeyError"""
        if index == 'project_domain_id':
            self.config["project_domain_id"] = value
        elif index == 'user_domain_id':
                self.config["user_domain_id"] = value
        else:
            vimconn.vimconnector.__setitem__(self, index, value)
        self.session['reload_client'] = True

    def _reload_connection(self):
        '''Called before any operation, it check if credentials has changed
        Throw keystoneclient.apiclient.exceptions.AuthorizationFailure
        '''
        #TODO control the timing and possible token timeout, but it seams that python client does this task for us :-) 
        if self.session['reload_client']:
            if self.config.get('APIversion'):
                self.api_version3 = self.config['APIversion'] == 'v3.3' or self.config['APIversion'] == '3'
            else:  # get from ending auth_url that end with v3 or with v2.0
                self.api_version3 =  self.url.split("/")[-1] == "v3"
            self.session['api_version3'] = self.api_version3
            if self.api_version3:
                auth = v3.Password(auth_url=self.url,
                                   username=self.user,
                                   password=self.passwd,
                                   project_name=self.tenant_name,
                                   project_id=self.tenant_id,
                                   project_domain_id=self.config.get('project_domain_id', 'default'),
                                   user_domain_id=self.config.get('user_domain_id', 'default'))
            else:
                auth = v2.Password(auth_url=self.url,
                                   username=self.user,
                                   password=self.passwd,
                                   tenant_name=self.tenant_name,
                                   tenant_id=self.tenant_id)
            sess = session.Session(auth=auth, verify=not self.insecure)
            if self.api_version3:
                self.keystone = ksClient_v3.Client(session=sess)
            else:
                self.keystone = ksClient_v2.Client(session=sess)
            self.session['keystone'] = self.keystone
            self.nova = self.session['nova'] = nClient.Client("2.1", session=sess)
            self.neutron = self.session['neutron'] = neClient.Client('2.0', session=sess)
            self.cinder = self.session['cinder'] = cClient.Client(2, session=sess)
            self.glance = self.session['glance'] = glClient.Client(2, session=sess)
            self.session['reload_client'] = False
            self.persistent_info['session'] = self.session

    def __net_os2mano(self, net_list_dict):
        '''Transform the net openstack format to mano format
        net_list_dict can be a list of dict or a single dict'''
        if type(net_list_dict) is dict:
            net_list_=(net_list_dict,)
        elif type(net_list_dict) is list:
            net_list_=net_list_dict
        else:
            raise TypeError("param net_list_dict must be a list or a dictionary")
        for net in net_list_:
            if net.get('provider:network_type') == "vlan":
                net['type']='data'
            else:
                net['type']='bridge'
                
                
            
    def _format_exception(self, exception):
        '''Transform a keystone, nova, neutron  exception into a vimconn exception'''
        if isinstance(exception, (HTTPException, gl1Exceptions.HTTPException, gl1Exceptions.CommunicationError,
                                  ConnectionError, ksExceptions.ConnectionError, neExceptions.ConnectionFailed
                                  )):
            raise vimconn.vimconnConnectionException(type(exception).__name__ + ": " + str(exception))            
        elif isinstance(exception, (nvExceptions.ClientException, ksExceptions.ClientException, 
                                    neExceptions.NeutronException, nvExceptions.BadRequest)):
            raise vimconn.vimconnUnexpectedResponse(type(exception).__name__ + ": " + str(exception))
        elif isinstance(exception, (neExceptions.NetworkNotFoundClient, nvExceptions.NotFound)):
            raise vimconn.vimconnNotFoundException(type(exception).__name__ + ": " + str(exception))
        elif isinstance(exception, nvExceptions.Conflict):
            raise vimconn.vimconnConflictException(type(exception).__name__ + ": " + str(exception))
        else:  # ()
            raise vimconn.vimconnConnectionException(type(exception).__name__ + ": " + str(exception))

    def get_tenant_list(self, filter_dict={}):
        '''Obtain tenants of VIM
        filter_dict can contain the following keys:
            name: filter by tenant name
            id: filter by tenant uuid/id
            <other VIM specific>
        Returns the tenant list of dictionaries: [{'name':'<name>, 'id':'<id>, ...}, ...]
        '''
        self.logger.debug("Getting tenants from VIM filter: '%s'", str(filter_dict))
        try:
            self._reload_connection()
            if self.api_version3:
                project_class_list = self.keystone.projects.list(name=filter_dict.get("name"))
            else:
                project_class_list = self.keystone.tenants.findall(**filter_dict)
            project_list=[]
            for project in project_class_list:
                if filter_dict.get('id') and filter_dict["id"] != project.id:
                    continue
                project_list.append(project.to_dict())
            return project_list
        except (ksExceptions.ConnectionError, ksExceptions.ClientException, ConnectionError) as e:
            self._format_exception(e)

    def new_tenant(self, tenant_name, tenant_description):
        '''Adds a new tenant to openstack VIM. Returns the tenant identifier'''
        self.logger.debug("Adding a new tenant name: %s", tenant_name)
        try:
            self._reload_connection()
            if self.api_version3:
                project = self.keystone.projects.create(tenant_name, self.config.get("project_domain_id", "default"),
                                                        description=tenant_description, is_domain=False)
            else:
                project = self.keystone.tenants.create(tenant_name, tenant_description)
            return project.id
        except (ksExceptions.ConnectionError, ksExceptions.ClientException, ConnectionError)  as e:
            self._format_exception(e)

    def delete_tenant(self, tenant_id):
        '''Delete a tenant from openstack VIM. Returns the old tenant identifier'''
        self.logger.debug("Deleting tenant %s from VIM", tenant_id)
        try:
            self._reload_connection()
            if self.api_version3:
                self.keystone.projects.delete(tenant_id)
            else:
                self.keystone.tenants.delete(tenant_id)
            return tenant_id
        except (ksExceptions.ConnectionError, ksExceptions.ClientException, ConnectionError)  as e:
            self._format_exception(e)

    def new_network(self,net_name, net_type, ip_profile=None, shared=False, vlan=None):
        '''Adds a tenant network to VIM. Returns the network identifier'''
        self.logger.debug("Adding a new network to VIM name '%s', type '%s'", net_name, net_type)
        #self.logger.debug(">>>>>>>>>>>>>>>>>> IP profile %s", str(ip_profile))
        try:
            new_net = None
            self._reload_connection()
            network_dict = {'name': net_name, 'admin_state_up': True}
            if net_type=="data" or net_type=="ptp":
                if self.config.get('dataplane_physical_net') == None:
                    raise vimconn.vimconnConflictException("You must provide a 'dataplane_physical_net' at config value before creating sriov network")
                network_dict["provider:physical_network"] = self.config['dataplane_physical_net'] #"physnet_sriov" #TODO physical
                network_dict["provider:network_type"]     = "vlan"
                if vlan!=None:
                    network_dict["provider:network_type"] = vlan
            network_dict["shared"]=shared
            new_net=self.neutron.create_network({'network':network_dict})
            #print new_net
            #create subnetwork, even if there is no profile
            if not ip_profile:
                ip_profile = {}
            if 'subnet_address' not in ip_profile:
                #Fake subnet is required
                subnet_rand = random.randint(0, 255)
                ip_profile['subnet_address'] = "192.168.{}.0/24".format(subnet_rand)
            if 'ip_version' not in ip_profile: 
                ip_profile['ip_version'] = "IPv4"
            subnet = {"name":net_name+"-subnet",
                    "network_id": new_net["network"]["id"],
                    "ip_version": 4 if ip_profile['ip_version']=="IPv4" else 6,
                    "cidr": ip_profile['subnet_address']
                    }
            # Gateway should be set to None if not needed. Otherwise openstack assigns one by default
            subnet['gateway_ip'] = ip_profile.get('gateway_address')
            if ip_profile.get('dns_address'):
                subnet['dns_nameservers'] = ip_profile['dns_address'].split(";")
            if 'dhcp_enabled' in ip_profile:
                subnet['enable_dhcp'] = False if ip_profile['dhcp_enabled']=="false" else True
            if 'dhcp_start_address' in ip_profile:
                subnet['allocation_pools'] = []
                subnet['allocation_pools'].append(dict())
                subnet['allocation_pools'][0]['start'] = ip_profile['dhcp_start_address']
            if 'dhcp_count' in ip_profile:
                #parts = ip_profile['dhcp_start_address'].split('.')
                #ip_int = (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])
                ip_int = int(netaddr.IPAddress(ip_profile['dhcp_start_address']))
                ip_int += ip_profile['dhcp_count'] - 1
                ip_str = str(netaddr.IPAddress(ip_int))
                subnet['allocation_pools'][0]['end'] = ip_str
            #self.logger.debug(">>>>>>>>>>>>>>>>>> Subnet: %s", str(subnet))
            self.neutron.create_subnet({"subnet": subnet} )
            return new_net["network"]["id"]
        except (neExceptions.ConnectionFailed, ksExceptions.ClientException, neExceptions.NeutronException, ConnectionError) as e:
            if new_net:
                self.neutron.delete_network(new_net['network']['id'])
            self._format_exception(e)

    def get_network_list(self, filter_dict={}):
        '''Obtain tenant networks of VIM
        Filter_dict can be:
            name: network name
            id: network uuid
            shared: boolean
            tenant_id: tenant
            admin_state_up: boolean
            status: 'ACTIVE'
        Returns the network list of dictionaries
        '''
        self.logger.debug("Getting network from VIM filter: '%s'", str(filter_dict))
        try:
            self._reload_connection()
            if self.api_version3 and "tenant_id" in filter_dict:
                filter_dict['project_id'] = filter_dict.pop('tenant_id') #TODO check
            net_dict=self.neutron.list_networks(**filter_dict)
            net_list=net_dict["networks"]
            self.__net_os2mano(net_list)
            return net_list
        except (neExceptions.ConnectionFailed, ksExceptions.ClientException, neExceptions.NeutronException, ConnectionError) as e:
            self._format_exception(e)

    def get_network(self, net_id):
        '''Obtain details of network from VIM
        Returns the network information from a network id'''
        self.logger.debug(" Getting tenant network %s from VIM", net_id)
        filter_dict={"id": net_id}
        net_list = self.get_network_list(filter_dict)
        if len(net_list)==0:
            raise vimconn.vimconnNotFoundException("Network '{}' not found".format(net_id))
        elif len(net_list)>1:
            raise vimconn.vimconnConflictException("Found more than one network with this criteria")
        net = net_list[0]
        subnets=[]
        for subnet_id in net.get("subnets", () ):
            try:
                subnet = self.neutron.show_subnet(subnet_id)
            except Exception as e:
                self.logger.error("osconnector.get_network(): Error getting subnet %s %s" % (net_id, str(e)))
                subnet = {"id": subnet_id, "fault": str(e)}
            subnets.append(subnet)
        net["subnets"] = subnets
        net["encapsulation"] = net.get('provider:network_type')
        net["segmentation_id"] = net.get('provider:segmentation_id')
        return net

    def delete_network(self, net_id):
        '''Deletes a tenant network from VIM. Returns the old network identifier'''
        self.logger.debug("Deleting network '%s' from VIM", net_id)
        try:
            self._reload_connection()
            #delete VM ports attached to this networks before the network
            ports = self.neutron.list_ports(network_id=net_id)
            for p in ports['ports']:
                try:
                    self.neutron.delete_port(p["id"])
                except Exception as e:
                    self.logger.error("Error deleting port %s: %s", p["id"], str(e))
            self.neutron.delete_network(net_id)
            return net_id
        except (neExceptions.ConnectionFailed, neExceptions.NetworkNotFoundClient, neExceptions.NeutronException,
                ksExceptions.ClientException, neExceptions.NeutronException, ConnectionError) as e:
            self._format_exception(e)

    def refresh_nets_status(self, net_list):
        '''Get the status of the networks
           Params: the list of network identifiers
           Returns a dictionary with:
                net_id:         #VIM id of this network
                    status:     #Mandatory. Text with one of:
                                #  DELETED (not found at vim)
                                #  VIM_ERROR (Cannot connect to VIM, VIM response error, ...) 
                                #  OTHER (Vim reported other status not understood)
                                #  ERROR (VIM indicates an ERROR status)
                                #  ACTIVE, INACTIVE, DOWN (admin down), 
                                #  BUILD (on building process)
                                #
                    error_msg:  #Text with VIM error message, if any. Or the VIM connection ERROR 
                    vim_info:   #Text with plain information obtained from vim (yaml.safe_dump)

        '''        
        net_dict={}
        for net_id in net_list:
            net = {}
            try:
                net_vim = self.get_network(net_id)
                if net_vim['status'] in netStatus2manoFormat:
                    net["status"] = netStatus2manoFormat[ net_vim['status'] ]
                else:
                    net["status"] = "OTHER"
                    net["error_msg"] = "VIM status reported " + net_vim['status']
                    
                if net['status'] == "ACTIVE" and not net_vim['admin_state_up']:
                    net['status'] = 'DOWN'
                try:
                    net['vim_info'] = yaml.safe_dump(net_vim, default_flow_style=True, width=256)
                except yaml.representer.RepresenterError:
                    net['vim_info'] = str(net_vim)
                if net_vim.get('fault'):  #TODO
                    net['error_msg'] = str(net_vim['fault'])
            except vimconn.vimconnNotFoundException as e:
                self.logger.error("Exception getting net status: %s", str(e))
                net['status'] = "DELETED"
                net['error_msg'] = str(e)
            except vimconn.vimconnException as e:
                self.logger.error("Exception getting net status: %s", str(e))
                net['status'] = "VIM_ERROR"
                net['error_msg'] = str(e)
            net_dict[net_id] = net
        return net_dict

    def get_flavor(self, flavor_id):
        '''Obtain flavor details from the  VIM. Returns the flavor dict details'''
        self.logger.debug("Getting flavor '%s'", flavor_id)
        try:
            self._reload_connection()
            flavor = self.nova.flavors.find(id=flavor_id)
            #TODO parse input and translate to VIM format (openmano_schemas.new_vminstance_response_schema)
            return flavor.to_dict()
        except (nvExceptions.NotFound, nvExceptions.ClientException, ksExceptions.ClientException, ConnectionError) as e:
            self._format_exception(e)

    def get_flavor_id_from_data(self, flavor_dict):
        """Obtain flavor id that match the flavor description
           Returns the flavor_id or raises a vimconnNotFoundException
           flavor_dict: contains the required ram, vcpus, disk
           If 'use_existing_flavors' is set to True at config, the closer flavor that provides same or more ram, vcpus
                and disk is returned. Otherwise a flavor with exactly same ram, vcpus and disk is returned or a
                vimconnNotFoundException is raised
        """
        exact_match = False if self.config.get('use_existing_flavors') else True
        try:
            self._reload_connection()
            flavor_candidate_id = None
            flavor_candidate_data = (10000, 10000, 10000)
            flavor_target = (flavor_dict["ram"], flavor_dict["vcpus"], flavor_dict["disk"])
            # numa=None
            numas = flavor_dict.get("extended", {}).get("numas")
            if numas:
                #TODO
                raise vimconn.vimconnNotFoundException("Flavor with EPA still not implemted")
                # if len(numas) > 1:
                #     raise vimconn.vimconnNotFoundException("Cannot find any flavor with more than one numa")
                # numa=numas[0]
                # numas = extended.get("numas")
            for flavor in self.nova.flavors.list():
                epa = flavor.get_keys()
                if epa:
                    continue
                    # TODO
                flavor_data = (flavor.ram, flavor.vcpus, flavor.disk)
                if flavor_data == flavor_target:
                    return flavor.id
                elif not exact_match and flavor_target < flavor_data < flavor_candidate_data:
                    flavor_candidate_id = flavor.id
                    flavor_candidate_data = flavor_data
            if not exact_match and flavor_candidate_id:
                return flavor_candidate_id
            raise vimconn.vimconnNotFoundException("Cannot find any flavor matching '{}'".format(str(flavor_dict)))
        except (nvExceptions.NotFound, nvExceptions.ClientException, ksExceptions.ClientException, ConnectionError) as e:
            self._format_exception(e)


    def new_flavor(self, flavor_data, change_name_if_used=True):
        '''Adds a tenant flavor to openstack VIM
        if change_name_if_used is True, it will change name in case of conflict, because it is not supported name repetition
        Returns the flavor identifier
        '''
        self.logger.debug("Adding flavor '%s'", str(flavor_data))
        retry=0
        max_retries=3
        name_suffix = 0
        name=flavor_data['name']
        while retry<max_retries:
            retry+=1
            try:
                self._reload_connection()
                if change_name_if_used:
                    #get used names
                    fl_names=[]
                    fl=self.nova.flavors.list()
                    for f in fl:
                        fl_names.append(f.name)
                    while name in fl_names:
                        name_suffix += 1
                        name = flavor_data['name']+"-" + str(name_suffix)
                        
                ram = flavor_data.get('ram',64)
                vcpus = flavor_data.get('vcpus',1)
                numa_properties=None

                extended = flavor_data.get("extended")
                if extended:
                    numas=extended.get("numas")
                    if numas:
                        numa_nodes = len(numas)
                        if numa_nodes > 1:
                            return -1, "Can not add flavor with more than one numa"
                        numa_properties = {"hw:numa_nodes":str(numa_nodes)}
                        numa_properties["hw:mem_page_size"] = "large"
                        numa_properties["hw:cpu_policy"] = "dedicated"
                        numa_properties["hw:numa_mempolicy"] = "strict"
                        for numa in numas:
                            #overwrite ram and vcpus
                            ram = numa['memory']*1024
                            #See for reference: https://specs.openstack.org/openstack/nova-specs/specs/mitaka/implemented/virt-driver-cpu-thread-pinning.html
                            if 'paired-threads' in numa:
                                vcpus = numa['paired-threads']*2
                                #cpu_thread_policy "require" implies that the compute node must have an STM architecture
                                numa_properties["hw:cpu_thread_policy"] = "require"
                                numa_properties["hw:cpu_policy"] = "dedicated"
                            elif 'cores' in numa:
                                vcpus = numa['cores']
                                # cpu_thread_policy "prefer" implies that the host must not have an SMT architecture, or a non-SMT architecture will be emulated
                                numa_properties["hw:cpu_thread_policy"] = "isolate"
                                numa_properties["hw:cpu_policy"] = "dedicated"
                            elif 'threads' in numa:
                                vcpus = numa['threads']
                                # cpu_thread_policy "prefer" implies that the host may or may not have an SMT architecture
                                numa_properties["hw:cpu_thread_policy"] = "prefer"
                                numa_properties["hw:cpu_policy"] = "dedicated"
                            # for interface in numa.get("interfaces",() ):
                            #     if interface["dedicated"]=="yes":
                            #         raise vimconn.vimconnException("Passthrough interfaces are not supported for the openstack connector", http_code=vimconn.HTTP_Service_Unavailable)
                            #     #TODO, add the key 'pci_passthrough:alias"="<label at config>:<number ifaces>"' when a way to connect it is available
                                
                #create flavor                 
                new_flavor=self.nova.flavors.create(name, 
                                ram, 
                                vcpus, 
                                flavor_data.get('disk',1),
                                is_public=flavor_data.get('is_public', True)
                            ) 
                #add metadata
                if numa_properties:
                    new_flavor.set_keys(numa_properties)
                return new_flavor.id
            except nvExceptions.Conflict as e:
                if change_name_if_used and retry < max_retries:
                    continue
                self._format_exception(e)
            #except nvExceptions.BadRequest as e:
            except (ksExceptions.ClientException, nvExceptions.ClientException, ConnectionError) as e:
                self._format_exception(e)

    def delete_flavor(self,flavor_id):
        '''Deletes a tenant flavor from openstack VIM. Returns the old flavor_id
        '''
        try:
            self._reload_connection()
            self.nova.flavors.delete(flavor_id)
            return flavor_id
        #except nvExceptions.BadRequest as e:
        except (nvExceptions.NotFound, ksExceptions.ClientException, nvExceptions.ClientException, ConnectionError) as e:
            self._format_exception(e)

    def new_image(self,image_dict):
        '''
        Adds a tenant image to VIM. imge_dict is a dictionary with:
            name: name
            disk_format: qcow2, vhd, vmdk, raw (by default), ...
            location: path or URI
            public: "yes" or "no"
            metadata: metadata of the image
        Returns the image_id
        '''
        # ALF TODO: revise and change for the new method or session
        #using version 1 of glance client
        glancev1 = gl1Client.Client('1',self.glance_endpoint, token=self.keystone.auth_token, **self.k_creds)  #TODO check k_creds vs n_creds
        retry=0
        max_retries=3
        while retry<max_retries:
            retry+=1
            try:
                self._reload_connection()
                #determine format  http://docs.openstack.org/developer/glance/formats.html
                if "disk_format" in image_dict:
                    disk_format=image_dict["disk_format"]
                else: #autodiscover based on extension
                    if image_dict['location'][-6:]==".qcow2":
                        disk_format="qcow2"
                    elif image_dict['location'][-4:]==".vhd":
                        disk_format="vhd"
                    elif image_dict['location'][-5:]==".vmdk":
                        disk_format="vmdk"
                    elif image_dict['location'][-4:]==".vdi":
                        disk_format="vdi"
                    elif image_dict['location'][-4:]==".iso":
                        disk_format="iso"
                    elif image_dict['location'][-4:]==".aki":
                        disk_format="aki"
                    elif image_dict['location'][-4:]==".ari":
                        disk_format="ari"
                    elif image_dict['location'][-4:]==".ami":
                        disk_format="ami"
                    else:
                        disk_format="raw"
                self.logger.debug("new_image: '%s' loading from '%s'", image_dict['name'], image_dict['location'])
                if image_dict['location'][0:4]=="http":
                    new_image = glancev1.images.create(name=image_dict['name'], is_public=image_dict.get('public',"yes")=="yes",
                            container_format="bare", location=image_dict['location'], disk_format=disk_format)
                else: #local path
                    with open(image_dict['location']) as fimage:
                        new_image = glancev1.images.create(name=image_dict['name'], is_public=image_dict.get('public',"yes")=="yes",
                            container_format="bare", data=fimage, disk_format=disk_format)
                #insert metadata. We cannot use 'new_image.properties.setdefault' 
                #because nova and glance are "INDEPENDENT" and we are using nova for reading metadata
                new_image_nova=self.nova.images.find(id=new_image.id)
                new_image_nova.metadata.setdefault('location',image_dict['location'])
                metadata_to_load = image_dict.get('metadata')
                if metadata_to_load:
                    for k,v in yaml.load(metadata_to_load).iteritems():
                        new_image_nova.metadata.setdefault(k,v)
                return new_image.id
            except (nvExceptions.Conflict, ksExceptions.ClientException, nvExceptions.ClientException) as e:
                self._format_exception(e)
            except (HTTPException, gl1Exceptions.HTTPException, gl1Exceptions.CommunicationError, ConnectionError) as e:
                if retry==max_retries:
                    continue
                self._format_exception(e)
            except IOError as e:  #can not open the file
                raise vimconn.vimconnConnectionException(type(e).__name__ + ": " + str(e)+ " for " + image_dict['location'],
                                                         http_code=vimconn.HTTP_Bad_Request)
     
    def delete_image(self, image_id):
        '''Deletes a tenant image from openstack VIM. Returns the old id
        '''
        try:
            self._reload_connection()
            self.nova.images.delete(image_id)
            return image_id
        except (nvExceptions.NotFound, ksExceptions.ClientException, nvExceptions.ClientException, gl1Exceptions.CommunicationError, ConnectionError) as e: #TODO remove
            self._format_exception(e)

    def get_image_id_from_path(self, path):
        '''Get the image id from image path in the VIM database. Returns the image_id''' 
        try:
            self._reload_connection()
            images = self.nova.images.list()
            for image in images:
                if image.metadata.get("location")==path:
                    return image.id
            raise vimconn.vimconnNotFoundException("image with location '{}' not found".format( path))
        except (ksExceptions.ClientException, nvExceptions.ClientException, gl1Exceptions.CommunicationError, ConnectionError) as e:
            self._format_exception(e)
        
    def get_image_list(self, filter_dict={}):
        '''Obtain tenant images from VIM
        Filter_dict can be:
            id: image id
            name: image name
            checksum: image checksum
        Returns the image list of dictionaries:
            [{<the fields at Filter_dict plus some VIM specific>}, ...]
            List can be empty
        '''
        self.logger.debug("Getting image list from VIM filter: '%s'", str(filter_dict))
        try:
            self._reload_connection()
            filter_dict_os=filter_dict.copy()
            #First we filter by the available filter fields: name, id. The others are removed.
            filter_dict_os.pop('checksum',None)
            image_list=self.nova.images.findall(**filter_dict_os)
            if len(image_list)==0:
                return []
            #Then we filter by the rest of filter fields: checksum
            filtered_list = []
            for image in image_list:
                image_class=self.glance.images.get(image.id)
                if 'checksum' not in filter_dict or image_class['checksum']==filter_dict.get('checksum'):
                    filtered_list.append(image_class.copy())
            return filtered_list
        except (ksExceptions.ClientException, nvExceptions.ClientException, gl1Exceptions.CommunicationError, ConnectionError) as e:
            self._format_exception(e)

    def new_vminstance(self,name,description,start,image_id,flavor_id,net_list,cloud_config=None,disk_list=None):
        '''Adds a VM instance to VIM
        Params:
            start: indicates if VM must start or boot in pause mode. Ignored
            image_id,flavor_id: iamge and flavor uuid
            net_list: list of interfaces, each one is a dictionary with:
                name:
                net_id: network uuid to connect
                vpci: virtual vcpi to assign, ignored because openstack lack #TODO
                model: interface model, ignored #TODO
                mac_address: used for  SR-IOV ifaces #TODO for other types
                use: 'data', 'bridge',  'mgmt'
                type: 'virtual', 'PF', 'VF', 'VFnotShared'
                vim_id: filled/added by this function
                floating_ip: True/False (or it can be None)
                #TODO ip, security groups
        Returns the instance identifier
        '''
        self.logger.debug("new_vminstance input: image='%s' flavor='%s' nics='%s'",image_id, flavor_id,str(net_list))
        try:
            metadata={}
            net_list_vim=[]
            external_network=[] #list of external networks to be connected to instance, later on used to create floating_ip
            self._reload_connection()
            metadata_vpci={} #For a specific neutron plugin 
            for net in net_list:
                if not net.get("net_id"): #skip non connected iface
                    continue

                port_dict={
                    "network_id": net["net_id"],
                    "name": net.get("name"),
                    "admin_state_up": True
                }
                if net["type"]=="virtual":
                    if "vpci" in net:
                        metadata_vpci[ net["net_id"] ] = [[ net["vpci"], "" ]]
                elif net["type"]=="VF": # for VF
                    if "vpci" in net:
                        if "VF" not in metadata_vpci:
                            metadata_vpci["VF"]=[]
                        metadata_vpci["VF"].append([ net["vpci"], "" ])
                    port_dict["binding:vnic_type"]="direct"
                else: #For PT
                    if "vpci" in net:
                        if "PF" not in metadata_vpci:
                            metadata_vpci["PF"]=[]
                        metadata_vpci["PF"].append([ net["vpci"], "" ])
                    port_dict["binding:vnic_type"]="direct-physical"
                if not port_dict["name"]:
                    port_dict["name"]=name
                if net.get("mac_address"):
                    port_dict["mac_address"]=net["mac_address"]
                if net.get("port_security") == False:
                    port_dict["port_security_enabled"]=net["port_security"]
                new_port = self.neutron.create_port({"port": port_dict })
                net["mac_adress"] = new_port["port"]["mac_address"]
                net["vim_id"] = new_port["port"]["id"]
                net["ip"] = new_port["port"].get("fixed_ips", [{}])[0].get("ip_address")
                net_list_vim.append({"port-id": new_port["port"]["id"]})

                if net.get('floating_ip', False):
                    net['exit_on_floating_ip_error'] = True
                    external_network.append(net)
                elif net['use'] == 'mgmt' and self.config.get('use_floating_ip'):
                    net['exit_on_floating_ip_error'] = False
                    external_network.append(net)

            if metadata_vpci:
                metadata = {"pci_assignement": json.dumps(metadata_vpci)}
                if len(metadata["pci_assignement"]) >255:
                    #limit the metadata size
                    #metadata["pci_assignement"] = metadata["pci_assignement"][0:255]
                    self.logger.warn("Metadata deleted since it exceeds the expected length (255) ")
                    metadata = {}
            
            self.logger.debug("name '%s' image_id '%s'flavor_id '%s' net_list_vim '%s' description '%s' metadata %s",
                              name, image_id, flavor_id, str(net_list_vim), description, str(metadata))
            
            security_groups   = self.config.get('security_groups')
            if type(security_groups) is str:
                security_groups = ( security_groups, )
            #cloud config
            userdata=None
            config_drive = None
            if isinstance(cloud_config, dict):
                if cloud_config.get("user-data"):
                    userdata=cloud_config["user-data"]
                if cloud_config.get("boot-data-drive") != None:
                    config_drive = cloud_config["boot-data-drive"]
                if cloud_config.get("config-files") or cloud_config.get("users") or cloud_config.get("key-pairs"):
                    if userdata:
                        raise vimconn.vimconnConflictException("Cloud-config cannot contain both 'userdata' and 'config-files'/'users'/'key-pairs'")
                    userdata_dict={}
                    #default user
                    if cloud_config.get("key-pairs"):
                        userdata_dict["ssh-authorized-keys"] = cloud_config["key-pairs"]
                        userdata_dict["users"] = [{"default": None, "ssh-authorized-keys": cloud_config["key-pairs"] }]
                    if cloud_config.get("users"):
                        if "users" not in userdata_dict:
                            userdata_dict["users"] = [ "default" ]
                        for user in cloud_config["users"]:
                            user_info = {
                                "name" : user["name"],
                                "sudo": "ALL = (ALL)NOPASSWD:ALL"
                            }
                            if "user-info" in user:
                                user_info["gecos"] = user["user-info"]
                            if user.get("key-pairs"):
                                user_info["ssh-authorized-keys"] = user["key-pairs"]
                            userdata_dict["users"].append(user_info)

                    if cloud_config.get("config-files"):
                        userdata_dict["write_files"] = []
                        for file in cloud_config["config-files"]:
                            file_info = {
                                "path" : file["dest"],
                                "content": file["content"]
                            }
                            if file.get("encoding"):
                                file_info["encoding"] = file["encoding"]
                            if file.get("permissions"):
                                file_info["permissions"] = file["permissions"]
                            if file.get("owner"):
                                file_info["owner"] = file["owner"]
                            userdata_dict["write_files"].append(file_info)
                    userdata = "#cloud-config\n"
                    userdata += yaml.safe_dump(userdata_dict, indent=4, default_flow_style=False)
                self.logger.debug("userdata: %s", userdata)
            elif isinstance(cloud_config, str):
                userdata = cloud_config

            #Create additional volumes in case these are present in disk_list
            block_device_mapping = None
            base_disk_index = ord('b')
            if disk_list != None:
                block_device_mapping = dict()
                for disk in disk_list:
                    if 'image_id' in disk:
                        volume = self.cinder.volumes.create(size = disk['size'],name = name + '_vd' +
                                    chr(base_disk_index), imageRef = disk['image_id'])
                    else:
                        volume = self.cinder.volumes.create(size=disk['size'], name=name + '_vd' +
                                    chr(base_disk_index))
                    block_device_mapping['_vd' +  chr(base_disk_index)] = volume.id
                    base_disk_index += 1

                #wait until volumes are with status available
                keep_waiting = True
                elapsed_time = 0
                while keep_waiting and elapsed_time < volume_timeout:
                    keep_waiting = False
                    for volume_id in block_device_mapping.itervalues():
                        if self.cinder.volumes.get(volume_id).status != 'available':
                            keep_waiting = True
                    if keep_waiting:
                        time.sleep(1)
                        elapsed_time += 1

                #if we exceeded the timeout rollback
                if elapsed_time >= volume_timeout:
                    #delete the volumes we just created
                    for volume_id in block_device_mapping.itervalues():
                        self.cinder.volumes.delete(volume_id)

                    #delete ports we just created
                    for net_item  in net_list_vim:
                        if 'port-id' in net_item:
                            self.neutron.delete_port(net_item['port-id'])

                    raise vimconn.vimconnException('Timeout creating volumes for instance ' + name,
                                                   http_code=vimconn.HTTP_Request_Timeout)

            self.logger.debug("nova.servers.create({}, {}, {}, nics={}, meta={}, security_groups={}," \
                                              "availability_zone={}, key_name={}, userdata={}, config_drive={}, " \
                                              "block_device_mapping={})".format(name, image_id, flavor_id, net_list_vim,
                                                metadata, security_groups, self.config.get('availability_zone'),
                                                self.config.get('keypair'), userdata, config_drive, block_device_mapping))
            server = self.nova.servers.create(name, image_id, flavor_id, nics=net_list_vim, meta=metadata,
                                              security_groups=security_groups,
                                              availability_zone=self.config.get('availability_zone'),
                                              key_name=self.config.get('keypair'),
                                              userdata=userdata,
                                              config_drive = config_drive,
                                              block_device_mapping = block_device_mapping
                                              )  # , description=description)
            #print "DONE :-)", server
            pool_id = None
            floating_ips = self.neutron.list_floatingips().get("floatingips", ())
            for floating_network in external_network:
                try:
                    # wait until vm is active
                    elapsed_time = 0
                    while elapsed_time < server_timeout:
                        status = self.nova.servers.get(server.id).status
                        if status == 'ACTIVE':
                            break
                        time.sleep(1)
                        elapsed_time += 1

                    #if we exceeded the timeout rollback
                    if elapsed_time >= server_timeout:
                        raise vimconn.vimconnException('Timeout creating instance ' + name,
                                                       http_code=vimconn.HTTP_Request_Timeout)

                    assigned = False
                    while(assigned == False):
                        if floating_ips:
                            ip = floating_ips.pop(0)
                            if not ip.get("port_id", False) and ip.get('tenant_id') == server.tenant_id:
                                free_floating_ip = ip.get("floating_ip_address")
                                try:
                                    fix_ip = floating_network.get('ip')
                                    server.add_floating_ip(free_floating_ip, fix_ip)
                                    assigned = True
                                except Exception as e:
                                    raise vimconn.vimconnException(type(e).__name__ + ": Cannot create floating_ip "+  str(e), http_code=vimconn.HTTP_Conflict)
                        else:
                            #Find the external network
                            external_nets = list()
                            for net in self.neutron.list_networks()['networks']:
                                if net['router:external']:
                                        external_nets.append(net)

                            if len(external_nets) == 0:
                                raise vimconn.vimconnException("Cannot create floating_ip automatically since no external "
                                                               "network is present",
                                                                http_code=vimconn.HTTP_Conflict)
                            if len(external_nets) > 1:
                                raise vimconn.vimconnException("Cannot create floating_ip automatically since multiple "
                                                               "external networks are present",
                                                               http_code=vimconn.HTTP_Conflict)

                            pool_id = external_nets[0].get('id')
                            param = {'floatingip': {'floating_network_id': pool_id, 'tenant_id': server.tenant_id}}
                            try:
                                #self.logger.debug("Creating floating IP")
                                new_floating_ip = self.neutron.create_floatingip(param)
                                free_floating_ip = new_floating_ip['floatingip']['floating_ip_address']
                                fix_ip = floating_network.get('ip')
                                server.add_floating_ip(free_floating_ip, fix_ip)
                                assigned=True
                            except Exception as e:
                                raise vimconn.vimconnException(type(e).__name__ + ": Cannot assign floating_ip "+  str(e), http_code=vimconn.HTTP_Conflict)
                except Exception as e:
                    if not floating_network['exit_on_floating_ip_error']:
                        self.logger.warn("Cannot create floating_ip. %s", str(e))
                        continue
                    self.delete_vminstance(server.id)
                    raise

            return server.id
#        except nvExceptions.NotFound as e:
#            error_value=-vimconn.HTTP_Not_Found
#            error_text= "vm instance %s not found" % vm_id
        except (ksExceptions.ClientException, nvExceptions.ClientException, ConnectionError) as e:
            # delete the volumes we just created
            if block_device_mapping != None:
                for volume_id in block_device_mapping.itervalues():
                    self.cinder.volumes.delete(volume_id)

            # delete ports we just created
            for net_item in net_list_vim:
                if 'port-id' in net_item:
                    self.neutron.delete_port(net_item['port-id'])
            self._format_exception(e)
        except TypeError as e:
            raise vimconn.vimconnException(type(e).__name__ + ": "+  str(e), http_code=vimconn.HTTP_Bad_Request)

    def get_vminstance(self,vm_id):
        '''Returns the VM instance information from VIM'''
        #self.logger.debug("Getting VM from VIM")
        try:
            self._reload_connection()
            server = self.nova.servers.find(id=vm_id)
            #TODO parse input and translate to VIM format (openmano_schemas.new_vminstance_response_schema)
            return server.to_dict()
        except (ksExceptions.ClientException, nvExceptions.ClientException, nvExceptions.NotFound, ConnectionError) as e:
            self._format_exception(e)

    def get_vminstance_console(self,vm_id, console_type="vnc"):
        '''
        Get a console for the virtual machine
        Params:
            vm_id: uuid of the VM
            console_type, can be:
                "novnc" (by default), "xvpvnc" for VNC types, 
                "rdp-html5" for RDP types, "spice-html5" for SPICE types
        Returns dict with the console parameters:
                protocol: ssh, ftp, http, https, ...
                server:   usually ip address 
                port:     the http, ssh, ... port 
                suffix:   extra text, e.g. the http path and query string   
        '''
        self.logger.debug("Getting VM CONSOLE from VIM")
        try:
            self._reload_connection()
            server = self.nova.servers.find(id=vm_id)
            if console_type == None or console_type == "novnc":
                console_dict = server.get_vnc_console("novnc")
            elif console_type == "xvpvnc":
                console_dict = server.get_vnc_console(console_type)
            elif console_type == "rdp-html5":
                console_dict = server.get_rdp_console(console_type)
            elif console_type == "spice-html5":
                console_dict = server.get_spice_console(console_type)
            else:
                raise vimconn.vimconnException("console type '{}' not allowed".format(console_type), http_code=vimconn.HTTP_Bad_Request)
            
            console_dict1 = console_dict.get("console")
            if console_dict1:
                console_url = console_dict1.get("url")
                if console_url:
                    #parse console_url
                    protocol_index = console_url.find("//")
                    suffix_index = console_url[protocol_index+2:].find("/") + protocol_index+2
                    port_index = console_url[protocol_index+2:suffix_index].find(":") + protocol_index+2
                    if protocol_index < 0 or port_index<0 or suffix_index<0:
                        return -vimconn.HTTP_Internal_Server_Error, "Unexpected response from VIM"
                    console_dict={"protocol": console_url[0:protocol_index],
                                  "server":   console_url[protocol_index+2:port_index], 
                                  "port":     console_url[port_index:suffix_index], 
                                  "suffix":   console_url[suffix_index+1:] 
                                  }
                    protocol_index += 2
                    return console_dict
            raise vimconn.vimconnUnexpectedResponse("Unexpected response from VIM")
            
        except (nvExceptions.NotFound, ksExceptions.ClientException, nvExceptions.ClientException, nvExceptions.BadRequest, ConnectionError) as e:
            self._format_exception(e)

    def delete_vminstance(self, vm_id):
        '''Removes a VM instance from VIM. Returns the old identifier
        '''
        #print "osconnector: Getting VM from VIM"
        try:
            self._reload_connection()
            #delete VM ports attached to this networks before the virtual machine
            ports = self.neutron.list_ports(device_id=vm_id)
            for p in ports['ports']:
                try:
                    self.neutron.delete_port(p["id"])
                except Exception as e:
                    self.logger.error("Error deleting port: " + type(e).__name__ + ": "+  str(e))

            #commented because detaching the volumes makes the servers.delete not work properly ?!?
            #dettach volumes attached
            server = self.nova.servers.get(vm_id)
            volumes_attached_dict = server._info['os-extended-volumes:volumes_attached']
            #for volume in volumes_attached_dict:
            #    self.cinder.volumes.detach(volume['id'])

            self.nova.servers.delete(vm_id)

            #delete volumes.
            #Although having detached them should have them  in active status
            #we ensure in this loop
            keep_waiting = True
            elapsed_time = 0
            while keep_waiting and elapsed_time < volume_timeout:
                keep_waiting = False
                for volume in volumes_attached_dict:
                    if self.cinder.volumes.get(volume['id']).status != 'available':
                        keep_waiting = True
                    else:
                        self.cinder.volumes.delete(volume['id'])
                if keep_waiting:
                    time.sleep(1)
                    elapsed_time += 1

            return vm_id
        except (nvExceptions.NotFound, ksExceptions.ClientException, nvExceptions.ClientException, ConnectionError) as e:
            self._format_exception(e)
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception

    def refresh_vms_status(self, vm_list):
        '''Get the status of the virtual machines and their interfaces/ports
           Params: the list of VM identifiers
           Returns a dictionary with:
                vm_id:          #VIM id of this Virtual Machine
                    status:     #Mandatory. Text with one of:
                                #  DELETED (not found at vim)
                                #  VIM_ERROR (Cannot connect to VIM, VIM response error, ...) 
                                #  OTHER (Vim reported other status not understood)
                                #  ERROR (VIM indicates an ERROR status)
                                #  ACTIVE, PAUSED, SUSPENDED, INACTIVE (not running), 
                                #  CREATING (on building process), ERROR
                                #  ACTIVE:NoMgmtIP (Active but any of its interface has an IP address
                                #
                    error_msg:  #Text with VIM error message, if any. Or the VIM connection ERROR 
                    vim_info:   #Text with plain information obtained from vim (yaml.safe_dump)
                    interfaces:
                     -  vim_info:         #Text with plain information obtained from vim (yaml.safe_dump)
                        mac_address:      #Text format XX:XX:XX:XX:XX:XX
                        vim_net_id:       #network id where this interface is connected
                        vim_interface_id: #interface/port VIM id
                        ip_address:       #null, or text with IPv4, IPv6 address
                        compute_node:     #identification of compute node where PF,VF interface is allocated
                        pci:              #PCI address of the NIC that hosts the PF,VF
                        vlan:             #physical VLAN used for VF
        '''
        vm_dict={}
        self.logger.debug("refresh_vms status: Getting tenant VM instance information from VIM")
        for vm_id in vm_list:
            vm={}
            try:
                vm_vim = self.get_vminstance(vm_id)
                if vm_vim['status'] in vmStatus2manoFormat:
                    vm['status']    =  vmStatus2manoFormat[ vm_vim['status'] ]
                else:
                    vm['status']    = "OTHER"
                    vm['error_msg'] = "VIM status reported " + vm_vim['status']
                try:
                    vm['vim_info']  = yaml.safe_dump(vm_vim, default_flow_style=True, width=256)
                except yaml.representer.RepresenterError:
                    vm['vim_info'] = str(vm_vim)
                vm["interfaces"] = []
                if vm_vim.get('fault'):
                    vm['error_msg'] = str(vm_vim['fault'])
                #get interfaces
                try:
                    self._reload_connection()
                    port_dict=self.neutron.list_ports(device_id=vm_id)
                    for port in port_dict["ports"]:
                        interface={}
                        try:
                            interface['vim_info'] = yaml.safe_dump(port, default_flow_style=True, width=256)
                        except yaml.representer.RepresenterError:
                            interface['vim_info'] = str(port)
                        interface["mac_address"] = port.get("mac_address")
                        interface["vim_net_id"] = port["network_id"]
                        interface["vim_interface_id"] = port["id"]
                        # check if OS-EXT-SRV-ATTR:host is there, 
                        # in case of non-admin credentials, it will be missing
                        if vm_vim.get('OS-EXT-SRV-ATTR:host'):
                            interface["compute_node"] = vm_vim['OS-EXT-SRV-ATTR:host']
                        interface["pci"] = None

                        # check if binding:profile is there, 
                        # in case of non-admin credentials, it will be missing
                        if port.get('binding:profile'):
                            if port['binding:profile'].get('pci_slot'):
                                # TODO: At the moment sr-iov pci addresses are converted to PF pci addresses by setting the slot to 0x00
                                # TODO: This is just a workaround valid for niantinc. Find a better way to do so
                                #   CHANGE DDDD:BB:SS.F to DDDD:BB:00.(F%2)   assuming there are 2 ports per nic
                                pci = port['binding:profile']['pci_slot']
                                # interface["pci"] = pci[:-4] + "00." + str(int(pci[-1]) % 2)
                                interface["pci"] = pci
                        interface["vlan"] = None
                        #if network is of type vlan and port is of type direct (sr-iov) then set vlan id
                        network = self.neutron.show_network(port["network_id"])
                        if network['network'].get('provider:network_type') == 'vlan' and \
                            port.get("binding:vnic_type") == "direct":
                            interface["vlan"] = network['network'].get('provider:segmentation_id')
                        ips=[]
                        #look for floating ip address
                        floating_ip_dict = self.neutron.list_floatingips(port_id=port["id"])
                        if floating_ip_dict.get("floatingips"):
                            ips.append(floating_ip_dict["floatingips"][0].get("floating_ip_address") )

                        for subnet in port["fixed_ips"]:
                            ips.append(subnet["ip_address"])
                        interface["ip_address"] = ";".join(ips)
                        vm["interfaces"].append(interface)
                except Exception as e:
                    self.logger.error("Error getting vm interface information " + type(e).__name__ + ": "+  str(e))
            except vimconn.vimconnNotFoundException as e:
                self.logger.error("Exception getting vm status: %s", str(e))
                vm['status'] = "DELETED"
                vm['error_msg'] = str(e)
            except vimconn.vimconnException as e:
                self.logger.error("Exception getting vm status: %s", str(e))
                vm['status'] = "VIM_ERROR"
                vm['error_msg'] = str(e)
            vm_dict[vm_id] = vm
        return vm_dict
    
    def action_vminstance(self, vm_id, action_dict):
        '''Send and action over a VM instance from VIM
        Returns the vm_id if the action was successfully sent to the VIM'''
        self.logger.debug("Action over VM '%s': %s", vm_id, str(action_dict))
        try:
            self._reload_connection()
            server = self.nova.servers.find(id=vm_id)
            if "start" in action_dict:
                if action_dict["start"]=="rebuild":  
                    server.rebuild()
                else:
                    if server.status=="PAUSED":
                        server.unpause()
                    elif server.status=="SUSPENDED":
                        server.resume()
                    elif server.status=="SHUTOFF":
                        server.start()
            elif "pause" in action_dict:
                server.pause()
            elif "resume" in action_dict:
                server.resume()
            elif "shutoff" in action_dict or "shutdown" in action_dict:
                server.stop()
            elif "forceOff" in action_dict:
                server.stop() #TODO
            elif "terminate" in action_dict:
                server.delete()
            elif "createImage" in action_dict:
                server.create_image()
                #"path":path_schema,
                #"description":description_schema,
                #"name":name_schema,
                #"metadata":metadata_schema,
                #"imageRef": id_schema,
                #"disk": {"oneOf":[{"type": "null"}, {"type":"string"}] },
            elif "rebuild" in action_dict:
                server.rebuild(server.image['id'])
            elif "reboot" in action_dict:
                server.reboot() #reboot_type='SOFT'
            elif "console" in action_dict:
                console_type = action_dict["console"]
                if console_type == None or console_type == "novnc":
                    console_dict = server.get_vnc_console("novnc")
                elif console_type == "xvpvnc":
                    console_dict = server.get_vnc_console(console_type)
                elif console_type == "rdp-html5":
                    console_dict = server.get_rdp_console(console_type)
                elif console_type == "spice-html5":
                    console_dict = server.get_spice_console(console_type)
                else:
                    raise vimconn.vimconnException("console type '{}' not allowed".format(console_type), 
                                                   http_code=vimconn.HTTP_Bad_Request)
                try:
                    console_url = console_dict["console"]["url"]
                    #parse console_url
                    protocol_index = console_url.find("//")
                    suffix_index = console_url[protocol_index+2:].find("/") + protocol_index+2
                    port_index = console_url[protocol_index+2:suffix_index].find(":") + protocol_index+2
                    if protocol_index < 0 or port_index<0 or suffix_index<0:
                        raise vimconn.vimconnException("Unexpected response from VIM " + str(console_dict))
                    console_dict2={"protocol": console_url[0:protocol_index],
                                  "server":   console_url[protocol_index+2 : port_index], 
                                  "port":     int(console_url[port_index+1 : suffix_index]), 
                                  "suffix":   console_url[suffix_index+1:] 
                                  }
                    return console_dict2               
                except Exception as e:
                    raise vimconn.vimconnException("Unexpected response from VIM " + str(console_dict))
            
            return vm_id
        except (ksExceptions.ClientException, nvExceptions.ClientException, nvExceptions.NotFound, ConnectionError) as e:
            self._format_exception(e)
        #TODO insert exception vimconn.HTTP_Unauthorized

#NOT USED FUNCTIONS
    
    def new_external_port(self, port_data):
        #TODO openstack if needed
        '''Adds a external port to VIM'''
        '''Returns the port identifier'''
        return -vimconn.HTTP_Internal_Server_Error, "osconnector.new_external_port() not implemented" 
        
    def connect_port_network(self, port_id, network_id, admin=False):
        #TODO openstack if needed
        '''Connects a external port to a network'''
        '''Returns status code of the VIM response'''
        return -vimconn.HTTP_Internal_Server_Error, "osconnector.connect_port_network() not implemented" 
    
    def new_user(self, user_name, user_passwd, tenant_id=None):
        '''Adds a new user to openstack VIM'''
        '''Returns the user identifier'''
        self.logger.debug("osconnector: Adding a new user to VIM")
        try:
            self._reload_connection()
            user=self.keystone.users.create(user_name, user_passwd, tenant_id=tenant_id)
            #self.keystone.tenants.add_user(self.k_creds["username"], #role)
            return user.id
        except ksExceptions.ConnectionError as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        except ksExceptions.ClientException as e: #TODO remove
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            self.logger.debug("new_user " + error_text)
        return error_value, error_text        

    def delete_user(self, user_id):
        '''Delete a user from openstack VIM'''
        '''Returns the user identifier'''
        if self.debug:
            print "osconnector: Deleting  a  user from VIM"
        try:
            self._reload_connection()
            self.keystone.users.delete(user_id)
            return 1, user_id
        except ksExceptions.ConnectionError as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        except ksExceptions.NotFound as e:
            error_value=-vimconn.HTTP_Not_Found
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        except ksExceptions.ClientException as e: #TODO remove
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            print "delete_tenant " + error_text
        return error_value, error_text
 
    def get_hosts_info(self):
        '''Get the information of deployed hosts
        Returns the hosts content'''
        if self.debug:
            print "osconnector: Getting Host info from VIM"
        try:
            h_list=[]
            self._reload_connection()
            hypervisors = self.nova.hypervisors.list()
            for hype in hypervisors:
                h_list.append( hype.to_dict() )
            return 1, {"hosts":h_list}
        except nvExceptions.NotFound as e:
            error_value=-vimconn.HTTP_Not_Found
            error_text= (str(e) if len(e.args)==0 else str(e.args[0]))
        except (ksExceptions.ClientException, nvExceptions.ClientException) as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            print "get_hosts_info " + error_text
        return error_value, error_text        

    def get_hosts(self, vim_tenant):
        '''Get the hosts and deployed instances
        Returns the hosts content'''
        r, hype_dict = self.get_hosts_info()
        if r<0:
            return r, hype_dict
        hypervisors = hype_dict["hosts"]
        try:
            servers = self.nova.servers.list()
            for hype in hypervisors:
                for server in servers:
                    if server.to_dict()['OS-EXT-SRV-ATTR:hypervisor_hostname']==hype['hypervisor_hostname']:
                        if 'vm' in hype:
                            hype['vm'].append(server.id)
                        else:
                            hype['vm'] = [server.id]
            return 1, hype_dict
        except nvExceptions.NotFound as e:
            error_value=-vimconn.HTTP_Not_Found
            error_text= (str(e) if len(e.args)==0 else str(e.args[0]))
        except (ksExceptions.ClientException, nvExceptions.ClientException) as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            print "get_hosts " + error_text
        return error_value, error_text        
  

