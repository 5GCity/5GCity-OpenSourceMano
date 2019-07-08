# -*- coding: utf-8 -*-

##
# Copyright 2017  Telefonica Digital Spain S.L.U.
# This file is part of ETSI OSM
#  All Rights Reserved.
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
# contact with: patent-office@telefonica.com
##

"""
vimconnector implements all the methods to interact with OpenNebula using the XML-RPC API.
"""
__author__ = "Jose Maria Carmona Perez,Juan Antonio Hernando Labajo, Emilio Abraham Garrido Garcia,Alberto Florez " \
             "Pages, Andres Pozo Munoz, Santiago Perez Marin, Onlife Networks Telefonica I+D Product Innovation "
__date__ = "$13-dec-2017 11:09:29$"
import vimconn
import requests
import logging
import oca
import untangle
import math
import random
import pyone

class vimconnector(vimconn.vimconnector):
    def __init__(self, uuid, name, tenant_id, tenant_name, url, url_admin=None, user=None, passwd=None,
                 log_level="DEBUG", config={}, persistent_info={}):

        """Constructor of VIM
        Params:
            'uuid': id asigned to this VIM
            'name': name assigned to this VIM, can be used for logging
            'tenant_id', 'tenant_name': (only one of them is mandatory) VIM tenant to be used
            'url_admin': (optional), url used for administrative tasks
            'user', 'passwd': credentials of the VIM user
            'log_level': provider if it should use a different log_level than the general one
            'config': dictionary with extra VIM information. This contains a consolidate version of general VIM config
                    at creation and particular VIM config at teh attachment
            'persistent_info': dict where the class can store information that will be available among class
                    destroy/creation cycles. This info is unique per VIM/credential. At first call it will contain an
                    empty dict. Useful to store login/tokens information for speed up communication

        Returns: Raise an exception is some needed parameter is missing, but it must not do any connectivity
            check against the VIM
        """

        vimconn.vimconnector.__init__(self, uuid, name, tenant_id, tenant_name, url, url_admin, user, passwd, log_level,
                                      config)

    def _new_one_connection(self):
        return pyone.OneServer(self.url, session=self.user + ':' + self.passwd)

    def new_tenant(self, tenant_name, tenant_description):
        # '''Adds a new tenant to VIM with this name and description, returns the tenant identifier'''
        try:
            client = oca.Client(self.user + ':' + self.passwd, self.url)
            group_list = oca.GroupPool(client)
            user_list = oca.UserPool(client)
            group_list.info()
            user_list.info()
            create_primarygroup = 1
            # create group-tenant
            for group in group_list:
                if str(group.name) == str(tenant_name):
                    create_primarygroup = 0
                    break
            if create_primarygroup == 1:
                oca.Group.allocate(client, tenant_name)
            group_list.info()
            # set to primary_group the tenant_group and oneadmin to secondary_group
            for group in group_list:
                if str(group.name) == str(tenant_name):
                    for user in user_list:
                        if str(user.name) == str(self.user):
                            if user.name == "oneadmin":
                                return str(0)
                            else:
                                self._add_secondarygroup(user.id, group.id)
                                user.chgrp(group.id)
                                return str(group.id)
        except Exception as e:
            self.logger.error("Create new tenant error: " + str(e))
            raise vimconn.vimconnException(e)

    def delete_tenant(self, tenant_id):
        """Delete a tenant from VIM. Returns the old tenant identifier"""
        try:
            client = oca.Client(self.user + ':' + self.passwd, self.url)
            group_list = oca.GroupPool(client)
            user_list = oca.UserPool(client)
            group_list.info()
            user_list.info()
            for group in group_list:
                if str(group.id) == str(tenant_id):
                    for user in user_list:
                        if str(user.name) == str(self.user):
                            self._delete_secondarygroup(user.id, group.id)
                            group.delete(client)
                    return None
            raise vimconn.vimconnNotFoundException("Group {} not found".format(tenant_id))
        except Exception as e:
            self.logger.error("Delete tenant " + str(tenant_id) + " error: " + str(e))
            raise vimconn.vimconnException(e)

    def _add_secondarygroup(self, id_user, id_group):
        # change secondary_group to primary_group
        params = '<?xml version="1.0"?> \
                   <methodCall>\
                   <methodName>one.user.addgroup</methodName>\
                   <params>\
                   <param>\
                   <value><string>{}:{}</string></value>\
                   </param>\
                   <param>\
                   <value><int>{}</int></value>\
                   </param>\
                   <param>\
                   <value><int>{}</int></value>\
                   </param>\
                   </params>\
                   </methodCall>'.format(self.user, self.passwd, (str(id_user)), (str(id_group)))
        requests.post(self.url, params)

    def _delete_secondarygroup(self, id_user, id_group):
        params = '<?xml version="1.0"?> \
                   <methodCall>\
                   <methodName>one.user.delgroup</methodName>\
                   <params>\
                   <param>\
                   <value><string>{}:{}</string></value>\
                   </param>\
                   <param>\
                   <value><int>{}</int></value>\
                   </param>\
                   <param>\
                   <value><int>{}</int></value>\
                   </param>\
                   </params>\
                   </methodCall>'.format(self.user, self.passwd, (str(id_user)), (str(id_group)))
        requests.post(self.url, params)

    def new_network(self, net_name, net_type, ip_profile=None, shared=False, vlan=None):  # , **vim_specific):
        """Adds a tenant network to VIM
        Params:
            'net_name': name of the network
            'net_type': one of:
                'bridge': overlay isolated network
                'data':   underlay E-LAN network for Passthrough and SRIOV interfaces
                'ptp':    underlay E-LINE network for Passthrough and SRIOV interfaces.
            'ip_profile': is a dict containing the IP parameters of the network
                'ip_version': can be "IPv4" or "IPv6" (Currently only IPv4 is implemented)
                'subnet_address': ip_prefix_schema, that is X.X.X.X/Y
                'gateway_address': (Optional) ip_schema, that is X.X.X.X
                'dns_address': (Optional) comma separated list of ip_schema, e.g. X.X.X.X[,X,X,X,X]
                'dhcp_enabled': True or False
                'dhcp_start_address': ip_schema, first IP to grant
                'dhcp_count': number of IPs to grant.
            'shared': if this network can be seen/use by other tenants/organization
            'vlan': in case of a data or ptp net_type, the intended vlan tag to be used for the network
        Returns a tuple with the network identifier and created_items, or raises an exception on error
            created_items can be None or a dictionary where this method can include key-values that will be passed to
            the method delete_network. Can be used to store created segments, created l2gw connections, etc.
            Format is vimconnector dependent, but do not use nested dictionaries and a value of None should be the same
            as not present.
        """

        # oca library method cannot be used in this case (problem with cluster parameters)
        try:
            created_items = {}
            one = self._new_one_connection()
            size = "254"
            if ip_profile is None:
                subnet_rand = random.randint(0, 255)
                ip_start = "192.168.{}.1".format(subnet_rand)
            else:
                index = ip_profile["subnet_address"].find("/")
                ip_start = ip_profile["subnet_address"][:index]
                if "dhcp_count" in ip_profile.keys() and ip_profile["dhcp_count"] is not None:
                    size = str(ip_profile["dhcp_count"])
                elif not ("dhcp_count" in ip_profile.keys()) and ip_profile["ip_version"] == "IPv4":
                    prefix = ip_profile["subnet_address"][index + 1:]
                    size = int(math.pow(2, 32 - prefix))
                if "dhcp_start_address" in ip_profile.keys() and ip_profile["dhcp_start_address"] is not None:
                    ip_start = str(ip_profile["dhcp_start_address"])
                if ip_profile["ip_version"] == "IPv6":
                    ip_prefix_type = "GLOBAL_PREFIX"

            if vlan is not None:
                vlan_id = vlan
            else:
                vlan_id = str(random.randint(100, 4095))
            #if "internal" in net_name:
            # OpenNebula not support two networks with same name
            random_net_name = str(random.randint(1, 1000000))
            net_name = net_name + random_net_name
            net_id = one.vn.allocate({
                        'NAME': net_name,
                        'VN_MAD': '802.1Q',
                        'PHYDEV': self.config["network"]["phydev"],
                        'VLAN_ID': vlan_id
                    }, self.config["cluster"]["id"])
            arpool = {'AR_POOL': {
                        'AR': {
                            'TYPE': 'IP4',
                            'IP': ip_start,
                            'SIZE': size
                        }
                    }
            }
            one.vn.add_ar(net_id, arpool)
            return net_id, created_items
        except Exception as e:
            self.logger.error("Create new network error: " + str(e))
            raise vimconn.vimconnException(e)

    def get_network_list(self, filter_dict={}):
        """Obtain tenant networks of VIM
        Params:
            'filter_dict' (optional) contains entries to return only networks that matches ALL entries:
                name: string  => returns only networks with this name
                id:   string  => returns networks with this VIM id, this imply returns one network at most
                shared: boolean >= returns only networks that are (or are not) shared
                tenant_id: sting => returns only networks that belong to this tenant/project
                ,#(not used yet) admin_state_up: boolean => returns only networks that are (or are not) in admin state active
                #(not used yet) status: 'ACTIVE','ERROR',... => filter networks that are on this status
        Returns the network list of dictionaries. each dictionary contains:
            'id': (mandatory) VIM network id
            'name': (mandatory) VIM network name
            'status': (mandatory) can be 'ACTIVE', 'INACTIVE', 'DOWN', 'BUILD', 'ERROR', 'VIM_ERROR', 'OTHER'
            'network_type': (optional) can be 'vxlan', 'vlan' or 'flat'
            'segmentation_id': (optional) in case network_type is vlan or vxlan this field contains the segmentation id
            'error_msg': (optional) text that explains the ERROR status
            other VIM specific fields: (optional) whenever possible using the same naming of filter_dict param
        List can be empty if no network map the filter_dict. Raise an exception only upon VIM connectivity,
            authorization, or some other unspecific error
        """

        try:
            one = self._new_one_connection()
            net_pool = one.vnpool.info(-2, -1, -1).VNET
            response = []
            if "name" in filter_dict.keys():
                network_name_filter = filter_dict["name"]
            else:
                network_name_filter = None
            if "id" in filter_dict.keys():
                network_id_filter = filter_dict["id"]
            else:
                network_id_filter = None
            for network in net_pool:
                if network.NAME == network_name_filter or str(network.ID) == str(network_id_filter):
                    net_dict = {"name": network.NAME, "id": str(network.ID), "status": "ACTIVE"}
                    response.append(net_dict)
            return response
        except Exception as e:
            self.logger.error("Get network list error: " + str(e))
            raise vimconn.vimconnException(e)

    def get_network(self, net_id):
        """Obtain network details from the 'net_id' VIM network
        Return a dict that contains:
            'id': (mandatory) VIM network id, that is, net_id
            'name': (mandatory) VIM network name
            'status': (mandatory) can be 'ACTIVE', 'INACTIVE', 'DOWN', 'BUILD', 'ERROR', 'VIM_ERROR', 'OTHER'
            'error_msg': (optional) text that explains the ERROR status
            other VIM specific fields: (optional) whenever possible using the same naming of filter_dict param
        Raises an exception upon error or when network is not found
        """
        try:
            one = self._new_one_connection()
            net_pool = one.vnpool.info(-2, -1, -1).VNET
            net = {}
            for network in net_pool:
                if str(network.ID) == str(net_id):
                    net['id'] = network.ID
                    net['name'] = network.NAME
                    net['status'] = "ACTIVE"
                    break
            if net:
                return net
            else:
                raise vimconn.vimconnNotFoundException("Network {} not found".format(net_id))
        except Exception as e:
            self.logger.error("Get network " + str(net_id) + " error): " + str(e))
            raise vimconn.vimconnException(e)

    def delete_network(self, net_id, created_items=None):
        """
        Removes a tenant network from VIM and its associated elements
        :param net_id: VIM identifier of the network, provided by method new_network
        :param created_items: dictionary with extra items to be deleted. provided by method new_network
        Returns the network identifier or raises an exception upon error or when network is not found
        """
        try:

            one = self._new_one_connection()
            one.vn.delete(int(net_id))
            return net_id
        except Exception as e:
            self.logger.error("Delete network " + str(net_id) + "error: network not found" + str(e))
            raise vimconn.vimconnException(e)

    def refresh_nets_status(self, net_list):
        """Get the status of the networks
        Params:
            'net_list': a list with the VIM network id to be get the status
        Returns a dictionary with:
            'net_id':         #VIM id of this network
                status:     #Mandatory. Text with one of:
                    #  DELETED (not found at vim)
                    #  VIM_ERROR (Cannot connect to VIM, authentication problems, VIM response error, ...)
                    #  OTHER (Vim reported other status not understood)
                    #  ERROR (VIM indicates an ERROR status)
                    #  ACTIVE, INACTIVE, DOWN (admin down),
                    #  BUILD (on building process)
                error_msg:  #Text with VIM error message, if any. Or the VIM connection ERROR
                vim_info:   #Text with plain information obtained from vim (yaml.safe_dump)
            'net_id2': ...
        """
        net_dict = {}
        try:
            for net_id in net_list:
                net = {}
                try:
                    net_vim = self.get_network(net_id)
                    net["status"] = net_vim["status"]
                    net["vim_info"] = None
                except vimconn.vimconnNotFoundException as e:
                    self.logger.error("Exception getting net status: {}".format(str(e)))
                    net['status'] = "DELETED"
                    net['error_msg'] = str(e)
                except vimconn.vimconnException as e:
                    self.logger.error(e)
                    net["status"] = "VIM_ERROR"
                    net["error_msg"] = str(e)
                net_dict[net_id] = net
            return net_dict
        except vimconn.vimconnException as e:
            self.logger.error(e)
            for k in net_dict:
                net_dict[k]["status"] = "VIM_ERROR"
                net_dict[k]["error_msg"] = str(e)
            return net_dict

    def get_flavor(self, flavor_id):  # Esta correcto
        """Obtain flavor details from the VIM
        Returns the flavor dict details {'id':<>, 'name':<>, other vim specific }
        Raises an exception upon error or if not found
        """
        try:

            one = self._new_one_connection()
            template = one.template.info(int(flavor_id))
            if template is not None:
                return {'id': template.ID, 'name': template.NAME}
            raise vimconn.vimconnNotFoundException("Flavor {} not found".format(flavor_id))
        except Exception as e:
            self.logger.error("get flavor " + str(flavor_id) + " error: " + str(e))
            raise vimconn.vimconnException(e)

    def new_flavor(self, flavor_data):
        """Adds a tenant flavor to VIM
            flavor_data contains a dictionary with information, keys:
                name: flavor name
                ram: memory (cloud type) in MBytes
                vpcus: cpus (cloud type)
                extended: EPA parameters
                  - numas: #items requested in same NUMA
                        memory: number of 1G huge pages memory
                        paired-threads|cores|threads: number of paired hyperthreads, complete cores OR individual threads
                        interfaces: # passthrough(PT) or SRIOV interfaces attached to this numa
                          - name: interface name
                            dedicated: yes|no|yes:sriov;  for PT, SRIOV or only one SRIOV for the physical NIC
                            bandwidth: X Gbps; requested guarantee bandwidth
                            vpci: requested virtual PCI address
                disk: disk size
                is_public:
                 #TODO to concrete
        Returns the flavor identifier"""

        disk_size = str(int(flavor_data["disk"])*1024)

        try:
            one = self._new_one_connection()
            template_id = one.template.allocate({
                'TEMPLATE': {
                    'NAME': flavor_data["name"],
                    'CPU': flavor_data["vcpus"],
                    'VCPU': flavor_data["vcpus"],
                    'MEMORY': flavor_data["ram"],
                    'DISK': {
                        'SIZE': disk_size
                    },
                    'CONTEXT': {
                        'NETWORK': "YES",
                        'SSH_PUBLIC_KEY': '$USER[SSH_PUBLIC_KEY]'
                    },
                    'GRAPHICS': {
                        'LISTEN': '0.0.0.0',
                        'TYPE': 'VNC'
                    },
                    'CLUSTER_ID': self.config["cluster"]["id"]
                }
            })
            return template_id

        except Exception as e:
            self.logger.error("Create new flavor error: " + str(e))
            raise vimconn.vimconnException(e)

    def delete_flavor(self, flavor_id):
        """ Deletes a tenant flavor from VIM
            Returns the old flavor_id
        """
        try:
            one = self._new_one_connection()
            one.template.delete(int(flavor_id), False)
            return flavor_id
        except Exception as e:
            self.logger.error("Error deleting flavor " + str(flavor_id) + ". Flavor not found")
            raise vimconn.vimconnException(e)

    def get_image_list(self, filter_dict={}):
        """Obtain tenant images from VIM
        Filter_dict can be:
            name: image name
            id: image uuid
            checksum: image checksum
            location: image path
        Returns the image list of dictionaries:
            [{<the fields at Filter_dict plus some VIM specific>}, ...]
            List can be empty
        """
        try:
            one = self._new_one_connection()
            image_pool = one.imagepool.info(-2, -1, -1).IMAGE
            images = []
            if "name" in filter_dict.keys():
                image_name_filter = filter_dict["name"]
            else:
                image_name_filter = None
            if "id" in filter_dict.keys():
                image_id_filter = filter_dict["id"]
            else:
                image_id_filter = None
            for image in image_pool:
                if str(image_name_filter) == str(image.NAME) or str(image.ID) == str(image_id_filter):
                    images_dict = {"name": image.NAME, "id": str(image.ID)}
                    images.append(images_dict)
            return images
        except Exception as e:
            self.logger.error("Get image list error: " + str(e))
            raise vimconn.vimconnException(e)

    def new_vminstance(self, name, description, start, image_id, flavor_id, net_list, cloud_config=None, disk_list=None,
                       availability_zone_index=None, availability_zone_list=None):

        """Adds a VM instance to VIM
            Params:
                'start': (boolean) indicates if VM must start or created in pause mode.
                'image_id','flavor_id': image and flavor VIM id to use for the VM
                'net_list': list of interfaces, each one is a dictionary with:
                    'name': (optional) name for the interface.
                    'net_id': VIM network id where this interface must be connect to. Mandatory for type==virtual
                    'vpci': (optional) virtual vPCI address to assign at the VM. Can be ignored depending on VIM capabilities
                    'model': (optional and only have sense for type==virtual) interface model: virtio, e1000, ...
                    'mac_address': (optional) mac address to assign to this interface
                    'ip_address': (optional) IP address to assign to this interface
                    #TODO: CHECK if an optional 'vlan' parameter is needed for VIMs when type if VF and net_id is not provided,
                        the VLAN tag to be used. In case net_id is provided, the internal network vlan is used for tagging VF
                    'type': (mandatory) can be one of:
                        'virtual', in this case always connected to a network of type 'net_type=bridge'
                        'PCI-PASSTHROUGH' or 'PF' (passthrough): depending on VIM capabilities it can be connected to a data/ptp network ot it
                            can created unconnected
                        'SR-IOV' or 'VF' (SRIOV with VLAN tag): same as PF for network connectivity.
                        'VFnotShared'(SRIOV without VLAN tag) same as PF for network connectivity. VF where no other VFs
                                are allocated on the same physical NIC
                    'bw': (optional) only for PF/VF/VFnotShared. Minimal Bandwidth required for the interface in GBPS
                    'port_security': (optional) If False it must avoid any traffic filtering at this interface. If missing
                                    or True, it must apply the default VIM behaviour
                    After execution the method will add the key:
                    'vim_id': must be filled/added by this method with the VIM identifier generated by the VIM for this
                            interface. 'net_list' is modified
                'cloud_config': (optional) dictionary with:
                    'key-pairs': (optional) list of strings with the public key to be inserted to the default user
                    'users': (optional) list of users to be inserted, each item is a dict with:
                        'name': (mandatory) user name,
                        'key-pairs': (optional) list of strings with the public key to be inserted to the user
                    'user-data': (optional) can be a string with the text script to be passed directly to cloud-init,
                        or a list of strings, each one contains a script to be passed, usually with a MIMEmultipart file
                    'config-files': (optional). List of files to be transferred. Each item is a dict with:
                        'dest': (mandatory) string with the destination absolute path
                        'encoding': (optional, by default text). Can be one of:
                            'b64', 'base64', 'gz', 'gz+b64', 'gz+base64', 'gzip+b64', 'gzip+base64'
                        'content' (mandatory): string with the content of the file
                        'permissions': (optional) string with file permissions, typically octal notation '0644'
                        'owner': (optional) file owner, string with the format 'owner:group'
                    'boot-data-drive': boolean to indicate if user-data must be passed using a boot drive (hard disk)
                'disk_list': (optional) list with additional disks to the VM. Each item is a dict with:
                    'image_id': (optional). VIM id of an existing image. If not provided an empty disk must be mounted
                    'size': (mandatory) string with the size of the disk in GB
                availability_zone_index: Index of availability_zone_list to use for this this VM. None if not AV required
                availability_zone_list: list of availability zones given by user in the VNFD descriptor.  Ignore if
                    availability_zone_index is None
            Returns a tuple with the instance identifier and created_items or raises an exception on error
                created_items can be None or a dictionary where this method can include key-values that will be passed to
                the method delete_vminstance and action_vminstance. Can be used to store created ports, volumes, etc.
                Format is vimconnector dependent, but do not use nested dictionaries and a value of None should be the same
                as not present.
            """
        self.logger.debug(
            "new_vminstance input: image='{}' flavor='{}' nics='{}'".format(image_id, flavor_id, str(net_list)))
        try:
            one = self._new_one_connection()
            template_vim = one.template.info(int(flavor_id), True)
            disk_size = str(template_vim.TEMPLATE["DISK"]["SIZE"])

            one = self._new_one_connection()
            template_updated = ""
            for net in net_list:
                net_in_vim = one.vn.info(int(net["net_id"]))
                net["vim_id"] = str(net_in_vim.ID)
                network = 'NIC = [NETWORK = "{}",NETWORK_UNAME = "{}" ]'.format(
                    net_in_vim.NAME, net_in_vim.UNAME)
                template_updated += network

            template_updated += "DISK = [ IMAGE_ID = {},\n  SIZE = {}]".format(image_id, disk_size)

            if isinstance(cloud_config, dict):
                if cloud_config.get("key-pairs"):
                    context = 'CONTEXT = [\n  NETWORK = "YES",\n  SSH_PUBLIC_KEY = "'
                    for key in cloud_config["key-pairs"]:
                        context += key + '\n'
                    # if False:
                    #     context += '"\n  USERNAME = '
                    context += '"]'
                    template_updated += context

            vm_instance_id = one.template.instantiate(int(flavor_id), name, False, template_updated)
            self.logger.info(
                "Instanciating in OpenNebula a new VM name:{} id:{}".format(name, flavor_id))
            return str(vm_instance_id), None
        except pyone.OneNoExistsException as e:
            self.logger.error("Network with id " + str(e) + " not found: " + str(e))
            raise vimconn.vimconnNotFoundException(e)
        except Exception as e:
            self.logger.error("Create new vm instance error: " + str(e))
            raise vimconn.vimconnException(e)

    def get_vminstance(self, vm_id):
        """Returns the VM instance information from VIM"""
        try:
            one = self._new_one_connection()
            vm = one.vm.info(int(vm_id))
            return vm
        except Exception as e:
            self.logger.error("Getting vm instance error: " + str(e) + ": VM Instance not found")
            raise vimconn.vimconnException(e)

    def delete_vminstance(self, vm_id, created_items=None):
        """
        Removes a VM instance from VIM and its associated elements
        :param vm_id: VIM identifier of the VM, provided by method new_vminstance
        :param created_items: dictionary with extra items to be deleted. provided by method new_vminstance and/or method
            action_vminstance
        :return: None or the same vm_id. Raises an exception on fail
        """
        try:
            one = self._new_one_connection()
            one.vm.recover(int(vm_id), 3)
            vm = None
            while True:
                if vm is not None and vm.LCM_STATE == 0:
                    break
                else:
                    vm = one.vm.info(int(vm_id))

        except pyone.OneNoExistsException as e:
            self.logger.info("The vm " + str(vm_id) + " does not exist or is already deleted")
            raise vimconn.vimconnNotFoundException("The vm {} does not exist or is already deleted".format(vm_id))
        except Exception as e:
            self.logger.error("Delete vm instance " + str(vm_id) + " error: " + str(e))
            raise vimconn.vimconnException(e)

    def refresh_vms_status(self, vm_list):
        """Get the status of the virtual machines and their interfaces/ports
           Params: the list of VM identifiers
           Returns a dictionary with:
                vm_id:          #VIM id of this Virtual Machine
                    status:     #Mandatory. Text with one of:
                                #  DELETED (not found at vim)
                                #  VIM_ERROR (Cannot connect to VIM, VIM response error, ...)
                                #  OTHER (Vim reported other status not understood)
                                #  ERROR (VIM indicates an ERROR status)
                                #  ACTIVE, PAUSED, SUSPENDED, INACTIVE (not running),
                                #  BUILD (on building process), ERROR
                                #  ACTIVE:NoMgmtIP (Active but any of its interface has an IP address
                                #
                    error_msg:  #Text with VIM error message, if any. Or the VIM connection ERROR
                    vim_info:   #Text with plain information obtained from vim (yaml.safe_dump)
                    interfaces: list with interface info. Each item a dictionary with:
                        vim_info:         #Text with plain information obtained from vim (yaml.safe_dump)
                        mac_address:      #Text format XX:XX:XX:XX:XX:XX
                        vim_net_id:       #network id where this interface is connected, if provided at creation
                        vim_interface_id: #interface/port VIM id
                        ip_address:       #null, or text with IPv4, IPv6 address
                        compute_node:     #identification of compute node where PF,VF interface is allocated
                        pci:              #PCI address of the NIC that hosts the PF,VF
                        vlan:             #physical VLAN used for VF
        """
        vm_dict = {}
        try:
            for vm_id in vm_list:
                vm = {}
                if self.get_vminstance(vm_id) is not None:
                    vm_element = self.get_vminstance(vm_id)
                else:
                    self.logger.info("The vm " + str(vm_id) + " does not exist.")
                    vm['status'] = "DELETED"
                    vm['error_msg'] = ("The vm " + str(vm_id) + " does not exist.")
                    continue
                vm["vim_info"] = None
                vm_status = vm_element.LCM_STATE
                if vm_status == 3:
                    vm['status'] = "ACTIVE"
                elif vm_status == 36:
                    vm['status'] = "ERROR"
                    vm['error_msg'] = "VM failure"
                else:
                    vm['status'] = "BUILD"

                if vm_element is not None:
                    interfaces = self._get_networks_vm(vm_element)
                    vm["interfaces"] = interfaces
                vm_dict[vm_id] = vm
            return vm_dict
        except Exception as e:
            self.logger.error(e)
            for k in vm_dict:
                vm_dict[k]["status"] = "VIM_ERROR"
                vm_dict[k]["error_msg"] = str(e)
            return vm_dict

    def _get_networks_vm(self, vm_element):
        interfaces = []
        try:
            if isinstance(vm_element.TEMPLATE["NIC"], list):
                for net in vm_element.TEMPLATE["NIC"]:
                    interface = {'vim_info': None, "mac_address": str(net["MAC"]), "vim_net_id": str(net["NETWORK_ID"]),
                                 "vim_interface_id": str(net["NETWORK_ID"])}
                    # maybe it should be 2 different keys for ip_address if an interface has ipv4 and ipv6
                    if u'IP' in net:
                        interface["ip_address"] = str(net["IP"])
                    if u'IP6_GLOBAL' in net:
                        interface["ip_address"] = str(net["IP6_GLOBAL"])
                    interfaces.append(interface)
            else:
                net = vm_element.TEMPLATE["NIC"]
                interface = {'vim_info': None, "mac_address": str(net["MAC"]), "vim_net_id": str(net["NETWORK_ID"]),
                             "vim_interface_id": str(net["NETWORK_ID"])}
                # maybe it should be 2 different keys for ip_address if an interface has ipv4 and ipv6
                if u'IP' in net:
                    interface["ip_address"] = str(net["IP"])
                if u'IP6_GLOBAL' in net:
                    interface["ip_address"] = str(net["IP6_GLOBAL"])
                interfaces.append(interface)
            return interfaces
        except Exception as e:
            self.logger.error("Error getting vm interface_information of vm_id: " + str(vm_element.ID))
