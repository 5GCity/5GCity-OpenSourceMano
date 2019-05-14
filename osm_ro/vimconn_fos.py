# -*- coding: utf-8 -*-

##
# Copyright 2019 ADLINK Technology Inc..
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
#

"""
Eclipse fog05 connector, implements methods to interact with fog05 using REST Client + REST Proxy

Manages LXD containers on x86_64 by default, currently missing EPA and VF/PF
Support config dict:
    - arch : cpu architecture for the VIM
    - hypervisor: virtualization technology supported by the VIM, can
                can be one of: LXD, KVM, BARE, XEN, DOCKER, MCU
                the selected VIM need to have at least a node with support
                for the selected hypervisor

"""
__author__="Gabriele Baldoni"
__date__ ="$13-may-2019 10:35:12$"

import uuid
import socket
import struct
import vimconn
import random
import yaml
from functools import partial
from fog05rest import FIMAPI
from fog05rest import fimerrors


class vimconnector(vimconn.vimconnector):
    def __init__(self, uuid, name, tenant_id, tenant_name, url, url_admin=None, user=None, passwd=None, log_level=None,
                 config={}, persistent_info={}):
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
                                      config, persistent_info)

        self.logger.debug('vimconn_fos init with config: {}'.format(config))
        self.arch = config.get('arch', 'x86_64')
        self.hv = config.get('hypervisor', 'LXD')
        self.nodes = config.get('nodes', [])
        self.fdu_node_map = {}
        self.fos_api = FIMAPI(locator=self.url)


    def __get_ip_range(self, first, count):
        int_first = struct.unpack('!L', socket.inet_aton(first))[0]
        int_last = int_first + count
        last = socket.inet_ntoa(struct.pack('!L', int_last))
        return (first, last)

    def __name_filter(self, desc, filter_name=None):
        if filter_name is None:
            return True
        return desc.get('name') == filter_name

    def __id_filter(self, desc, filter_id=None):
        if filter_id is None:
            return True
        return desc.get('uuid') == filter_id

    def __checksum_filter(self, desc, filter_checksum=None):
        if filter_checksum is None:
            return True
        return desc.get('checksum') == filter_checksum

    def check_vim_connectivity(self):
        """Checks VIM can be reached and user credentials are ok.
        Returns None if success or raised vimconnConnectionException, vimconnAuthException, ...
        """
        try:
            self.fos_api.check()
            return None
        except fimerrors.FIMAuthExcetpion as fae:
            raise vimconn.vimconnAuthException("Unable to authenticate to the VIM. Error {}".format(fae))
        except Exception as e:
            raise vimconn.vimconnConnectionException("VIM not reachable. Error {}".format(e))

    def new_network(self, net_name, net_type, ip_profile=None, shared=False, vlan=None):
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
        Returns the network identifier on success or raises and exception on failure
        """
        self.logger.debug('new_network: {}'.format(locals()))
        if net_type in ['data','ptp']:
            raise vimconn.vimconnNotImplemented('{} type of network not supported'.format(net_type))

        net_uuid = '{}'.format(uuid.uuid4())
        desc = {
            'uuid':net_uuid,
            'name':net_name,
            'net_type':'ELAN',
            'is_mgmt':False
            }

        if ip_profile is not None:
            ip = {}
            if ip_profile.get('ip_version') == 'IPv4':
                ip_info = {}
                ip_range = self.__get_ip_range(ip_profile.get('dhcp_start_address'), ip_profile.get('dhcp_count'))
                dhcp_range = '{},{}'.format(ip_range[0],ip_range[1])
                ip.update({'subnet':ip_profile.get('subnet_address')})
                ip.update({'dns':ip_profile.get('dns', None)})
                ip.update({'dhcp_enable':ip_profile.get('dhcp_enabled', False)})
                ip.update({'dhcp_range': dhcp_range})
                ip.update({'gateway':ip_profile.get('gateway_address', None)})
                desc.update({'ip_configuration':ip_info})
            else:
                raise vimconn.vimconnNotImplemented('IPV6 network is not implemented at VIM')
            desc.update({'ip_configuration':ip})
        self.logger.debug('VIM new_network args: {} - Generated Eclipse fog05 Descriptor {}'.format(locals(), desc))
        try:
            self.fos_api.network.add_network(desc)
        except fimerrors.FIMAResouceExistingException as free:
            raise vimconn.vimconnConflictException("Network already exists at VIM. Error {}".format(free))
        except Exception as e:
            raise vimconn.vimconnException("Unable to create network {}. Error {}".format(net_name, e))
            # No way from the current rest service to get the actual error, most likely it will be an already existing error
        return net_uuid

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
        self.logger.debug('get_network_list: {}'.format(filter_dict))
        res = []
        try:
            nets = self.fos_api.network.list()
        except Exception as e:
            raise vimconn.vimconnConnectionException("Cannot get network list from VIM, connection error. Error {}".format(e))

        filters = [
            partial(self.__name_filter, filter_name=filter_dict.get('name')),
            partial(self.__id_filter,filter_id=filter_dict.get('id'))
        ]

        r1 = []

        for n in nets:
            match = True
            for f in filters:
                match = match and f(n)
            if match:
                r1.append(n)

        for n in r1:
            osm_net = {
                'id':n.get('uuid'),
                'name':n.get('name'),
                'status':'ACTIVE'
            }
            res.append(osm_net)
        return res

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
        self.logger.debug('get_network: {}'.format(net_id))
        res = self.get_network_list(filter_dict={'id':net_id})
        if len(res) == 0:
            raise vimconn.vimconnNotFoundException("Network {} not found at VIM".format(net_id))
        return res[0]

    def delete_network(self, net_id):
        """Deletes a tenant network from VIM
        Returns the network identifier or raises an exception upon error or when network is not found
        """
        self.logger.debug('delete_network: {}'.format(net_id))
        try:
            self.fos_api.network.remove_network(net_id)
        except fimerrors.FIMNotFoundException as fnfe:
            raise vimconn.vimconnNotFoundException("Network {} not found at VIM (already deleted?). Error {}".format(net_id, fnfe))
        except Exception as e:
            raise vimconn.vimconnException("Cannot delete network {} from VIM. Error {}".format(net_id, e))
        return net_id

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
        self.logger.debug('Refeshing network status with args: {}'.format(locals()))
        r = {}
        for n in net_list:
            try:
                osm_n = self.get_network(n)
                r.update({
                    osm_n.get('id'):{'status':osm_n.get('status')}
                })
            except vimconn.vimconnNotFoundException:
                r.update({
                    n:{'status':'VIM_ERROR'}
                })
        return r

    def get_flavor(self, flavor_id):
        """Obtain flavor details from the VIM
        Returns the flavor dict details {'id':<>, 'name':<>, other vim specific }
        Raises an exception upon error or if not found
        """
        self.logger.debug('VIM get_flavor with args: {}'.format(locals()))
        try:
            r = self.fos_api.flavor.get(flavor_id)
        except Exception as e:
            raise vimconn.vimconnConnectionException("VIM not reachable. Error {}".format(e))
        if r is None:
            raise vimconn.vimconnNotFoundException("Flavor not found at VIM")
        return {'id':r.get('uuid'), 'name':r.get('name'), 'fos':r}

    def get_flavor_id_from_data(self, flavor_dict):
        """Obtain flavor id that match the flavor description
        Params:
            'flavor_dict': dictionary that contains:
                'disk': main hard disk in GB
                'ram': meomry in MB
                'vcpus': number of virtual cpus
                #TODO: complete parameters for EPA
        Returns the flavor_id or raises a vimconnNotFoundException
        """
        self.logger.debug('VIM get_flavor_id_from_data with args : {}'.format(locals()))

        try:
            flvs = self.fos_api.flavor.list()
        except Exception as e:
            raise vimconn.vimconnConnectionException("VIM not reachable. Error {}".format(e))
        r = [x.get('uuid') for x in flvs if (x.get('cpu_min_count') == flavor_dict.get('vcpus') and x.get('ram_size_mb') == flavor_dict.get('ram') and x.get('storage_size_gb') == flavor_dict.get('disk'))]
        if len(r) == 0:
            raise vimconn.vimconnNotFoundException ( "No flavor found" )
        return r[0]

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
        self.logger.debug('VIM new_flavor with args: {}'.format(locals()))
        flv_id = '{}'.format(uuid.uuid4())
        desc = {
            'uuid':flv_id,
            'name':flavor_data.get('name'),
            'cpu_arch': self.arch,
            'cpu_min_count': flavor_data.get('vcpus'),
            'cpu_min_freq': 0.0,
            'ram_size_mb':float(flavor_data.get('ram')),
            'storage_size_gb':float(flavor_data.get('disk'))
        }
        try:
            self.fos_api.flavor.add(desc)
        except fimerrors.FIMAResouceExistingException as free:
            raise vimconn.vimconnConflictException("Flavor {} already exist at VIM. Error {}".format(flv_id, free))
        except Exception as e:
            raise vimconn.vimconnConnectionException("VIM not reachable. Error {}".format(e))
        return flv_id


    def delete_flavor(self, flavor_id):
        """Deletes a tenant flavor from VIM identify by its id
        Returns the used id or raise an exception"""
        try:
            self.fos_api.flavor.remove(flavor_id)
        except fimerrors.FIMNotFoundException as fnfe:
            raise vimconn.vimconnNotFoundException("Flavor {} not found at VIM (already deleted?). Error {}".format(flavor_id, fnfe))
        except Exception as e:
            raise vimconn.vimconnConnectionException("VIM not reachable. Error {}".format(e))
        return flavor_id

    def new_image(self, image_dict):
        """ Adds a tenant image to VIM. imge_dict is a dictionary with:
            name: name
            disk_format: qcow2, vhd, vmdk, raw (by default), ...
            location: path or URI
            public: "yes" or "no"
            metadata: metadata of the image
        Returns the image id or raises an exception if failed
        """
        self.logger.debug('VIM new_image with args: {}'.format(locals()))
        img_id = '{}'.format(uuid.uuid4())
        desc = {
            'name':image_dict.get('name'),
            'uuid':img_id,
            'uri':image_dict.get('location')
        }
        try:
            self.fos_api.image.add(desc)
        except fimerrors.FIMAResouceExistingException as free:
            raise vimconn.vimconnConflictException("Image {} already exist at VIM. Error {}".format(img_id, free))
        except Exception as e:
            raise vimconn.vimconnConnectionException("VIM not reachable. Error {}".format(e))
        return img_id

    def get_image_id_from_path(self, path):

        """Get the image id from image path in the VIM database.
           Returns the image_id or raises a vimconnNotFoundException
        """
        self.logger.debug('VIM get_image_id_from_path with args: {}'.format(locals()))
        try:
            imgs = self.fos_api.image.list()
        except Exception as e:
            raise vimconn.vimconnConnectionException("VIM not reachable. Error {}".format(e))
        res = [x.get('uuid') for x in imgs if x.get('uri')==path]
        if len(res) == 0:
            raise vimconn.vimconnNotFoundException("Image with this path was not found")
        return res[0]

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
        self.logger.debug('VIM get_image_list args: {}'.format(locals()))
        r = []
        try:
            fimgs = self.fos_api.image.list()
        except Exception as e:
            raise vimconn.vimconnConnectionException("VIM not reachable. Error {}".format(e))

        filters = [
            partial(self.__name_filter, filter_name=filter_dict.get('name')),
            partial(self.__id_filter,filter_id=filter_dict.get('id')),
            partial(self.__checksum_filter,filter_checksum=filter_dict.get('checksum'))
        ]

        r1 = []

        for i in fimgs:
            match = True
            for f in filters:
                match = match and f(i)
            if match:
                r1.append(i)

        for i in r1:
            img_info = {
                'name':i.get('name'),
                'id':i.get('uuid'),
                'checksum':i.get('checksum'),
                'location':i.get('uri'),
                'fos':i
            }
            r.append(img_info)
        return r
        #raise vimconnNotImplemented( "Should have implemented this" )

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
        self.logger.debug('new_vminstance with rgs: {}'.format(locals()))
        fdu_uuid = '{}'.format(uuid.uuid4())

        flv = self.fos_api.flavor.get(flavor_id)
        img = self.fos_api.image.get(image_id)

        if flv is None:
            raise vimconn.vimconnNotFoundException("Flavor {} not found at VIM".format(flavor_id))
        if img is None:
            raise vimconn.vimconnNotFoundException("Image {} not found at VIM".format(image_id))

        created_items = {
            'fdu_id':'',
            'node_id':'',
            'connection_points':[]
            }

        fdu_desc = {
            'name':name,
            'uuid':fdu_uuid,
            'computation_requirements':flv,
            'image':img,
            'hypervisor':self.hv,
            'migration_kind':'LIVE',
            'interfaces':[],
            'io_ports':[],
            'connection_points':[],
            'depends_on':[]
        }

        nets = []
        cps = []
        intf_id = 0
        for n in net_list:
            cp_id = '{}'.format(uuid.uuid4())
            n.update({'vim_id':cp_id})
            pair_id = n.get('net_id')

            cp_d = {
                'uuid':cp_id,
                'pair_id':pair_id
            }
            intf_d = {
                'name':n.get('name','eth{}'.format(intf_id)),
                'is_mgmt':False,
                'if_type':'INTERNAL',
                'virtual_interface':{
                    'intf_type':n.get('model','VIRTIO'),
                    'vpci':n.get('vpci','0:0:0'),
                    'bandwidth':int(n.get('bw', 100))
                }
            }
            if n.get('mac_address', None) is not None:
                intf_d['mac_address'] = n['mac_address']

            created_items['connection_points'].append(cp_id)
            fdu_desc['connection_points'].append(cp_d)
            fdu_desc['interfaces'].append(intf_d)

            intf_id = intf_id + 1

        if cloud_config is not None:
            configuration = {
                    'conf_type':'CLOUD_INIT'
                }
            if cloud_config.get('user-data') is not None:
                configuration.update({'script':cloud_config.get('user-data')})
            if cloud_config.get('key-pairs') is not None:
                configuration.update({'ssh_keys':cloud_config.get('key-pairs')})

            if 'script' in configuration:
                fdu_desc.update({'configuration':configuration})

        ### NODE Selection ###
        # Infrastructure info
        #   nodes dict with
        #        uuid -> node uuid
        #        computational capabilities -> cpu, ram, and disk available
        #        hypervisors -> list of available hypervisors (eg. KVM, LXD, BARE)
        #
        #

        # UPDATING AVAILABLE INFRASTRUCTURE

        if len(self.nodes) == 0:
            nodes_id = self.fos_api.node.list()
        else:
            nodes_id = self.nodes
        nodes = []
        for n in nodes_id:
            n_info = self.fos_api.node.info(n)
            if n_info is None:
                continue
            n_plugs = []
            for p in self.fos_api.node.plugins(n):
                n_plugs.append(self.fos_api.plugin.info(n,p))

            n_cpu_number =  len(n_info.get('cpu'))
            n_cpu_arch = n_info.get('cpu')[0].get('arch')
            n_cpu_freq = n_info.get('cpu')[0].get('frequency')
            n_ram = n_info.get('ram').get('size')
            n_disk_size = sorted(list(filter(lambda x: 'sda' in x['local_address'], n_info.get('disks'))), key= lambda k: k['dimension'])[-1].get('dimension')

            hvs = []
            for p in n_plugs:
                if p.get('type') == 'runtime':
                    hvs.append(p.get('name'))

            ni = {
                'uuid':n,
                'computational_capabilities':{
                    'cpu_count':n_cpu_number,
                    'cpu_arch':n_cpu_arch,
                    'cpu_freq':n_cpu_freq,
                    'ram_size':n_ram,
                    'disk_size':n_disk_size
                },
                'hypervisors':hvs
            }
            nodes.append(ni)

        # NODE SELECTION
        compatible_nodes = []
        for n in nodes:
            if fdu_desc.get('hypervisor') in n.get('hypervisors'):
                n_comp = n.get('computational_capabilities')
                f_comp = fdu_desc.get('computation_requirements')
                if f_comp.get('cpu_arch') == n_comp.get('cpu_arch'):
                    if f_comp.get('cpu_min_count') <= n_comp.get('cpu_count') and f_comp.get('ram_size_mb') <= n_comp.get('ram_size'):
                        if f_comp.get('disk_size_gb') <= n_comp.get('disk_size'):
                            compatible_nodes.append(n)

        if len(compatible_nodes) == 0:
            raise vimconn.vimconnConflictException("No available nodes at VIM")
        selected_node = random.choice(compatible_nodes)

        created_items.update({'fdu_id':fdu_uuid, 'node_id': selected_node.get('uuid')})

        self.logger.debug('FOS Node {} FDU Descriptor: {}'.format(selected_node.get('uuid'), fdu_desc))

        try:
            self.fos_api.fdu.onboard(fdu_desc)
            instanceid = self.fos_api.fdu.instantiate(fdu_uuid, selected_node.get('uuid'))
            created_items.update({'instance_id':instanceid})

            self.fdu_node_map.update({instanceid: selected_node.get('uuid')})
            self.logger.debug('new_vminstance return: {}'.format((fdu_uuid, created_items)))
            return (instanceid, created_items)
        except fimerrors.FIMAResouceExistingException as free:
            raise vimconn.vimconnConflictException("VM already exists at VIM. Error {}".format(free))
        except Exception as e:
            raise vimconn.vimconnException("Error while instantiating VM {}. Error {}".format(name, e))


    def get_vminstance(self,vm_id):
        """Returns the VM instance information from VIM"""
        self.logger.debug('VIM get_vminstance with args: {}'.format(locals()))

        try:
            intsinfo = self.fos_api.fdu.instance_info(vm_id)
        except Exception as e:
            raise vimconn.vimconnConnectionException("VIM not reachable. Error {}".format(e))
        if intsinfo is None:
            raise vimconn.vimconnNotFoundException('VM with id {} not found!'.format(vm_id))
        return intsinfo


    def delete_vminstance(self, vm_id, created_items=None):
        """
        Removes a VM instance from VIM and each associate elements
        :param vm_id: VIM identifier of the VM, provided by method new_vminstance
        :param created_items: dictionary with extra items to be deleted. provided by method new_vminstance and/or method
            action_vminstance
        :return: None or the same vm_id. Raises an exception on fail
        """
        self.logger.debug('FOS delete_vminstance with args: {}'.format(locals()))
        fduid =  created_items.get('fdu_id')
        try:
            self.fos_api.fdu.terminate(vm_id)
            self.fos_api.fdu.offload(fduid)
        except Exception as e:
            raise vimconn.vimconnException("Error on deletting VM with id {}. Error {}".format(vm_id,e))
        return vm_id

        #raise vimconnNotImplemented( "Should have implemented this" )

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
        self.logger.debug('FOS refresh_vms_status with args: {}'.format(locals()))
        fos2osm_status = {
            'DEFINE':'OTHER',
            'CONFIGURE':'INACTIVE',
            'RUN':'ACTIVE',
            'PAUSE':'PAUSED',
            'ERROR':'ERROR'
        }

        r = {}

        for vm in vm_list:
            self.logger.debug('FOS refresh_vms_status for {}'.format(vm))

            info = {}
            nid = self.fdu_node_map.get(vm)
            if nid is None:
                r.update({vm:{
                    'status':'VIM_ERROR',
                    'error_msg':'Not compute node associated for VM'
                }})
                continue

            try:
                vm_info = self.fos_api.fdu.instance_info(vm)
            except:
                r.update({vm:{
                    'status':'VIM_ERROR',
                    'error_msg':'unable to connect to VIM'
                }})
                continue

            if vm_info is None:
                r.update({vm:{'status':'DELETED'}})
                continue


            desc = self.fos_api.fdu.info(vm_info['fdu_uuid'])
            osm_status = fos2osm_status.get(vm_info.get('status'))

            self.logger.debug('FOS status info {}'.format(vm_info))
            self.logger.debug('FOS status is {} <-> OSM Status {}'.format(vm_info.get('status'), osm_status))
            info.update({'status':osm_status})
            if vm_info.get('status') == 'ERROR':
                info.update({'error_msg':vm_info.get('error_code')})
            info.update({'vim_info':yaml.safe_dump(vm_info)})
            faces = []
            i = 0
            for intf_name in vm_info.get('hypervisor_info').get('network',[]):
                intf_info = vm_info.get('hypervisor_info').get('network').get(intf_name)
                face = {}
                face['compute_node'] = nid
                face['vim_info'] = yaml.safe_dump(intf_info)
                face['mac_address'] = intf_info.get('hwaddr')
                addrs = []
                for a in intf_info.get('addresses'):
                    addrs.append(a.get('address'))
                if len(addrs) >= 0:
                    face['ip_address'] = ','.join(addrs)
                else:
                    face['ip_address'] = ''
                face['pci'] = '0:0:0.0'
                # getting net id by CP
                try:
                    cp_info = vm_info.get('connection_points')[i]
                except IndexError:
                    cp_info = None
                if cp_info is not None:
                    cp_id = cp_info['cp_uuid']
                    cps_d = desc['connection_points']
                    matches = [x for x in cps_d if x['uuid'] == cp_id]
                    if len(matches) > 0:
                        cpd = matches[0]
                        face['vim_net_id'] = cpd.get('pair_id','')
                    else:
                        face['vim_net_id'] = ''
                    face['vim_interface_id'] = cp_id
                    # cp_info.get('uuid')
                else:
                    face['vim_net_id'] = ''
                    face['vim_interface_id'] = intf_name
                faces.append(face)
                i += 1



            info.update({'interfaces':faces})
            r.update({vm:info})
            self.logger.debug('FOS refresh_vms_status res for {} is {}'.format(vm, info))
        self.logger.debug('FOS refresh_vms_status res is {}'.format(r))
        return r


        #raise vimconnNotImplemented( "Should have implemented this" )

    def action_vminstance(self, vm_id, action_dict, created_items={}):
        """
        Send and action over a VM instance. Returns created_items if the action was successfully sent to the VIM.
        created_items is a dictionary with items that
        :param vm_id: VIM identifier of the VM, provided by method new_vminstance
        :param action_dict: dictionary with the action to perform
        :param created_items: provided by method new_vminstance is a dictionary with key-values that will be passed to
            the method delete_vminstance. Can be used to store created ports, volumes, etc. Format is vimconnector
            dependent, but do not use nested dictionaries and a value of None should be the same as not present. This
            method can modify this value
        :return: None, or a console dict
        """
        self.logger.debug('VIM action_vminstance with args: {}'.format(locals()))
        nid = self.fdu_node_map.get(vm_id)
        if nid is None:
            raise vimconn.vimconnNotFoundException('No node for this VM')
        try:
            fdu_info = self.fos_api.fdu.instance_info(vm_id)
            if "start" in action_dict:
                if fdu_info.get('status') == 'CONFIGURE':
                    self.fos_api.fdu.start(vm_id)
                elif fdu_info.get('status') == 'PAUSE':
                    self.fos_api.fdu.resume(vm_id)
                else:
                    raise vimconn.vimconnConflictException("Cannot start from this state")
            elif "pause" in action_dict:
                if fdu_info.get('status') == 'RUN':
                    self.fos_api.fdu.pause(vm_id)
                else:
                    raise vimconn.vimconnConflictException("Cannot pause from this state")
            elif "resume" in action_dict:
                if fdu_info.get('status') == 'PAUSE':
                    self.fos_api.fdu.resume(vm_id)
                else:
                    raise vimconn.vimconnConflictException("Cannot resume from this state")
            elif "shutoff" in action_dict or "shutdown" or "forceOff" in action_dict:
                if fdu_info.get('status') == 'RUN':
                    self.fos_api.fdu.stop(vm_id)
                else:
                    raise vimconn.vimconnConflictException("Cannot shutoff from this state")
            elif "terminate" in action_dict:
                if fdu_info.get('status') == 'RUN':
                    self.fos_api.fdu.stop(vm_id)
                    self.fos_api.fdu.clean(vm_id)
                    self.fos_api.fdu.undefine(vm_id)
                    # self.fos_api.fdu.offload(vm_id)
                elif fdu_info.get('status') == 'CONFIGURE':
                    self.fos_api.fdu.clean(vm_id)
                    self.fos_api.fdu.undefine(vm_id)
                    # self.fos_api.fdu.offload(vm_id)
                elif fdu_info.get('status') == 'PAUSE':
                    self.fos_api.fdu.resume(vm_id)
                    self.fos_api.fdu.stop(vm_id)
                    self.fos_api.fdu.clean(vm_id)
                    self.fos_api.fdu.undefine(vm_id)
                    # self.fos_api.fdu.offload(vm_id)
                else:
                    raise vimconn.vimconnConflictException("Cannot terminate from this state")
            elif "rebuild" in action_dict:
                raise vimconnNotImplemented("Rebuild not implememnted")
            elif "reboot" in action_dict:
                if fdu_info.get('status') == 'RUN':
                    self.fos_api.fdu.stop(vm_id)
                    self.fos_api.fdu.start(vm_id)
                else:
                    raise vimconn.vimconnConflictException("Cannot reboot from this state")
        except Exception as e:
            raise vimconn.vimconnConnectionException("VIM not reachable. Error {}".format(e))
