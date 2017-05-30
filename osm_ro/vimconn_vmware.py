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
import random

# global variable for vcd connector type
STANDALONE = 'standalone'

# key for flavor dicts
FLAVOR_RAM_KEY = 'ram'
FLAVOR_VCPUS_KEY = 'vcpus'
FLAVOR_DISK_KEY = 'disk'
DEFAULT_IP_PROFILE = {'dhcp_count':50,
                      'dhcp_enabled':True,
                      'ip_version':"IPv4"
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

class vimconnector(vimconn.vimconnector):
    # dict used to store flavor in memory
    flavorlist = {}

    def __init__(self, uuid=None, name=None, tenant_id=None, tenant_name=None,
                 url=None, url_admin=None, user=None, passwd=None, log_level=None, config={}, persistent_info={}):
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
            config - Provide NSX and vCenter information

            Returns:
                Nothing.
        """

        vimconn.vimconnector.__init__(self, uuid, name, tenant_id, tenant_name, url,
                                      url_admin, user, passwd, log_level, config)

        self.logger = logging.getLogger('openmano.vim.vmware')
        self.logger.setLevel(10)
        self.persistent_info = persistent_info

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
        self.nsx_manager = None
        self.nsx_user = None
        self.nsx_password = None

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

        try:
            self.nsx_manager = config['nsx_manager']
            self.nsx_user = config['nsx_user']
            self.nsx_password = config['nsx_password']
        except KeyError:
            raise vimconn.vimconnException(message="Error: nsx manager or nsx user or nsx password is empty in Config")

        self.vcenter_ip = config.get("vcenter_ip", None)
        self.vcenter_port = config.get("vcenter_port", None)
        self.vcenter_user = config.get("vcenter_user", None)
        self.vcenter_password = config.get("vcenter_password", None)

# ############# Stub code for SRIOV #################
#         try:
#             self.dvs_name = config['dv_switch_name']
#         except KeyError:
#             raise vimconn.vimconnException(message="Error: distributed virtaul switch name is empty in Config")
#
#         self.vlanID_range = config.get("vlanID_range", None)

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

# ############# Stub code for SRIOV #################
#         if net_type == "data" or net_type == "ptp":
#             if self.config.get('dv_switch_name') == None:
#                  raise vimconn.vimconnConflictException("You must provide 'dv_switch_name' at config value")
#             network_uuid = self.create_dvPort_group(net_name)

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

        try:
            vdcid = vdc.get_id().split(":")[3]
            networks = vca.get_networks(vdc.get_name())
            network_list = []

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

        try:
            vdc = vca.get_vdc(self.tenant_name)
            vdc_id = vdc.get_id().split(":")[3]

            networks = vca.get_networks(vdc.get_name())
            filter_dict = {}

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

        # ############# Stub code for SRIOV #################
#         dvport_group = self.get_dvport_group(net_id)
#         if dvport_group:
#             #delete portgroup
#             status = self.destroy_dvport_group(net_id)
#             if status:
#                 # Remove vlanID from persistent info
#                 if net_id in self.persistent_info["used_vlanIDs"]:
#                     del self.persistent_info["used_vlanIDs"][net_id]
#
#                 return net_id

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
        if flavor_id not in vimconnector.flavorlist:
            raise vimconn.vimconnNotFoundException("Flavor not found.")
        return vimconnector.flavorlist[flavor_id]

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
        vimconnector.flavorlist[str(flavor_id)] = new_flavor
        self.logger.debug("Created flavor - {} : {}".format(flavor_id, new_flavor))

        return str(flavor_id)

    def delete_flavor(self, flavor_id):
        """Deletes a tenant flavor from VIM identify by its id

           Returns the used id or raise an exception
        """
        if flavor_id not in vimconnector.flavorlist:
            raise vimconn.vimconnNotFoundException("Flavor not found.")

        vimconnector.flavorlist.pop(flavor_id, None)
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
        try:
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
        except Exception as exp:
            self.logger.debug("Failed while uploading OVF to catalog {} for OVF file {} with Exception {}"
                .format(catalog_name,media_file_name, exp))
            raise vimconn.vimconnException(
                "Failed while uploading OVF to catalog {} for OVF file {} with Exception {}"
                .format(catalog_name,media_file_name, exp))

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

    def get_catalog_obj(self, catalog_uuid=None, catalogs=None):
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
                return catalog
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

        try:
            catalogs = vca.get_catalogs()
        except Exception as exp:
            self.logger.debug("Failed get catalogs() with Exception {} ".format(exp))
            raise vimconn.vimconnException("Failed get catalogs() with Exception {} ".format(exp))

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
                    if filter_dict.get("name") and filter_dict["name"] != name:
                        continue
                    if filter_dict.get("id") and filter_dict["id"] != catalog_uuid:
                        continue
                    filtered_dict ["name"] = name
                    filtered_dict ["id"] = catalog_uuid
                    image_list.append(filtered_dict)

                self.logger.debug("List of already created catalog items: {}".format(image_list))
                return image_list
        except Exception as exp:
            raise vimconn.vimconnException("Exception occured while retriving catalog items {}".format(exp))

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
        self.logger.debug("desc {} boot {} image_id: {} flavor_id: {} net_list: {} cloud_config {} disk_list {}".format(
                                    description, start, image_id, flavor_id, net_list, cloud_config, disk_list))
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
        vm_cpus = None
        vm_memory = None
        vm_disk = None

        if flavor_id is not None:
            if flavor_id not in vimconnector.flavorlist:
                raise vimconn.vimconnNotFoundException("new_vminstance(): Failed create vApp {}: "
                                                       "Failed retrieve flavor information "
                                                       "flavor id {}".format(name, flavor_id))
            else:
                try:
                    flavor = vimconnector.flavorlist[flavor_id]
                    vm_cpus = flavor[FLAVOR_VCPUS_KEY]
                    vm_memory = flavor[FLAVOR_RAM_KEY]
                    vm_disk = flavor[FLAVOR_DISK_KEY]
                    extended = flavor.get("extended", None)
                    if extended:
                        numas=extended.get("numas", None)

                except Exception as exp:
                    raise vimconn.vimconnException("Corrupted flavor. {}.Exception: {}".format(flavor_id, exp))

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
        try:
            vapptask = vca.create_vapp(self.tenant_name, vmname_andid, templateName,
                                       self.get_catalogbyid(image_id, catalogs),
                                       network_name=None,  # None while creating vapp
                                       network_mode=network_mode,
                                       vm_name=vmname_andid,
                                       vm_cpus=vm_cpus,  # can be None if flavor is None
                                       vm_memory=vm_memory)  # can be None if flavor is None

            if vapptask is None or vapptask is False:
                raise vimconn.vimconnUnexpectedResponse(
                    "new_vminstance(): failed to create vApp {}".format(vmname_andid))
            if type(vapptask) is VappTask:
                vca.block_until_completed(vapptask)

        except Exception as exp:
            raise vimconn.vimconnUnexpectedResponse(
                "new_vminstance(): failed to create vApp {} with Exception:{}".format(vmname_andid, exp))

        # we should have now vapp in undeployed state.
        try:
            vapp = vca.get_vapp(vca.get_vdc(self.tenant_name), vmname_andid)
            vapp_uuid = self.get_vappid(vca.get_vdc(self.tenant_name), vmname_andid)
        except Exception as exp:
            raise vimconn.vimconnUnexpectedResponse(
                    "new_vminstance(): Failed to retrieve vApp {} after creation: Exception:{}"
                    .format(vmname_andid, exp))

        if vapp is None:
            raise vimconn.vimconnUnexpectedResponse(
                "new_vminstance(): Failed to retrieve vApp {} after creation".format(
                                                                            vmname_andid))

        #Add PCI passthrough/SRIOV configrations
        vm_obj = None
        pci_devices_info = []
        sriov_net_info = []
        reserve_memory = False

        for net in net_list:
            if net["type"]=="PF":
                pci_devices_info.append(net)
            elif  (net["type"]=="VF" or  net["type"]=="VFnotShared") and 'net_id'in net:
                sriov_net_info.append(net)

        #Add PCI
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
                reserve_memory = True
            else:
                self.logger.info("Fail to add PCI devives {} to VM {}".format(
                                                            pci_devices_info,
                                                            vmname_andid)
                                 )
        # Modify vm disk
        if vm_disk:
            #Assuming there is only one disk in ovf and fast provisioning in organization vDC is disabled
            result = self.modify_vm_disk(vapp_uuid, vm_disk)
            if result :
                self.logger.debug("Modified Disk size of VM {} ".format(vmname_andid))

        #Add new or existing disks to vApp
        if disk_list:
            added_existing_disk = False
            for disk in disk_list:
                if 'device_type' in disk and disk['device_type'] == 'cdrom':
                    image_id = disk['image_id']
                    # Adding CD-ROM to VM
                    # will revisit code once specification ready to support this feature
                    self.insert_media_to_vm(vapp, image_id)
                elif "image_id" in disk and disk["image_id"] is not None:
                    self.logger.debug("Adding existing disk from image {} to vm {} ".format(
                                                                    disk["image_id"] , vapp_uuid))
                    self.add_existing_disk(catalogs=catalogs,
                                           image_id=disk["image_id"],
                                           size = disk["size"],
                                           template_name=templateName,
                                           vapp_uuid=vapp_uuid
                                           )
                    added_existing_disk = True
                else:
                    #Wait till added existing disk gets reflected into vCD database/API
                    if added_existing_disk:
                        time.sleep(5)
                        added_existing_disk = False
                    self.add_new_disk(vca, vapp_uuid, disk['size'])

        if numas:
            # Assigning numa affinity setting
            for numa in numas:
                if 'paired-threads-id' in numa:
                    paired_threads_id = numa['paired-threads-id']
                    self.set_numa_affinity(vapp_uuid, paired_threads_id)

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

                        type_list = ['PF','VF','VFnotShared']
                        if 'type' in net and net['type'] not in type_list:
                            # fetching nic type from vnf
                            if 'model' in net:
                                nic_type = net['model']
                                self.logger.info("new_vminstance(): adding network adapter "\
                                                          "to a network {}".format(nets[0].name))
                                self.add_network_adapter_to_vms(vapp, nets[0].name,
                                                                primary_nic_index,
                                                                nicIndex,
                                                                net,
                                                                nic_type=nic_type)
                            else:
                                self.logger.info("new_vminstance(): adding network adapter "\
                                                         "to a network {}".format(nets[0].name))
                                self.add_network_adapter_to_vms(vapp, nets[0].name,
                                                                primary_nic_index,
                                                                nicIndex,
                                                                net)
                nicIndex += 1

            # cloud-init for ssh-key injection
            if cloud_config:
                self.cloud_init(vapp,cloud_config)

            # deploy and power on vm
            self.logger.debug("new_vminstance(): Deploying vApp {} ".format(name))
            deploytask = vapp.deploy(powerOn=False)
            if type(deploytask) is GenericTask:
                vca.block_until_completed(deploytask)

        # ############# Stub code for SRIOV #################
        #Add SRIOV
#         if len(sriov_net_info) > 0:
#             self.logger.info("Need to add SRIOV adapters {} into VM {}".format(sriov_net_info,
#                                                                         vmname_andid ))
#             sriov_status, vm_obj, vcenter_conect = self.add_sriov(vapp_uuid,
#                                                                   sriov_net_info,
#                                                                   vmname_andid)
#             if sriov_status:
#                 self.logger.info("Added SRIOV {} to VM {}".format(
#                                                             sriov_net_info,
#                                                             vmname_andid)
#                                  )
#                 reserve_memory = True
#             else:
#                 self.logger.info("Fail to add SRIOV {} to VM {}".format(
#                                                             sriov_net_info,
#                                                             vmname_andid)
#                                  )

            # If VM has PCI devices or SRIOV reserve memory for VM
            if reserve_memory:
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

        except Exception as exp :
            # it might be a case if specific mandatory entry in dict is empty or some other pyVcloud exception
            self.logger.debug("new_vminstance(): Failed create new vm instance {}".format(name, exp))
            raise vimconn.vimconnException("new_vminstance(): Failed create new vm instance {}".format(name, exp))

        # check if vApp deployed and if that the case return vApp UUID otherwise -1
        wait_time = 0
        vapp_uuid = None
        while wait_time <= MAX_WAIT_TIME:
            try:
                vapp = vca.get_vapp(vca.get_vdc(self.tenant_name), vmname_andid)
            except Exception as exp:
                raise vimconn.vimconnUnexpectedResponse(
                        "new_vminstance(): Failed to retrieve vApp {} after creation: Exception:{}"
                        .format(vmname_andid, exp))

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
        nsx_edge_list = []
        for vmuuid in vm_list:
            vmname = self.get_namebyvappid(vca, vdc, vmuuid)
            if vmname is not None:

                try:
                    the_vapp = vca.get_vapp(vdc, vmname)
                    vm_info = the_vapp.get_vms_details()
                    vm_status = vm_info[0]['status']
                    vm_pci_details = self.get_vm_pci_details(vmuuid)
                    vm_info[0].update(vm_pci_details)

                    vm_dict = {'status': vcdStatusCode2manoFormat[the_vapp.me.get_status()],
                               'error_msg': vcdStatusCode2manoFormat[the_vapp.me.get_status()],
                               'vim_info': yaml.safe_dump(vm_info), 'interfaces': []}

                    # get networks
                    vm_app_networks = the_vapp.get_vms_network_info()
                    for vapp_network in vm_app_networks:
                        for vm_network in vapp_network:
                            if vm_network['name'] == vmname:
                                #Assign IP Address based on MAC Address in NSX DHCP lease info
                                if vm_network['ip'] is None:
                                    if not nsx_edge_list:
                                        nsx_edge_list = self.get_edge_details()
                                        if nsx_edge_list is None:
                                            raise vimconn.vimconnException("refresh_vms_status:"\
                                                                           "Failed to get edge details from NSX Manager")
                                    if vm_network['mac'] is not None:
                                        vm_network['ip'] = self.get_ipaddr_from_NSXedge(nsx_edge_list, vm_network['mac'])

                                vm_net_id = self.get_network_id_by_name(vm_network['network_name'])
                                interface = {"mac_address": vm_network['mac'],
                                             "vim_net_id": vm_net_id,
                                             "vim_interface_id": vm_net_id,
                                             'ip_address': vm_network['ip']}
                                # interface['vim_info'] = yaml.safe_dump(vm_network)
                                vm_dict["interfaces"].append(interface)
                    # add a vm to vm dict
                    vms_dict.setdefault(vmuuid, vm_dict)
                except Exception as exp:
                    self.logger.debug("Error in response {}".format(exp))
                    self.logger.debug(traceback.format_exc())

        return vms_dict


    def get_edge_details(self):
        """Get the NSX edge list from NSX Manager
           Returns list of NSX edges
        """
        edge_list = []
        rheaders = {'Content-Type': 'application/xml'}
        nsx_api_url = '/api/4.0/edges'

        self.logger.debug("Get edge details from NSX Manager {} {}".format(self.nsx_manager, nsx_api_url))

        try:
            resp = requests.get(self.nsx_manager + nsx_api_url,
                                auth = (self.nsx_user, self.nsx_password),
                                verify = False, headers = rheaders)
            if resp.status_code == requests.codes.ok:
                paged_Edge_List = XmlElementTree.fromstring(resp.text)
                for edge_pages in paged_Edge_List:
                    if edge_pages.tag == 'edgePage':
                        for edge_summary in edge_pages:
                            if edge_summary.tag == 'pagingInfo':
                                for element in edge_summary:
                                    if element.tag == 'totalCount' and element.text == '0':
                                        raise vimconn.vimconnException("get_edge_details: No NSX edges details found: {}"
                                                                       .format(self.nsx_manager))

                            if edge_summary.tag == 'edgeSummary':
                                for element in edge_summary:
                                    if element.tag == 'id':
                                        edge_list.append(element.text)
                    else:
                        raise vimconn.vimconnException("get_edge_details: No NSX edge details found: {}"
                                                       .format(self.nsx_manager))

                if not edge_list:
                    raise vimconn.vimconnException("get_edge_details: "\
                                                   "No NSX edge details found: {}"
                                                   .format(self.nsx_manager))
                else:
                    self.logger.debug("get_edge_details: Found NSX edges {}".format(edge_list))
                    return edge_list
            else:
                self.logger.debug("get_edge_details: "
                                  "Failed to get NSX edge details from NSX Manager: {}"
                                  .format(resp.content))
                return None

        except Exception as exp:
            self.logger.debug("get_edge_details: "\
                              "Failed to get NSX edge details from NSX Manager: {}"
                              .format(exp))
            raise vimconn.vimconnException("get_edge_details: "\
                                           "Failed to get NSX edge details from NSX Manager: {}"
                                           .format(exp))


    def get_ipaddr_from_NSXedge(self, nsx_edges, mac_address):
        """Get IP address details from NSX edges, using the MAC address
           PARAMS: nsx_edges : List of NSX edges
                   mac_address : Find IP address corresponding to this MAC address
           Returns: IP address corrresponding to the provided MAC address
        """

        ip_addr = None
        rheaders = {'Content-Type': 'application/xml'}

        self.logger.debug("get_ipaddr_from_NSXedge: Finding IP addr from NSX edge")

        try:
            for edge in nsx_edges:
                nsx_api_url = '/api/4.0/edges/'+ edge +'/dhcp/leaseInfo'

                resp = requests.get(self.nsx_manager + nsx_api_url,
                                    auth = (self.nsx_user, self.nsx_password),
                                    verify = False, headers = rheaders)

                if resp.status_code == requests.codes.ok:
                    dhcp_leases = XmlElementTree.fromstring(resp.text)
                    for child in dhcp_leases:
                        if child.tag == 'dhcpLeaseInfo':
                            dhcpLeaseInfo = child
                            for leaseInfo in dhcpLeaseInfo:
                                for elem in leaseInfo:
                                    if (elem.tag)=='macAddress':
                                        edge_mac_addr = elem.text
                                    if (elem.tag)=='ipAddress':
                                        ip_addr = elem.text
                                if edge_mac_addr is not None:
                                    if edge_mac_addr == mac_address:
                                        self.logger.debug("Found ip addr {} for mac {} at NSX edge {}"
                                                          .format(ip_addr, mac_address,edge))
                                        return ip_addr
                else:
                    self.logger.debug("get_ipaddr_from_NSXedge: "\
                                      "Error occurred while getting DHCP lease info from NSX Manager: {}"
                                      .format(resp.content))

            self.logger.debug("get_ipaddr_from_NSXedge: No IP addr found in any NSX edge")
            return None

        except XmlElementTree.ParseError as Err:
            self.logger.debug("ParseError in response from NSX Manager {}".format(Err.message), exc_info=True)


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
                vm_info = the_vapp.get_vms_details()
                vm_status = vm_info[0]['status']
                self.logger.info("action_vminstance: Power on vApp: {}".format(vapp_name))
                if vm_status == "Suspended" or vm_status == "Powered off":
                    power_on_task = the_vapp.poweron()
                    result = vca.block_until_completed(power_on_task)
                    self.instance_actions_result("start", result, vapp_name)
            elif "rebuild" in action_dict:
                self.logger.info("action_vminstance: Rebuild vApp: {}".format(vapp_name))
                rebuild_task = the_vapp.deploy(powerOn=True)
                result = vca.block_until_completed(rebuild_task)
                self.instance_actions_result("rebuild", result, vapp_name)
            elif "pause" in action_dict:
                self.logger.info("action_vminstance: pause vApp: {}".format(vapp_name))
                pause_task = the_vapp.undeploy(action='suspend')
                result = vca.block_until_completed(pause_task)
                self.instance_actions_result("pause", result, vapp_name)
            elif "resume" in action_dict:
                self.logger.info("action_vminstance: resume vApp: {}".format(vapp_name))
                power_task = the_vapp.poweron()
                result = vca.block_until_completed(power_task)
                self.instance_actions_result("resume", result, vapp_name)
            elif "shutoff" in action_dict or "shutdown" in action_dict:
                action_name , value = action_dict.items()[0]
                self.logger.info("action_vminstance: {} vApp: {}".format(action_name, vapp_name))
                power_off_task = the_vapp.undeploy(action='powerOff')
                result = vca.block_until_completed(power_off_task)
                if action_name == "shutdown":
                    self.instance_actions_result("shutdown", result, vapp_name)
                else:
                    self.instance_actions_result("shutoff", result, vapp_name)
            elif "forceOff" in action_dict:
                result = the_vapp.undeploy(action='force')
                self.instance_actions_result("forceOff", result, vapp_name)
            elif "reboot" in action_dict:
                self.logger.info("action_vminstance: reboot vApp: {}".format(vapp_name))
                reboot_task = the_vapp.reboot()
            else:
                raise vimconn.vimconnException("action_vminstance: Invalid action {} or action is None.".format(action_dict))
            return vm__vim_uuid
        except Exception as exp :
            self.logger.debug("action_vminstance: Failed with Exception {}".format(exp))
            raise vimconn.vimconnException("action_vminstance: Failed with Exception {}".format(exp))

    def instance_actions_result(self, action, result, vapp_name):
        if result:
            self.logger.info("action_vminstance: Sucessfully {} the vApp: {}".format(action, vapp_name))
        else:
            self.logger.error("action_vminstance: Failed to {} vApp: {}".format(action, vapp_name))

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

        try:
            content = self.get_network_action(network_uuid=network_uuid)
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
        except Exception as exp :
            self.logger.debug("get_vcd_network: Failed with Exception {}".format(exp))
            raise vimconn.vimconnException("get_vcd_network: Failed with Exception {}".format(exp))

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
                self.logger.info("Created new network name: {} uuid: {}".format(network_name, vcd_uuid[3]))
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

            try:
                #Configure IP profile of the network
                ip_profile = ip_profile if ip_profile is not None else DEFAULT_IP_PROFILE

                if 'subnet_address' not in ip_profile or ip_profile['subnet_address'] is None:
                    subnet_rand = random.randint(0, 255)
                    ip_base = "192.168.{}.".format(subnet_rand)
                    ip_profile['subnet_address'] = ip_base + "0/24"
                else:
                    ip_base = ip_profile['subnet_address'].rsplit('.',1)[0] + '.'

                if 'gateway_address' not in ip_profile or ip_profile['gateway_address'] is None:
                    ip_profile['gateway_address']=ip_base + "1"
                if 'dhcp_count' not in ip_profile or ip_profile['dhcp_count'] is None:
                    ip_profile['dhcp_count']=DEFAULT_IP_PROFILE['dhcp_count']
                if 'dhcp_enabled' not in ip_profile or ip_profile['dhcp_enabled'] is None:
                    ip_profile['dhcp_enabled']=DEFAULT_IP_PROFILE['dhcp_enabled']
                if 'dhcp_start_address' not in ip_profile or ip_profile['dhcp_start_address'] is None:
                    ip_profile['dhcp_start_address']=ip_base + "3"
                if 'ip_version' not in ip_profile or ip_profile['ip_version'] is None:
                    ip_profile['ip_version']=DEFAULT_IP_PROFILE['ip_version']
                if 'dns_address' not in ip_profile or ip_profile['dns_address'] is None:
                    ip_profile['dns_address']=ip_base + "2"

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
            except KeyError as exp:
                self.logger.debug("Create Network REST: Key error {}".format(exp))
                raise vimconn.vimconnException("Create Network REST: Key error{}".format(exp))

            # either use client provided UUID or search for a first available
            #  if both are not defined we return none
            if parent_network_uuid is not None:
                url_list = [vca.host, '/api/admin/network/', parent_network_uuid]
                add_vdc_rest_url = ''.join(url_list)

            #Creating all networks as Direct Org VDC type networks.
            #Unused in case of Underlay (data/ptp) network interface.
            fence_mode="bridged"
            is_inherited='false'
            dns_list = dns_address.split(";")
            dns1 = dns_list[0]
            dns2_text = ""
            if len(dns_list) >= 2:
                dns2_text = "\n                                                <Dns2>{}</Dns2>\n".format(dns_list[1])
            data = """ <OrgVdcNetwork name="{0:s}" xmlns="http://www.vmware.com/vcloud/v1.5">
                            <Description>Openmano created</Description>
                                    <Configuration>
                                        <IpScopes>
                                            <IpScope>
                                                <IsInherited>{1:s}</IsInherited>
                                                <Gateway>{2:s}</Gateway>
                                                <Netmask>{3:s}</Netmask>
                                                <Dns1>{4:s}</Dns1>{5:s}
                                                <IsEnabled>{6:s}</IsEnabled>
                                                <IpRanges>
                                                    <IpRange>
                                                        <StartAddress>{7:s}</StartAddress>
                                                        <EndAddress>{8:s}</EndAddress>
                                                    </IpRange>
                                                </IpRanges>
                                            </IpScope>
                                        </IpScopes>
                                        <ParentNetwork href="{9:s}"/>
                                        <FenceMode>{10:s}</FenceMode>
                                    </Configuration>
                                    <IsShared>{11:s}</IsShared>
                        </OrgVdcNetwork> """.format(escape(network_name), is_inherited, gateway_address,
                                                    subnet_address, dns1, dns2_text, dhcp_enabled,
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
                    self.logger.debug("Create Network POST REST API call failed. Return status code {}, Response content: {}"
                                      .format(response.status_code,response.content))
                else:
                    network = networkType.parseString(response.content, True)
                    create_nw_task = network.get_Tasks().get_Task()[0]

                    # if we all ok we respond with content after network creation completes
                    # otherwise by default return None
                    if create_nw_task is not None:
                        self.logger.debug("Create Network REST : Waiting for Network creation complete")
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
        self.logger.info("Add pci devices {} into vApp {}".format(pci_devices , vapp_uuid))
        vcenter_conect, content = self.get_vcenter_content()
        vm_moref_id = self.get_vm_moref_id(vapp_uuid)

        if vm_moref_id:
            try:
                no_of_pci_devices = len(pci_devices)
                if no_of_pci_devices > 0:
                    #Get VM and its host
                    host_obj, vm_obj = self.get_vm_obj(content, vm_moref_id)
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
                                    self.logger.error("Fail to add PCI device {} to VM {}".format(pci_device,str(vm_obj)))
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

    def get_vm_vcenter_info(self):
        """
        Method to get details of vCenter and vm

            Args:
                vapp_uuid - uuid of vApp or VM

            Returns:
                Moref Id of VM and deails of vCenter
        """
        vm_vcenter_info = {}

        if self.vcenter_ip is not None:
            vm_vcenter_info["vm_vcenter_ip"] = self.vcenter_ip
        else:
            raise vimconn.vimconnException(message="vCenter IP is not provided."\
                                           " Please provide vCenter IP while attaching datacenter to tenant in --config")
        if self.vcenter_port is not None:
            vm_vcenter_info["vm_vcenter_port"] = self.vcenter_port
        else:
            raise vimconn.vimconnException(message="vCenter port is not provided."\
                                           " Please provide vCenter port while attaching datacenter to tenant in --config")
        if self.vcenter_user is not None:
            vm_vcenter_info["vm_vcenter_user"] = self.vcenter_user
        else:
            raise vimconn.vimconnException(message="vCenter user is not provided."\
                                           " Please provide vCenter user while attaching datacenter to tenant in --config")

        if self.vcenter_password is not None:
            vm_vcenter_info["vm_vcenter_password"] = self.vcenter_password
        else:
            raise vimconn.vimconnException(message="vCenter user password is not provided."\
                                           " Please provide vCenter user password while attaching datacenter to tenant in --config")

        return vm_vcenter_info


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
            vcenter_conect, content = self.get_vcenter_content()
            vm_moref_id = self.get_vm_moref_id(vmuuid)
            if vm_moref_id:
                #Get VM and its host
                if content:
                    host_obj, vm_obj = self.get_vm_obj(content, vm_moref_id)
                    if host_obj and vm_obj:
                        vm_pci_devices_info["host_name"]= host_obj.name
                        vm_pci_devices_info["host_ip"]= host_obj.config.network.vnic[0].spec.ip.ipAddress
                        for device in vm_obj.config.hardware.device:
                            if type(device) == vim.vm.device.VirtualPCIPassthrough:
                                device_details={'devide_id':device.backing.id,
                                                'pciSlotNumber':device.slotInfo.pciSlotNumber,
                                            }
                                vm_pci_devices_info[device.deviceInfo.label] = device_details
                else:
                    self.logger.error("Can not connect to vCenter while getting "\
                                          "PCI devices infromationn")
                return vm_pci_devices_info
        except Exception as exp:
            self.logger.error("Error occurred while getting VM infromationn"\
                             " for VM : {}".format(exp))
            raise vimconn.vimconnException(message=exp)

    def add_network_adapter_to_vms(self, vapp, network_name, primary_nic_index, nicIndex, net, nic_type=None):
        """
            Method to add network adapter type to vm
            Args :
                network_name - name of network
                primary_nic_index - int value for primary nic index
                nicIndex - int value for nic index
                nic_type - specify model name to which add to vm
            Returns:
                None
        """
        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("Failed to connect vCloud director")

        try:
            ip_address = None
            floating_ip = False
            if 'floating_ip' in net: floating_ip = net['floating_ip']

            # Stub for ip_address feature
            if 'ip_address' in net: ip_address = net['ip_address']

            if floating_ip:
                allocation_mode = "POOL"
            elif ip_address:
                allocation_mode = "MANUAL"
            else:
                allocation_mode = "DHCP"

            if not nic_type:
                for vms in vapp._get_vms():
                    vm_id = (vms.id).split(':')[-1]

                    url_rest_call = "{}/api/vApp/vm-{}/networkConnectionSection/".format(vca.host, vm_id)

                    response = Http.get(url=url_rest_call,
                                        headers=vca.vcloud_session.get_vcloud_headers(),
                                        verify=vca.verify,
                                        logger=vca.logger)
                    if response.status_code != 200:
                        self.logger.error("REST call {} failed reason : {}"\
                                             "status code : {}".format(url_rest_call,
                                                                    response.content,
                                                               response.status_code))
                        raise vimconn.vimconnException("add_network_adapter_to_vms : Failed to get "\
                                                                         "network connection section")

                    data = response.content
                    if '<PrimaryNetworkConnectionIndex>' not in data:
                        item = """<PrimaryNetworkConnectionIndex>{}</PrimaryNetworkConnectionIndex>
                                <NetworkConnection network="{}">
                                <NetworkConnectionIndex>{}</NetworkConnectionIndex>
                                <IsConnected>true</IsConnected>
                                <IpAddressAllocationMode>{}</IpAddressAllocationMode>
                                </NetworkConnection>""".format(primary_nic_index, network_name, nicIndex,
                                                                                         allocation_mode)
                        # Stub for ip_address feature
                        if ip_address:
                            ip_tag = '<IpAddress>{}</IpAddress>'.format(ip_address)
                            item =  item.replace('</NetworkConnectionIndex>\n','</NetworkConnectionIndex>\n{}\n'.format(ip_tag))

                        data = data.replace('</ovf:Info>\n','</ovf:Info>\n{}\n'.format(item))
                    else:
                        new_item = """<NetworkConnection network="{}">
                                    <NetworkConnectionIndex>{}</NetworkConnectionIndex>
                                    <IsConnected>true</IsConnected>
                                    <IpAddressAllocationMode>{}</IpAddressAllocationMode>
                                    </NetworkConnection>""".format(network_name, nicIndex,
                                                                          allocation_mode)
                        # Stub for ip_address feature
                        if ip_address:
                            ip_tag = '<IpAddress>{}</IpAddress>'.format(ip_address)
                            new_item =  new_item.replace('</NetworkConnectionIndex>\n','</NetworkConnectionIndex>\n{}\n'.format(ip_tag))

                        data = data.replace('</NetworkConnection>\n','</NetworkConnection>\n{}\n'.format(new_item))

                    headers = vca.vcloud_session.get_vcloud_headers()
                    headers['Content-Type'] = 'application/vnd.vmware.vcloud.networkConnectionSection+xml'
                    response = Http.put(url=url_rest_call, headers=headers, data=data,
                                                                   verify=vca.verify,
                                                                   logger=vca.logger)
                    if response.status_code != 202:
                        self.logger.error("REST call {} failed reason : {}"\
                                            "status code : {} ".format(url_rest_call,
                                                                    response.content,
                                                               response.status_code))
                        raise vimconn.vimconnException("add_network_adapter_to_vms : Failed to update "\
                                                                            "network connection section")
                    else:
                        nic_task = taskType.parseString(response.content, True)
                        if isinstance(nic_task, GenericTask):
                            vca.block_until_completed(nic_task)
                            self.logger.info("add_network_adapter_to_vms(): VM {} conneced to "\
                                                               "default NIC type".format(vm_id))
                        else:
                            self.logger.error("add_network_adapter_to_vms(): VM {} failed to "\
                                                              "connect NIC type".format(vm_id))
            else:
                for vms in vapp._get_vms():
                    vm_id = (vms.id).split(':')[-1]

                    url_rest_call = "{}/api/vApp/vm-{}/networkConnectionSection/".format(vca.host, vm_id)

                    response = Http.get(url=url_rest_call,
                                        headers=vca.vcloud_session.get_vcloud_headers(),
                                        verify=vca.verify,
                                        logger=vca.logger)
                    if response.status_code != 200:
                        self.logger.error("REST call {} failed reason : {}"\
                                            "status code : {}".format(url_rest_call,
                                                                   response.content,
                                                              response.status_code))
                        raise vimconn.vimconnException("add_network_adapter_to_vms : Failed to get "\
                                                                        "network connection section")
                    data = response.content
                    if '<PrimaryNetworkConnectionIndex>' not in data:
                        item = """<PrimaryNetworkConnectionIndex>{}</PrimaryNetworkConnectionIndex>
                                <NetworkConnection network="{}">
                                <NetworkConnectionIndex>{}</NetworkConnectionIndex>
                                <IsConnected>true</IsConnected>
                                <IpAddressAllocationMode>{}</IpAddressAllocationMode>
                                <NetworkAdapterType>{}</NetworkAdapterType>
                                </NetworkConnection>""".format(primary_nic_index, network_name, nicIndex,
                                                                               allocation_mode, nic_type)
                        # Stub for ip_address feature
                        if ip_address:
                            ip_tag = '<IpAddress>{}</IpAddress>'.format(ip_address)
                            item =  item.replace('</NetworkConnectionIndex>\n','</NetworkConnectionIndex>\n{}\n'.format(ip_tag))

                        data = data.replace('</ovf:Info>\n','</ovf:Info>\n{}\n'.format(item))
                    else:
                        new_item = """<NetworkConnection network="{}">
                                    <NetworkConnectionIndex>{}</NetworkConnectionIndex>
                                    <IsConnected>true</IsConnected>
                                    <IpAddressAllocationMode>{}</IpAddressAllocationMode>
                                    <NetworkAdapterType>{}</NetworkAdapterType>
                                    </NetworkConnection>""".format(network_name, nicIndex,
                                                                allocation_mode, nic_type)
                        # Stub for ip_address feature
                        if ip_address:
                            ip_tag = '<IpAddress>{}</IpAddress>'.format(ip_address)
                            new_item =  new_item.replace('</NetworkConnectionIndex>\n','</NetworkConnectionIndex>\n{}\n'.format(ip_tag))

                        data = data.replace('</NetworkConnection>\n','</NetworkConnection>\n{}\n'.format(new_item))

                    headers = vca.vcloud_session.get_vcloud_headers()
                    headers['Content-Type'] = 'application/vnd.vmware.vcloud.networkConnectionSection+xml'
                    response = Http.put(url=url_rest_call, headers=headers, data=data,
                                                                   verify=vca.verify,
                                                                   logger=vca.logger)

                    if response.status_code != 202:
                        self.logger.error("REST call {} failed reason : {}"\
                                            "status code : {}".format(url_rest_call,
                                                                   response.content,
                                                              response.status_code))
                        raise vimconn.vimconnException("add_network_adapter_to_vms : Failed to update "\
                                                                           "network connection section")
                    else:
                        nic_task = taskType.parseString(response.content, True)
                        if isinstance(nic_task, GenericTask):
                            vca.block_until_completed(nic_task)
                            self.logger.info("add_network_adapter_to_vms(): VM {} "\
                                               "conneced to NIC type {}".format(vm_id, nic_type))
                        else:
                            self.logger.error("add_network_adapter_to_vms(): VM {} "\
                                               "failed to connect NIC type {}".format(vm_id, nic_type))
        except Exception as exp:
            self.logger.error("add_network_adapter_to_vms() : exception occurred "\
                                               "while adding Network adapter")
            raise vimconn.vimconnException(message=exp)


    def set_numa_affinity(self, vmuuid, paired_threads_id):
        """
            Method to assign numa affinity in vm configuration parammeters
            Args :
                vmuuid - vm uuid
                paired_threads_id - one or more virtual processor
                                    numbers
            Returns:
                return if True
        """
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

                    host_obj, vm_obj = self.get_vm_obj(content ,vm_moref_id)
                    if vm_obj:
                        config_spec = vim.vm.ConfigSpec()
                        config_spec.extraConfig = []
                        opt = vim.option.OptionValue()
                        opt.key = 'numa.nodeAffinity'
                        opt.value = str(paired_threads_id)
                        config_spec.extraConfig.append(opt)
                        task = vm_obj.ReconfigVM_Task(config_spec)
                        if task:
                            result = self.wait_for_vcenter_task(task, vcenter_conect)
                            extra_config = vm_obj.config.extraConfig
                            flag = False
                            for opts in extra_config:
                                if 'numa.nodeAffinity' in opts.key:
                                    flag = True
                                    self.logger.info("set_numa_affinity: Sucessfully assign numa affinity "\
                                                             "value {} for vm {}".format(opt.value, vm_obj))
                            if flag:
                                return
                    else:
                        self.logger.error("set_numa_affinity: Failed to assign numa affinity")
        except Exception as exp:
            self.logger.error("set_numa_affinity : exception occurred while setting numa affinity "\
                                                       "for VM {} : {}".format(vm_obj, vm_moref_id))
            raise vimconn.vimconnException("set_numa_affinity : Error {} failed to assign numa "\
                                                                           "affinity".format(exp))



    def cloud_init(self, vapp, cloud_config):
        """
        Method to inject ssh-key
        vapp - vapp object
        cloud_config a dictionary with:
                'key-pairs': (optional) list of strings with the public key to be inserted to the default user
                'users': (optional) list of users to be inserted, each item is a dict with:
                    'name': (mandatory) user name,
                    'key-pairs': (optional) list of strings with the public key to be inserted to the user
                'user-data': (optional) string is a text script to be passed directly to cloud-init
                'config-files': (optional). List of files to be transferred. Each item is a dict with:
                    'dest': (mandatory) string with the destination absolute path
                    'encoding': (optional, by default text). Can be one of:
                        'b64', 'base64', 'gz', 'gz+b64', 'gz+base64', 'gzip+b64', 'gzip+base64'
                    'content' (mandatory): string with the content of the file
                    'permissions': (optional) string with file permissions, typically octal notation '0644'
                    'owner': (optional) file owner, string with the format 'owner:group'
                'boot-data-drive': boolean to indicate if user-data must be passed using a boot drive (hard disk
        """
        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("Failed to connect vCloud director")

        try:
            if isinstance(cloud_config, dict):
                key_pairs = []
                userdata = []
                if "key-pairs" in cloud_config:
                    key_pairs = cloud_config["key-pairs"]

                if "users" in cloud_config:
                    userdata = cloud_config["users"]

            for key in key_pairs:
                for user in userdata:
                    if 'name' in user: user_name = user['name']
                    if 'key-pairs' in user and len(user['key-pairs']) > 0:
                        for user_key in user['key-pairs']:
                            customize_script = """
                        #!/bin/bash
                        echo performing customization tasks with param $1 at `date "+DATE: %Y-%m-%d - TIME: %H:%M:%S"` >> /root/customization.log
                        if [ "$1" = "precustomization" ];then
                            echo performing precustomization tasks   on `date "+DATE: %Y-%m-%d - TIME: %H:%M:%S"` >> /root/customization.log
                            if [ ! -d /root/.ssh ];then
                                mkdir /root/.ssh
                                chown root:root /root/.ssh
                                chmod 700 /root/.ssh
                                touch /root/.ssh/authorized_keys
                                chown root:root /root/.ssh/authorized_keys
                                chmod 600 /root/.ssh/authorized_keys
                                # make centos with selinux happy
                                which restorecon && restorecon -Rv /root/.ssh
                                echo '{key}' >> /root/.ssh/authorized_keys
                            else
                                touch /root/.ssh/authorized_keys
                                chown root:root /root/.ssh/authorized_keys
                                chmod 600 /root/.ssh/authorized_keys
                                echo '{key}' >> /root/.ssh/authorized_keys
                            fi
                            if [ -d /home/{user_name} ];then
                                if [ ! -d /home/{user_name}/.ssh ];then
                                    mkdir /home/{user_name}/.ssh
                                    chown {user_name}:{user_name} /home/{user_name}/.ssh
                                    chmod 700 /home/{user_name}/.ssh
                                    touch /home/{user_name}/.ssh/authorized_keys
                                    chown {user_name}:{user_name} /home/{user_name}/.ssh/authorized_keys
                                    chmod 600 /home/{user_name}/.ssh/authorized_keys
                                    # make centos with selinux happy
                                    which restorecon && restorecon -Rv /home/{user_name}/.ssh
                                    echo '{user_key}' >> /home/{user_name}/.ssh/authorized_keys
                                else
                                    touch /home/{user_name}/.ssh/authorized_keys
                                    chown {user_name}:{user_name} /home/{user_name}/.ssh/authorized_keys
                                    chmod 600 /home/{user_name}/.ssh/authorized_keys
                                    echo '{user_key}' >> /home/{user_name}/.ssh/authorized_keys
                                fi
                            fi
                        fi""".format(key=key, user_name=user_name, user_key=user_key)

                            for vm in vapp._get_vms():
                                vm_name = vm.name
                                task = vapp.customize_guest_os(vm_name, customization_script=customize_script)
                                if isinstance(task, GenericTask):
                                    vca.block_until_completed(task)
                                    self.logger.info("cloud_init : customized guest os task "\
                                                        "completed for VM {}".format(vm_name))
                                else:
                                    self.logger.error("cloud_init : task for customized guest os"\
                                                               "failed for VM {}".format(vm_name))
        except Exception as exp:
            self.logger.error("cloud_init : exception occurred while injecting "\
                                                                       "ssh-key")
            raise vimconn.vimconnException("cloud_init : Error {} failed to inject "\
                                                               "ssh-key".format(exp))


    def add_new_disk(self, vca, vapp_uuid, disk_size):
        """
            Method to create an empty vm disk

            Args:
                vapp_uuid - is vapp identifier.
                disk_size - size of disk to be created in GB

            Returns:
                None
        """
        status = False
        vm_details = None
        try:
            #Disk size in GB, convert it into MB
            if disk_size is not None:
                disk_size_mb = int(disk_size) * 1024
                vm_details = self.get_vapp_details_rest(vapp_uuid)

            if vm_details and "vm_virtual_hardware" in vm_details:
                self.logger.info("Adding disk to VM: {} disk size:{}GB".format(vm_details["name"], disk_size))
                disk_href = vm_details["vm_virtual_hardware"]["disk_edit_href"]
                status = self.add_new_disk_rest(vca, disk_href, disk_size_mb)

        except Exception as exp:
            msg = "Error occurred while creating new disk {}.".format(exp)
            self.rollback_newvm(vapp_uuid, msg)

        if status:
            self.logger.info("Added new disk to VM: {} disk size:{}GB".format(vm_details["name"], disk_size))
        else:
            #If failed to add disk, delete VM
            msg = "add_new_disk: Failed to add new disk to {}".format(vm_details["name"])
            self.rollback_newvm(vapp_uuid, msg)


    def add_new_disk_rest(self, vca, disk_href, disk_size_mb):
        """
        Retrives vApp Disks section & add new empty disk

        Args:
            disk_href: Disk section href to addd disk
            disk_size_mb: Disk size in MB

            Returns: Status of add new disk task
        """
        status = False
        if vca.vcloud_session and vca.vcloud_session.organization:
            response = Http.get(url=disk_href,
                                headers=vca.vcloud_session.get_vcloud_headers(),
                                verify=vca.verify,
                                logger=vca.logger)

        if response.status_code != requests.codes.ok:
            self.logger.error("add_new_disk_rest: GET REST API call {} failed. Return status code {}"
                              .format(disk_href, response.status_code))
            return status
        try:
            #Find but type & max of instance IDs assigned to disks
            lxmlroot_respond = lxmlElementTree.fromstring(response.content)
            namespaces = {prefix:uri for prefix,uri in lxmlroot_respond.nsmap.iteritems() if prefix}
            namespaces["xmlns"]= "http://www.vmware.com/vcloud/v1.5"
            instance_id = 0
            for item in lxmlroot_respond.iterfind('xmlns:Item',namespaces):
                if item.find("rasd:Description",namespaces).text == "Hard disk":
                    inst_id = int(item.find("rasd:InstanceID" ,namespaces).text)
                    if inst_id > instance_id:
                        instance_id = inst_id
                        disk_item = item.find("rasd:HostResource" ,namespaces)
                        bus_subtype = disk_item.attrib["{"+namespaces['xmlns']+"}busSubType"]
                        bus_type = disk_item.attrib["{"+namespaces['xmlns']+"}busType"]

            instance_id = instance_id + 1
            new_item =   """<Item>
                                <rasd:Description>Hard disk</rasd:Description>
                                <rasd:ElementName>New disk</rasd:ElementName>
                                <rasd:HostResource
                                    xmlns:vcloud="http://www.vmware.com/vcloud/v1.5"
                                    vcloud:capacity="{}"
                                    vcloud:busSubType="{}"
                                    vcloud:busType="{}"></rasd:HostResource>
                                <rasd:InstanceID>{}</rasd:InstanceID>
                                <rasd:ResourceType>17</rasd:ResourceType>
                            </Item>""".format(disk_size_mb, bus_subtype, bus_type, instance_id)

            new_data = response.content
            #Add new item at the bottom
            new_data = new_data.replace('</Item>\n</RasdItemsList>', '</Item>\n{}\n</RasdItemsList>'.format(new_item))

            # Send PUT request to modify virtual hardware section with new disk
            headers = vca.vcloud_session.get_vcloud_headers()
            headers['Content-Type'] = 'application/vnd.vmware.vcloud.rasdItemsList+xml; charset=ISO-8859-1'

            response = Http.put(url=disk_href,
                                data=new_data,
                                headers=headers,
                                verify=vca.verify, logger=self.logger)

            if response.status_code != 202:
                self.logger.error("PUT REST API call {} failed. Return status code {}. Response Content:{}"
                                  .format(disk_href, response.status_code, response.content))
            else:
                add_disk_task = taskType.parseString(response.content, True)
                if type(add_disk_task) is GenericTask:
                    status = vca.block_until_completed(add_disk_task)
                    if not status:
                        self.logger.error("Add new disk REST task failed to add {} MB disk".format(disk_size_mb))

        except Exception as exp:
            self.logger.error("Error occurred calling rest api for creating new disk {}".format(exp))

        return status


    def add_existing_disk(self, catalogs=None, image_id=None, size=None, template_name=None, vapp_uuid=None):
        """
            Method to add existing disk to vm
            Args :
                catalogs - List of VDC catalogs
                image_id - Catalog ID
                template_name - Name of template in catalog
                vapp_uuid - UUID of vApp
            Returns:
                None
        """
        disk_info = None
        vcenter_conect, content = self.get_vcenter_content()
        #find moref-id of vm in image
        catalog_vm_info = self.get_vapp_template_details(catalogs=catalogs,
                                                         image_id=image_id,
                                                        )

        if catalog_vm_info and "vm_vcenter_info" in catalog_vm_info:
            if "vm_moref_id" in catalog_vm_info["vm_vcenter_info"]:
                catalog_vm_moref_id = catalog_vm_info["vm_vcenter_info"].get("vm_moref_id", None)
                if catalog_vm_moref_id:
                    self.logger.info("Moref_id of VM in catalog : {}" .format(catalog_vm_moref_id))
                    host, catalog_vm_obj = self.get_vm_obj(content, catalog_vm_moref_id)
                    if catalog_vm_obj:
                        #find existing disk
                        disk_info = self.find_disk(catalog_vm_obj)
                    else:
                        exp_msg = "No VM with image id {} found".format(image_id)
                        self.rollback_newvm(vapp_uuid, exp_msg, exp_type="NotFound")
        else:
            exp_msg = "No Image found with image ID {} ".format(image_id)
            self.rollback_newvm(vapp_uuid, exp_msg, exp_type="NotFound")

        if disk_info:
            self.logger.info("Existing disk_info : {}".format(disk_info))
            #get VM
            vm_moref_id = self.get_vm_moref_id(vapp_uuid)
            host, vm_obj = self.get_vm_obj(content, vm_moref_id)
            if vm_obj:
                status = self.add_disk(vcenter_conect=vcenter_conect,
                                       vm=vm_obj,
                                       disk_info=disk_info,
                                       size=size,
                                       vapp_uuid=vapp_uuid
                                       )
            if status:
                self.logger.info("Disk from image id {} added to {}".format(image_id,
                                                                            vm_obj.config.name)
                                 )
        else:
            msg = "No disk found with image id {} to add in VM {}".format(
                                                            image_id,
                                                            vm_obj.config.name)
            self.rollback_newvm(vapp_uuid, msg, exp_type="NotFound")


    def find_disk(self, vm_obj):
        """
         Method to find details of existing disk in VM
            Args :
                vm_obj - vCenter object of VM
                image_id - Catalog ID
            Returns:
                disk_info : dict of disk details
        """
        disk_info = {}
        if vm_obj:
            try:
                devices = vm_obj.config.hardware.device
                for device in devices:
                    if type(device) is vim.vm.device.VirtualDisk:
                        if isinstance(device.backing,vim.vm.device.VirtualDisk.FlatVer2BackingInfo) and hasattr(device.backing, 'fileName'):
                            disk_info["full_path"] = device.backing.fileName
                            disk_info["datastore"] = device.backing.datastore
                            disk_info["capacityKB"] = device.capacityInKB
                            break
            except Exception as exp:
                self.logger.error("find_disk() : exception occurred while "\
                                  "getting existing disk details :{}".format(exp))
        return disk_info


    def add_disk(self, vcenter_conect=None, vm=None, size=None, vapp_uuid=None, disk_info={}):
        """
         Method to add existing disk in VM
            Args :
                vcenter_conect - vCenter content object
                vm - vCenter vm object
                disk_info : dict of disk details
            Returns:
                status : status of add disk task
        """
        datastore = disk_info["datastore"] if "datastore" in disk_info else None
        fullpath = disk_info["full_path"] if "full_path" in disk_info else None
        capacityKB = disk_info["capacityKB"] if "capacityKB" in disk_info else None
        if size is not None:
            #Convert size from GB to KB
            sizeKB = int(size) * 1024 * 1024
            #compare size of existing disk and user given size.Assign whicherver is greater
            self.logger.info("Add Existing disk : sizeKB {} , capacityKB {}".format(
                                                                    sizeKB, capacityKB))
            if sizeKB > capacityKB:
                capacityKB = sizeKB

        if datastore and fullpath and capacityKB:
            try:
                spec = vim.vm.ConfigSpec()
                # get all disks on a VM, set unit_number to the next available
                unit_number = 0
                for dev in vm.config.hardware.device:
                    if hasattr(dev.backing, 'fileName'):
                        unit_number = int(dev.unitNumber) + 1
                        # unit_number 7 reserved for scsi controller
                        if unit_number == 7:
                            unit_number += 1
                    if isinstance(dev, vim.vm.device.VirtualDisk):
                        #vim.vm.device.VirtualSCSIController
                        controller_key = dev.controllerKey

                self.logger.info("Add Existing disk : unit number {} , controller key {}".format(
                                                                    unit_number, controller_key))
                # add disk here
                dev_changes = []
                disk_spec = vim.vm.device.VirtualDeviceSpec()
                disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
                disk_spec.device = vim.vm.device.VirtualDisk()
                disk_spec.device.backing = \
                    vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
                disk_spec.device.backing.thinProvisioned = True
                disk_spec.device.backing.diskMode = 'persistent'
                disk_spec.device.backing.datastore  = datastore
                disk_spec.device.backing.fileName  = fullpath

                disk_spec.device.unitNumber = unit_number
                disk_spec.device.capacityInKB = capacityKB
                disk_spec.device.controllerKey = controller_key
                dev_changes.append(disk_spec)
                spec.deviceChange = dev_changes
                task = vm.ReconfigVM_Task(spec=spec)
                status = self.wait_for_vcenter_task(task, vcenter_conect)
                return status
            except Exception as exp:
                exp_msg = "add_disk() : exception {} occurred while adding disk "\
                          "{} to vm {}".format(exp,
                                               fullpath,
                                               vm.config.name)
                self.rollback_newvm(vapp_uuid, exp_msg)
        else:
            msg = "add_disk() : Can not add disk to VM with disk info {} ".format(disk_info)
            self.rollback_newvm(vapp_uuid, msg)


    def get_vcenter_content(self):
        """
         Get the vsphere content object
        """
        try:
            vm_vcenter_info = self.get_vm_vcenter_info()
        except Exception as exp:
            self.logger.error("Error occurred while getting vCenter infromationn"\
                             " for VM : {}".format(exp))
            raise vimconn.vimconnException(message=exp)

        context = None
        if hasattr(ssl, '_create_unverified_context'):
            context = ssl._create_unverified_context()

        vcenter_conect = SmartConnect(
                    host=vm_vcenter_info["vm_vcenter_ip"],
                    user=vm_vcenter_info["vm_vcenter_user"],
                    pwd=vm_vcenter_info["vm_vcenter_password"],
                    port=int(vm_vcenter_info["vm_vcenter_port"]),
                    sslContext=context
                )
        atexit.register(Disconnect, vcenter_conect)
        content = vcenter_conect.RetrieveContent()
        return vcenter_conect, content


    def get_vm_moref_id(self, vapp_uuid):
        """
        Get the moref_id of given VM
        """
        try:
            if vapp_uuid:
                vm_details = self.get_vapp_details_rest(vapp_uuid, need_admin_access=True)
                if vm_details and "vm_vcenter_info" in vm_details:
                    vm_moref_id = vm_details["vm_vcenter_info"].get("vm_moref_id", None)

            return vm_moref_id

        except Exception as exp:
            self.logger.error("Error occurred while getting VM moref ID "\
                             " for VM : {}".format(exp))
            return None


    def get_vapp_template_details(self, catalogs=None, image_id=None , template_name=None):
        """
            Method to get vApp template details
                Args :
                    catalogs - list of VDC catalogs
                    image_id - Catalog ID to find
                    template_name : template name in catalog
                Returns:
                    parsed_respond : dict of vApp tempalte details
        """
        parsed_response = {}

        vca = self.connect_as_admin()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")

        try:
            catalog = self.get_catalog_obj(image_id, catalogs)
            if catalog:
                template_name = self.get_catalogbyid(image_id, catalogs)
                catalog_items = filter(lambda catalogItemRef: catalogItemRef.get_name() == template_name, catalog.get_CatalogItems().get_CatalogItem())
                if len(catalog_items) == 1:
                    response = Http.get(catalog_items[0].get_href(),
                                        headers=vca.vcloud_session.get_vcloud_headers(),
                                        verify=vca.verify,
                                        logger=vca.logger)
                    catalogItem = XmlElementTree.fromstring(response.content)
                    entity = [child for child in catalogItem if child.get("type") == "application/vnd.vmware.vcloud.vAppTemplate+xml"][0]
                    vapp_tempalte_href = entity.get("href")
                    #get vapp details and parse moref id

                    namespaces = {"vssd":"http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData" ,
                                  'ovf': 'http://schemas.dmtf.org/ovf/envelope/1',
                                  'vmw': 'http://www.vmware.com/schema/ovf',
                                  'vm': 'http://www.vmware.com/vcloud/v1.5',
                                  'rasd':"http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData",
                                  'vmext':"http://www.vmware.com/vcloud/extension/v1.5",
                                  'xmlns':"http://www.vmware.com/vcloud/v1.5"
                                }

                    if vca.vcloud_session and vca.vcloud_session.organization:
                        response = Http.get(url=vapp_tempalte_href,
                                            headers=vca.vcloud_session.get_vcloud_headers(),
                                            verify=vca.verify,
                                            logger=vca.logger
                                            )

                        if response.status_code != requests.codes.ok:
                            self.logger.debug("REST API call {} failed. Return status code {}".format(
                                                vapp_tempalte_href, response.status_code))

                        else:
                            xmlroot_respond = XmlElementTree.fromstring(response.content)
                            children_section = xmlroot_respond.find('vm:Children/', namespaces)
                            if children_section is not None:
                                vCloud_extension_section = children_section.find('xmlns:VCloudExtension', namespaces)
                            if vCloud_extension_section is not None:
                                vm_vcenter_info = {}
                                vim_info = vCloud_extension_section.find('vmext:VmVimInfo', namespaces)
                                vmext = vim_info.find('vmext:VmVimObjectRef', namespaces)
                                if vmext is not None:
                                    vm_vcenter_info["vm_moref_id"] = vmext.find('vmext:MoRef', namespaces).text
                                parsed_response["vm_vcenter_info"]= vm_vcenter_info

        except Exception as exp :
            self.logger.info("Error occurred calling rest api for getting vApp details {}".format(exp))

        return parsed_response


    def rollback_newvm(self, vapp_uuid, msg , exp_type="Genric"):
        """
            Method to delete vApp
                Args :
                    vapp_uuid - vApp UUID
                    msg - Error message to be logged
                    exp_type : Exception type
                Returns:
                    None
        """
        if vapp_uuid:
            status = self.delete_vminstance(vapp_uuid)
        else:
            msg = "No vApp ID"
        self.logger.error(msg)
        if exp_type == "Genric":
            raise vimconn.vimconnException(msg)
        elif exp_type == "NotFound":
            raise vimconn.vimconnNotFoundException(message=msg)

    def add_sriov(self, vapp_uuid, sriov_nets, vmname_andid):
        """
            Method to attach SRIOV adapters to VM

             Args:
                vapp_uuid - uuid of vApp/VM
                sriov_nets - SRIOV devices infromation as specified in VNFD (flavor)
                vmname_andid - vmname

            Returns:
                The status of add SRIOV adapter task , vm object and
                vcenter_conect object
        """
        vm_obj = None
        vcenter_conect, content = self.get_vcenter_content()
        vm_moref_id = self.get_vm_moref_id(vapp_uuid)

        if vm_moref_id:
            try:
                no_of_sriov_devices = len(sriov_nets)
                if no_of_sriov_devices > 0:
                    #Get VM and its host
                    host_obj, vm_obj = self.get_vm_obj(content, vm_moref_id)
                    self.logger.info("VM {} is currently on host {}".format(vm_obj, host_obj))
                    if host_obj and vm_obj:
                        #get SRIOV devies from host on which vapp is currently installed
                        avilable_sriov_devices = self.get_sriov_devices(host_obj,
                                                                no_of_sriov_devices,
                                                                )

                        if len(avilable_sriov_devices) == 0:
                            #find other hosts with active pci devices
                            new_host_obj , avilable_sriov_devices = self.get_host_and_sriov_devices(
                                                                content,
                                                                no_of_sriov_devices,
                                                                )

                            if new_host_obj is not None and len(avilable_sriov_devices)> 0:
                                #Migrate vm to the host where SRIOV devices are available
                                self.logger.info("Relocate VM {} on new host {}".format(vm_obj,
                                                                                    new_host_obj))
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

                        if host_obj is not None and avilable_sriov_devices is not None and len(avilable_sriov_devices)> 0:
                            #Add SRIOV devices one by one
                            for sriov_net in sriov_nets:
                                network_name = sriov_net.get('net_id')
                                dvs_portgr_name = self.create_dvPort_group(network_name)
                                if sriov_net.get('type') == "VF":
                                    #add vlan ID ,Modify portgroup for vlan ID
                                    self.configure_vlanID(content, vcenter_conect, network_name)

                                task = self.add_sriov_to_vm(content,
                                                            vm_obj,
                                                            host_obj,
                                                            network_name,
                                                            avilable_sriov_devices[0]
                                                            )
                                if task:
                                    status= self.wait_for_vcenter_task(task, vcenter_conect)
                                    if status:
                                        self.logger.info("Added SRIOV {} to VM {}".format(
                                                                        no_of_sriov_devices,
                                                                        str(vm_obj)))
                                else:
                                    self.logger.error("Fail to add SRIOV {} to VM {}".format(
                                                                        no_of_sriov_devices,
                                                                        str(vm_obj)))
                                    raise vimconn.vimconnUnexpectedResponse(
                                    "Fail to add SRIOV adapter in VM ".format(str(vm_obj))
                                        )
                            return True, vm_obj, vcenter_conect
                        else:
                            self.logger.error("Currently there is no host with"\
                                              " {} number of avaialble SRIOV "\
                                              "VFs required for VM {}".format(
                                                                no_of_sriov_devices,
                                                                vmname_andid)
                                              )
                            raise vimconn.vimconnNotFoundException(
                                    "Currently there is no host with {} "\
                                    "number of avaialble SRIOV devices required for VM {}".format(
                                                                            no_of_sriov_devices,
                                                                            vmname_andid))
                else:
                    self.logger.debug("No infromation about SRIOV devices {} ",sriov_nets)

            except vmodl.MethodFault as error:
                self.logger.error("Error occurred while adding SRIOV {} ",error)
        return None, vm_obj, vcenter_conect


    def get_sriov_devices(self,host, no_of_vfs):
        """
            Method to get the details of SRIOV devices on given host
             Args:
                host - vSphere host object
                no_of_vfs - number of VFs needed on host

             Returns:
                array of SRIOV devices
        """
        sriovInfo=[]
        if host:
            for device in host.config.pciPassthruInfo:
                if isinstance(device,vim.host.SriovInfo) and device.sriovActive:
                    if device.numVirtualFunction >= no_of_vfs:
                        sriovInfo.append(device)
                        break
        return sriovInfo


    def get_host_and_sriov_devices(self, content, no_of_vfs):
        """
         Method to get the details of SRIOV devices infromation on all hosts

            Args:
                content - vSphere host object
                no_of_vfs - number of pci VFs needed on host

            Returns:
                 array of SRIOV devices and host object
        """
        host_obj = None
        sriov_device_objs = None
        try:
            if content:
                container = content.viewManager.CreateContainerView(content.rootFolder,
                                                            [vim.HostSystem], True)
                for host in container.view:
                    devices = self.get_sriov_devices(host, no_of_vfs)
                    if devices:
                        host_obj = host
                        sriov_device_objs = devices
                        break
        except Exception as exp:
            self.logger.error("Error {} occurred while finding SRIOV devices on host: {}".format(exp, host_obj))

        return host_obj,sriov_device_objs


    def add_sriov_to_vm(self,content, vm_obj, host_obj, network_name, sriov_device):
        """
         Method to add SRIOV adapter to vm

            Args:
                host_obj - vSphere host object
                vm_obj - vSphere vm object
                content - vCenter content object
                network_name - name of distributed virtaul portgroup
                sriov_device - SRIOV device info

            Returns:
                 task object
        """
        devices = []
        vnic_label = "sriov nic"
        try:
            dvs_portgr = self.get_dvport_group(network_name)
            network_name = dvs_portgr.name
            nic = vim.vm.device.VirtualDeviceSpec()
            # VM device
            nic.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
            nic.device = vim.vm.device.VirtualSriovEthernetCard()
            nic.device.addressType = 'assigned'
            #nic.device.key = 13016
            nic.device.deviceInfo = vim.Description()
            nic.device.deviceInfo.label = vnic_label
            nic.device.deviceInfo.summary = network_name
            nic.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()

            nic.device.backing.network = self.get_obj(content, [vim.Network], network_name)
            nic.device.backing.deviceName = network_name
            nic.device.backing.useAutoDetect = False
            nic.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
            nic.device.connectable.startConnected = True
            nic.device.connectable.allowGuestControl = True

            nic.device.sriovBacking = vim.vm.device.VirtualSriovEthernetCard.SriovBackingInfo()
            nic.device.sriovBacking.physicalFunctionBacking = vim.vm.device.VirtualPCIPassthrough.DeviceBackingInfo()
            nic.device.sriovBacking.physicalFunctionBacking.id = sriov_device.id

            devices.append(nic)
            vmconf = vim.vm.ConfigSpec(deviceChange=devices)
            task = vm_obj.ReconfigVM_Task(vmconf)
            return task
        except Exception as exp:
            self.logger.error("Error {} occurred while adding SRIOV adapter in VM: {}".format(exp, vm_obj))
            return None


    def create_dvPort_group(self, network_name):
        """
         Method to create disributed virtual portgroup

            Args:
                network_name - name of network/portgroup

            Returns:
                portgroup key
        """
        try:
            new_network_name = [network_name, '-', str(uuid.uuid4())]
            network_name=''.join(new_network_name)
            vcenter_conect, content = self.get_vcenter_content()

            dv_switch = self.get_obj(content, [vim.DistributedVirtualSwitch], self.dvs_name)
            if dv_switch:
                dv_pg_spec = vim.dvs.DistributedVirtualPortgroup.ConfigSpec()
                dv_pg_spec.name = network_name

                dv_pg_spec.type = vim.dvs.DistributedVirtualPortgroup.PortgroupType.earlyBinding
                dv_pg_spec.defaultPortConfig = vim.dvs.VmwareDistributedVirtualSwitch.VmwarePortConfigPolicy()
                dv_pg_spec.defaultPortConfig.securityPolicy = vim.dvs.VmwareDistributedVirtualSwitch.SecurityPolicy()
                dv_pg_spec.defaultPortConfig.securityPolicy.allowPromiscuous = vim.BoolPolicy(value=False)
                dv_pg_spec.defaultPortConfig.securityPolicy.forgedTransmits = vim.BoolPolicy(value=False)
                dv_pg_spec.defaultPortConfig.securityPolicy.macChanges = vim.BoolPolicy(value=False)

                task = dv_switch.AddDVPortgroup_Task([dv_pg_spec])
                self.wait_for_vcenter_task(task, vcenter_conect)

                dvPort_group = self.get_obj(content, [vim.dvs.DistributedVirtualPortgroup], network_name)
                if dvPort_group:
                    self.logger.info("Created disributed virtaul port group: {}".format(dvPort_group))
                    return dvPort_group.key
            else:
                self.logger.debug("No disributed virtual switch found with name {}".format(network_name))

        except Exception as exp:
            self.logger.error("Error occurred while creating disributed virtaul port group {}"\
                             " : {}".format(network_name, exp))
        return None

    def reconfig_portgroup(self, content, dvPort_group_name , config_info={}):
        """
         Method to reconfigure disributed virtual portgroup

            Args:
                dvPort_group_name - name of disributed virtual portgroup
                content - vCenter content object
                config_info - disributed virtual portgroup configuration

            Returns:
                task object
        """
        try:
            dvPort_group = self.get_dvport_group(dvPort_group_name)
            if dvPort_group:
                dv_pg_spec = vim.dvs.DistributedVirtualPortgroup.ConfigSpec()
                dv_pg_spec.configVersion = dvPort_group.config.configVersion
                dv_pg_spec.defaultPortConfig = vim.dvs.VmwareDistributedVirtualSwitch.VmwarePortConfigPolicy()
                if "vlanID" in config_info:
                    dv_pg_spec.defaultPortConfig.vlan = vim.dvs.VmwareDistributedVirtualSwitch.VlanIdSpec()
                    dv_pg_spec.defaultPortConfig.vlan.vlanId = config_info.get('vlanID')

                task = dvPort_group.ReconfigureDVPortgroup_Task(spec=dv_pg_spec)
                return task
            else:
                return None
        except Exception as exp:
            self.logger.error("Error occurred while reconfiguraing disributed virtaul port group {}"\
                             " : {}".format(dvPort_group_name, exp))
            return None


    def destroy_dvport_group(self , dvPort_group_name):
        """
         Method to destroy disributed virtual portgroup

            Args:
                network_name - name of network/portgroup

            Returns:
                True if portgroup successfully got deleted else false
        """
        vcenter_conect, content = self.get_vcenter_content()
        try:
            status = None
            dvPort_group = self.get_dvport_group(dvPort_group_name)
            if dvPort_group:
                task = dvPort_group.Destroy_Task()
                status = self.wait_for_vcenter_task(task, vcenter_conect)
            return status
        except vmodl.MethodFault as exp:
            self.logger.error("Caught vmodl fault {} while deleting disributed virtaul port group {}".format(
                                                                    exp, dvPort_group_name))
            return None


    def get_dvport_group(self, dvPort_group_name):
        """
        Method to get disributed virtual portgroup

            Args:
                network_name - name of network/portgroup

            Returns:
                portgroup object
        """
        vcenter_conect, content = self.get_vcenter_content()
        dvPort_group = None
        try:
            container = content.viewManager.CreateContainerView(content.rootFolder, [vim.dvs.DistributedVirtualPortgroup], True)
            for item in container.view:
                if item.key == dvPort_group_name:
                    dvPort_group = item
                    break
            return dvPort_group
        except vmodl.MethodFault as exp:
            self.logger.error("Caught vmodl fault {} for disributed virtaul port group {}".format(
                                                                            exp, dvPort_group_name))
            return None

    def get_vlanID_from_dvs_portgr(self, dvPort_group_name):
        """
         Method to get disributed virtual portgroup vlanID

            Args:
                network_name - name of network/portgroup

            Returns:
                vlan ID
        """
        vlanId = None
        try:
            dvPort_group = self.get_dvport_group(dvPort_group_name)
            if dvPort_group:
                vlanId = dvPort_group.config.defaultPortConfig.vlan.vlanId
        except vmodl.MethodFault as exp:
            self.logger.error("Caught vmodl fault {} for disributed virtaul port group {}".format(
                                                                            exp, dvPort_group_name))
        return vlanId


    def configure_vlanID(self, content, vcenter_conect, dvPort_group_name):
        """
         Method to configure vlanID in disributed virtual portgroup vlanID

            Args:
                network_name - name of network/portgroup

            Returns:
                None
        """
        vlanID = self.get_vlanID_from_dvs_portgr(dvPort_group_name)
        if vlanID == 0:
            #configure vlanID
            vlanID = self.genrate_vlanID(dvPort_group_name)
            config = {"vlanID":vlanID}
            task = self.reconfig_portgroup(content, dvPort_group_name,
                                    config_info=config)
            if task:
                status= self.wait_for_vcenter_task(task, vcenter_conect)
                if status:
                    self.logger.info("Reconfigured Port group {} for vlan ID {}".format(
                                                        dvPort_group_name,vlanID))
            else:
                self.logger.error("Fail reconfigure portgroup {} for vlanID{}".format(
                                        dvPort_group_name, vlanID))


    def genrate_vlanID(self, network_name):
        """
         Method to get unused vlanID
            Args:
                network_name - name of network/portgroup
            Returns:
                vlanID
        """
        vlan_id = None
        used_ids = []
        if self.config.get('vlanID_range') == None:
            raise vimconn.vimconnConflictException("You must provide a 'vlanID_range' "\
                        "at config value before creating sriov network with vlan tag")
        if "used_vlanIDs" not in self.persistent_info:
                self.persistent_info["used_vlanIDs"] = {}
        else:
            used_ids = self.persistent_info["used_vlanIDs"].values()

        for vlanID_range in self.config.get('vlanID_range'):
            start_vlanid , end_vlanid = vlanID_range.split("-")
            if start_vlanid > end_vlanid:
                raise vimconn.vimconnConflictException("Invalid vlan ID range {}".format(
                                                                        vlanID_range))

            for id in xrange(int(start_vlanid), int(end_vlanid) + 1):
                if id not in used_ids:
                    vlan_id = id
                    self.persistent_info["used_vlanIDs"][network_name] = vlan_id
                    return vlan_id
        if vlan_id is None:
            raise vimconn.vimconnConflictException("All Vlan IDs are in use")


    def get_obj(self, content, vimtype, name):
        """
         Get the vsphere object associated with a given text name
        """
        obj = None
        container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
        for item in container.view:
            if item.name == name:
                obj = item
                break
        return obj


    def insert_media_to_vm(self, vapp, image_id):
        """
        Method to insert media CD-ROM (ISO image) from catalog to vm.
        vapp - vapp object to get vm id
        Image_id - image id for cdrom to be inerted to vm
        """
        # create connection object
        vca = self.connect()
        try:
            # fetching catalog details
            rest_url = "{}/api/catalog/{}".format(vca.host,image_id)
            response = Http.get(url=rest_url,
                                headers=vca.vcloud_session.get_vcloud_headers(),
                                verify=vca.verify,
                                logger=vca.logger)

            if response.status_code != 200:
                self.logger.error("REST call {} failed reason : {}"\
                             "status code : {}".format(url_rest_call,
                                                    response.content,
                                               response.status_code))
                raise vimconn.vimconnException("insert_media_to_vm(): Failed to get "\
                                                                    "catalog details")
            # searching iso name and id
            iso_name,media_id = self.get_media_details(vca, response.content)

            if iso_name and media_id:
                data ="""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                     <ns6:MediaInsertOrEjectParams
                     xmlns="http://www.vmware.com/vcloud/versions" xmlns:ns2="http://schemas.dmtf.org/ovf/envelope/1" xmlns:ns3="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData" xmlns:ns4="http://schemas.dmtf.org/wbem/wscim/1/common" xmlns:ns5="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData" xmlns:ns6="http://www.vmware.com/vcloud/v1.5" xmlns:ns7="http://www.vmware.com/schema/ovf" xmlns:ns8="http://schemas.dmtf.org/ovf/environment/1" xmlns:ns9="http://www.vmware.com/vcloud/extension/v1.5">
                     <ns6:Media
                        type="application/vnd.vmware.vcloud.media+xml"
                        name="{}.iso"
                        id="urn:vcloud:media:{}"
                        href="https://{}/api/media/{}"/>
                     </ns6:MediaInsertOrEjectParams>""".format(iso_name, media_id,
                                                                vca.host,media_id)

                for vms in vapp._get_vms():
                    vm_id = (vms.id).split(':')[-1]

                    headers = vca.vcloud_session.get_vcloud_headers()
                    headers['Content-Type'] = 'application/vnd.vmware.vcloud.mediaInsertOrEjectParams+xml'
                    rest_url = "{}/api/vApp/vm-{}/media/action/insertMedia".format(vca.host,vm_id)

                    response = Http.post(url=rest_url,
                                      headers=headers,
                                            data=data,
                                    verify=vca.verify,
                                    logger=vca.logger)

                    if response.status_code != 202:
                        self.logger.error("Failed to insert CD-ROM to vm")
                        raise vimconn.vimconnException("insert_media_to_vm() : Failed to insert"\
                                                                                    "ISO image to vm")
                    else:
                        task = taskType.parseString(response.content, True)
                        if isinstance(task, GenericTask):
                            vca.block_until_completed(task)
                            self.logger.info("insert_media_to_vm(): Sucessfully inserted media ISO"\
                                                                    " image to vm {}".format(vm_id))
        except Exception as exp:
            self.logger.error("insert_media_to_vm() : exception occurred "\
                                            "while inserting media CD-ROM")
            raise vimconn.vimconnException(message=exp)


    def get_media_details(self, vca, content):
        """
        Method to get catalog item details
        vca - connection object
        content - Catalog details
        Return - Media name, media id
        """
        cataloghref_list = []
        try:
            if content:
                vm_list_xmlroot = XmlElementTree.fromstring(content)
                for child in vm_list_xmlroot.iter():
                    if 'CatalogItem' in child.tag:
                        cataloghref_list.append(child.attrib.get('href'))
                if cataloghref_list is not None:
                    for href in cataloghref_list:
                        if href:
                            response = Http.get(url=href,
                                        headers=vca.vcloud_session.get_vcloud_headers(),
                                        verify=vca.verify,
                                        logger=vca.logger)
                            if response.status_code != 200:
                                self.logger.error("REST call {} failed reason : {}"\
                                             "status code : {}".format(href,
                                                           response.content,
                                                      response.status_code))
                                raise vimconn.vimconnException("get_media_details : Failed to get "\
                                                                         "catalogitem details")
                            list_xmlroot = XmlElementTree.fromstring(response.content)
                            for child in list_xmlroot.iter():
                                if 'Entity' in child.tag:
                                    if 'media' in child.attrib.get('href'):
                                        name = child.attrib.get('name')
                                        media_id = child.attrib.get('href').split('/').pop()
                                        return name,media_id
                            else:
                                self.logger.debug("Media name and id not found")
                                return False,False
        except Exception as exp:
            self.logger.error("get_media_details : exception occurred "\
                                               "getting media details")
            raise vimconn.vimconnException(message=exp)

