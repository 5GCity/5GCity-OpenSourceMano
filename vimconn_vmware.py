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

"""
vimconn_vmware implementation an Abstract class in order to interact with VMware  vCloud Director.
mbayramov@vmware.com
"""
from progressbar import Percentage, Bar, ETA, FileTransferSpeed, ProgressBar

import vimconn
import os
import traceback
import itertools
import requests
import ssl
import atexit

from pyVmomi import vim, vmodl
from pyVim.connect import SmartConnect, Disconnect

from xml.etree import ElementTree as XmlElementTree
from lxml import etree as lxmlElementTree

import yaml
from pyvcloud import Http
from pyvcloud.vcloudair import VCA
from pyvcloud.schema.vcd.v1_5.schemas.vcloud import sessionType, organizationType, \
    vAppType, organizationListType, vdcType, catalogType, queryRecordViewType, \
    networkType, vcloudType, taskType, diskType, vmsType, vdcTemplateListType, mediaType
from xml.sax.saxutils import escape

from pyvcloud.schema.vcd.v1_5.schemas.admin.vCloudEntities import TaskType
from pyvcloud.schema.vcd.v1_5.schemas.vcloud.taskType import TaskType as GenericTask
from pyvcloud.schema.vcd.v1_5.schemas.vcloud.vAppType import TaskType as VappTask
from pyvcloud.schema.vcd.v1_5.schemas.admin.vCloudEntities import TasksInProgressType

import logging
import json
import time
import uuid
import httplib
import hashlib
import socket
import struct
import netaddr

# global variable for vcd connector type
STANDALONE = 'standalone'

# key for flavor dicts
FLAVOR_RAM_KEY = 'ram'
FLAVOR_VCPUS_KEY = 'vcpus'
FLAVOR_DISK_KEY = 'disk'
DEFAULT_IP_PROFILE = {'gateway_address':"192.168.1.1",
                      'dhcp_count':50,
                      'subnet_address':"192.168.1.0/24",
                      'dhcp_enabled':True,
                      'dhcp_start_address':"192.168.1.3",
                      'ip_version':"IPv4",
                      'dns_address':"192.168.1.2"
                      }
# global variable for wait time
INTERVAL_TIME = 5
MAX_WAIT_TIME = 1800

VCAVERSION = '5.9'

__author__ = "Mustafa Bayramov, Arpita Kate, Sachin Bhangare"
__date__ = "$12-Jan-2017 11:09:29$"
__version__ = '0.1'

#     -1: "Could not be created",
#     0: "Unresolved",
#     1: "Resolved",
#     2: "Deployed",
#     3: "Suspended",
#     4: "Powered on",
#     5: "Waiting for user input",
#     6: "Unknown state",
#     7: "Unrecognized state",
#     8: "Powered off",
#     9: "Inconsistent state",
#     10: "Children do not all have the same status",
#     11: "Upload initiated, OVF descriptor pending",
#     12: "Upload initiated, copying contents",
#     13: "Upload initiated , disk contents pending",
#     14: "Upload has been quarantined",
#     15: "Upload quarantine period has expired"

# mapping vCD status to MANO
vcdStatusCode2manoFormat = {4: 'ACTIVE',
                            7: 'PAUSED',
                            3: 'SUSPENDED',
                            8: 'INACTIVE',
                            12: 'BUILD',
                            -1: 'ERROR',
                            14: 'DELETED'}

#
netStatus2manoFormat = {'ACTIVE': 'ACTIVE', 'PAUSED': 'PAUSED', 'INACTIVE': 'INACTIVE', 'BUILD': 'BUILD',
                        'ERROR': 'ERROR', 'DELETED': 'DELETED'
                        }

# dict used to store flavor in memory
flavorlist = {}


class vimconnector(vimconn.vimconnector):
    def __init__(self, uuid=None, name=None, tenant_id=None, tenant_name=None,
                 url=None, url_admin=None, user=None, passwd=None, log_level=None, config={}):
        """
        Constructor create vmware connector to vCloud director.

        By default construct doesn't validate connection state. So client can create object with None arguments.
        If client specified username , password and host and VDC name.  Connector initialize other missing attributes.

        a) It initialize organization UUID
        b) Initialize tenant_id/vdc ID.   (This information derived from tenant name)

        Args:
            uuid - is organization uuid.
            name - is organization name that must be presented in vCloud director.
            tenant_id - is VDC uuid it must be presented in vCloud director
            tenant_name - is VDC name.
            url - is hostname or ip address of vCloud director
            url_admin - same as above.
            user - is user that administrator for organization. Caller must make sure that
                    username has right privileges.

            password - is password for a user.

            VMware connector also requires PVDC administrative privileges and separate account.
            This variables must be passed via config argument dict contains keys

            dict['admin_username']
            dict['admin_password']

            Returns:
                Nothing.
        """

        vimconn.vimconnector.__init__(self, uuid, name, tenant_id, tenant_name, url,
                                      url_admin, user, passwd, log_level, config)

        self.logger = logging.getLogger('openmano.vim.vmware')
        self.logger.setLevel(10)

        self.name = name
        self.id = uuid
        self.url = url
        self.url_admin = url_admin
        self.tenant_id = tenant_id
        self.tenant_name = tenant_name
        self.user = user
        self.passwd = passwd
        self.config = config
        self.admin_password = None
        self.admin_user = None
        self.org_name = ""

        if tenant_name is not None:
            orgnameandtenant = tenant_name.split(":")
            if len(orgnameandtenant) == 2:
                self.tenant_name = orgnameandtenant[1]
                self.org_name = orgnameandtenant[0]
            else:
                self.tenant_name = tenant_name
        if "orgname" in config:
            self.org_name = config['orgname']

        if log_level:
            self.logger.setLevel(getattr(logging, log_level))

        try:
            self.admin_user = config['admin_username']
            self.admin_password = config['admin_password']
        except KeyError:
            raise vimconn.vimconnException(message="Error admin username or admin password is empty.")

        self.org_uuid = None
        self.vca = None

        if not url:
            raise vimconn.vimconnException('url param can not be NoneType')

        if not self.url_admin:  # try to use normal url
            self.url_admin = self.url

        logging.debug("UUID: {} name: {} tenant_id: {} tenant name {}".format(self.id, self.org_name,
                                                                              self.tenant_id, self.tenant_name))
        logging.debug("vcd url {} vcd username: {} vcd password: {}".format(self.url, self.user, self.passwd))
        logging.debug("vcd admin username {} vcd admin passowrd {}".format(self.admin_user, self.admin_password))

        # initialize organization
        if self.user is not None and self.passwd is not None and self.url:
            self.init_organization()

    def __getitem__(self, index):
        if index == 'name':
            return self.name
        if index == 'tenant_id':
            return self.tenant_id
        if index == 'tenant_name':
            return self.tenant_name
        elif index == 'id':
            return self.id
        elif index == 'org_name':
            return self.org_name
        elif index == 'org_uuid':
            return self.org_uuid
        elif index == 'user':
            return self.user
        elif index == 'passwd':
            return self.passwd
        elif index == 'url':
            return self.url
        elif index == 'url_admin':
            return self.url_admin
        elif index == "config":
            return self.config
        else:
            raise KeyError("Invalid key '%s'" % str(index))

    def __setitem__(self, index, value):
        if index == 'name':
            self.name = value
        if index == 'tenant_id':
            self.tenant_id = value
        if index == 'tenant_name':
            self.tenant_name = value
        elif index == 'id':
            self.id = value
        elif index == 'org_name':
            self.org_name = value
        elif index == 'org_uuid':
            self.org_uuid = value
        elif index == 'user':
            self.user = value
        elif index == 'passwd':
            self.passwd = value
        elif index == 'url':
            self.url = value
        elif index == 'url_admin':
            self.url_admin = value
        else:
            raise KeyError("Invalid key '%s'" % str(index))

    def connect_as_admin(self):
        """ Method connect as pvdc admin user to vCloud director.
            There are certain action that can be done only by provider vdc admin user.
            Organization creation / provider network creation etc.

            Returns:
                The return vca object that letter can be used to connect to vcloud direct as admin for provider vdc
        """

        self.logger.debug("Logging in to a vca {} as admin.".format(self.org_name))

        vca_admin = VCA(host=self.url,
                        username=self.admin_user,
                        service_type=STANDALONE,
                        version=VCAVERSION,
                        verify=False,
                        log=False)
        result = vca_admin.login(password=self.admin_password, org='System')
        if not result:
            raise vimconn.vimconnConnectionException(
                "Can't connect to a vCloud director as: {}".format(self.admin_user))
        result = vca_admin.login(token=vca_admin.token, org='System', org_url=vca_admin.vcloud_session.org_url)
        if result is True:
            self.logger.info(
                "Successfully logged to a vcloud direct org: {} as user: {}".format('System', self.admin_user))

        return vca_admin

    def connect(self):
        """ Method connect as normal user to vCloud director.

            Returns:
                The return vca object that letter can be used to connect to vCloud director as admin for VDC
        """

        try:
            self.logger.debug("Logging in to a vca {} as {} to datacenter {}.".format(self.org_name,
                                                                                      self.user,
                                                                                      self.org_name))
            vca = VCA(host=self.url,
                      username=self.user,
                      service_type=STANDALONE,
                      version=VCAVERSION,
                      verify=False,
                      log=False)

            result = vca.login(password=self.passwd, org=self.org_name)
            if not result:
                raise vimconn.vimconnConnectionException("Can't connect to a vCloud director as: {}".format(self.user))
            result = vca.login(token=vca.token, org=self.org_name, org_url=vca.vcloud_session.org_url)
            if result is True:
                self.logger.info(
                    "Successfully logged to a vcloud direct org: {} as user: {}".format(self.org_name, self.user))

        except:
            raise vimconn.vimconnConnectionException("Can't connect to a vCloud director org: "
                                                     "{} as user: {}".format(self.org_name, self.user))

        return vca

    def init_organization(self):
        """ Method initialize organization UUID and VDC parameters.

            At bare minimum client must provide organization name that present in vCloud director and VDC.

            The VDC - UUID ( tenant_id) will be initialized at the run time if client didn't call constructor.
            The Org - UUID will be initialized at the run time if data center present in vCloud director.

            Returns:
                The return vca object that letter can be used to connect to vcloud direct as admin
        """
        try:
            if self.org_uuid is None:
                org_dict = self.get_org_list()
                for org in org_dict:
                    # we set org UUID at the init phase but we can do it only when we have valid credential.
                    if org_dict[org] == self.org_name:
                        self.org_uuid = org
                        self.logger.debug("Setting organization UUID {}".format(self.org_uuid))
                        break
                else:
                    raise vimconn.vimconnException("Vcloud director organization {} not found".format(self.org_name))

                # if well good we require for org details
                org_details_dict = self.get_org(org_uuid=self.org_uuid)

                # we have two case if we want to initialize VDC ID or VDC name at run time
                # tenant_name provided but no tenant id
                if self.tenant_id is None and self.tenant_name is not None and 'vdcs' in org_details_dict:
                    vdcs_dict = org_details_dict['vdcs']
                    for vdc in vdcs_dict:
                        if vdcs_dict[vdc] == self.tenant_name:
                            self.tenant_id = vdc
                            self.logger.debug("Setting vdc uuid {} for organization UUID {}".format(self.tenant_id,
                                                                                                    self.org_name))
                            break
                    else:
                        raise vimconn.vimconnException("Tenant name indicated but not present in vcloud director.")
                    # case two we have tenant_id but we don't have tenant name so we find and set it.
                    if self.tenant_id is not None and self.tenant_name is None and 'vdcs' in org_details_dict:
                        vdcs_dict = org_details_dict['vdcs']
                        for vdc in vdcs_dict:
                            if vdc == self.tenant_id:
                                self.tenant_name = vdcs_dict[vdc]
                                self.logger.debug("Setting vdc uuid {} for organization UUID {}".format(self.tenant_id,
                                                                                                        self.org_name))
                                break
                        else:
                            raise vimconn.vimconnException("Tenant id indicated but not present in vcloud director")
            self.logger.debug("Setting organization uuid {}".format(self.org_uuid))
        except:
            self.logger.debug("Failed initialize organization UUID for org {}".format(self.org_name))
            self.logger.debug(traceback.format_exc())
            self.org_uuid = None

    def new_tenant(self, tenant_name=None, tenant_description=None):
        """ Method adds a new tenant to VIM with this name.
            This action requires access to create VDC action in vCloud director.

            Args:
                tenant_name is tenant_name to be created.
                tenant_description not used for this call

            Return:
                returns the tenant identifier in UUID format.
                If action is failed method will throw vimconn.vimconnException method
            """
        vdc_task = self.create_vdc(vdc_name=tenant_name)
        if vdc_task is not None:
            vdc_uuid, value = vdc_task.popitem()
            self.logger.info("Crated new vdc {} and uuid: {}".format(tenant_name, vdc_uuid))
            return vdc_uuid
        else:
            raise vimconn.vimconnException("Failed create tenant {}".format(tenant_name))

    def delete_tenant(self, tenant_id=None):
        """Delete a tenant from VIM"""
        'Returns the tenant identifier'
        raise vimconn.vimconnNotImplemented("Should have implemented this")

    def get_tenant_list(self, filter_dict={}):
        """Obtain tenants of VIM
        filter_dict can contain the following keys:
            name: filter by tenant name
            id: filter by tenant uuid/id
            <other VIM specific>
        Returns the tenant list of dictionaries:
            [{'name':'<name>, 'id':'<id>, ...}, ...]

        """
        org_dict = self.get_org(self.org_uuid)
        vdcs_dict = org_dict['vdcs']

        vdclist = []
        try:
            for k in vdcs_dict:
                entry = {'name': vdcs_dict[k], 'id': k}
                # if caller didn't specify dictionary we return all tenants.
                if filter_dict is not None and filter_dict:
                    filtered_entry = entry.copy()
                    filtered_dict = set(entry.keys()) - set(filter_dict)
                    for unwanted_key in filtered_dict: del entry[unwanted_key]
                    if filter_dict == entry:
                        vdclist.append(filtered_entry)
                else:
                    vdclist.append(entry)
        except:
            self.logger.debug("Error in get_tenant_list()")
            self.logger.debug(traceback.format_exc())
            raise vimconn.vimconnException("Incorrect state. {}")

        return vdclist

    def new_network(self, net_name, net_type, ip_profile=None, shared=False):
        """Adds a tenant network to VIM
            net_name is the name
            net_type can be 'bridge','data'.'ptp'.
            ip_profile is a dict containing the IP parameters of the network
            shared is a boolean
        Returns the network identifier"""

        self.logger.debug("new_network tenant {} net_type {} ip_profile {} shared {}"
                          .format(net_name, net_type, ip_profile, shared))

        isshared = 'false'
        if shared:
            isshared = 'true'

        network_uuid = self.create_network(network_name=net_name, net_type=net_type,
                                           ip_profile=ip_profile, isshared=isshared)
        if network_uuid is not None:
            return network_uuid
        else:
            raise vimconn.vimconnUnexpectedResponse("Failed create a new network {}".format(net_name))

    def get_vcd_network_list(self):
        """ Method available organization for a logged in tenant

            Returns:
                The return vca object that letter can be used to connect to vcloud direct as admin
        """

        self.logger.debug("get_vcd_network_list(): retrieving network list for vcd {}".format(self.tenant_name))
        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed.")

        if not self.tenant_name:
            raise vimconn.vimconnConnectionException("Tenant name is empty.")

        vdc = vca.get_vdc(self.tenant_name)
        if vdc is None:
            raise vimconn.vimconnConnectionException("Can't retrieve information for a VDC {}".format(self.tenant_name))

        vdc_uuid = vdc.get_id().split(":")[3]
        networks = vca.get_networks(vdc.get_name())
        network_list = []
        try:
            for network in networks:
                filter_dict = {}
                netid = network.get_id().split(":")
                if len(netid) != 4:
                    continue

                filter_dict["name"] = network.get_name()
                filter_dict["id"] = netid[3]
                filter_dict["shared"] = network.get_IsShared()
                filter_dict["tenant_id"] = vdc_uuid
                if network.get_status() == 1:
                    filter_dict["admin_state_up"] = True
                else:
                    filter_dict["admin_state_up"] = False
                filter_dict["status"] = "ACTIVE"
                filter_dict["type"] = "bridge"
                network_list.append(filter_dict)
                self.logger.debug("get_vcd_network_list adding entry {}".format(filter_dict))
        except:
            self.logger.debug("Error in get_vcd_network_list")
            self.logger.debug(traceback.format_exc())
            pass

        self.logger.debug("get_vcd_network_list returning {}".format(network_list))
        return network_list

    def get_network_list(self, filter_dict={}):
        """Obtain tenant networks of VIM
        Filter_dict can be:
            name: network name  OR/AND
            id: network uuid    OR/AND
            shared: boolean     OR/AND
            tenant_id: tenant   OR/AND
            admin_state_up: boolean
            status: 'ACTIVE'

        [{key : value , key : value}]

        Returns the network list of dictionaries:
            [{<the fields at Filter_dict plus some VIM specific>}, ...]
            List can be empty
        """

        self.logger.debug("get_vcd_network_list(): retrieving network list for vcd {}".format(self.tenant_name))
        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed.")

        if not self.tenant_name:
            raise vimconn.vimconnConnectionException("Tenant name is empty.")

        vdc = vca.get_vdc(self.tenant_name)
        if vdc is None:
            raise vimconn.vimconnConnectionException("Can't retrieve information for a VDC {}.".format(self.tenant_name))

        vdcid = vdc.get_id().split(":")[3]
        networks = vca.get_networks(vdc.get_name())
        network_list = []

        try:
            for network in networks:
                filter_entry = {}
                net_uuid = network.get_id().split(":")
                if len(net_uuid) != 4:
                    continue
                else:
                    net_uuid = net_uuid[3]
                # create dict entry
                self.logger.debug("Adding  {} to a list vcd id {} network {}".format(net_uuid,
                                                                                     vdcid,
                                                                                     network.get_name()))
                filter_entry["name"] = network.get_name()
                filter_entry["id"] = net_uuid
                filter_entry["shared"] = network.get_IsShared()
                filter_entry["tenant_id"] = vdcid
                if network.get_status() == 1:
                    filter_entry["admin_state_up"] = True
                else:
                    filter_entry["admin_state_up"] = False
                filter_entry["status"] = "ACTIVE"
                filter_entry["type"] = "bridge"
                filtered_entry = filter_entry.copy()

                if filter_dict is not None and filter_dict:
                    # we remove all the key : value we don't care and match only
                    # respected field
                    filtered_dict = set(filter_entry.keys()) - set(filter_dict)
                    for unwanted_key in filtered_dict: del filter_entry[unwanted_key]
                    if filter_dict == filter_entry:
                        network_list.append(filtered_entry)
                else:
                    network_list.append(filtered_entry)
        except:
            self.logger.debug("Error in get_vcd_network_list")
            self.logger.debug(traceback.format_exc())

        self.logger.debug("Returning {}".format(network_list))
        return network_list

    def get_network(self, net_id):
        """Method obtains network details of net_id VIM network
           Return a dict with  the fields at filter_dict (see get_network_list) plus some VIM specific>}, ...]"""

        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")

        vdc = vca.get_vdc(self.tenant_name)
        vdc_id = vdc.get_id().split(":")[3]

        networks = vca.get_networks(vdc.get_name())
        filter_dict = {}

        try:
            for network in networks:
                vdc_network_id = network.get_id().split(":")
                if len(vdc_network_id) == 4 and vdc_network_id[3] == net_id:
                    filter_dict["name"] = network.get_name()
                    filter_dict["id"] = vdc_network_id[3]
                    filter_dict["shared"] = network.get_IsShared()
                    filter_dict["tenant_id"] = vdc_id
                    if network.get_status() == 1:
                        filter_dict["admin_state_up"] = True
                    else:
                        filter_dict["admin_state_up"] = False
                    filter_dict["status"] = "ACTIVE"
                    filter_dict["type"] = "bridge"
                    self.logger.debug("Returning {}".format(filter_dict))
                    return filter_dict
        except:
            self.logger.debug("Error in get_network")
            self.logger.debug(traceback.format_exc())

        return filter_dict

    def delete_network(self, net_id):
        """
            Method Deletes a tenant network from VIM, provide the network id.

            Returns the network identifier or raise an exception
        """

        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() for tenant {} is failed.".format(self.tenant_name))

        vcd_network = self.get_vcd_network(network_uuid=net_id)
        if vcd_network is not None and vcd_network:
            if self.delete_network_action(network_uuid=net_id):
                return net_id
        else:
            raise vimconn.vimconnNotFoundException("Network {} not found".format(net_id))

    def refresh_nets_status(self, net_list):
        """Get the status of the networks
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

        """

        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")

        dict_entry = {}
        try:
            for net in net_list:
                errormsg = ''
                vcd_network = self.get_vcd_network(network_uuid=net)
                if vcd_network is not None and vcd_network:
                    if vcd_network['status'] == '1':
                        status = 'ACTIVE'
                    else:
                        status = 'DOWN'
                else:
                    status = 'DELETED'
                    errormsg = 'Network not found.'

                dict_entry[net] = {'status': status, 'error_msg': errormsg,
                                   'vim_info': yaml.safe_dump(vcd_network)}
        except:
            self.logger.debug("Error in refresh_nets_status")
            self.logger.debug(traceback.format_exc())

        return dict_entry

    def get_flavor(self, flavor_id):
        """Obtain flavor details from the  VIM
            Returns the flavor dict details {'id':<>, 'name':<>, other vim specific } #TODO to concrete
        """
        if flavor_id not in flavorlist:
            raise vimconn.vimconnNotFoundException("Flavor not found.")
        return flavorlist[flavor_id]

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

        # generate a new uuid put to internal dict and return it.
        self.logger.debug("Creating new flavor - flavor_data: {}".format(flavor_data))
        new_flavor=flavor_data
        ram = flavor_data.get(FLAVOR_RAM_KEY, 1024)
        cpu = flavor_data.get(FLAVOR_VCPUS_KEY, 1)
        disk = flavor_data.get(FLAVOR_DISK_KEY, 1)

        extended_flv = flavor_data.get("extended")
        if extended_flv:
            numas=extended_flv.get("numas")
            if numas:
                for numa in numas:
                    #overwrite ram and vcpus
                    ram = numa['memory']*1024
                    if 'paired-threads' in numa:
                        cpu = numa['paired-threads']*2
                    elif 'cores' in numa:
                        cpu = numa['cores']
                    elif 'threads' in numa:
                        cpu = numa['threads']

        new_flavor[FLAVOR_RAM_KEY] = ram
        new_flavor[FLAVOR_VCPUS_KEY] = cpu
        new_flavor[FLAVOR_DISK_KEY] = disk
        # generate a new uuid put to internal dict and return it.
        flavor_id = uuid.uuid4()
        flavorlist[str(flavor_id)] = new_flavor
        self.logger.debug("Created flavor - {} : {}".format(flavor_id, new_flavor))

        return str(flavor_id)

    def delete_flavor(self, flavor_id):
        """Deletes a tenant flavor from VIM identify by its id

           Returns the used id or raise an exception
        """
        if flavor_id not in flavorlist:
            raise vimconn.vimconnNotFoundException("Flavor not found.")

        flavorlist.pop(flavor_id, None)
        return flavor_id

    def new_image(self, image_dict):
        """
        Adds a tenant image to VIM
        Returns:
            200, image-id        if the image is created
            <0, message          if there is an error
        """

        return self.get_image_id_from_path(image_dict['location'])

    def delete_image(self, image_id):
        """

        :param image_id:
        :return:
        """

        raise vimconn.vimconnNotImplemented("Should have implemented this")

    def catalog_exists(self, catalog_name, catalogs):
        """

        :param catalog_name:
        :param catalogs:
        :return:
        """
        for catalog in catalogs:
            if catalog.name == catalog_name:
                return True
        return False

    def create_vimcatalog(self, vca=None, catalog_name=None):
        """ Create new catalog entry in vCloud director.

            Args
                vca:  vCloud director.
                catalog_name catalog that client wish to create.   Note no validation done for a name.
                Client must make sure that provide valid string representation.

             Return (bool) True if catalog created.

        """
        try:
            task = vca.create_catalog(catalog_name, catalog_name)
            result = vca.block_until_completed(task)
            if not result:
                return False
            catalogs = vca.get_catalogs()
        except:
            return False
        return self.catalog_exists(catalog_name, catalogs)

    # noinspection PyIncorrectDocstring
    def upload_ovf(self, vca=None, catalog_name=None, image_name=None, media_file_name=None,
                   description='', progress=False, chunk_bytes=128 * 1024):
        """
        Uploads a OVF file to a vCloud catalog

        :param chunk_bytes:
        :param progress:
        :param description:
        :param image_name:
        :param vca:
        :param catalog_name: (str): The name of the catalog to upload the media.
        :param media_file_name: (str): The name of the local media file to upload.
        :return: (bool) True if the media file was successfully uploaded, false otherwise.
        """
        os.path.isfile(media_file_name)
        statinfo = os.stat(media_file_name)

        #  find a catalog entry where we upload OVF.
        #  create vApp Template and check the status if vCD able to read OVF it will respond with appropirate
        #  status change.
        #  if VCD can parse OVF we upload VMDK file
        for catalog in vca.get_catalogs():
            if catalog_name != catalog.name:
                continue
            link = filter(lambda link: link.get_type() == "application/vnd.vmware.vcloud.media+xml" and
                                       link.get_rel() == 'add', catalog.get_Link())
            assert len(link) == 1
            data = """
            <UploadVAppTemplateParams name="%s" xmlns="http://www.vmware.com/vcloud/v1.5" xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1"><Description>%s vApp Template</Description></UploadVAppTemplateParams>
            """ % (escape(catalog_name), escape(description))
            headers = vca.vcloud_session.get_vcloud_headers()
            headers['Content-Type'] = 'application/vnd.vmware.vcloud.uploadVAppTemplateParams+xml'
            response = Http.post(link[0].get_href(), headers=headers, data=data, verify=vca.verify, logger=self.logger)
            if response.status_code == requests.codes.created:
                catalogItem = XmlElementTree.fromstring(response.content)
                entity = [child for child in catalogItem if
                          child.get("type") == "application/vnd.vmware.vcloud.vAppTemplate+xml"][0]
                href = entity.get('href')
                template = href
                response = Http.get(href, headers=vca.vcloud_session.get_vcloud_headers(),
                                    verify=vca.verify, logger=self.logger)

                if response.status_code == requests.codes.ok:
                    media = mediaType.parseString(response.content, True)
                    link = filter(lambda link: link.get_rel() == 'upload:default',
                                  media.get_Files().get_File()[0].get_Link())[0]
                    headers = vca.vcloud_session.get_vcloud_headers()
                    headers['Content-Type'] = 'Content-Type text/xml'
                    response = Http.put(link.get_href(),
                                        data=open(media_file_name, 'rb'),
                                        headers=headers,
                                        verify=vca.verify, logger=self.logger)
                    if response.status_code != requests.codes.ok:
                        self.logger.debug(
                            "Failed create vApp template for catalog name {} and image {}".format(catalog_name,
                                                                                                  media_file_name))
                        return False

                # TODO fix this with aync block
                time.sleep(5)

                self.logger.debug("vApp template for catalog name {} and image {}".format(catalog_name, media_file_name))

                # uploading VMDK file
                # check status of OVF upload and upload remaining files.
                response = Http.get(template,
                                    headers=vca.vcloud_session.get_vcloud_headers(),
                                    verify=vca.verify,
                                    logger=self.logger)

                if response.status_code == requests.codes.ok:
                    media = mediaType.parseString(response.content, True)
                    number_of_files = len(media.get_Files().get_File())
                    for index in xrange(0, number_of_files):
                        links_list = filter(lambda link: link.get_rel() == 'upload:default',
                                            media.get_Files().get_File()[index].get_Link())
                        for link in links_list:
                            # we skip ovf since it already uploaded.
                            if 'ovf' in link.get_href():
                                continue
                            # The OVF file and VMDK must be in a same directory
                            head, tail = os.path.split(media_file_name)
                            file_vmdk = head + '/' + link.get_href().split("/")[-1]
                            if not os.path.isfile(file_vmdk):
                                return False
                            statinfo = os.stat(file_vmdk)
                            if statinfo.st_size == 0:
                                return False
                            hrefvmdk = link.get_href()

                            if progress:
                                print("Uploading file: {}".format(file_vmdk))
                            if progress:
                                widgets = ['Uploading file: ', Percentage(), ' ', Bar(), ' ', ETA(), ' ',
                                           FileTransferSpeed()]
                                progress_bar = ProgressBar(widgets=widgets, maxval=statinfo.st_size).start()

                            bytes_transferred = 0
                            f = open(file_vmdk, 'rb')
                            while bytes_transferred < statinfo.st_size:
                                my_bytes = f.read(chunk_bytes)
                                if len(my_bytes) <= chunk_bytes:
                                    headers = vca.vcloud_session.get_vcloud_headers()
                                    headers['Content-Range'] = 'bytes %s-%s/%s' % (
                                        bytes_transferred, len(my_bytes) - 1, statinfo.st_size)
                                    headers['Content-Length'] = str(len(my_bytes))
                                    response = Http.put(hrefvmdk,
                                                        headers=headers,
                                                        data=my_bytes,
                                                        verify=vca.verify,
                                                        logger=None)

                                    if response.status_code == requests.codes.ok:
                                        bytes_transferred += len(my_bytes)
                                        if progress:
                                            progress_bar.update(bytes_transferred)
                                    else:
                                        self.logger.debug(
                                            'file upload failed with error: [%s] %s' % (response.status_code,
                                                                                        response.content))

                                        f.close()
                                        return False
                            f.close()
                            if progress:
                                progress_bar.finish()
                            time.sleep(10)
                    return True
                else:
                    self.logger.debug("Failed retrieve vApp template for catalog name {} for OVF {}".
                                      format(catalog_name, media_file_name))
                    return False

        self.logger.debug("Failed retrieve catalog name {} for OVF file {}".format(catalog_name, media_file_name))
        return False

    def upload_vimimage(self, vca=None, catalog_name=None, media_name=None, medial_file_name=None, progress=False):
        """Upload media file"""
        # TODO add named parameters for readability

        return self.upload_ovf(vca=vca, catalog_name=catalog_name, image_name=media_name.split(".")[0],
                               media_file_name=medial_file_name, description='medial_file_name', progress=progress)

    def validate_uuid4(self, uuid_string=None):
        """  Method validate correct format of UUID.

        Return: true if string represent valid uuid
        """
        try:
            val = uuid.UUID(uuid_string, version=4)
        except ValueError:
            return False
        return True

    def get_catalogid(self, catalog_name=None, catalogs=None):
        """  Method check catalog and return catalog ID in UUID format.

        Args
            catalog_name: catalog name as string
            catalogs:  list of catalogs.

        Return: catalogs uuid
        """

        for catalog in catalogs:
            if catalog.name == catalog_name:
                catalog_id = catalog.get_id().split(":")
                return catalog_id[3]
        return None

    def get_catalogbyid(self, catalog_uuid=None, catalogs=None):
        """  Method check catalog and return catalog name lookup done by catalog UUID.

        Args
            catalog_name: catalog name as string
            catalogs:  list of catalogs.

        Return: catalogs name or None
        """

        if not self.validate_uuid4(uuid_string=catalog_uuid):
            return None

        for catalog in catalogs:
            catalog_id = catalog.get_id().split(":")[3]
            if catalog_id == catalog_uuid:
                return catalog.name
        return None

    def get_image_id_from_path(self, path=None, progress=False):
        """  Method upload OVF image to vCloud director.

        Each OVF image represented as single catalog entry in vcloud director.
        The method check for existing catalog entry.  The check done by file name without file extension.

        if given catalog name already present method will respond with existing catalog uuid otherwise
        it will create new catalog entry and upload OVF file to newly created catalog.

        If method can't create catalog entry or upload a file it will throw exception.

        Method accept boolean flag progress that will output progress bar. It useful method
        for standalone upload use case. In case to test large file upload.

        Args
            path: - valid path to OVF file.
            progress - boolean progress bar show progress bar.

        Return: if image uploaded correct method will provide image catalog UUID.
        """
        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed.")

        if not path:
            raise vimconn.vimconnException("Image path can't be None.")

        if not os.path.isfile(path):
            raise vimconn.vimconnException("Can't read file. File not found.")

        if not os.access(path, os.R_OK):
            raise vimconn.vimconnException("Can't read file. Check file permission to read.")

        self.logger.debug("get_image_id_from_path() client requesting {} ".format(path))

        dirpath, filename = os.path.split(path)
        flname, file_extension = os.path.splitext(path)
        if file_extension != '.ovf':
            self.logger.debug("Wrong file extension {} connector support only OVF container.".format(file_extension))
            raise vimconn.vimconnException("Wrong container.  vCloud director supports only OVF.")

        catalog_name = os.path.splitext(filename)[0]
        catalog_md5_name = hashlib.md5(path).hexdigest()
        self.logger.debug("File name {} Catalog Name {} file path {} "
                          "vdc catalog name {}".format(filename, catalog_name, path, catalog_md5_name))

        catalogs = vca.get_catalogs()
        if len(catalogs) == 0:
            self.logger.info("Creating a new catalog entry {} in vcloud director".format(catalog_name))
            result = self.create_vimcatalog(vca, catalog_md5_name)
            if not result:
                raise vimconn.vimconnException("Failed create new catalog {} ".format(catalog_md5_name))
            result = self.upload_vimimage(vca=vca, catalog_name=catalog_md5_name,
                                          media_name=filename, medial_file_name=path, progress=progress)
            if not result:
                raise vimconn.vimconnException("Failed create vApp template for catalog {} ".format(catalog_name))
            return self.get_catalogid(catalog_name, vca.get_catalogs())
        else:
            for catalog in catalogs:
                # search for existing catalog if we find same name we return ID
                # TODO optimize this
                if catalog.name == catalog_md5_name:
                    self.logger.debug("Found existing catalog entry for {} "
                                      "catalog id {}".format(catalog_name,
                                                             self.get_catalogid(catalog_md5_name, catalogs)))
                    return self.get_catalogid(catalog_md5_name, vca.get_catalogs())

        # if we didn't find existing catalog we create a new one and upload image.
        self.logger.debug("Creating new catalog entry {} - {}".format(catalog_name, catalog_md5_name))
        result = self.create_vimcatalog(vca, catalog_md5_name)
        if not result:
            raise vimconn.vimconnException("Failed create new catalog {} ".format(catalog_md5_name))

        result = self.upload_vimimage(vca=vca, catalog_name=catalog_md5_name,
                                      media_name=filename, medial_file_name=path, progress=progress)
        if not result:
            raise vimconn.vimconnException("Failed create vApp template for catalog {} ".format(catalog_md5_name))

        return self.get_catalogid(catalog_md5_name, vca.get_catalogs())

    def get_image_list(self, filter_dict={}):
        '''Obtain tenant images from VIM
        Filter_dict can be:
            name: image name
            id: image uuid
            checksum: image checksum
            location: image path
        Returns the image list of dictionaries:
            [{<the fields at Filter_dict plus some VIM specific>}, ...]
            List can be empty
        '''
        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed.")
        try:
            image_list = []
            catalogs = vca.get_catalogs()
            if len(catalogs) == 0:
                return image_list
            else:
                for catalog in catalogs:
                    catalog_uuid = catalog.get_id().split(":")[3]
                    name = catalog.name
                    filtered_dict = {}

                    if ("name" not in filter_dict and "id" not in filter_dict) or \
                       (filter_dict.get('id') == catalog_uuid or filter_dict.get('name') == name):
                        filtered_dict ["name"] = name
                        filtered_dict ["id"] = catalog_uuid
                        image_list.append(filtered_dict)

                self.logger.debug("List of already created catalog items: {}".format(image_list))
                return image_list
        except Exception as exp:
            self.logger.error("Exception occured while retriving catalog items {}".format(exp))

    def get_vappid(self, vdc=None, vapp_name=None):
        """ Method takes vdc object and vApp name and returns vapp uuid or None

        Args:
            vdc: The VDC object.
            vapp_name: is application vappp name identifier

        Returns:
                The return vApp name otherwise None
        """
        if vdc is None or vapp_name is None:
            return None
        # UUID has following format https://host/api/vApp/vapp-30da58a3-e7c7-4d09-8f68-d4c8201169cf
        try:
            refs = filter(lambda ref: ref.name == vapp_name and ref.type_ == 'application/vnd.vmware.vcloud.vApp+xml',
                          vdc.ResourceEntities.ResourceEntity)
            if len(refs) == 1:
                return refs[0].href.split("vapp")[1][1:]
        except Exception as e:
            self.logger.exception(e)
            return False
        return None

    def check_vapp(self, vdc=None, vapp_uuid=None):
        """ Method Method returns True or False if vapp deployed in vCloud director

            Args:
                vca: Connector to VCA
                vdc: The VDC object.
                vappid: vappid is application identifier

            Returns:
                The return True if vApp deployed
                :param vdc:
                :param vapp_uuid:
        """
        try:
            refs = filter(lambda ref:
                          ref.type_ == 'application/vnd.vmware.vcloud.vApp+xml',
                          vdc.ResourceEntities.ResourceEntity)
            for ref in refs:
                vappid = ref.href.split("vapp")[1][1:]
                # find vapp with respected vapp uuid
                if vappid == vapp_uuid:
                    return True
        except Exception as e:
            self.logger.exception(e)
            return False
        return False

    def get_namebyvappid(self, vca=None, vdc=None, vapp_uuid=None):
        """Method returns vApp name from vCD and lookup done by vapp_id.

        Args:
            vca: Connector to VCA
            vdc: The VDC object.
            vapp_uuid: vappid is application identifier

        Returns:
            The return vApp name otherwise None
        """

        try:
            refs = filter(lambda ref: ref.type_ == 'application/vnd.vmware.vcloud.vApp+xml',
                          vdc.ResourceEntities.ResourceEntity)
            for ref in refs:
                # we care only about UUID the rest doesn't matter
                vappid = ref.href.split("vapp")[1][1:]
                if vappid == vapp_uuid:
                    response = Http.get(ref.href, headers=vca.vcloud_session.get_vcloud_headers(), verify=vca.verify,
                                        logger=self.logger)
                    tree = XmlElementTree.fromstring(response.content)
                    return tree.attrib['name']
        except Exception as e:
            self.logger.exception(e)
            return None
        return None

    def new_vminstance(self, name=None, description="", start=False, image_id=None, flavor_id=None, net_list={},
                       cloud_config=None, disk_list=None):
        """Adds a VM instance to VIM
        Params:
            start: indicates if VM must start or boot in pause mode. Ignored
            image_id,flavor_id: image and flavor uuid
            net_list: list of interfaces, each one is a dictionary with:
                name:
                net_id: network uuid to connect
                vpci: virtual vcpi to assign
                model: interface model, virtio, e2000, ...
                mac_address:
                use: 'data', 'bridge',  'mgmt'
                type: 'virtual', 'PF', 'VF', 'VFnotShared'
                vim_id: filled/added by this function
                cloud_config: can be a text script to be passed directly to cloud-init,
                    or an object to inject users and ssh keys with format:
                        key-pairs: [] list of keys to install to the default user
                        users: [{ name, key-pairs: []}] list of users to add with their key-pair
                #TODO ip, security groups
        Returns >=0, the instance identifier
                <0, error_text
        """

        self.logger.info("Creating new instance for entry {}".format(name))
        self.logger.debug("desc {} boot {} image_id: {} flavor_id: {} net_list: {} cloud_config {}".
                          format(description, start, image_id, flavor_id, net_list, cloud_config))
        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed.")

        #new vm name = vmname + tenant_id + uuid
        new_vm_name = [name, '-', str(uuid.uuid4())]
        vmname_andid = ''.join(new_vm_name)

        # if vm already deployed we return existing uuid
        # vapp_uuid = self.get_vappid(vca.get_vdc(self.tenant_name), name)
        # if vapp_uuid is not None:
        #     return vapp_uuid

        # we check for presence of VDC, Catalog entry and Flavor.
        vdc = vca.get_vdc(self.tenant_name)
        if vdc is None:
            raise vimconn.vimconnNotFoundException(
                "new_vminstance(): Failed create vApp {}: (Failed retrieve VDC information)".format(name))
        catalogs = vca.get_catalogs()
        if catalogs is None:
            raise vimconn.vimconnNotFoundException(
                "new_vminstance(): Failed create vApp {}: (Failed retrieve catalogs list)".format(name))

        catalog_hash_name = self.get_catalogbyid(catalog_uuid=image_id, catalogs=catalogs)
        if catalog_hash_name:
            self.logger.info("Found catalog entry {} for image id {}".format(catalog_hash_name, image_id))
        else:
            raise vimconn.vimconnNotFoundException("new_vminstance(): Failed create vApp {}: "
                                                   "(Failed retrieve catalog information {})".format(name, image_id))


        # Set vCPU and Memory based on flavor.
        #
        vm_cpus = None
        vm_memory = None
        vm_disk = None
        pci_devices_info = []
        if flavor_id is not None:
            if flavor_id not in flavorlist:
                raise vimconn.vimconnNotFoundException("new_vminstance(): Failed create vApp {}: "
                                                       "Failed retrieve flavor information "
                                                       "flavor id {}".format(name, flavor_id))
            else:
                try:
                    flavor = flavorlist[flavor_id]
                    vm_cpus = flavor[FLAVOR_VCPUS_KEY]
                    vm_memory = flavor[FLAVOR_RAM_KEY]
                    vm_disk = flavor[FLAVOR_DISK_KEY]
                    extended = flavor.get("extended", None)
                    if extended:
                        numas=extended.get("numas", None)
                        if numas:
                            for numa in numas:
                                for interface in numa.get("interfaces",() ):
                                    if interface["dedicated"].strip()=="yes":
                                        pci_devices_info.append(interface)
                except KeyError:
                    raise vimconn.vimconnException("Corrupted flavor. {}".format(flavor_id))

        # image upload creates template name as catalog name space Template.
        templateName = self.get_catalogbyid(catalog_uuid=image_id, catalogs=catalogs)
        power_on = 'false'
        if start:
            power_on = 'true'

        # client must provide at least one entry in net_list if not we report error
        #If net type is mgmt, then configure it as primary net & use its NIC index as primary NIC
        #If no mgmt, then the 1st NN in netlist is considered as primary net. 
        primary_net = None
        primary_netname = None
        network_mode = 'bridged'
        if net_list is not None and len(net_list) > 0:
            for net in net_list:
                if 'use' in net and net['use'] == 'mgmt':
                    primary_net = net
            if primary_net is None:
                primary_net = net_list[0]

            try:
                primary_net_id = primary_net['net_id']
                network_dict = self.get_vcd_network(network_uuid=primary_net_id)
                if 'name' in network_dict:
                    primary_netname = network_dict['name']

            except KeyError:
                raise vimconn.vimconnException("Corrupted flavor. {}".format(primary_net))
        else:
            raise vimconn.vimconnUnexpectedResponse("new_vminstance(): Failed network list is empty.".format(name))

        # use: 'data', 'bridge', 'mgmt'
        # create vApp.  Set vcpu and ram based on flavor id.
        vapptask = vca.create_vapp(self.tenant_name, vmname_andid, templateName,
                                   self.get_catalogbyid(image_id, catalogs),
                                   network_name=None,  # None while creating vapp
                                   network_mode=network_mode,
                                   vm_name=vmname_andid,
                                   vm_cpus=vm_cpus,  # can be None if flavor is None
                                   vm_memory=vm_memory)  # can be None if flavor is None

        if vapptask is None or vapptask is False:
            raise vimconn.vimconnUnexpectedResponse("new_vminstance(): failed deploy vApp {}".format(vmname_andid))
        if type(vapptask) is VappTask:
            vca.block_until_completed(vapptask)

        # we should have now vapp in undeployed state.
        vapp = vca.get_vapp(vca.get_vdc(self.tenant_name), vmname_andid)
        vapp_uuid = self.get_vappid(vca.get_vdc(self.tenant_name), vmname_andid)
        if vapp is None:
            raise vimconn.vimconnUnexpectedResponse(
                "new_vminstance(): Failed failed retrieve vApp {} after we deployed".format(
                                                                            vmname_andid))

        #Add PCI passthrough configrations
        PCI_devices_status = False
        vm_obj = None
        si = None
        if len(pci_devices_info) > 0:
            self.logger.info("Need to add PCI devices {} into VM {}".format(pci_devices_info,
                                                                        vmname_andid ))
            PCI_devices_status, vm_obj, vcenter_conect = self.add_pci_devices(vapp_uuid,
                                                                            pci_devices_info,
                                                                            vmname_andid)
            if PCI_devices_status:
                self.logger.info("Added PCI devives {} to VM {}".format(
                                                            pci_devices_info,
                                                            vmname_andid)
                                 )
            else:
                self.logger.info("Fail to add PCI devives {} to VM {}".format(
                                                            pci_devices_info,
                                                            vmname_andid)
                                 )
        # add vm disk
        if vm_disk:
            #Assuming there is only one disk in ovf and fast provisioning in organization vDC is disabled
            result = self.modify_vm_disk(vapp_uuid, vm_disk)
            if result :
                self.logger.debug("Modified Disk size of VM {} ".format(vmname_andid))

        # add NICs & connect to networks in netlist
        try:
            self.logger.info("Request to connect VM to a network: {}".format(net_list))
            nicIndex = 0
            primary_nic_index = 0
            for net in net_list:
                # openmano uses network id in UUID format.
                # vCloud Director need a name so we do reverse operation from provided UUID we lookup a name
                # [{'use': 'bridge', 'net_id': '527d4bf7-566a-41e7-a9e7-ca3cdd9cef4f', 'type': 'virtual',
                #   'vpci': '0000:00:11.0', 'name': 'eth0'}]

                if 'net_id' not in net:
                    continue

                interface_net_id = net['net_id']
                interface_net_name = self.get_network_name_by_id(network_uuid=interface_net_id)
                interface_network_mode = net['use']

                if interface_network_mode == 'mgmt':
                    primary_nic_index = nicIndex

                """- POOL (A static IP address is allocated automatically from a pool of addresses.)
                                  - DHCP (The IP address is obtained from a DHCP service.)
                                  - MANUAL (The IP address is assigned manually in the IpAddress element.)
                                  - NONE (No IP addressing mode specified.)"""

                if primary_netname is not None:
                    nets = filter(lambda n: n.name == interface_net_name, vca.get_networks(self.tenant_name))
                    if len(nets) == 1:
                        self.logger.info("new_vminstance(): Found requested network: {}".format(nets[0].name))
                        task = vapp.connect_to_network(nets[0].name, nets[0].href)
                        if type(task) is GenericTask:
                            vca.block_until_completed(task)
                        # connect network to VM - with all DHCP by default
                        self.logger.info("new_vminstance(): Connecting VM to a network {}".format(nets[0].name))
                        task = vapp.connect_vms(nets[0].name,
                                                connection_index=nicIndex,
                                                connections_primary_index=primary_nic_index,
                                                ip_allocation_mode='DHCP')
                        if type(task) is GenericTask:
                            vca.block_until_completed(task)
                nicIndex += 1
        except KeyError:
            # it might be a case if specific mandatory entry in dict is empty
            self.logger.debug("Key error {}".format(KeyError.message))
            raise vimconn.vimconnUnexpectedResponse("new_vminstance(): Failed create new vm instance {}".format(name))

        # deploy and power on vm
        self.logger.debug("new_vminstance(): Deploying vApp {} ".format(name))
        deploytask = vapp.deploy(powerOn=False)
        if type(deploytask) is GenericTask:
            vca.block_until_completed(deploytask)

        # If VM has PCI devices reserve memory for VM
        if PCI_devices_status and vm_obj and vcenter_conect:
            memReserve = vm_obj.config.hardware.memoryMB
            spec = vim.vm.ConfigSpec()
            spec.memoryAllocation = vim.ResourceAllocationInfo(reservation=memReserve)
            task = vm_obj.ReconfigVM_Task(spec=spec)
            if task:
                result = self.wait_for_vcenter_task(task, vcenter_conect)
                self.logger.info("Reserved memmoery {} MB for "\
                                 "VM VM status: {}".format(str(memReserve),result))
            else:
                self.logger.info("Fail to reserved memmoery {} to VM {}".format(
                                                            str(memReserve),str(vm_obj)))

        self.logger.debug("new_vminstance(): power on vApp {} ".format(name))
        poweron_task = vapp.poweron()
        if type(poweron_task) is GenericTask:
            vca.block_until_completed(poweron_task)

        # check if vApp deployed and if that the case return vApp UUID otherwise -1
        wait_time = 0
        vapp_uuid = None
        while wait_time <= MAX_WAIT_TIME:
            vapp = vca.get_vapp(vca.get_vdc(self.tenant_name), vmname_andid)
            if vapp and vapp.me.deployed:
                vapp_uuid = self.get_vappid(vca.get_vdc(self.tenant_name), vmname_andid)
                break
            else:
                self.logger.debug("new_vminstance(): Wait for vApp {} to deploy".format(name))
                time.sleep(INTERVAL_TIME)

            wait_time +=INTERVAL_TIME

        if vapp_uuid is not None:
            return vapp_uuid
        else:
            raise vimconn.vimconnUnexpectedResponse("new_vminstance(): Failed create new vm instance {}".format(name))

    ##
    ##
    ##  based on current discussion
    ##
    ##
    ##  server:
    #   created: '2016-09-08T11:51:58'
    #   description: simple-instance.linux1.1
    #   flavor: ddc6776e-75a9-11e6-ad5f-0800273e724c
    #   hostId: e836c036-74e7-11e6-b249-0800273e724c
    #   image: dde30fe6-75a9-11e6-ad5f-0800273e724c
    #   status: ACTIVE
    #   error_msg:
    #   interfaces: …
    #
    def get_vminstance(self, vim_vm_uuid=None):
        """Returns the VM instance information from VIM"""

        self.logger.debug("Client requesting vm instance {} ".format(vim_vm_uuid))
        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed.")

        vdc = vca.get_vdc(self.tenant_name)
        if vdc is None:
            raise vimconn.vimconnConnectionException(
                "Failed to get a reference of VDC for a tenant {}".format(self.tenant_name))

        vm_info_dict = self.get_vapp_details_rest(vapp_uuid=vim_vm_uuid)
        if not vm_info_dict:
            self.logger.debug("get_vminstance(): Failed to get vApp name by UUID {}".format(vim_vm_uuid))
            raise vimconn.vimconnNotFoundException("Failed to get vApp name by UUID {}".format(vim_vm_uuid))

        status_key = vm_info_dict['status']
        error = ''
        try:
            vm_dict = {'created': vm_info_dict['created'],
                       'description': vm_info_dict['name'],
                       'status': vcdStatusCode2manoFormat[int(status_key)],
                       'hostId': vm_info_dict['vmuuid'],
                       'error_msg': error,
                       'vim_info': yaml.safe_dump(vm_info_dict), 'interfaces': []}

            if 'interfaces' in vm_info_dict:
                vm_dict['interfaces'] = vm_info_dict['interfaces']
            else:
                vm_dict['interfaces'] = []
        except KeyError:
            vm_dict = {'created': '',
                       'description': '',
                       'status': vcdStatusCode2manoFormat[int(-1)],
                       'hostId': vm_info_dict['vmuuid'],
                       'error_msg': "Inconsistency state",
                       'vim_info': yaml.safe_dump(vm_info_dict), 'interfaces': []}

        return vm_dict

    def delete_vminstance(self, vm__vim_uuid):
        """Method poweroff and remove VM instance from vcloud director network.

        Args:
            vm__vim_uuid: VM UUID

        Returns:
            Returns the instance identifier
        """

        self.logger.debug("Client requesting delete vm instance {} ".format(vm__vim_uuid))
        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed.")

        vdc = vca.get_vdc(self.tenant_name)
        if vdc is None:
            self.logger.debug("delete_vminstance(): Failed to get a reference of VDC for a tenant {}".format(
                self.tenant_name))
            raise vimconn.vimconnException(
                "delete_vminstance(): Failed to get a reference of VDC for a tenant {}".format(self.tenant_name))

        try:
            vapp_name = self.get_namebyvappid(vca, vdc, vm__vim_uuid)
            if vapp_name is None:
                self.logger.debug("delete_vminstance(): Failed to get vm by given {} vm uuid".format(vm__vim_uuid))
                return -1, "delete_vminstance(): Failed to get vm by given {} vm uuid".format(vm__vim_uuid)
            else:
                self.logger.info("Deleting vApp {} and UUID {}".format(vapp_name, vm__vim_uuid))

            # Delete vApp and wait for status change if task executed and vApp is None.
            vapp = vca.get_vapp(vca.get_vdc(self.tenant_name), vapp_name)

            if vapp:
                if vapp.me.deployed:
                    self.logger.info("Powering off vApp {}".format(vapp_name))
                    #Power off vApp
                    powered_off = False
                    wait_time = 0
                    while wait_time <= MAX_WAIT_TIME:
                        vapp = vca.get_vapp(vca.get_vdc(self.tenant_name), vapp_name)
                        if not vapp:
                            self.logger.debug("delete_vminstance(): Failed to get vm by given {} vm uuid".format(vm__vim_uuid))
                            return -1, "delete_vminstance(): Failed to get vm by given {} vm uuid".format(vm__vim_uuid)

                        power_off_task = vapp.poweroff()
                        if type(power_off_task) is GenericTask:
                            result = vca.block_until_completed(power_off_task)
                            if result:
                                powered_off = True
                                break
                        else:
                            self.logger.info("Wait for vApp {} to power off".format(vapp_name))
                            time.sleep(INTERVAL_TIME)

                        wait_time +=INTERVAL_TIME
                    if not powered_off:
                        self.logger.debug("delete_vminstance(): Failed to power off VM instance {} ".format(vm__vim_uuid))
                    else:
                        self.logger.info("delete_vminstance(): Powered off VM instance {} ".format(vm__vim_uuid))

                    #Undeploy vApp
                    self.logger.info("Undeploy vApp {}".format(vapp_name))
                    wait_time = 0
                    undeployed = False
                    while wait_time <= MAX_WAIT_TIME:
                        vapp = vca.get_vapp(vca.get_vdc(self.tenant_name), vapp_name)
                        if not vapp:
                            self.logger.debug("delete_vminstance(): Failed to get vm by given {} vm uuid".format(vm__vim_uuid))
                            return -1, "delete_vminstance(): Failed to get vm by given {} vm uuid".format(vm__vim_uuid)
                        undeploy_task = vapp.undeploy(action='powerOff')

                        if type(undeploy_task) is GenericTask:
                            result = vca.block_until_completed(undeploy_task)
                            if result:
                                undeployed = True
                                break
                        else:
                            self.logger.debug("Wait for vApp {} to undeploy".format(vapp_name))
                            time.sleep(INTERVAL_TIME)

                        wait_time +=INTERVAL_TIME

                    if not undeployed:
                        self.logger.debug("delete_vminstance(): Failed to undeploy vApp {} ".format(vm__vim_uuid)) 

                # delete vapp
                self.logger.info("Start deletion of vApp {} ".format(vapp_name))
                vapp = vca.get_vapp(vca.get_vdc(self.tenant_name), vapp_name)

                if vapp is not None:
                    wait_time = 0
                    result = False

                    while wait_time <= MAX_WAIT_TIME:
                        vapp = vca.get_vapp(vca.get_vdc(self.tenant_name), vapp_name)
                        if not vapp:
                            self.logger.debug("delete_vminstance(): Failed to get vm by given {} vm uuid".format(vm__vim_uuid))
                            return -1, "delete_vminstance(): Failed to get vm by given {} vm uuid".format(vm__vim_uuid)

                        delete_task = vapp.delete()

                        if type(delete_task) is GenericTask:
                            vca.block_until_completed(delete_task)
                            result = vca.block_until_completed(delete_task)
                            if result:
                                break
                        else:
                            self.logger.debug("Wait for vApp {} to delete".format(vapp_name))
                            time.sleep(INTERVAL_TIME)

                        wait_time +=INTERVAL_TIME

                    if not result:
                        self.logger.debug("delete_vminstance(): Failed delete uuid {} ".format(vm__vim_uuid))

        except:
            self.logger.debug(traceback.format_exc())
            raise vimconn.vimconnException("delete_vminstance(): Failed delete vm instance {}".format(vm__vim_uuid))

        if vca.get_vapp(vca.get_vdc(self.tenant_name), vapp_name) is None:
            self.logger.info("Deleted vm instance {} sccessfully".format(vm__vim_uuid))
            return vm__vim_uuid
        else:
            raise vimconn.vimconnException("delete_vminstance(): Failed delete vm instance {}".format(vm__vim_uuid))

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
        """

        self.logger.debug("Client requesting refresh vm status for {} ".format(vm_list))
        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed.")

        vdc = vca.get_vdc(self.tenant_name)
        if vdc is None:
            raise vimconn.vimconnException("Failed to get a reference of VDC for a tenant {}".format(self.tenant_name))

        vms_dict = {}
        for vmuuid in vm_list:
            vmname = self.get_namebyvappid(vca, vdc, vmuuid)
            if vmname is not None:

                the_vapp = vca.get_vapp(vdc, vmname)
                vm_info = the_vapp.get_vms_details()
                vm_status = vm_info[0]['status']
                vm_pci_details = self.get_vm_pci_details(vmuuid)
                vm_info[0].update(vm_pci_details)

                vm_dict = {'status': vcdStatusCode2manoFormat[the_vapp.me.get_status()],
                           'error_msg': vcdStatusCode2manoFormat[the_vapp.me.get_status()],
                           'vim_info': yaml.safe_dump(vm_info), 'interfaces': []}

                # get networks
                try:
                    vm_app_networks = the_vapp.get_vms_network_info()
                    for vapp_network in vm_app_networks:
                        for vm_network in vapp_network:
                            if vm_network['name'] == vmname:
                                interface = {"mac_address": vm_network['mac'],
                                             "vim_net_id": self.get_network_id_by_name(vm_network['network_name']),
                                             "vim_interface_id": self.get_network_id_by_name(vm_network['network_name']),
                                             'ip_address': vm_network['ip']}
                                # interface['vim_info'] = yaml.safe_dump(vm_network)
                                vm_dict["interfaces"].append(interface)
                    # add a vm to vm dict
                    vms_dict.setdefault(vmuuid, vm_dict)
                except KeyError:
                    self.logger.debug("Error in respond {}".format(KeyError.message))
                    self.logger.debug(traceback.format_exc())

        return vms_dict

    def action_vminstance(self, vm__vim_uuid=None, action_dict=None):
        """Send and action over a VM instance from VIM
        Returns the vm_id if the action was successfully sent to the VIM"""

        self.logger.debug("Received action for vm {} and action dict {}".format(vm__vim_uuid, action_dict))
        if vm__vim_uuid is None or action_dict is None:
            raise vimconn.vimconnException("Invalid request. VM id or action is None.")

        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed.")

        vdc = vca.get_vdc(self.tenant_name)
        if vdc is None:
            return -1, "Failed to get a reference of VDC for a tenant {}".format(self.tenant_name)

        vapp_name = self.get_namebyvappid(vca, vdc, vm__vim_uuid)
        if vapp_name is None:
            self.logger.debug("action_vminstance(): Failed to get vm by given {} vm uuid".format(vm__vim_uuid))
            raise vimconn.vimconnException("Failed to get vm by given {} vm uuid".format(vm__vim_uuid))
        else:
            self.logger.info("Action_vminstance vApp {} and UUID {}".format(vapp_name, vm__vim_uuid))

        try:
            the_vapp = vca.get_vapp(vdc, vapp_name)
            # TODO fix all status
            if "start" in action_dict:
                if action_dict["start"] == "rebuild":
                    the_vapp.deploy(powerOn=True)
                else:
                    vm_info = the_vapp.get_vms_details()
                    vm_status = vm_info[0]['status']
                    if vm_status == "Suspended":
                        the_vapp.poweron()
                    elif vm_status.status == "Powered off":
                        the_vapp.poweron()
            elif "pause" in action_dict:
                pass
                ## server.pause()
            elif "resume" in action_dict:
                pass
                ## server.resume()
            elif "shutoff" in action_dict or "shutdown" in action_dict:
                the_vapp.shutdown()
            elif "forceOff" in action_dict:
                the_vapp.reset()
            elif "terminate" in action_dict:
                the_vapp.delete()
            # elif "createImage" in action_dict:
            #     server.create_image()
            else:
                pass
        except:
            pass

    def get_vminstance_console(self, vm_id, console_type="vnc"):
        """
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
        """
        raise vimconn.vimconnNotImplemented("Should have implemented this")

    # NOT USED METHODS in current version

    def host_vim2gui(self, host, server_dict):
        """Transform host dictionary from VIM format to GUI format,
        and append to the server_dict
        """
        raise vimconn.vimconnNotImplemented("Should have implemented this")

    def get_hosts_info(self):
        """Get the information of deployed hosts
        Returns the hosts content"""
        raise vimconn.vimconnNotImplemented("Should have implemented this")

    def get_hosts(self, vim_tenant):
        """Get the hosts and deployed instances
        Returns the hosts content"""
        raise vimconn.vimconnNotImplemented("Should have implemented this")

    def get_processor_rankings(self):
        """Get the processor rankings in the VIM database"""
        raise vimconn.vimconnNotImplemented("Should have implemented this")

    def new_host(self, host_data):
        """Adds a new host to VIM"""
        '''Returns status code of the VIM response'''
        raise vimconn.vimconnNotImplemented("Should have implemented this")

    def new_external_port(self, port_data):
        """Adds a external port to VIM"""
        '''Returns the port identifier'''
        raise vimconn.vimconnNotImplemented("Should have implemented this")

    def new_external_network(self, net_name, net_type):
        """Adds a external network to VIM (shared)"""
        '''Returns the network identifier'''
        raise vimconn.vimconnNotImplemented("Should have implemented this")

    def connect_port_network(self, port_id, network_id, admin=False):
        """Connects a external port to a network"""
        '''Returns status code of the VIM response'''
        raise vimconn.vimconnNotImplemented("Should have implemented this")

    def new_vminstancefromJSON(self, vm_data):
        """Adds a VM instance to VIM"""
        '''Returns the instance identifier'''
        raise vimconn.vimconnNotImplemented("Should have implemented this")

    def get_network_name_by_id(self, network_uuid=None):
        """Method gets vcloud director network named based on supplied uuid.

        Args:
            network_uuid: network_id

        Returns:
            The return network name.
        """

        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed.")

        if not network_uuid:
            return None

        try:
            org_dict = self.get_org(self.org_uuid)
            if 'networks' in org_dict:
                org_network_dict = org_dict['networks']
                for net_uuid in org_network_dict:
                    if net_uuid == network_uuid:
                        return org_network_dict[net_uuid]
        except:
            self.logger.debug("Exception in get_network_name_by_id")
            self.logger.debug(traceback.format_exc())

        return None

    def get_network_id_by_name(self, network_name=None):
        """Method gets vcloud director network uuid based on supplied name.

        Args:
            network_name: network_name
        Returns:
            The return network uuid.
            network_uuid: network_id
        """

        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed.")

        if not network_name:
            self.logger.debug("get_network_id_by_name() : Network name is empty")
            return None

        try:
            org_dict = self.get_org(self.org_uuid)
            if org_dict and 'networks' in org_dict:
                org_network_dict = org_dict['networks']
                for net_uuid,net_name in org_network_dict.iteritems():
                    if net_name == network_name:
                        return net_uuid

        except KeyError as exp:
            self.logger.debug("get_network_id_by_name() : KeyError- {} ".format(exp))

        return None

    def list_org_action(self):
        """
        Method leverages vCloud director and query for available organization for particular user

        Args:
            vca - is active VCA connection.
            vdc_name - is a vdc name that will be used to query vms action

            Returns:
                The return XML respond
        """

        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")

        url_list = [vca.host, '/api/org']
        vm_list_rest_call = ''.join(url_list)

        if not (not vca.vcloud_session or not vca.vcloud_session.organization):
            response = Http.get(url=vm_list_rest_call,
                                headers=vca.vcloud_session.get_vcloud_headers(),
                                verify=vca.verify,
                                logger=vca.logger)
            if response.status_code == requests.codes.ok:
                return response.content

        return None

    def get_org_action(self, org_uuid=None):
        """
        Method leverages vCloud director and retrieve available object fdr organization.

        Args:
            vca - is active VCA connection.
            vdc_name - is a vdc name that will be used to query vms action

            Returns:
                The return XML respond
        """

        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")

        if org_uuid is None:
            return None

        url_list = [vca.host, '/api/org/', org_uuid]
        vm_list_rest_call = ''.join(url_list)

        if not (not vca.vcloud_session or not vca.vcloud_session.organization):
            response = Http.get(url=vm_list_rest_call,
                                headers=vca.vcloud_session.get_vcloud_headers(),
                                verify=vca.verify,
                                logger=vca.logger)
            if response.status_code == requests.codes.ok:
                return response.content

        return None

    def get_org(self, org_uuid=None):
        """
        Method retrieves available organization in vCloud Director

        Args:
            org_uuid - is a organization uuid.

            Returns:
                The return dictionary with following key
                    "network" - for network list under the org
                    "catalogs" - for network list under the org
                    "vdcs" - for vdc list under org
        """

        org_dict = {}
        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")

        if org_uuid is None:
            return org_dict

        content = self.get_org_action(org_uuid=org_uuid)
        try:
            vdc_list = {}
            network_list = {}
            catalog_list = {}
            vm_list_xmlroot = XmlElementTree.fromstring(content)
            for child in vm_list_xmlroot:
                if child.attrib['type'] == 'application/vnd.vmware.vcloud.vdc+xml':
                    vdc_list[child.attrib['href'].split("/")[-1:][0]] = child.attrib['name']
                    org_dict['vdcs'] = vdc_list
                if child.attrib['type'] == 'application/vnd.vmware.vcloud.orgNetwork+xml':
                    network_list[child.attrib['href'].split("/")[-1:][0]] = child.attrib['name']
                    org_dict['networks'] = network_list
                if child.attrib['type'] == 'application/vnd.vmware.vcloud.catalog+xml':
                    catalog_list[child.attrib['href'].split("/")[-1:][0]] = child.attrib['name']
                    org_dict['catalogs'] = catalog_list
        except:
            pass

        return org_dict

    def get_org_list(self):
        """
        Method retrieves available organization in vCloud Director

        Args:
            vca - is active VCA connection.

            Returns:
                The return dictionary and key for each entry VDC UUID
        """

        org_dict = {}
        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")

        content = self.list_org_action()
        try:
            vm_list_xmlroot = XmlElementTree.fromstring(content)
            for vm_xml in vm_list_xmlroot:
                if vm_xml.tag.split("}")[1] == 'Org':
                    org_uuid = vm_xml.attrib['href'].split('/')[-1:]
                    org_dict[org_uuid[0]] = vm_xml.attrib['name']
        except:
            pass

        return org_dict

    def vms_view_action(self, vdc_name=None):
        """ Method leverages vCloud director vms query call

        Args:
            vca - is active VCA connection.
            vdc_name - is a vdc name that will be used to query vms action

            Returns:
                The return XML respond
        """
        vca = self.connect()
        if vdc_name is None:
            return None

        url_list = [vca.host, '/api/vms/query']
        vm_list_rest_call = ''.join(url_list)

        if not (not vca.vcloud_session or not vca.vcloud_session.organization):
            refs = filter(lambda ref: ref.name == vdc_name and ref.type_ == 'application/vnd.vmware.vcloud.vdc+xml',
                          vca.vcloud_session.organization.Link)
            if len(refs) == 1:
                response = Http.get(url=vm_list_rest_call,
                                    headers=vca.vcloud_session.get_vcloud_headers(),
                                    verify=vca.verify,
                                    logger=vca.logger)
                if response.status_code == requests.codes.ok:
                    return response.content

        return None

    def get_vapp_list(self, vdc_name=None):
        """
        Method retrieves vApp list deployed vCloud director and returns a dictionary
        contains a list of all vapp deployed for queried VDC.
        The key for a dictionary is vApp UUID


        Args:
            vca - is active VCA connection.
            vdc_name - is a vdc name that will be used to query vms action

            Returns:
                The return dictionary and key for each entry vapp UUID
        """

        vapp_dict = {}
        if vdc_name is None:
            return vapp_dict

        content = self.vms_view_action(vdc_name=vdc_name)
        try:
            vm_list_xmlroot = XmlElementTree.fromstring(content)
            for vm_xml in vm_list_xmlroot:
                if vm_xml.tag.split("}")[1] == 'VMRecord':
                    if vm_xml.attrib['isVAppTemplate'] == 'true':
                        rawuuid = vm_xml.attrib['container'].split('/')[-1:]
                        if 'vappTemplate-' in rawuuid[0]:
                            # vm in format vappTemplate-e63d40e7-4ff5-4c6d-851f-96c1e4da86a5 we remove
                            # vm and use raw UUID as key
                            vapp_dict[rawuuid[0][13:]] = vm_xml.attrib
        except:
            pass

        return vapp_dict

    def get_vm_list(self, vdc_name=None):
        """
        Method retrieves VM's list deployed vCloud director. It returns a dictionary
        contains a list of all VM's deployed for queried VDC.
        The key for a dictionary is VM UUID


        Args:
            vca - is active VCA connection.
            vdc_name - is a vdc name that will be used to query vms action

            Returns:
                The return dictionary and key for each entry vapp UUID
        """
        vm_dict = {}

        if vdc_name is None:
            return vm_dict

        content = self.vms_view_action(vdc_name=vdc_name)
        try:
            vm_list_xmlroot = XmlElementTree.fromstring(content)
            for vm_xml in vm_list_xmlroot:
                if vm_xml.tag.split("}")[1] == 'VMRecord':
                    if vm_xml.attrib['isVAppTemplate'] == 'false':
                        rawuuid = vm_xml.attrib['href'].split('/')[-1:]
                        if 'vm-' in rawuuid[0]:
                            # vm in format vm-e63d40e7-4ff5-4c6d-851f-96c1e4da86a5 we remove
                            #  vm and use raw UUID as key
                            vm_dict[rawuuid[0][3:]] = vm_xml.attrib
        except:
            pass

        return vm_dict

    def get_vapp(self, vdc_name=None, vapp_name=None, isuuid=False):
        """
        Method retrieves VM deployed vCloud director. It returns VM attribute as dictionary
        contains a list of all VM's deployed for queried VDC.
        The key for a dictionary is VM UUID


        Args:
            vca - is active VCA connection.
            vdc_name - is a vdc name that will be used to query vms action

            Returns:
                The return dictionary and key for each entry vapp UUID
        """
        vm_dict = {}
        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")

        if vdc_name is None:
            return vm_dict

        content = self.vms_view_action(vdc_name=vdc_name)
        try:
            vm_list_xmlroot = XmlElementTree.fromstring(content)
            for vm_xml in vm_list_xmlroot:
                if vm_xml.tag.split("}")[1] == 'VMRecord' and vm_xml.attrib['isVAppTemplate'] == 'false':
                    # lookup done by UUID
                    if isuuid:
                        if vapp_name in vm_xml.attrib['container']:
                            rawuuid = vm_xml.attrib['href'].split('/')[-1:]
                            if 'vm-' in rawuuid[0]:
                                vm_dict[rawuuid[0][3:]] = vm_xml.attrib
                                break
                    # lookup done by Name
                    else:
                        if vapp_name in vm_xml.attrib['name']:
                            rawuuid = vm_xml.attrib['href'].split('/')[-1:]
                            if 'vm-' in rawuuid[0]:
                                vm_dict[rawuuid[0][3:]] = vm_xml.attrib
                                break
        except:
            pass

        return vm_dict

    def get_network_action(self, network_uuid=None):
        """
        Method leverages vCloud director and query network based on network uuid

        Args:
            vca - is active VCA connection.
            network_uuid - is a network uuid

            Returns:
                The return XML respond
        """

        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")

        if network_uuid is None:
            return None

        url_list = [vca.host, '/api/network/', network_uuid]
        vm_list_rest_call = ''.join(url_list)

        if not (not vca.vcloud_session or not vca.vcloud_session.organization):
            response = Http.get(url=vm_list_rest_call,
                                headers=vca.vcloud_session.get_vcloud_headers(),
                                verify=vca.verify,
                                logger=vca.logger)
            if response.status_code == requests.codes.ok:
                return response.content

        return None

    def get_vcd_network(self, network_uuid=None):
        """
        Method retrieves available network from vCloud Director

        Args:
            network_uuid - is VCD network UUID

        Each element serialized as key : value pair

        Following keys available for access.    network_configuration['Gateway'}
        <Configuration>
          <IpScopes>
            <IpScope>
                <IsInherited>true</IsInherited>
                <Gateway>172.16.252.100</Gateway>
                <Netmask>255.255.255.0</Netmask>
                <Dns1>172.16.254.201</Dns1>
                <Dns2>172.16.254.202</Dns2>
                <DnsSuffix>vmwarelab.edu</DnsSuffix>
                <IsEnabled>true</IsEnabled>
                <IpRanges>
                    <IpRange>
                        <StartAddress>172.16.252.1</StartAddress>
                        <EndAddress>172.16.252.99</EndAddress>
                    </IpRange>
                </IpRanges>
            </IpScope>
        </IpScopes>
        <FenceMode>bridged</FenceMode>

        Returns:
                The return dictionary and key for each entry vapp UUID
        """

        network_configuration = {}
        if network_uuid is None:
            return network_uuid

        content = self.get_network_action(network_uuid=network_uuid)
        try:
            vm_list_xmlroot = XmlElementTree.fromstring(content)

            network_configuration['status'] = vm_list_xmlroot.get("status")
            network_configuration['name'] = vm_list_xmlroot.get("name")
            network_configuration['uuid'] = vm_list_xmlroot.get("id").split(":")[3]

            for child in vm_list_xmlroot:
                if child.tag.split("}")[1] == 'IsShared':
                    network_configuration['isShared'] = child.text.strip()
                if child.tag.split("}")[1] == 'Configuration':
                    for configuration in child.iter():
                        tagKey = configuration.tag.split("}")[1].strip()
                        if tagKey != "":
                            network_configuration[tagKey] = configuration.text.strip()
            return network_configuration
        except:
            pass

        return network_configuration

    def delete_network_action(self, network_uuid=None):
        """
        Method delete given network from vCloud director

        Args:
            network_uuid - is a network uuid that client wish to delete

            Returns:
                The return None or XML respond or false
        """

        vca = self.connect_as_admin()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")
        if network_uuid is None:
            return False

        url_list = [vca.host, '/api/admin/network/', network_uuid]
        vm_list_rest_call = ''.join(url_list)

        if not (not vca.vcloud_session or not vca.vcloud_session.organization):
            response = Http.delete(url=vm_list_rest_call,
                                   headers=vca.vcloud_session.get_vcloud_headers(),
                                   verify=vca.verify,
                                   logger=vca.logger)

            if response.status_code == 202:
                return True

        return False

    def create_network(self, network_name=None, net_type='bridge', parent_network_uuid=None,
                       ip_profile=None, isshared='true'):
        """
        Method create network in vCloud director

        Args:
            network_name - is network name to be created.
            net_type - can be 'bridge','data','ptp','mgmt'.
            ip_profile is a dict containing the IP parameters of the network
            isshared - is a boolean
            parent_network_uuid - is parent provider vdc network that will be used for mapping.
            It optional attribute. by default if no parent network indicate the first available will be used.

            Returns:
                The return network uuid or return None
        """

        new_network_name = [network_name, '-', str(uuid.uuid4())]
        content = self.create_network_rest(network_name=''.join(new_network_name),
                                           ip_profile=ip_profile,
                                           net_type=net_type,
                                           parent_network_uuid=parent_network_uuid,
                                           isshared=isshared)
        if content is None:
            self.logger.debug("Failed create network {}.".format(network_name))
            return None

        try:
            vm_list_xmlroot = XmlElementTree.fromstring(content)
            vcd_uuid = vm_list_xmlroot.get('id').split(":")
            if len(vcd_uuid) == 4:
                self.logger.info("Create new network name: {} uuid: {}".format(network_name, vcd_uuid[3]))
                return vcd_uuid[3]
        except:
            self.logger.debug("Failed create network {}".format(network_name))
            return None

    def create_network_rest(self, network_name=None, net_type='bridge', parent_network_uuid=None,
                            ip_profile=None, isshared='true'):
        """
        Method create network in vCloud director

        Args:
            network_name - is network name to be created.
            net_type - can be 'bridge','data','ptp','mgmt'.
            ip_profile is a dict containing the IP parameters of the network
            isshared - is a boolean
            parent_network_uuid - is parent provider vdc network that will be used for mapping.
            It optional attribute. by default if no parent network indicate the first available will be used.

            Returns:
                The return network uuid or return None
        """

        vca = self.connect_as_admin()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed.")
        if network_name is None:
            return None

        url_list = [vca.host, '/api/admin/vdc/', self.tenant_id]
        vm_list_rest_call = ''.join(url_list)
        if not (not vca.vcloud_session or not vca.vcloud_session.organization):
            response = Http.get(url=vm_list_rest_call,
                                headers=vca.vcloud_session.get_vcloud_headers(),
                                verify=vca.verify,
                                logger=vca.logger)

            provider_network = None
            available_networks = None
            add_vdc_rest_url = None

            if response.status_code != requests.codes.ok:
                self.logger.debug("REST API call {} failed. Return status code {}".format(vm_list_rest_call,
                                                                                          response.status_code))
                return None
            else:
                try:
                    vm_list_xmlroot = XmlElementTree.fromstring(response.content)
                    for child in vm_list_xmlroot:
                        if child.tag.split("}")[1] == 'ProviderVdcReference':
                            provider_network = child.attrib.get('href')
                            # application/vnd.vmware.admin.providervdc+xml
                        if child.tag.split("}")[1] == 'Link':
                            if child.attrib.get('type') == 'application/vnd.vmware.vcloud.orgVdcNetwork+xml' \
                                    and child.attrib.get('rel') == 'add':
                                add_vdc_rest_url = child.attrib.get('href')
                except:
                    self.logger.debug("Failed parse respond for rest api call {}".format(vm_list_rest_call))
                    self.logger.debug("Respond body {}".format(response.content))
                    return None

            # find  pvdc provided available network
            response = Http.get(url=provider_network,
                                headers=vca.vcloud_session.get_vcloud_headers(),
                                verify=vca.verify,
                                logger=vca.logger)
            if response.status_code != requests.codes.ok:
                self.logger.debug("REST API call {} failed. Return status code {}".format(vm_list_rest_call,
                                                                                          response.status_code))
                return None

            # available_networks.split("/")[-1]

            if parent_network_uuid is None:
                try:
                    vm_list_xmlroot = XmlElementTree.fromstring(response.content)
                    for child in vm_list_xmlroot.iter():
                        if child.tag.split("}")[1] == 'AvailableNetworks':
                            for networks in child.iter():
                                # application/vnd.vmware.admin.network+xml
                                if networks.attrib.get('href') is not None:
                                    available_networks = networks.attrib.get('href')
                                    break
                except:
                    return None

            #Configure IP profile of the network
            ip_profile = ip_profile if ip_profile is not None else DEFAULT_IP_PROFILE

            gateway_address=ip_profile['gateway_address']
            dhcp_count=int(ip_profile['dhcp_count'])
            subnet_address=self.convert_cidr_to_netmask(ip_profile['subnet_address'])

            if ip_profile['dhcp_enabled']==True:
                dhcp_enabled='true'
            else:
                dhcp_enabled='false'
            dhcp_start_address=ip_profile['dhcp_start_address']

            #derive dhcp_end_address from dhcp_start_address & dhcp_count
            end_ip_int = int(netaddr.IPAddress(dhcp_start_address))
            end_ip_int += dhcp_count - 1
            dhcp_end_address = str(netaddr.IPAddress(end_ip_int))

            ip_version=ip_profile['ip_version']
            dns_address=ip_profile['dns_address']

            # either use client provided UUID or search for a first available
            #  if both are not defined we return none
            if parent_network_uuid is not None:
                url_list = [vca.host, '/api/admin/network/', parent_network_uuid]
                add_vdc_rest_url = ''.join(url_list)

            if net_type=='ptp':
                fence_mode="isolated"
                isshared='false'
                is_inherited='false'
                data = """ <OrgVdcNetwork name="{0:s}" xmlns="http://www.vmware.com/vcloud/v1.5">
                                <Description>Openmano created</Description>
                                        <Configuration>
                                            <IpScopes>
                                                <IpScope>
                                                    <IsInherited>{1:s}</IsInherited>
                                                    <Gateway>{2:s}</Gateway>
                                                    <Netmask>{3:s}</Netmask>
                                                    <Dns1>{4:s}</Dns1>
                                                    <IsEnabled>{5:s}</IsEnabled>
                                                    <IpRanges>
                                                        <IpRange>
                                                            <StartAddress>{6:s}</StartAddress>
                                                            <EndAddress>{7:s}</EndAddress>
                                                        </IpRange>
                                                    </IpRanges>
                                                </IpScope>
                                            </IpScopes>
                                            <FenceMode>{8:s}</FenceMode>
                                        </Configuration>
                                        <IsShared>{9:s}</IsShared>
                            </OrgVdcNetwork> """.format(escape(network_name), is_inherited, gateway_address,
                                                        subnet_address, dns_address, dhcp_enabled,
                                                        dhcp_start_address, dhcp_end_address, fence_mode, isshared)

            else:
                fence_mode="bridged"
                is_inherited='false'
                data = """ <OrgVdcNetwork name="{0:s}" xmlns="http://www.vmware.com/vcloud/v1.5">
                                <Description>Openmano created</Description>
                                        <Configuration>
                                            <IpScopes>
                                                <IpScope>
                                                    <IsInherited>{1:s}</IsInherited>
                                                    <Gateway>{2:s}</Gateway>
                                                    <Netmask>{3:s}</Netmask>
                                                    <Dns1>{4:s}</Dns1>
                                                    <IsEnabled>{5:s}</IsEnabled>
                                                    <IpRanges>
                                                        <IpRange>
                                                            <StartAddress>{6:s}</StartAddress>
                                                            <EndAddress>{7:s}</EndAddress>
                                                        </IpRange>
                                                    </IpRanges>
                                                </IpScope>
                                            </IpScopes>
                                            <ParentNetwork href="{8:s}"/>
                                            <FenceMode>{9:s}</FenceMode>
                                        </Configuration>
                                        <IsShared>{10:s}</IsShared>
                            </OrgVdcNetwork> """.format(escape(network_name), is_inherited, gateway_address,
                                                        subnet_address, dns_address, dhcp_enabled,
                                                        dhcp_start_address, dhcp_end_address, available_networks,
                                                        fence_mode, isshared)

            headers = vca.vcloud_session.get_vcloud_headers()
            headers['Content-Type'] = 'application/vnd.vmware.vcloud.orgVdcNetwork+xml'
            try:
                response = Http.post(url=add_vdc_rest_url,
                                     headers=headers,
                                     data=data,
                                     verify=vca.verify,
                                     logger=vca.logger)

                if response.status_code != 201:
                    self.logger.debug("Create Network POST REST API call failed. Return status code {}"
                                      .format(response.status_code))
                else:
                    network = networkType.parseString(response.content, True)
                    create_nw_task = network.get_Tasks().get_Task()[0]

                    # if we all ok we respond with content after network creation completes
                    # otherwise by default return None
                    if create_nw_task is not None:
                        self.logger.debug("Create Network REST : Waiting for Nw creation complete")
                        status = vca.block_until_completed(create_nw_task)
                        if status:
                            return response.content
                        else:
                            self.logger.debug("create_network_rest task failed. Network Create response : {}"
                                              .format(response.content))
            except Exception as exp:
                self.logger.debug("create_network_rest : Exception : {} ".format(exp))

        return None

    def convert_cidr_to_netmask(self, cidr_ip=None):
        """
        Method sets convert CIDR netmask address to normal IP format
        Args:
            cidr_ip : CIDR IP address
            Returns:
                netmask : Converted netmask
        """
        if cidr_ip is not None:
            if '/' in cidr_ip:
                network, net_bits = cidr_ip.split('/')
                netmask = socket.inet_ntoa(struct.pack(">I", (0xffffffff << (32 - int(net_bits))) & 0xffffffff))
            else:
                netmask = cidr_ip
            return netmask
        return None

    def get_provider_rest(self, vca=None):
        """
        Method gets provider vdc view from vcloud director

        Args:
            network_name - is network name to be created.
            parent_network_uuid - is parent provider vdc network that will be used for mapping.
            It optional attribute. by default if no parent network indicate the first available will be used.

            Returns:
                The return xml content of respond or None
        """

        url_list = [vca.host, '/api/admin']
        response = Http.get(url=''.join(url_list),
                            headers=vca.vcloud_session.get_vcloud_headers(),
                            verify=vca.verify,
                            logger=vca.logger)

        if response.status_code == requests.codes.ok:
            return response.content
        return None

    def create_vdc(self, vdc_name=None):

        vdc_dict = {}

        xml_content = self.create_vdc_from_tmpl_rest(vdc_name=vdc_name)
        if xml_content is not None:
            try:
                task_resp_xmlroot = XmlElementTree.fromstring(xml_content)
                for child in task_resp_xmlroot:
                    if child.tag.split("}")[1] == 'Owner':
                        vdc_id = child.attrib.get('href').split("/")[-1]
                        vdc_dict[vdc_id] = task_resp_xmlroot.get('href')
                        return vdc_dict
            except:
                self.logger.debug("Respond body {}".format(xml_content))

        return None

    def create_vdc_from_tmpl_rest(self, vdc_name=None):
        """
        Method create vdc in vCloud director based on VDC template.
        it uses pre-defined template that must be named openmano

        Args:
            vdc_name -  name of a new vdc.

            Returns:
                The return xml content of respond or None
        """

        self.logger.info("Creating new vdc {}".format(vdc_name))
        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")
        if vdc_name is None:
            return None

        url_list = [vca.host, '/api/vdcTemplates']
        vm_list_rest_call = ''.join(url_list)
        response = Http.get(url=vm_list_rest_call,
                            headers=vca.vcloud_session.get_vcloud_headers(),
                            verify=vca.verify,
                            logger=vca.logger)

        # container url to a template
        vdc_template_ref = None
        try:
            vm_list_xmlroot = XmlElementTree.fromstring(response.content)
            for child in vm_list_xmlroot:
                # application/vnd.vmware.admin.providervdc+xml
                # we need find a template from witch we instantiate VDC
                if child.tag.split("}")[1] == 'VdcTemplate':
                    if child.attrib.get('type') == 'application/vnd.vmware.admin.vdcTemplate+xml' and child.attrib.get(
                            'name') == 'openmano':
                        vdc_template_ref = child.attrib.get('href')
        except:
            self.logger.debug("Failed parse respond for rest api call {}".format(vm_list_rest_call))
            self.logger.debug("Respond body {}".format(response.content))
            return None

        # if we didn't found required pre defined template we return None
        if vdc_template_ref is None:
            return None

        try:
            # instantiate vdc
            url_list = [vca.host, '/api/org/', self.org_uuid, '/action/instantiate']
            vm_list_rest_call = ''.join(url_list)
            data = """<InstantiateVdcTemplateParams name="{0:s}" xmlns="http://www.vmware.com/vcloud/v1.5">
                                        <Source href="{1:s}"></Source>
                                        <Description>opnemano</Description>
                                        </InstantiateVdcTemplateParams>""".format(vdc_name, vdc_template_ref)
            headers = vca.vcloud_session.get_vcloud_headers()
            headers['Content-Type'] = 'application/vnd.vmware.vcloud.instantiateVdcTemplateParams+xml'
            response = Http.post(url=vm_list_rest_call, headers=headers, data=data, verify=vca.verify,
                                 logger=vca.logger)
            # if we all ok we respond with content otherwise by default None
            if response.status_code >= 200 and response.status_code < 300:
                return response.content
            return None
        except:
            self.logger.debug("Failed parse respond for rest api call {}".format(vm_list_rest_call))
            self.logger.debug("Respond body {}".format(response.content))

        return None

    def create_vdc_rest(self, vdc_name=None):
        """
        Method create network in vCloud director

        Args:
            network_name - is network name to be created.
            parent_network_uuid - is parent provider vdc network that will be used for mapping.
            It optional attribute. by default if no parent network indicate the first available will be used.

            Returns:
                The return network uuid or return None
        """

        self.logger.info("Creating new vdc {}".format(vdc_name))

        vca = self.connect_as_admin()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")
        if vdc_name is None:
            return None

        url_list = [vca.host, '/api/admin/org/', self.org_uuid]
        vm_list_rest_call = ''.join(url_list)
        if not (not vca.vcloud_session or not vca.vcloud_session.organization):
            response = Http.get(url=vm_list_rest_call,
                                headers=vca.vcloud_session.get_vcloud_headers(),
                                verify=vca.verify,
                                logger=vca.logger)

            provider_vdc_ref = None
            add_vdc_rest_url = None
            available_networks = None

            if response.status_code != requests.codes.ok:
                self.logger.debug("REST API call {} failed. Return status code {}".format(vm_list_rest_call,
                                                                                          response.status_code))
                return None
            else:
                try:
                    vm_list_xmlroot = XmlElementTree.fromstring(response.content)
                    for child in vm_list_xmlroot:
                        # application/vnd.vmware.admin.providervdc+xml
                        if child.tag.split("}")[1] == 'Link':
                            if child.attrib.get('type') == 'application/vnd.vmware.admin.createVdcParams+xml' \
                                    and child.attrib.get('rel') == 'add':
                                add_vdc_rest_url = child.attrib.get('href')
                except:
                    self.logger.debug("Failed parse respond for rest api call {}".format(vm_list_rest_call))
                    self.logger.debug("Respond body {}".format(response.content))
                    return None

                response = self.get_provider_rest(vca=vca)
                try:
                    vm_list_xmlroot = XmlElementTree.fromstring(response)
                    for child in vm_list_xmlroot:
                        if child.tag.split("}")[1] == 'ProviderVdcReferences':
                            for sub_child in child:
                                provider_vdc_ref = sub_child.attrib.get('href')
                except:
                    self.logger.debug("Failed parse respond for rest api call {}".format(vm_list_rest_call))
                    self.logger.debug("Respond body {}".format(response))
                    return None

                if add_vdc_rest_url is not None and provider_vdc_ref is not None:
                    data = """ <CreateVdcParams name="{0:s}" xmlns="http://www.vmware.com/vcloud/v1.5"><Description>{1:s}</Description>
                            <AllocationModel>ReservationPool</AllocationModel>
                            <ComputeCapacity><Cpu><Units>MHz</Units><Allocated>2048</Allocated><Limit>2048</Limit></Cpu>
                            <Memory><Units>MB</Units><Allocated>2048</Allocated><Limit>2048</Limit></Memory>
                            </ComputeCapacity><NicQuota>0</NicQuota><NetworkQuota>100</NetworkQuota>
                            <VdcStorageProfile><Enabled>true</Enabled><Units>MB</Units><Limit>20480</Limit><Default>true</Default></VdcStorageProfile>
                            <ProviderVdcReference
                            name="Main Provider"
                            href="{2:s}" />
                    <UsesFastProvisioning>true</UsesFastProvisioning></CreateVdcParams>""".format(escape(vdc_name),
                                                                                                  escape(vdc_name),
                                                                                                  provider_vdc_ref)

                    headers = vca.vcloud_session.get_vcloud_headers()
                    headers['Content-Type'] = 'application/vnd.vmware.admin.createVdcParams+xml'
                    response = Http.post(url=add_vdc_rest_url, headers=headers, data=data, verify=vca.verify,
                                         logger=vca.logger)

                    # if we all ok we respond with content otherwise by default None
                    if response.status_code == 201:
                        return response.content
        return None

    def get_vapp_details_rest(self, vapp_uuid=None, need_admin_access=False):
        """
        Method retrieve vapp detail from vCloud director

        Args:
            vapp_uuid - is vapp identifier.

            Returns:
                The return network uuid or return None
        """

        parsed_respond = {}
        vca = None

        if need_admin_access:
            vca = self.connect_as_admin()
        else:
            vca = self.connect()

        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")
        if vapp_uuid is None:
            return None

        url_list = [vca.host, '/api/vApp/vapp-', vapp_uuid]
        get_vapp_restcall = ''.join(url_list)

        if vca.vcloud_session and vca.vcloud_session.organization:
            response = Http.get(url=get_vapp_restcall,
                                headers=vca.vcloud_session.get_vcloud_headers(),
                                verify=vca.verify,
                                logger=vca.logger)

            if response.status_code != requests.codes.ok:
                self.logger.debug("REST API call {} failed. Return status code {}".format(get_vapp_restcall,
                                                                                          response.status_code))
                return parsed_respond

            try:
                xmlroot_respond = XmlElementTree.fromstring(response.content)
                parsed_respond['ovfDescriptorUploaded'] = xmlroot_respond.attrib['ovfDescriptorUploaded']

                namespaces = {"vssd":"http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData" ,
                              'ovf': 'http://schemas.dmtf.org/ovf/envelope/1',
                              'vmw': 'http://www.vmware.com/schema/ovf',
                              'vm': 'http://www.vmware.com/vcloud/v1.5',
                              'rasd':"http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData",
                              "vmext":"http://www.vmware.com/vcloud/extension/v1.5",
                              "xmlns":"http://www.vmware.com/vcloud/v1.5"
                             }

                created_section = xmlroot_respond.find('vm:DateCreated', namespaces)
                if created_section is not None:
                    parsed_respond['created'] = created_section.text

                network_section = xmlroot_respond.find('vm:NetworkConfigSection/vm:NetworkConfig', namespaces)
                if network_section is not None and 'networkName' in network_section.attrib:
                    parsed_respond['networkname'] = network_section.attrib['networkName']

                ipscopes_section = \
                    xmlroot_respond.find('vm:NetworkConfigSection/vm:NetworkConfig/vm:Configuration/vm:IpScopes',
                                         namespaces)
                if ipscopes_section is not None:
                    for ipscope in ipscopes_section:
                        for scope in ipscope:
                            tag_key = scope.tag.split("}")[1]
                            if tag_key == 'IpRanges':
                                ip_ranges = scope.getchildren()
                                for ipblock in ip_ranges:
                                    for block in ipblock:
                                        parsed_respond[block.tag.split("}")[1]] = block.text
                            else:
                                parsed_respond[tag_key] = scope.text

                # parse children section for other attrib
                children_section = xmlroot_respond.find('vm:Children/', namespaces)
                if children_section is not None:
                    parsed_respond['name'] = children_section.attrib['name']
                    parsed_respond['nestedHypervisorEnabled'] = children_section.attrib['nestedHypervisorEnabled'] \
                     if  "nestedHypervisorEnabled" in children_section.attrib else None
                    parsed_respond['deployed'] = children_section.attrib['deployed']
                    parsed_respond['status'] = children_section.attrib['status']
                    parsed_respond['vmuuid'] = children_section.attrib['id'].split(":")[-1]
                    network_adapter = children_section.find('vm:NetworkConnectionSection', namespaces)
                    nic_list = []
                    for adapters in network_adapter:
                        adapter_key = adapters.tag.split("}")[1]
                        if adapter_key == 'PrimaryNetworkConnectionIndex':
                            parsed_respond['primarynetwork'] = adapters.text
                        if adapter_key == 'NetworkConnection':
                            vnic = {}
                            if 'network' in adapters.attrib:
                                vnic['network'] = adapters.attrib['network']
                            for adapter in adapters:
                                setting_key = adapter.tag.split("}")[1]
                                vnic[setting_key] = adapter.text
                            nic_list.append(vnic)

                    for link in children_section:
                        if link.tag.split("}")[1] == 'Link' and 'rel' in link.attrib:
                            if link.attrib['rel'] == 'screen:acquireTicket':
                                parsed_respond['acquireTicket'] = link.attrib
                            if link.attrib['rel'] == 'screen:acquireMksTicket':
                                parsed_respond['acquireMksTicket'] = link.attrib

                    parsed_respond['interfaces'] = nic_list
                    vCloud_extension_section = children_section.find('xmlns:VCloudExtension', namespaces)
                    if vCloud_extension_section is not None:
                        vm_vcenter_info = {}
                        vim_info = vCloud_extension_section.find('vmext:VmVimInfo', namespaces)
                        vmext = vim_info.find('vmext:VmVimObjectRef', namespaces)
                        if vmext is not None:
                            vm_vcenter_info["vm_moref_id"] = vmext.find('vmext:MoRef', namespaces).text
                            vm_vcenter_info["vim_server_href"] = vmext.find('vmext:VimServerRef', namespaces).attrib['href']
                        parsed_respond["vm_vcenter_info"]= vm_vcenter_info

                    virtual_hardware_section = children_section.find('ovf:VirtualHardwareSection', namespaces)
                    vm_virtual_hardware_info = {}
                    if virtual_hardware_section is not None:
                        for item in virtual_hardware_section.iterfind('ovf:Item',namespaces):
                            if item.find("rasd:Description",namespaces).text == "Hard disk":
                                disk_size = item.find("rasd:HostResource" ,namespaces
                                                ).attrib["{"+namespaces['vm']+"}capacity"]

                                vm_virtual_hardware_info["disk_size"]= disk_size
                                break

                        for link in virtual_hardware_section:
                            if link.tag.split("}")[1] == 'Link' and 'rel' in link.attrib:
                                if link.attrib['rel'] == 'edit' and link.attrib['href'].endswith("/disks"):
                                    vm_virtual_hardware_info["disk_edit_href"] = link.attrib['href']
                                    break

                    parsed_respond["vm_virtual_hardware"]= vm_virtual_hardware_info
            except Exception as exp :
                self.logger.info("Error occurred calling rest api for getting vApp details {}".format(exp))
        return parsed_respond

    def acuire_console(self, vm_uuid=None):

        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")
        if vm_uuid is None:
            return None

        if not (not vca.vcloud_session or not vca.vcloud_session.organization):
            vm_dict = self.get_vapp_details_rest(self, vapp_uuid=vm_uuid)
            console_dict = vm_dict['acquireTicket']
            console_rest_call = console_dict['href']

            response = Http.post(url=console_rest_call,
                                 headers=vca.vcloud_session.get_vcloud_headers(),
                                 verify=vca.verify,
                                 logger=vca.logger)

            if response.status_code == requests.codes.ok:
                return response.content

        return None

    def modify_vm_disk(self, vapp_uuid, flavor_disk):
        """
        Method retrieve vm disk details

        Args:
            vapp_uuid - is vapp identifier.
            flavor_disk - disk size as specified in VNFD (flavor)

            Returns:
                The return network uuid or return None
        """
        status = None
        try:
            #Flavor disk is in GB convert it into MB
            flavor_disk = int(flavor_disk) * 1024
            vm_details = self.get_vapp_details_rest(vapp_uuid)
            if vm_details:
                vm_name = vm_details["name"]
                self.logger.info("VM: {} flavor_disk :{}".format(vm_name , flavor_disk))

            if vm_details and "vm_virtual_hardware" in vm_details:
                vm_disk = int(vm_details["vm_virtual_hardware"]["disk_size"])
                disk_edit_href = vm_details["vm_virtual_hardware"]["disk_edit_href"]

                self.logger.info("VM: {} VM_disk :{}".format(vm_name , vm_disk))

                if flavor_disk > vm_disk:
                    status = self.modify_vm_disk_rest(disk_edit_href ,flavor_disk)
                    self.logger.info("Modify disk of VM {} from {} to {} MB".format(vm_name,
                                                         vm_disk,  flavor_disk ))
                else:
                    status = True
                    self.logger.info("No need to modify disk of VM {}".format(vm_name))

            return status
        except Exception as exp:
            self.logger.info("Error occurred while modifing disk size {}".format(exp))


    def modify_vm_disk_rest(self, disk_href , disk_size):
        """
        Method retrieve modify vm disk size

        Args:
            disk_href - vCD API URL to GET and PUT disk data
            disk_size - disk size as specified in VNFD (flavor)

            Returns:
                The return network uuid or return None
        """
        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")
        if disk_href is None or disk_size is None:
            return None

        if vca.vcloud_session and vca.vcloud_session.organization:
            response = Http.get(url=disk_href,
                                headers=vca.vcloud_session.get_vcloud_headers(),
                                verify=vca.verify,
                                logger=vca.logger)

        if response.status_code != requests.codes.ok:
            self.logger.debug("GET REST API call {} failed. Return status code {}".format(disk_href,
                                                                            response.status_code))
            return None
        try:
            lxmlroot_respond = lxmlElementTree.fromstring(response.content)
            namespaces = {prefix:uri for prefix,uri in lxmlroot_respond.nsmap.iteritems() if prefix}
            namespaces["xmlns"]= "http://www.vmware.com/vcloud/v1.5"

            for item in lxmlroot_respond.iterfind('xmlns:Item',namespaces):
                if item.find("rasd:Description",namespaces).text == "Hard disk":
                    disk_item = item.find("rasd:HostResource" ,namespaces )
                    if disk_item is not None:
                        disk_item.attrib["{"+namespaces['xmlns']+"}capacity"] = str(disk_size)
                        break

            data = lxmlElementTree.tostring(lxmlroot_respond, encoding='utf8', method='xml',
                                             xml_declaration=True)

            #Send PUT request to modify disk size
            headers = vca.vcloud_session.get_vcloud_headers()
            headers['Content-Type'] = 'application/vnd.vmware.vcloud.rasdItemsList+xml; charset=ISO-8859-1'

            response = Http.put(url=disk_href,
                                data=data,
                                headers=headers,
                                verify=vca.verify, logger=self.logger)

            if response.status_code != 202:
                self.logger.debug("PUT REST API call {} failed. Return status code {}".format(disk_href,
                                                                            response.status_code))
            else:
                modify_disk_task = taskType.parseString(response.content, True)
                if type(modify_disk_task) is GenericTask:
                    status = vca.block_until_completed(modify_disk_task)
                    return status

            return None

        except Exception as exp :
                self.logger.info("Error occurred calling rest api for modifing disk size {}".format(exp))
                return None

    def add_pci_devices(self, vapp_uuid , pci_devices , vmname_andid):
        """
            Method to attach pci devices to VM

             Args:
                vapp_uuid - uuid of vApp/VM
                pci_devices - pci devices infromation as specified in VNFD (flavor)

            Returns:
                The status of add pci device task , vm object and
                vcenter_conect object
        """
        vm_obj = None
        vcenter_conect = None
        self.logger.info("Add pci devices {} into vApp {}".format(pci_devices , vapp_uuid))
        #Assuming password of vCenter user is same as password of vCloud user
        vm_moref_id , vm_vcenter_host , vm_vcenter_username, vm_vcenter_port = self.get_vcenter_info_rest(vapp_uuid)
        self.logger.info("vm_moref_id,  {} vm_vcenter_host {} vm_vcenter_username{} "\
                         "vm_vcenter_port{}".format(
                                            vm_moref_id, vm_vcenter_host,
                                            vm_vcenter_username, vm_vcenter_port))
        if vm_moref_id and vm_vcenter_host and vm_vcenter_username:
            context = None
            if hasattr(ssl, '_create_unverified_context'):
                context = ssl._create_unverified_context()
            try:
                no_of_pci_devices = len(pci_devices)
                if no_of_pci_devices > 0:
                    vcenter_conect = SmartConnect(host=vm_vcenter_host, user=vm_vcenter_username,
                                      pwd=self.passwd, port=int(vm_vcenter_port) ,
                                      sslContext=context)
                    atexit.register(Disconnect, vcenter_conect)
                    content = vcenter_conect.RetrieveContent()

                    #Get VM and its host
                    host_obj, vm_obj = self.get_vm_obj(content ,vm_moref_id)
                    self.logger.info("VM {} is currently on host {}".format(vm_obj, host_obj))
                    if host_obj and vm_obj:
                        #get PCI devies from host on which vapp is currently installed
                        avilable_pci_devices = self.get_pci_devices(host_obj, no_of_pci_devices)

                        if avilable_pci_devices is None:
                            #find other hosts with active pci devices
                            new_host_obj , avilable_pci_devices = self.get_host_and_PCIdevices(
                                                                content,
                                                                no_of_pci_devices
                                                                )

                            if new_host_obj is not None and avilable_pci_devices is not None and len(avilable_pci_devices)> 0:
                                #Migrate vm to the host where PCI devices are availble
                                self.logger.info("Relocate VM {} on new host {}".format(vm_obj, new_host_obj))
                                task = self.relocate_vm(new_host_obj, vm_obj)
                                if task is not None:
                                    result = self.wait_for_vcenter_task(task, vcenter_conect)
                                    self.logger.info("Migrate VM status: {}".format(result))
                                    host_obj = new_host_obj
                                else:
                                    self.logger.info("Fail to migrate VM : {}".format(result))
                                    raise vimconn.vimconnNotFoundException(
                                    "Fail to migrate VM : {} to host {}".format(
                                                    vmname_andid,
                                                    new_host_obj)
                                        )

                        if host_obj is not None and avilable_pci_devices is not None and len(avilable_pci_devices)> 0:
                            #Add PCI devices one by one
                            for pci_device in avilable_pci_devices:
                                task = self.add_pci_to_vm(host_obj, vm_obj, pci_device)
                                if task:
                                    status= self.wait_for_vcenter_task(task, vcenter_conect)
                                    if status:
                                        self.logger.info("Added PCI device {} to VM {}".format(pci_device,str(vm_obj)))
                                else:
                                    self.logger.info("Fail to add PCI device {} to VM {}".format(pci_device,str(vm_obj)))
                            return True, vm_obj, vcenter_conect
                        else:
                            self.logger.error("Currently there is no host with"\
                                              " {} number of avaialble PCI devices required for VM {}".format(
                                                                            no_of_pci_devices,
                                                                            vmname_andid)
                                              )
                            raise vimconn.vimconnNotFoundException(
                                    "Currently there is no host with {} "\
                                    "number of avaialble PCI devices required for VM {}".format(
                                                                            no_of_pci_devices,
                                                                            vmname_andid))
                else:
                    self.logger.debug("No infromation about PCI devices {} ",pci_devices)

            except vmodl.MethodFault as error:
                self.logger.error("Error occurred while adding PCI devices {} ",error)
        return None, vm_obj, vcenter_conect

    def get_vm_obj(self, content, mob_id):
        """
            Method to get the vsphere VM object associated with a given morf ID
             Args:
                vapp_uuid - uuid of vApp/VM
                content - vCenter content object
                mob_id - mob_id of VM

            Returns:
                    VM and host object
        """
        vm_obj = None
        host_obj = None
        try :
            container = content.viewManager.CreateContainerView(content.rootFolder,
                                                        [vim.VirtualMachine], True
                                                        )
            for vm in container.view:
                mobID = vm._GetMoId()
                if mobID == mob_id:
                    vm_obj = vm
                    host_obj = vm_obj.runtime.host
                    break
        except Exception as exp:
            self.logger.error("Error occurred while finding VM object : {}".format(exp))
        return host_obj, vm_obj

    def get_pci_devices(self, host, need_devices):
        """
            Method to get the details of pci devices on given host
             Args:
                host - vSphere host object
                need_devices - number of pci devices needed on host

             Returns:
                array of pci devices
        """
        all_devices = []
        all_device_ids = []
        used_devices_ids = []

        try:
            if host:
                pciPassthruInfo = host.config.pciPassthruInfo
                pciDevies = host.hardware.pciDevice

            for pci_status in pciPassthruInfo:
                if pci_status.passthruActive:
                    for device in pciDevies:
                        if device.id == pci_status.id:
                            all_device_ids.append(device.id)
                            all_devices.append(device)

            #check if devices are in use
            avalible_devices = all_devices
            for vm in host.vm:
                if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                    vm_devices = vm.config.hardware.device
                    for device in vm_devices:
                        if type(device) is vim.vm.device.VirtualPCIPassthrough:
                            if device.backing.id in all_device_ids:
                                for use_device in avalible_devices:
                                    if use_device.id == device.backing.id:
                                        avalible_devices.remove(use_device)
                                used_devices_ids.append(device.backing.id)
                                self.logger.debug("Device {} from devices {}"\
                                        "is in use".format(device.backing.id,
                                                           device)
                                            )
            if len(avalible_devices) < need_devices:
                self.logger.debug("Host {} don't have {} number of active devices".format(host,
                                                                            need_devices))
                self.logger.debug("found only {} devives {}".format(len(avalible_devices),
                                                                    avalible_devices))
                return None
            else:
                required_devices = avalible_devices[:need_devices]
                self.logger.info("Found {} PCI devivces on host {} but required only {}".format(
                                                            len(avalible_devices),
                                                            host,
                                                            need_devices))
                self.logger.info("Retruning {} devices as {}".format(need_devices,
                                                                required_devices ))
                return required_devices

        except Exception as exp:
            self.logger.error("Error {} occurred while finding pci devices on host: {}".format(exp, host))

        return None

    def get_host_and_PCIdevices(self, content, need_devices):
        """
         Method to get the details of pci devices infromation on all hosts

            Args:
                content - vSphere host object
                need_devices - number of pci devices needed on host

            Returns:
                 array of pci devices and host object
        """
        host_obj = None
        pci_device_objs = None
        try:
            if content:
                container = content.viewManager.CreateContainerView(content.rootFolder,
                                                            [vim.HostSystem], True)
                for host in container.view:
                    devices = self.get_pci_devices(host, need_devices)
                    if devices:
                        host_obj = host
                        pci_device_objs = devices
                        break
        except Exception as exp:
            self.logger.error("Error {} occurred while finding pci devices on host: {}".format(exp, host_obj))

        return host_obj,pci_device_objs

    def relocate_vm(self, dest_host, vm) :
        """
         Method to get the relocate VM to new host

            Args:
                dest_host - vSphere host object
                vm - vSphere VM object

            Returns:
                task object
        """
        task = None
        try:
            relocate_spec = vim.vm.RelocateSpec(host=dest_host)
            task = vm.Relocate(relocate_spec)
            self.logger.info("Migrating {} to destination host {}".format(vm, dest_host))
        except Exception as exp:
            self.logger.error("Error occurred while relocate VM {} to new host {}: {}".format(
                                                                            dest_host, vm, exp))
        return task

    def wait_for_vcenter_task(self, task, actionName='job', hideResult=False):
        """
        Waits and provides updates on a vSphere task
        """
        while task.info.state == vim.TaskInfo.State.running:
            time.sleep(2)

        if task.info.state == vim.TaskInfo.State.success:
            if task.info.result is not None and not hideResult:
                self.logger.info('{} completed successfully, result: {}'.format(
                                                            actionName,
                                                            task.info.result))
            else:
                self.logger.info('Task {} completed successfully.'.format(actionName))
        else:
            self.logger.error('{} did not complete successfully: {} '.format(
                                                            actionName,
                                                            task.info.error)
                              )

        return task.info.result

    def add_pci_to_vm(self,host_object, vm_object, host_pci_dev):
        """
         Method to add pci device in given VM

            Args:
                host_object - vSphere host object
                vm_object - vSphere VM object
                host_pci_dev -  host_pci_dev must be one of the devices from the
                                host_object.hardware.pciDevice list
                                which is configured as a PCI passthrough device

            Returns:
                task object
        """
        task = None
        if vm_object and host_object and host_pci_dev:
            try :
                #Add PCI device to VM
                pci_passthroughs = vm_object.environmentBrowser.QueryConfigTarget(host=None).pciPassthrough
                systemid_by_pciid = {item.pciDevice.id: item.systemId for item in pci_passthroughs}

                if host_pci_dev.id not in systemid_by_pciid:
                    self.logger.error("Device {} is not a passthrough device ".format(host_pci_dev))
                    return None

                deviceId = hex(host_pci_dev.deviceId % 2**16).lstrip('0x')
                backing = vim.VirtualPCIPassthroughDeviceBackingInfo(deviceId=deviceId,
                                            id=host_pci_dev.id,
                                            systemId=systemid_by_pciid[host_pci_dev.id],
                                            vendorId=host_pci_dev.vendorId,
                                            deviceName=host_pci_dev.deviceName)

                hba_object = vim.VirtualPCIPassthrough(key=-100, backing=backing)

                new_device_config = vim.VirtualDeviceConfigSpec(device=hba_object)
                new_device_config.operation = "add"
                vmConfigSpec = vim.vm.ConfigSpec()
                vmConfigSpec.deviceChange = [new_device_config]

                task = vm_object.ReconfigVM_Task(spec=vmConfigSpec)
                self.logger.info("Adding PCI device {} into VM {} from host {} ".format(
                                                            host_pci_dev, vm_object, host_object)
                                )
            except Exception as exp:
                self.logger.error("Error occurred while adding pci devive {} to VM {}: {}".format(
                                                                            host_pci_dev,
                                                                            vm_object,
                                                                             exp))
        return task

    def get_vcenter_info_rest(self , vapp_uuid):
        """
        https://192.169.241.105/api/admin/extension/vimServer/cc82baf9-9f80-4468-bfe9-ce42b3f9dde5
        Method to get details of vCenter

            Args:
                vapp_uuid - uuid of vApp or VM

            Returns:
                Moref Id of VM and deails of vCenter
        """
        vm_moref_id = None
        vm_vcenter = None
        vm_vcenter_username = None
        vm_vcenter_port = None

        vm_details = self.get_vapp_details_rest(vapp_uuid, need_admin_access=True)
        if vm_details and "vm_vcenter_info" in vm_details:
            vm_moref_id = vm_details["vm_vcenter_info"]["vm_moref_id"]
            vim_server_href = vm_details["vm_vcenter_info"]["vim_server_href"]

            if vim_server_href:
                vca = self.connect_as_admin()
                if not vca:
                    raise vimconn.vimconnConnectionException("self.connect() is failed")
                if vim_server_href is None:
                    self.logger.error("No url to get vcenter details")

                if vca.vcloud_session and vca.vcloud_session.organization:
                    response = Http.get(url=vim_server_href,
                                        headers=vca.vcloud_session.get_vcloud_headers(),
                                        verify=vca.verify,
                                        logger=vca.logger)

                if response.status_code != requests.codes.ok:
                    self.logger.debug("GET REST API call {} failed. Return status code {}".format(vim_server_href,
                                                                                    response.status_code))
                try:
                    namespaces={"vmext":"http://www.vmware.com/vcloud/extension/v1.5",
                                "vcloud":"http://www.vmware.com/vcloud/v1.5"
                                }
                    xmlroot_respond = XmlElementTree.fromstring(response.content)
                    vm_vcenter_username =  xmlroot_respond.find('vmext:Username', namespaces).text
                    vcenter_url = xmlroot_respond.find('vmext:Url', namespaces).text
                    vm_vcenter_port = vcenter_url.split(":")[2]
                    vm_vcenter =  vcenter_url.split(":")[1].split("//")[1]

                except Exception as exp :
                    self.logger.info("Error occurred calling rest api for vcenter information {}".format(exp))

        return vm_moref_id , vm_vcenter , vm_vcenter_username, vm_vcenter_port


    def get_vm_pci_details(self, vmuuid):
        """
            Method to get VM PCI device details from vCenter

            Args:
                vm_obj - vSphere VM object

            Returns:
                dict of PCI devives attached to VM

        """
        vm_pci_devices_info = {}
        try:
            vm_moref_id , vm_vcenter_host , vm_vcenter_username, vm_vcenter_port = self.get_vcenter_info_rest(vmuuid)
            if vm_moref_id and vm_vcenter_host and vm_vcenter_username:
                context = None
                if hasattr(ssl, '_create_unverified_context'):
                    context = ssl._create_unverified_context()
                vcenter_conect = SmartConnect(host=vm_vcenter_host, user=vm_vcenter_username,
                                  pwd=self.passwd, port=int(vm_vcenter_port),
                                  sslContext=context)
                atexit.register(Disconnect, vcenter_conect)
                content = vcenter_conect.RetrieveContent()

                #Get VM and its host
                host_obj, vm_obj = self.get_vm_obj(content ,vm_moref_id)
                for device in vm_obj.config.hardware.device:
                    if type(device) == vim.vm.device.VirtualPCIPassthrough:
                        device_details={'devide_id':device.backing.id,
                                        'pciSlotNumber':device.slotInfo.pciSlotNumber
                                     }
                        vm_pci_devices_info[device.deviceInfo.label] = device_details
        except Exception as exp:
            self.logger.info("Error occurred while getting PCI devices infromationn"\
                             " for VM {} : {}".format(vm_obj,exp))
        return vm_pci_devices_info


