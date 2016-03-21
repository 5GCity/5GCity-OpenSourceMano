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
__author__="Alfonso Tierno, Gerardo Garcia"
__date__ ="$22-jun-2014 11:19:29$"

import vimconn
import json
import yaml

from novaclient import client as nClient, exceptions as nvExceptions
import keystoneclient.v2_0.client as ksClient
import keystoneclient.exceptions as ksExceptions
import glanceclient.v2.client as glClient
import glanceclient.client as gl1Client
import glanceclient.exc as gl1Exceptions
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

class vimconnector(vimconn.vimconnector):
    def __init__(self, uuid, name, tenant, url, url_admin=None, user=None, passwd=None, debug=True, config={}):
        '''using common constructor parameters. In this case 
        'url' is the keystone authorization url,
        'url_admin' is not use
        '''
        vimconn.vimconnector.__init__(self, uuid, name, tenant, url, url_admin, user, passwd, debug, config)
        
        self.k_creds={}
        self.n_creds={}
        if not url:
            raise TypeError, 'url param can not be NoneType'
        self.k_creds['auth_url'] = url
        self.n_creds['auth_url'] = url
        if tenant:
            self.k_creds['tenant_name'] = tenant
            self.n_creds['project_id']  = tenant
        if user:
            self.k_creds['username'] = user
            self.n_creds['username'] = user
        if passwd:
            self.k_creds['password'] = passwd
            self.n_creds['api_key']  = passwd
        self.reload_client       = True
    
    def __setitem__(self,index, value):
        '''Set individuals parameters 
        Throw TypeError, KeyError
        '''
        if index=='tenant':
            self.reload_client=True
            self.tenant = value
            if value:
                self.k_creds['tenant_name'] = value
                self.n_creds['project_id']  = value
            else:
                del self.k_creds['tenant_name']
                del self.n_creds['project_id']
        elif index=='user':
            self.reload_client=True
            self.user = value
            if value:
                self.k_creds['username'] = value
                self.n_creds['username'] = value
            else:
                del self.k_creds['username']
                del self.n_creds['username']
        elif index=='passwd':
            self.reload_client=True
            self.passwd = value
            if value:
                self.k_creds['password'] = value
                self.n_creds['api_key']  = value
            else:
                del self.k_creds['password']
                del self.n_creds['api_key']
        elif index=='url':
            self.reload_client=True
            self.url = value
            if value:
                self.k_creds['auth_url'] = value
                self.n_creds['auth_url'] = value
            else:
                raise TypeError, 'url param can not be NoneType'
        else:
            vimconn.vimconnector.__setitem__(self,index, value)
     
    def _reload_connection(self):
        '''Called before any operation, it check if credentials has changed
        Throw keystoneclient.apiclient.exceptions.AuthorizationFailure
        '''
        #TODO control the timing and possible token timeout, but it seams that python client does this task for us :-) 
        if self.reload_client:
            #test valid params
            if len(self.n_creds) <4:
                raise ksExceptions.ClientException("Not enough parameters to connect to openstack")
            self.nova = nClient.Client(2, **self.n_creds)
            self.keystone = ksClient.Client(**self.k_creds)
            self.glance_endpoint = self.keystone.service_catalog.url_for(service_type='image', endpoint_type='publicURL')
            self.glance = glClient.Client(self.glance_endpoint, token=self.keystone.auth_token, **self.k_creds)  #TODO check k_creds vs n_creds
            self.ne_endpoint=self.keystone.service_catalog.url_for(service_type='network', endpoint_type='publicURL')
            self.neutron = neClient.Client('2.0', endpoint_url=self.ne_endpoint, token=self.keystone.auth_token, **self.k_creds)
            self.reload_client = False
    
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
        if self.debug:
            print "osconnector: Adding a new user to VIM"
        try:
            self._reload_connection()
            user=self.keystone.users.create(user_name, user_passwd, tenant_id=tenant_id)
            #self.keystone.tenants.add_user(self.k_creds["username"], #role)
            return 1, user.id
        except ksExceptions.ConnectionError as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        except ksExceptions.ClientException as e: #TODO remove
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            print "new_tenant " + error_text
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
        
    def new_tenant(self,tenant_name,tenant_description):
        '''Adds a new tenant to openstack VIM'''
        '''Returns the tenant identifier'''
        if self.debug:
            print "osconnector: Adding a new tenant to VIM"
        try:
            self._reload_connection()
            tenant=self.keystone.tenants.create(tenant_name, tenant_description)
            #self.keystone.tenants.add_user(self.k_creds["username"], #role)
            return 1, tenant.id
        except ksExceptions.ConnectionError as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        except ksExceptions.ClientException as e: #TODO remove
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            print "new_tenant " + error_text
        return error_value, error_text

    def delete_tenant(self,tenant_id):
        '''Delete a tenant from openstack VIM'''
        '''Returns the tenant identifier'''
        if self.debug:
            print "osconnector: Deleting  a  tenant from VIM"
        try:
            self._reload_connection()
            self.keystone.tenants.delete(tenant_id)
            #self.keystone.tenants.add_user(self.k_creds["username"], #role)
            return 1, tenant_id
        except ksExceptions.ConnectionError as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        except ksExceptions.ClientException as e: #TODO remove
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            print "delete_tenant " + error_text
        return error_value, error_text

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
        
    def new_tenant_network(self,net_name,net_type,public=False,cidr=None,vlan=None):
        '''Adds a tenant network to VIM'''
        '''Returns the network identifier'''
        if self.debug:
            print "osconnector: Adding a new tenant network to VIM (tenant: " + self.tenant + ", type: " + net_type + "): "+ net_name
        try:
            self._reload_connection()
            network_dict = {'name': net_name, 'admin_state_up': True}
            if net_type=="data" or net_type=="ptp":
                if self.config.get('dataplane_physical_net') == None:
                    return -vimconn.HTTP_Bad_Request, "You must provide a 'dataplane_physical_net' at config value before creating sriov network "
                    
                network_dict["provider:physical_network"] = self.config['dataplane_physical_net'] #"physnet_sriov" #TODO physical
                network_dict["provider:network_type"]     = "vlan"
                if vlan!=None:
                    network_dict["provider:network_type"] = vlan
            network_dict["shared"]=public
            new_net=self.neutron.create_network({'network':network_dict})
            #print new_net
            #create fake subnetwork
            if not cidr:
                cidr="192.168.111.0/24"
            subnet={"name":net_name+"-subnet",
                    "network_id": new_net["network"]["id"],
                    "ip_version": 4,
                    "cidr": cidr
                    }
            self.neutron.create_subnet({"subnet": subnet} )
            return 1, new_net["network"]["id"]
        except neExceptions.ConnectionFailed as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        except (ksExceptions.ClientException, neExceptions.NeutronException) as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            print "new_tenant_network " + error_text
        return error_value, error_text

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
        if self.debug:
            print "osconnector.get_network_list(): Getting network from VIM (filter: " + str(filter_dict) + "): "
        try:
            self._reload_connection()
            net_dict=self.neutron.list_networks(**filter_dict)
            net_list=net_dict["networks"]
            self.__net_os2mano(net_list)
            return 1, net_list
        except neClient.exceptions.ConnectionFailed as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        except (ksExceptions.ClientException, neExceptions.NeutronException) as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            print "get_network_list " + error_text
        return error_value, error_text

    def get_tenant_network(self, net_id, tenant_id=None):
        '''Obtain tenant networks of VIM'''
        '''Returns the network information from a network id'''
        if self.debug:
            print "osconnector.get_tenant_network(): Getting tenant network %s from VIM" % net_id
        filter_dict={"id": net_id}
        if tenant_id:
            filter_dict["tenant_id"] = tenant_id
        r, net_list = self.get_network_list(filter_dict)
        if r<0:
            return r, net_list
        if len(net_list)==0:
            return -vimconn.HTTP_Not_Found, "Network '%s' not found" % net_id
        elif len(net_list)>1:
            return -vimconn.HTTP_Conflict, "Found more than one network with this criteria"
        net = net_list[0]
        subnets=[]
        for subnet_id in net.get("subnets", () ):
            try:
                subnet = self.neutron.show_subnet(subnet_id)
            except Exception as e:
                error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
                print "osconnector.get_tenant_network(): Error getting subnet %s %s" % (net_id, error_text)
                subnet = {"id": subnet_id, "fault": error_text}
            subnets.append(subnet)
        net["subnets"] = subnets
        return 1, net


    def delete_tenant_network(self, net_id):
        '''Deletes a tenant network from VIM'''
        '''Returns the network identifier'''
        if self.debug:
            print "osconnector: Deleting a new tenant network from VIM tenant: " + self.tenant + ", id: " + net_id
        try:
            self._reload_connection()
            #delete VM ports attached to this networks before the network
            ports = self.neutron.list_ports(network_id=net_id)
            for p in ports['ports']:
                try:
                    self.neutron.delete_port(p["id"])
                except Exception as e:
                    print "Error deleting port: " + type(e).__name__ + ": "+  str(e)
            self.neutron.delete_network(net_id)
            return 1, net_id
        except neClient.exceptions.ConnectionFailed as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        except neExceptions.NetworkNotFoundClient as e:
            error_value=-vimconn.HTTP_Not_Found
            error_text= type(e).__name__ + ": "+  str(e.args[0])
        except (ksExceptions.ClientException, neExceptions.NeutronException) as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            print "delete_tenant_network " + error_text
        return error_value, error_text

    def get_tenant_flavor(self, flavor_id):
        '''Obtain flavor details from the  VIM
            Returns the flavor dict details
        '''
        print "VIMConnector: Getting flavor from VIM"
        try:
            self._reload_connection()
            flavor = self.nova.flavors.find(id=flavor_id)
            #TODO parse input and translate to VIM format (openmano_schemas.new_vminstance_response_schema)
            return 1, {"flavor": flavor.to_dict()}
        except nvExceptions.NotFound as e:
            error_value=-vimconn.HTTP_Not_Found
            error_text= "flavor instance %s not found" % flavor_id
        except (ksExceptions.ClientException, nvExceptions.ClientException) as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            print "get_tenant_flavor " + error_text
        return error_value, error_text        

    def new_tenant_flavor(self, flavor_dict, change_name_if_used=True):
        '''Adds a tenant flavor to openstack VIM
        if change_name_if_used is True, it will change name in case of conflict
        Returns the flavor identifier
        '''
        retry=0
        name_suffix = 0
        name=flavor_dict['name']
        while retry<2:
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
                        name = flavor_dict['name']+"-" + str(name_suffix)
                        
                ram = flavor_dict.get('ram',64)
                vcpus = flavor_dict.get('vcpus',1)
                numa_properties=None

                extended=flavor_dict.get("extended")
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
                            if 'paired-threads' in numa:
                                vcpus = numa['paired-threads']*2
                                numa_properties["hw:cpu_threads_policy"] = "prefer"
                            elif 'cores' in numa:
                                vcpus = numa['cores']
                                #numa_properties["hw:cpu_threads_policy"] = "prefer"
                            elif 'threads' in numa:
                                vcpus = numa['threads']
                                numa_properties["hw:cpu_policy"] = "isolated"
                            for interface in numa.get("interfaces",() ):
                                if interface["dedicated"]=="yes":
                                    error_value=-vimconn.HTTP_Bad_Request
                                    error_text= "Passthrough interfaces are not supported for the openstack connector"
                                    break
                                #TODO, add the key 'pci_passthrough:alias"="<label at config>:<number ifaces>"' when a way to connect it is available
                                
                #create flavor                 
                new_flavor=self.nova.flavors.create(name, 
                                ram, 
                                vcpus, 
                                flavor_dict.get('disk',1),
                                is_public=flavor_dict.get('is_public', True)
                            ) 
                #add metadata
                if numa_properties:
                    new_flavor.set_keys(numa_properties)
                return 1, new_flavor.id
            except nvExceptions.Conflict as e:
                error_value=-vimconn.HTTP_Conflict
                error_text= str(e)
                if change_name_if_used:
                    continue
                break
            #except nvExceptions.BadRequest as e:
            except (ksExceptions.ClientException, nvExceptions.ClientException, ConnectionError) as e:
                error_value=-vimconn.HTTP_Bad_Request
                error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
                break
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            print "new_tenant_flavor " + error_text
        return error_value, error_text

    def delete_tenant_flavor(self,flavor_id):
        '''Deletes a tenant flavor from openstack VIM
           Returns >0,id if ok; or <0,error_text if error
        '''
        retry=0
        while retry<2:
            retry+=1
            try:
                self._reload_connection()
                self.nova.flavors.delete(flavor_id)
                return 1, flavor_id
            except nvExceptions.NotFound as e:
                error_value = -vimconn.HTTP_Not_Found
                error_text  = "flavor '%s' not found" % flavor_id
                break
            #except nvExceptions.BadRequest as e:
            except (ksExceptions.ClientException, nvExceptions.ClientException) as e:
                error_value=-vimconn.HTTP_Bad_Request
                error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
                break
        if self.debug:
            print "delete_tenant_flavor " + error_text
        #if reaching here is because an exception
        return error_value, error_text

    def new_tenant_image(self,image_dict):
        '''
        Adds a tenant image to VIM
        if change_name_if_used is True, it will change name in case of conflict
        Returns:
            >1, image-id        if the image is created
            <0, message          if there is an error
        '''
        retry=0
        #using version 1 of glance client
        glancev1 = gl1Client.Client('1',self.glance_endpoint, token=self.keystone.auth_token, **self.k_creds)  #TODO check k_creds vs n_creds
        while retry<2:
            retry+=1
            try:
                self._reload_connection()
                #determine format  http://docs.openstack.org/developer/glance/formats.html
                if "disk_format" in image_dict:
                    disk_format=image_dict["disk_format"]
                else: #autodiscover base on extention
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
                print "new_tenant_image: '%s' loading from '%s'" % (image_dict['name'], image_dict['location'])
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
                return 1, new_image.id
            except nvExceptions.Conflict as e:
                error_value=-vimconn.HTTP_Conflict
                error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
                break
            except (HTTPException, gl1Exceptions.HTTPException, gl1Exceptions.CommunicationError) as e:
                error_value=-vimconn.HTTP_Bad_Request
                error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
                continue
            except IOError as e:  #can not open the file
                error_value=-vimconn.HTTP_Bad_Request
                error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0])) + " for " + image_dict['location']
                break
            except (ksExceptions.ClientException, nvExceptions.ClientException) as e:
                error_value=-vimconn.HTTP_Bad_Request
                error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
                break
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            print "new_tenant_image " + error_text
        return error_value, error_text
     
    def delete_tenant_image(self, image_id):
        '''Deletes a tenant image from openstack VIM
        Returns >0,id if ok; or <0,error_text if error
        '''
        retry=0
        while retry<2:
            retry+=1
            try:
                self._reload_connection()
                self.nova.images.delete(image_id)
                return 1, image_id
            except nvExceptions.NotFound as e:
                error_value = -vimconn.HTTP_Not_Found
                error_text  = "flavor '%s' not found" % image_id
                break
            #except nvExceptions.BadRequest as e:
            except (ksExceptions.ClientException, nvExceptions.ClientException) as e: #TODO remove
                error_value=-vimconn.HTTP_Bad_Request
                error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
                break
        if self.debug:
            print "delete_tenant_image " + error_text
        #if reaching here is because an exception
        return error_value, error_text
        
    def new_tenant_vminstance(self,name,description,start,image_id,flavor_id,net_list):
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
                #TODO ip, security groups
        Returns >=0, the instance identifier
                <0, error_text
        '''
        if self.debug:
            print "osconnector: Creating VM into VIM"
            print "   image %s  flavor %s   nics=%s" %(image_id, flavor_id,net_list)
        try:
            metadata=[]
            net_list_vim=[]
            self._reload_connection()
            metadata_vpci={}
            for net in net_list:
                if not net.get("net_id"): #skip non connected iface
                    continue
                if net["type"]=="virtual":
                    net_list_vim.append({'net-id': net["net_id"]})
                    if "vpci" in net:
                        metadata_vpci[ net["net_id"] ] = [[ net["vpci"], "" ]]
                elif net["type"]=="PF":
                    print "new_tenant_vminstance: Warning, can not connect a passthrough interface "
                    #TODO insert this when openstack consider passthrough ports as openstack neutron ports
                else: #VF
                    if "vpci" in net:
                        if "VF" not in metadata_vpci:
                            metadata_vpci["VF"]=[]
                        metadata_vpci["VF"].append([ net["vpci"], "" ])
                    port_dict={
                         "network_id": net["net_id"],
                         "name": net.get("name"),
                         "binding:vnic_type": "direct", 
                         "admin_state_up": True
                    }
                    if not port_dict["name"]:
                        port_dict["name"] = name
                    if net.get("mac_address"):
                        port_dict["mac_address"]=net["mac_address"]
                    #TODO: manage having SRIOV without vlan tag
                    #if net["type"] == "VFnotShared"
                    #    port_dict["vlan"]=0
                    new_port = self.neutron.create_port({"port": port_dict })
                    net["mac_adress"] = new_port["port"]["mac_address"]
                    net["vim_id"] = new_port["port"]["id"]
                    net["ip"] = new_port["port"].get("fixed_ips",[{}])[0].get("ip_address")
                    net_list_vim.append({"port-id": new_port["port"]["id"]})
            if metadata_vpci:
                metadata = {"pci_assignement": json.dumps(metadata_vpci)}
            
            print "name '%s' image_id '%s'flavor_id '%s' net_list_vim '%s' description '%s' metadata %s"\
                 % (name, image_id, flavor_id, str(net_list_vim), description, str(metadata))
            
            security_groups   = self.config.get('security_groups')
            if type(security_groups) is str:
                security_groups = ( security_groups, )
            server = self.nova.servers.create(name, image_id, flavor_id, nics=net_list_vim, meta=metadata,
                                              security_groups   = security_groups,
                                              availability_zone = self.config.get('availability_zone'),
                                              key_name          = self.config.get('keypair'),
                                        ) #, description=description)
            
            
            print "DONE :-)", server
            
#             #TODO   server.add_floating_ip("10.95.87.209")
#             #To look for a free floating_ip
#             free_floating_ip = None
#             for floating_ip in self.neutron.list_floatingips().get("floatingips", () ):
#                 if not floating_ip["port_id"]:
#                     free_floating_ip = floating_ip["floating_ip_address"]
#                     break
#             if free_floating_ip:
#                 server.add_floating_ip(free_floating_ip)
                
            
            return 1, server.id
#        except nvExceptions.NotFound as e:
#            error_value=-vimconn.HTTP_Not_Found
#            error_text= "vm instance %s not found" % vm_id
        except (ksExceptions.ClientException, nvExceptions.ClientException, ConnectionError, TypeError) as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        except neClient.exceptions.ConnectionFailed as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            print "new_tenant_vminstance Exception",e, error_text
        return error_value, error_text    

    def get_tenant_vminstance(self,vm_id):
        '''Returns the VM instance information from VIM'''
        if self.debug:
            print "osconnector: Getting VM from VIM"
        try:
            self._reload_connection()
            server = self.nova.servers.find(id=vm_id)
            #TODO parse input and translate to VIM format (openmano_schemas.new_vminstance_response_schema)
            return 1, {"server": server.to_dict()}
        except nvExceptions.NotFound as e:
            error_value=-vimconn.HTTP_Not_Found
            error_text= "vm instance %s not found" % vm_id
        except (ksExceptions.ClientException, nvExceptions.ClientException) as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            print "get_tenant_vminstance " + error_text
        return error_value, error_text        
                
    def get_tenant_vminstance_console(self,vm_id, console_type="vnc"):
        '''
        Get a console for the virtual machine
        Params:
            vm_id: uuid of the VM
            console_type, can be:
                "novnc" (by default), "xvpvnc" for VNC types, 
                "rdp-html5" for RDP types, "spice-html5" for SPICE types
        Returns <0, text on error, for example not available
                1, URL/text with the console parameters
        '''
        if self.debug:
            print "osconnector: Getting VM CONSOLE from VIM"
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
                return -vimconn.HTTP_Bad_Request, "console type '%s' not allowed" % console_type
            
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
                    return 1, console_dict
            return -vimconn.HTTP_Internal_Server_Error, "Unexpected response from VIM"
            
            #TODO parse input and translate to VIM format (openmano_schemas.new_vminstance_response_schema)
            return 1, {"server": server.to_dict()}
        except nvExceptions.NotFound as e:
            error_value=-vimconn.HTTP_Not_Found
            error_text= "vm instance %s not found" % vm_id
        except (ksExceptions.ClientException, nvExceptions.ClientException, nvExceptions.BadRequest) as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            print "get_tenant_vminstance " + error_text
        return error_value, error_text        


    def delete_tenant_vminstance(self, vm_id):
        '''Removes a VM instance from VIM
        Returns >0, the instance identifier
                <0, error_text
        '''
        if self.debug:
            print "osconnector: Getting VM from VIM"
        try:
            self._reload_connection()
            #delete VM ports attached to this networks before the virtual machine
            ports = self.neutron.list_ports(device_id=vm_id)
            for p in ports['ports']:
                try:
                    self.neutron.delete_port(p["id"])
                except Exception as e:
                    print "Error deleting port: " + type(e).__name__ + ": "+  str(e)
            self.nova.servers.delete(vm_id)
            return 1, vm_id
        except nvExceptions.NotFound as e:
            error_value=-vimconn.HTTP_Not_Found
            error_text= (str(e) if len(e.args)==0 else str(e.args[0]))
        except (ksExceptions.ClientException, nvExceptions.ClientException) as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            print "get_tenant_vminstance " + error_text
        return error_value, error_text        

    def refresh_tenant_vms_and_nets(self, vmDict, netDict):
        '''Refreshes the status of the dictionaries of VM instances and nets passed as arguments. It modifies the dictionaries
        Returns:
            - result: 0 if all elements could be refreshed (even if its status didn't change)
                      n>0, the number of elements that couldn't be refreshed,
                      <0 if error (foreseen)
            - error_msg: text with reference to possible errors
        '''
        #vms_refreshed = []
        #nets_refreshed = []
        vms_unrefreshed = []
        nets_unrefreshed = []
        if self.debug:
            print "osconnector refresh_tenant_vms and nets: Getting tenant VM instance information from VIM"
        for vm_id in vmDict:
            vmDict[vm_id] = {'error_msg':None, 'vim_info':None}
            r,c = self.get_tenant_vminstance(vm_id)
            if r<0:
                print "osconnector refresh_tenant_vm. Error getting vm_id '%s' status: %s" % (vm_id, c)
                if r==-vimconn.HTTP_Not_Found:
                    vmDict[vm_id]['status'] = "DELETED" 
                else:
                    vmDict[vm_id]['status'] = "VIM_ERROR"
                    vmDict[vm_id]['error_msg'] = c
                    vms_unrefreshed.append(vm_id)
            else:
                try:
                    vmDict[vm_id]['status']    =  vmStatus2manoFormat[ c['server']['status'] ]
                    vmDict[vm_id]['vim_info']  = yaml.safe_dump(c['server'])
                    vmDict[vm_id]["interfaces"] = []
                    if c['server'].get('fault'):
                        vmDict[vm_id]['error_msg'] = str(c['server']['fault'])
                    #get interfaces
                    try:
                        self._reload_connection()
                        port_dict=self.neutron.list_ports(device_id=vm_id)
                        for port in port_dict["ports"]:
                            interface={}
                            interface['vim_info']  = yaml.safe_dump(port)
                            interface["mac_address"] = port.get("mac_address")
                            interface["vim_net_id"] = port["network_id"]
                            interface["vim_interface_id"] = port["id"]
                            ips=[]
                            #look for floating ip address
                            floating_ip_dict = self.neutron.list_floatingips(port_id=port["id"])
                            if floating_ip_dict.get("floatingips"):
                                ips.append(floating_ip_dict["floatingips"][0].get("floating_ip_address") )

                            for subnet in port["fixed_ips"]:
                                ips.append(subnet["ip_address"])
                            interface["ip_address"] = ";".join(ips)
                            vmDict[vm_id]["interfaces"].append(interface)
                    except Exception as e:
                        print type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
                
                    
                    #error message at server.fault["message"]
                except KeyError as e:
                    print "osconnector refresh_tenant_elements KeyError %s getting vm_id '%s' status  %s" % (str(e), vm_id, c['server']['status'])
                    vmDict[vm_id]['status'] = "VIM_ERROR"
                    vmDict[vm_id]['error_msg'] = str(e)
                    vms_unrefreshed.append(vm_id)
        
        #print "VMs refreshed: %s" % str(vms_refreshed)
        for net_id in netDict:
            netDict[net_id]={'error_msg':None, 'vim_info':None}
            r,c = self.get_tenant_network(net_id)
            if r<0:
                print "osconnector refresh_tenant_network. Error getting net_id '%s' status: %s" % (net_id, c)
                if r==-vimconn.HTTP_Not_Found:
                    netDict[net_id]['status'] = "DELETED" #TODO check exit status
                else:
                    netDict[vm_id]['status'] = "VIM_ERROR"
                    netDict[vm_id]['error_msg'] = c
                    nets_unrefreshed.append(net_id)
            else:
                try:
                    netDict[net_id]['status'] = netStatus2manoFormat[ c['status'] ]
                    if c['status'] == "ACIVE" and not c['admin_state_up']:
                        netDict[net_id]['status'] = 'DOWN'
                    netDict[net_id]['vim_info']  = yaml.safe_dump(c)
                    if c.get('fault'):  #TODO
                        netDict[net_id]['error_msg'] = str(c['fault'])
                except KeyError as e:
                    print "osconnector refresh_tenant_elements KeyError %s getting vm_id '%s' status  %s" % (str(e), vm_id, c['network']['status'])
                    netDict[net_id]['status'] = "VIM_ERROR"
                    netDict[net_id]['error_msg'] = str(e)
                    nets_unrefreshed.append(net_id)

        #print "Nets refreshed: %s" % str(nets_refreshed)
        
        error_msg=""
        if len(vms_unrefreshed)+len(nets_unrefreshed)>0:
            error_msg += "VMs unrefreshed: " + str(vms_unrefreshed) + "; nets unrefreshed: " + str(nets_unrefreshed)
            print error_msg

        #return len(vms_unrefreshed)+len(nets_unrefreshed), error_msg, vms_refreshed, nets_refreshed
        return len(vms_unrefreshed)+len(nets_unrefreshed), error_msg
    
    def action_tenant_vminstance(self, vm_id, action_dict):
        '''Send and action over a VM instance from VIM
        Returns the status'''
        if self.debug:
            print "osconnector: Action over VM instance from VIM " + vm_id
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
                    return -vimconn.HTTP_Bad_Request, "console type '%s' not allowed" % console_type
                
                try:
                    console_url = console_dict["console"]["url"]
                    #parse console_url
                    protocol_index = console_url.find("//")
                    suffix_index = console_url[protocol_index+2:].find("/") + protocol_index+2
                    port_index = console_url[protocol_index+2:suffix_index].find(":") + protocol_index+2
                    if protocol_index < 0 or port_index<0 or suffix_index<0:
                        print "action_tenant_vminstance, console: response", str(console_dict)
                        return -vimconn.HTTP_Internal_Server_Error, "Unexpected response from VIM"
                    console_dict2={"protocol": console_url[0:protocol_index],
                                  "server":   console_url[protocol_index+2 : port_index], 
                                  "port":     int(console_url[port_index+1 : suffix_index]), 
                                  "suffix":   console_url[suffix_index+1:] 
                                  }
                    protocol_index += 2
                    return 1, console_dict2               
                except:
                    print "action_tenant_vminstance, console: response", str(console_dict)
                    return -vimconn.HTTP_Internal_Server_Error, "Unexpected response from VIM"
            
            return 1, vm_id
        except nvExceptions.NotFound as e:
            error_value=-vimconn.HTTP_Not_Found
            error_text= (str(e) if len(e.args)==0 else str(e.args[0]))
        except (ksExceptions.ClientException, nvExceptions.ClientException) as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            print "action_tenant_vminstance " + error_text
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
  
    def get_image_id_from_path(self, path):
        '''Get the image id from image path in the VIM database'''
        '''Returns:
             0,"Image not found"   if there are no images with that path
             1,image-id            if there is one image with that path
             <0,message            if there was an error (Image not found, error contacting VIM, more than 1 image with that path, etc.) 
        '''
        try:
            self._reload_connection()
            images = self.nova.images.list()
            for image in images:
                if image.metadata.get("location")==path:
                    return 1, image.id
            return 0, "image with location '%s' not found" % path
        except (ksExceptions.ClientException, nvExceptions.ClientException) as e: #TODO remove
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        if self.debug:
            print "get_image_id_from_path " + error_text
        #if reaching here is because an exception
        return error_value, error_text
        

