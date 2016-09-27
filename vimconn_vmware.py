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
vimconn_vmware implementation an Abstract class in order to interact with VMware  vCloud Director.
mbayramov@vmware.com
'''
import os
import traceback

import itertools
import requests

from xml.etree import ElementTree as XmlElementTree

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
import vimconn
import time
import uuid
import httplib

DELETE_INSTANCE_RETRY = 3

__author__ = "Mustafa Bayramov"
__date__ = "$26-Aug-2016 11:09:29$"

# Error variables
HTTP_Bad_Request = 400
HTTP_Unauthorized = 401
HTTP_Not_Found = 404
HTTP_Method_Not_Allowed = 405
HTTP_Request_Timeout = 408
HTTP_Conflict = 409
HTTP_Not_Implemented = 501
HTTP_Service_Unavailable = 503
HTTP_Internal_Server_Error = 500

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


class vimconnException(Exception):
    '''Common and base class Exception for all vimconnector exceptions'''

    def __init__(self, message, http_code=HTTP_Bad_Request):
        Exception.__init__(self, message)
        self.http_code = http_code


class vimconnConnectionException(vimconnException):
    '''Connectivity error with the VIM'''

    def __init__(self, message, http_code=HTTP_Service_Unavailable):
        vimconnException.__init__(self, message, http_code)


class vimconnUnexpectedResponse(vimconnException):
    '''Get an wrong response from VIM'''

    def __init__(self, message, http_code=HTTP_Service_Unavailable):
        vimconnException.__init__(self, message, http_code)


class vimconnAuthException(vimconnException):
    '''Invalid credentials or authorization to perform this action over the VIM'''

    def __init__(self, message, http_code=HTTP_Unauthorized):
        vimconnException.__init__(self, message, http_code)


class vimconnNotFoundException(vimconnException):
    '''The item is not found at VIM'''

    def __init__(self, message, http_code=HTTP_Not_Found):
        vimconnException.__init__(self, message, http_code)


class vimconnConflictException(vimconnException):
    '''There is a conflict, e.g. more item found than one'''

    def __init__(self, message, http_code=HTTP_Conflict):
        vimconnException.__init__(self, message, http_code)


class vimconnNotImplemented(vimconnException):
    '''The method is not implemented by the connected'''

    def __init__(self, message, http_code=HTTP_Not_Implemented):
        vimconnException.__init__(self, message, http_code)


flavorlist = {}


class vimconnector():
    '''Vmware VIM Connector base class
    '''

    def __init__(self, uuid, name, tenant_id, tenant_name, url, url_admin=None, user=None, passwd=None,
                 log_level="ERROR", config={}):

        print config
        self.id = uuid
        self.name = name
        self.org_name = name
        self.url = url
        self.url_admin = url_admin
        self.tenant_id = tenant_id
        self.tenant_name = tenant_name
        self.user = user
        self.passwd = passwd
        self.config = config
        self.admin_password = None
        self.admin_user = None

        self.logger = logging.getLogger('openmano.vim.vmware')

        try:
            self.admin_user = config['admin_username']
            self.admin_password = config['admin_password']
        except KeyError:
            raise vimconnException(message="Error admin username or admin password is empty.")

        self.logger = logging.getLogger('mano.vim.vmware')
        self.org_uuid = None
        self.vca = None

        if not url:
            raise TypeError, 'url param can not be NoneType'

        if not self.url_admin:  # try to use normal url
            self.url_admin = self.url

        self.vcaversion = '5.6'

        logging.debug("Calling constructor with following paramters")
        logging.debug("UUID: {} name: {} tenant_id: {} tenant name {}".format(self.id, self.name,
                                                                              self.tenant_id, self.tenant_name))
        logging.debug("vcd url {} vcd username: {} vcd password: {}".format(self.url, self.user, self.passwd))
        logging.debug("vcd admin username {} vcd admin passowrd {}".format(self.admin_user, self.admin_password))

        # initialize organization
        if self.user is not None and self.passwd is not None:
            self.init_org_uuid()

    def __getitem__(self, index):
        if index == 'tenant_id':
            return self.tenant_id
        if index == 'tenant_name':
            return self.tenant_name
        elif index == 'id':
            return self.id
        elif index == 'name':
            return self.name
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
        if index == 'tenant_id':
            self.tenant_id = value
        if index == 'tenant_name':
            self.tenant_name = value
        elif index == 'id':
            self.id = value
        # we use name  = org #TODO later refactor
        elif index == 'name':
            self.name = value
            self.org = value
        elif index == 'org_name':
            self.org_name = value
            self.name = value
        elif index == 'org_uuid':
            self.org_name = value
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
        """ Method connect as admin user to vCloud director.

            Returns:
                The return vca object that letter can be used to connect to vcloud direct as admin for provider vdc
        """

        self.logger.debug("Logging in to a vca {} as admin.".format(self.name))

        service_type = 'standalone'
        version = '5.6'
        vca_admin = VCA(host=self.url,
                        username=self.admin_user,
                        service_type=service_type,
                        version=version,
                        verify=False,
                        log=False)
        result = vca_admin.login(password=self.admin_password, org='System')
        if not result:
            raise vimconnConnectionException("Can't connect to a vCloud director as: {}".format(self.admin_user))
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

        service_type = 'standalone'
        version = '5.9'

        self.logger.debug("Logging in to a vca {} as {} to datacenter {}.".format(self.name, self.user, self.name))
        vca = VCA(host=self.url,
                  username=self.user,
                  service_type=service_type,
                  version=version,
                  verify=False,
                  log=False)
        result = vca.login(password=self.passwd, org=self.name)
        if not result:
            raise vimconnConnectionException("Can't connect to a vCloud director as: {}".format(self.user))
        result = vca.login(token=vca.token, org=self.name, org_url=vca.vcloud_session.org_url)
        if result is True:
            self.logger.info("Successfully logged to a vcloud direct org: {} as user: {}".format(self.name, self.user))

        return vca

    def init_org_uuid(self):
        """ Method available organization for a logged in tenant

            Returns:
                The return vca object that letter can be used to connect to vcloud direct as admin
        """
        try:
            if self.org_uuid is None:
                org_dict = self.get_org_list()
                for org in org_dict:
                    if org_dict[org] == self.org_name:
                        self.org_uuid = org
            self.logger.debug("Setting organization uuid {}".format(self.org_uuid))
        except:
            self.logger.debug("Failed initialize organization UUID for org {}".format(self.org_name))
            self.logger.debug(traceback.format_exc())
            self.org_uuid = None

    def new_tenant(self, tenant_name=None, tenant_description=None):
        """
        Adds a new tenant to VIM with this name and description

        :param tenant_name:
        :param tenant_description:
        :return: returns the tenant identifier
        """
        vdc_task = self.create_vdc(vdc_name=tenant_name)
        if vdc_task is not None:
            vdc_uuid, value = vdc_task.popitem()
            self.logger.info("Crated new vdc {} and uuid: {}".format(tenant_name, vdc_uuid))
            return vdc_uuid
        else:
            raise vimconnException("Failed create tenant {}".format(tenant_name))

    def delete_tenant(self, tenant_id, ):
        """Delete a tenant from VIM"""
        'Returns the tenant identifier'

        print(" ")
        print(" ######## delete_tenant {} ".format(tenant_id))
        print(" ")

        raise vimconnNotImplemented("Should have implemented this")

    def get_tenant_list(self, filter_dict={}):
        '''Obtain tenants of VIM
        filter_dict can contain the following keys:
            name: filter by tenant name
            id: filter by tenant uuid/id
            <other VIM specific>
        Returns the tenant list of dictionaries: 
            [{'name':'<name>, 'id':'<id>, ...}, ...]

        '''

        org_dict = self.get_org(self.org_uuid)
        vdcs_dict = org_dict['vdcs']

        vdclist = []
        try:
            for k in vdcs_dict:
                entry = {'name': vdcs_dict[k], 'id': k}
                filtered_entry = entry.copy()
                filtered_dict = set(entry.keys()) - set(filter_dict)
                for unwanted_key in filtered_dict: del entry[unwanted_key]
                if filter_dict == entry:
                    vdclist.append(filtered_entry)
        except:
            self.logger.debug("Error in get_tenant_list()")
            self.logger.debug(traceback.format_exc())
            pass

        return vdclist

    def new_network(self, net_name, net_type, ip_profile=None, shared=False):
        '''Adds a tenant network to VIM
            net_name is the name
            net_type can be 'bridge','data'.'ptp'.  TODO: this need to be revised
            ip_profile is a dict containing the IP parameters of the network 
            shared is a boolean
        Returns the network identifier'''

        self.logger.debug(
            "new_network tenant {} net_type {} ip_profile {} shared {}".format(net_name, net_type, ip_profile, shared))

        isshared = 'false'
        if shared:
            isshared = 'true'

        network_uuid = self.create_network(network_name=net_name, isshared=isshared)
        if network_uuid is not None:
            return network_uuid
        else:
            raise vimconnUnexpectedResponse("Failed create a new network {}".format(net_name))

    def get_vcd_network_list(self):
        """ Method available organization for a logged in tenant

            Returns:
                The return vca object that letter can be used to connect to vcloud direct as admin
        """

        self.logger.debug("get_vcd_network_list(): retrieving network list for vcd")
        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed.")

        vdc = vca.get_vdc(self.tenant_name)
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
        '''Obtain tenant networks of VIM
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
        '''

        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")

        vdc = vca.get_vdc(self.tenant_name)
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

                # we remove all the key : value we dont' care and match only
                # respected field
                filtered_dict = set(filter_entry.keys()) - set(filter_dict)
                for unwanted_key in filtered_dict: del filter_entry[unwanted_key]
                if filter_dict == filter_entry:
                    network_list.append(filtered_entry)
        except:
            self.logger.debug("Error in get_vcd_network_list")
            self.logger.debug(traceback.format_exc())

        self.logger.debug("Returning {}".format(network_list))
        return network_list

    def get_network(self, net_id):
        """Method bbtain network details of net_id VIM network
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
            raise vimconn.vimconnConnectionException("self.connect() for tenant {} is failed".format(self.tenant_name))

        if self.delete_network_action(net_id):
            return net_id
        else:
            raise vimconn.vimconnNotFoundException("Network {} not found".format(net_id))

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

        # for net in net_list:
        #     net['status']
        #     net['error_msg']
        #     net['vim_info']

        # vim vimcon failed == ERROR
        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")

        dict_entry = {}
        try:
            for net in net_list:
                status = ''
                errormsg = ''
                vcd_network = self.get_vcd_network(network_uuid=net)
                if vcd_network is not None:
                    if vcd_network['status'] == 1:
                        status = 'ACTIVE'
                    else:
                        status = 'DOWN'
                else:
                    status = 'DELETED'
                    errormsg = 'network not found'
                    dict_entry['net'] = {'status': status, 'error_msg': errormsg,
                                         'vm_info': yaml.safe_dump(vcd_network)}
        except:
            self.logger.debug("Error in refresh_nets_status")
            self.logger.debug(traceback.format_exc())

        return dict_entry

    def get_flavor(flavor_id):
        """Obtain flavor details from the  VIM
            Returns the flavor dict details {'id':<>, 'name':<>, other vim specific } #TODO to concrete
        """
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
        flavor_id = uuid.uuid4()
        flavorlist[str(flavor_id)] = flavor_data

        return str(flavor_id)

    def delete_flavor(self, flavor_id):
        """Deletes a tenant flavor from VIM identify by its id

        Returns the used id or raise an exception
        """

        # if key not present it will raise KeyError
        # TODO check do I need raise any specific exception
        flavorlist.pop(flavor_id, None)
        return flavor_id

    def new_image(self, image_dict):
        '''
        Adds a tenant image to VIM
        Returns:
            200, image-id        if the image is created
            <0, message          if there is an error
        '''

        return self.get_image_id_from_path(image_dict['location'])

    def delete_image(self, image_id):
        '''Deletes a tenant image from VIM'''
        '''Returns the HTTP response code and a message indicating details of the success or fail'''

        print " ################################################################### "
        print " delete_image contains  {}".format(image_id)
        print " ################################################################### "

        raise vimconnNotImplemented("Should have implemented this")

    def catalog_exists(self, catalog_name, catalogs):
        for catalog in catalogs:
            if catalog.name == catalog_name:
                return True
        return False

    def create_vimcatalog(self, vca, catalog_name):
        """Create Catalog entry in VIM"""
        task = vca.create_catalog(catalog_name, catalog_name)
        result = vca.block_until_completed(task)
        if not result:
            return False
        catalogs = vca.get_catalogs()
        return self.catalog_exists(catalog_name, catalogs)

    def upload_ovf(self, vca, catalog_name, item_name, media_file_name, description='', display_progress=False,
                   chunk_bytes=128 * 1024):
        """
        Uploads a OVF file to a vCloud catalog

        :param catalog_name: (str): The name of the catalog to upload the media.
        :param item_name: (str): The name of the media file in the catalog.
        :param media_file_name: (str): The name of the local media file to upload.
        :return: (bool) True if the media file was successfully uploaded, false otherwise.
        """
        os.path.isfile(media_file_name)
        statinfo = os.stat(media_file_name)
        statinfo.st_size

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
            <UploadVAppTemplateParams name="%s Template" xmlns="http://www.vmware.com/vcloud/v1.5" xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1"><Description>%s vApp Template</Description></UploadVAppTemplateParams>
            """ % (escape(item_name), escape(description))
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
                    link = \
                        filter(lambda link: link.get_rel() == 'upload:default',
                               media.get_Files().get_File()[0].get_Link())[
                            0]
                    headers = vca.vcloud_session.get_vcloud_headers()
                    headers['Content-Type'] = 'Content-Type text/xml'
                    response = Http.put(link.get_href(), data=open(media_file_name, 'rb'), headers=headers,
                                        verify=vca.verify, logger=self.logger)
                    if response.status_code != requests.codes.ok:
                        self.logger.debug(
                            "Failed create vApp template for catalog name {} and image {}".format(catalog_name,
                                                                                                  media_file_name))
                        return False

                # TODO fix this with aync block
                time.sleep(5)

                self.logger.debug("Failed create vApp template for catalog name {} and image {}".
                                  format(catalog_name, media_file_name))

                # uploading VMDK file
                # check status of OVF upload
                response = Http.get(template, headers=vca.vcloud_session.get_vcloud_headers(), verify=vca.verify,
                                    logger=self.logger)
                if response.status_code == requests.codes.ok:
                    media = mediaType.parseString(response.content, True)
                    link = \
                        filter(lambda link: link.get_rel() == 'upload:default',
                               media.get_Files().get_File()[0].get_Link())[
                            0]

                    # The OVF file and VMDK must be in a same directory
                    head, tail = os.path.split(media_file_name)
                    filevmdk = head + '/' + os.path.basename(link.get_href())

                    os.path.isfile(filevmdk)
                    statinfo = os.stat(filevmdk)

                    # TODO debug output remove it
                    # print media.get_Files().get_File()[0].get_Link()[0].get_href()
                    # print media.get_Files().get_File()[1].get_Link()[0].get_href()
                    # print link.get_href()

                    # in case first element is pointer to OVF.
                    hrefvmdk = link.get_href().replace("descriptor.ovf", "Cirros-disk1.vmdk")

                    f = open(filevmdk, 'rb')
                    bytes_transferred = 0
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
                                self.logger.debug('transferred %s of %s bytes' % (str(bytes_transferred),
                                                                                  str(statinfo.st_size)))
                            else:
                                self.logger.debug('file upload failed with error: [%s] %s' % (response.status_code,
                                                                                              response.content))
                                return False
                    f.close()
                    return True
                else:
                    self.logger.debug("Failed retrieve vApp template for catalog name {} for OVF {}".
                                      format(catalog_name, media_file_name))
                    return False

        self.logger.debug("Failed retrieve catalog name {} for OVF file {}".format(catalog_name, media_file_name))
        return False

    def upload_vimimage(self, vca, catalog_name, media_name, medial_file_name):
        """Upload media file"""
        # TODO add named parameters for readbility
        return self.upload_ovf(vca, catalog_name, media_name.split(".")[0], medial_file_name, medial_file_name, True)

    def get_catalogid(self, catalog_name, catalogs):
        for catalog in catalogs:
            if catalog.name == catalog_name:
                catalog_id = catalog.get_id().split(":")
                return catalog_id[3]
        return None

    def get_catalogbyid(self, catalog_id, catalogs):
        for catalog in catalogs:
            catalogid = catalog.get_id().split(":")[3]
            if catalogid == catalog_id:
                return catalog.name
        return None

    def get_image_id_from_path(self, path):
        '''Get the image id from image path in the VIM database'''
        '''Returns:
             0,"Image not found"   if there are no images with that path
             1,image-id            if there is one image with that path
             <0,message            if there was an error (Image not found, error contacting VIM, more than 1 image with that path, etc.) 
        '''

        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")

        self.logger.debug("get_image_id_from_path path {}".format(path))

        dirpath, filename = os.path.split(path)
        flname, file_extension = os.path.splitext(path)
        if file_extension != '.ovf':
            self.logger.debug("Wrong file extension {}".format(file_extension))
            return -1, "Wrong container.  vCloud director supports only OVF."
        catalog_name = os.path.splitext(filename)[0]

        self.logger.debug("File name {} Catalog Name {} file path {}".format(filename, catalog_name, path))
        self.logger.debug("Catalog name {}".format(catalog_name))

        catalogs = vca.get_catalogs()
        if len(catalogs) == 0:
            self.logger.info("Creating new catalog entry {} in vcloud director".format(catalog_name))
            result = self.create_vimcatalog(vca, catalog_name)
            if not result:
                return -1, "Failed create new catalog {} ".format(catalog_name)
            result = self.upload_vimimage(vca, catalog_name, filename, path)
            if not result:
                return -1, "Failed create vApp template for catalog {} ".format(catalog_name)
            return self.get_catalogid(catalog_name, vca.get_catalogs())
        else:
            for catalog in catalogs:
                # search for existing catalog if we find same name we return ID
                # TODO optimize this
                if catalog.name == catalog_name:
                    self.logger.debug("Found existing catalog entry for {} catalog id {}".format(catalog_name,
                                                                                                 self.get_catalogid(
                                                                                                     catalog_name,
                                                                                                     catalogs)))
                    return self.get_catalogid(catalog_name, vca.get_catalogs())

        # if we didn't find existing catalog we create a new one.
        self.logger.debug("Creating new catalog entry".format(catalog_name))
        result = self.create_vimcatalog(vca, catalog_name)
        if not result:
            return -1, "Failed create new catalog {} ".format(catalog_name)
        result = self.upload_vimimage(vca, catalog_name, filename, path)
        if not result:
            return -1, "Failed create vApp template for catalog {} ".format(catalog_name)

        return self.get_catalogid(catalog_name, vca.get_catalogs())

    def get_vappid(self, vdc=None, vapp_name=None):
        """ Method takes vdc object and vApp name and returns vapp uuid or None

        Args:
            vca: Connector to VCA
            vdc: The VDC object.
            vapp_name: is application vappp name identifier

            Returns:
                The return vApp name otherwise None
        """

        """ Take vdc object and vApp name and returns vapp uuid or None
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

    def check_vapp(self, vdc, vapp_id):
        """ Take VDC object and vApp ID and return True if given ID in vCloud director
            otherwise return False
          """

        """ Method Method returns vApp name from vCD and lookup done by vapp_id.

            Args:
                vca: Connector to VCA
                vdc: The VDC object.
                vappid: vappid is application identifier

            Returns:
                The return vApp name otherwise None
        """
        try:
            refs = filter(lambda ref:
                          ref.type_ == 'application/vnd.vmware.vcloud.vApp+xml',
                          vdc.ResourceEntities.ResourceEntity)
            for ref in refs:
                vappid = ref.href.split("vapp")[1][1:]
                # find vapp with respected vapp uuid
                if vappid == vapp_id:
                    return True
        except Exception as e:
            self.logger.exception(e)
            return False
        return False

    def get_namebyvappid(self, vca, vdc, vapp_id):
        """Method returns vApp name from vCD and lookup done by vapp_id.

        Args:
            vca: Connector to VCA
            vdc: The VDC object.
            vapp_id: vappid is application identifier

        Returns:
            The return vApp name otherwise None
        """

        try:
            refs = filter(lambda ref: ref.type_ == 'application/vnd.vmware.vcloud.vApp+xml',
                          vdc.ResourceEntities.ResourceEntity)
            for ref in refs:
                # we care only about UUID the rest doesn't matter
                vappid = ref.href.split("vapp")[1][1:]
                if vappid == vapp_id:
                    response = Http.get(ref.href, headers=vca.vcloud_session.get_vcloud_headers(), verify=vca.verify,
                                        logger=self.logger)
                    tree = XmlElementTree.fromstring(response.content)
                    return tree.attrib['name']
        except Exception as e:
            self.logger.exception(e)
            return None
        return None

    def new_vminstance(self, name, description, start, image_id, flavor_id, net_list, cloud_config=None):
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

        self.logger.info("Creating new instance for entry".format(name))
        self.logger.debug("desc {} boot {} image_id: {} flavor_id: {} net_list: {} cloud_config {}".
                          format(description, start, image_id, flavor_id, net_list, cloud_config))
        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed.")

        # if vm already deployed we return existing uuid
        vapp_uuid = self.get_vappid(vca.get_vdc(self.tenant_name), name)
        if vapp_uuid is not None:
            return vapp_uuid

        # we check for presence of VDC, Catalog entry and Flavor.
        vdc = vca.get_vdc(self.tenant_name)
        if vdc is None:
            return -1, " Failed create vApp {}: (Failed reprieve VDC information)".format(name)
        catalogs = vca.get_catalogs()
        if catalogs is None:
            return -2, " Failed create vApp {}: (Failed reprieve Catalog information)".format(name)
        flavor = flavorlist[flavor_id]
        if catalogs is None:
            return -3, " Failed create vApp {}: (Failed reprieve Flavor information)".format(name)

        # image upload creates template name as catalog name space Template.
        templateName = self.get_catalogbyid(image_id, catalogs) + ' Template'
        power_on = 'false'
        if start:
            power_on = 'true'

        # client must provide at least one entry in net_list if not we report error
        primary_net = net_list[0]
        if primary_net is None:
            return -4, "Failed create vApp {}: (Network list is empty)".format(name)

        primary_net_id = primary_net['net_id']
        primary_net_name = self.get_network_name_by_id(primary_net_id)
        network_mode = primary_net['use']

        # use: 'data', 'bridge', 'mgmt'
        # create vApp.  Set vcpu and ram based on flavor id.
        vapptask = vca.create_vapp(self.tenant_name, name, templateName,
                                   self.get_catalogbyid(image_id, catalogs),
                                   network_name=primary_net_name,
                                   network_mode='bridged',
                                   vm_name=name,
                                   vm_cpus=flavor['vcpus'],
                                   vm_memory=flavor['ram'])

        if vapptask is None or vapptask is False:
            return -1, "create_vapp(): failed deploy vApp {}".format(name)
        if type(vapptask) is VappTask:
            vca.block_until_completed(vapptask)

        # we should have now vapp in undeployed state.
        vapp = vca.get_vapp(vca.get_vdc(self.tenant_name), name)
        if vapp is None:
            return -1, "get_vapp(): failed retrieve vApp {}".format(name)

        # add first NIC
        try:
            nicIndex = 0
            for net in net_list:
                # openmano uses network id in UUID format.
                # vCloud Director need a name so we do reverse operation from provided UUID we lookup a name
                interface_net_id = net['net_id']
                interface_net_name = self.get_network_name_by_id(interface_net_id)
                interface_network_mode = net['use']

                if primary_net_name is not None:
                    nets = filter(lambda n: n.name == interface_net_name, vca.get_networks(self.tenant_name))
                    if len(nets) == 1:
                        task = vapp.connect_to_network(nets[0].name, nets[0].href)
                        if type(task) is GenericTask:
                            vca.block_until_completed(task)
                        # connect network to VM
                        # TODO figure out mapping between openmano representation to vCloud director.
                        # one idea use first nic as managment DHCP all remaining in bridge mode
                        task = vapp.connect_vms(nets[0].name, connection_index=nicIndex,
                                                connections_primary_index=nicIndex,
                                                ip_allocation_mode='DHCP')
                        if type(task) is GenericTask:
                            vca.block_until_completed(task)
            nicIndex += 1
        except KeyError:
            # TODO
            # it might be a case if specific mandatory entry in dict is empty
            self.logger.debug("Key error {}".format(KeyError.message))

        # deploy and power on vm
        task = vapp.poweron()
        if type(task) is TaskType:
            vca.block_until_completed(task)
        deploytask = vapp.deploy(powerOn='True')
        if type(task) is TaskType:
            vca.block_until_completed(deploytask)

        # check if vApp deployed and if that the case return vApp UUID otherwise -1
        vapp_uuid = self.get_vappid(vca.get_vdc(self.tenant_name), name)
        if vapp_uuid is not None:
            return vapp_uuid

        return -1, " Failed create vApp {}".format(name)

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
    def get_vminstance(self, vim_vm_uuid):
        '''Returns the VM instance information from VIM'''

        self.logger.debug("Client requesting vm instance {} ".format(vim_vm_uuid))
        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed.")

        vdc = vca.get_vdc(self.tenant_name)
        if vdc is None:
            return -1, "Failed to get a reference of VDC for a tenant {}".format(self.tenant_name)

        vm_name = self.get_namebyvappid(vca, vdc, vim_vm_uuid)
        if vm_name is None:
            self.logger.debug("get_vminstance(): Failed to get vApp name by UUID {}".format(vim_vm_uuid))
            return None, "Failed to get vApp name by UUID {}".format(vim_vm_uuid)

        the_vapp = vca.get_vapp(vdc, vm_name)
        vm_info = the_vapp.get_vms_details()

        vm_dict = {'description': vm_info[0]['name'], 'status': vcdStatusCode2manoFormat[the_vapp.me.get_status()],
                   'error_msg': vcdStatusCode2manoFormat[the_vapp.me.get_status()],
                   'vim_info': yaml.safe_dump(the_vapp.get_vms_details()), 'interfaces': []}

        # get networks
        vm_app_networks = the_vapp.get_vms_network_info()

        interfaces = []
        try:
            org_network_dict = self.get_org(self.org_uuid)['networks']
            for vapp_network in vm_app_networks:
                for vm_network in vapp_network:
                    if vm_network['name'] == vm_name:
                        interface = {}
                        # interface['vim_info'] = yaml.safe_dump(vm_network)
                        interface["mac_address"] = vm_network['mac']
                        for net_uuid in org_network_dict:
                            if org_network_dict[net_uuid] == vm_network['network_name']:
                                interface["vim_net_id"] = net_uuid
                                interface["vim_interface_id"] = vm_network['network_name']
                                interface['ip_address'] = vm_network['ip']
                                interfaces.append(interface)
        except KeyError:
            self.logger.debug("Error in respond {}".format(KeyError.message))
            self.logger.debug(traceback.format_exc())

        vm_dict['interfaces'] = interfaces

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
            raise vimconnException("delete_vminstance(): Failed to get a reference of VDC for a tenant {}".format(self.tenant_name))

        try:
            vapp_name = self.get_namebyvappid(vca, vdc, vm__vim_uuid)
            if vapp_name is None:
                self.logger.debug("delete_vminstance(): Failed to get vm by given {} vm uuid".format(vm__vim_uuid))
                return -1, "delete_vminstance(): Failed to get vm by given {} vm uuid".format(vm__vim_uuid)
            else:
                self.logger.info("Deleting vApp {} and UUID {}".format(vapp_name, vm__vim_uuid))

            # Delete vApp and wait for status change if task executed and vApp is None.
            # We successfully delete vApp from vCloud
            vapp = vca.get_vapp(vca.get_vdc(self.tenant_name), vapp_name)
            # poweroff vapp / undeploy and delete
            power_off_task = vapp.poweroff()
            if type(power_off_task) is GenericTask:
                vca.block_until_completed(power_off_task)
            else:
                if not power_off_task:
                    self.logger.debug("delete_vminstance(): Failed power off VM uuid {} ".format(vm__vim_uuid))

            # refresh status
            if vapp.me.deployed:
                undeploy_task = vapp.undeploy()
                if type(undeploy_task) is GenericTask:
                    retry = 0
                    while retry <= DELETE_INSTANCE_RETRY:
                        result = vca.block_until_completed(undeploy_task)
                        if result:
                            break
                        retry += 1
                else:
                    return -1

            # delete vapp
            vapp = vca.get_vapp(vca.get_vdc(self.tenant_name), vapp_name)
            if vapp is not None:
                delete_task = vapp.delete()
                retry = 0
                while retry <= DELETE_INSTANCE_RETRY:
                    task = vapp.delete()
                    if type(task) is GenericTask:
                        vca.block_until_completed(delete_task)
                    if not delete_task:
                        self.loggger.debug("delete_vminstance(): Failed delete uuid {} ".format(vm__vim_uuid))
                    retry += 1

            if vca.get_vapp(vca.get_vdc(self.tenant_name), vapp_name) is None:
                return vm__vim_uuid
        except:
            self.logger.debug(traceback.format_exc())
            raise vimconnException("delete_vminstance(): Failed to get a reference of VDC for a tenant {}".format(self.tenant_name))

        return -1

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
            raise vimconnException("Failed to get a reference of VDC for a tenant {}".format(self.tenant_name))

        vms_dict = {}
        for vmuuid in vm_list:
            vmname = self.get_namebyvappid(vca, vdc, vmuuid)
            if vmname is not None:

                the_vapp = vca.get_vapp(vdc, vmname)
                vm_info = the_vapp.get_vms_details()
                vm_status = vm_info[0]['status']

                vm_dict = {'status': None, 'error_msg': None, 'vim_info': None, 'interfaces': []}
                vm_dict['status'] = vcdStatusCode2manoFormat[the_vapp.me.get_status()]
                vm_dict['error_msg'] = vcdStatusCode2manoFormat[the_vapp.me.get_status()]
                vm_dict['vim_info'] = yaml.safe_dump(the_vapp.get_vms_details())

                # get networks
                try:
                    vm_app_networks = the_vapp.get_vms_network_info()
                    for vapp_network in vm_app_networks:
                        for vm_network in vapp_network:
                            if vm_network['name'] == vmname:
                                interface = {}
                                # interface['vim_info'] = yaml.safe_dump(vm_network)
                                interface["mac_address"] = vm_network['mac']
                                interface["vim_net_id"] = self.get_network_name_by_id(vm_network['network_name'])
                                interface["vim_interface_id"] = vm_network['network_name']
                                interface['ip_address'] = vm_network['ip']
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
            raise vimconnException("Invalid request. VM id or action is None.")

        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed.")

        vdc = vca.get_vdc(self.tenant_name)
        if vdc is None:
            return -1, "Failed to get a reference of VDC for a tenant {}".format(self.tenant_name)

        vapp_name = self.get_namebyvappid(vca, vdc, vm__vim_uuid)
        if vapp_name is None:
            self.logger.debug("action_vminstance(): Failed to get vm by given {} vm uuid".format(vm__vim_uuid))
            raise vimconnException("Failed to get vm by given {} vm uuid".format(vm__vim_uuid))
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
                ##server.pause()
            elif "resume" in action_dict:
                pass
                ##server.resume()
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
        raise vimconnNotImplemented("Should have implemented this")

    # NOT USED METHODS in current version

    def host_vim2gui(self, host, server_dict):
        '''Transform host dictionary from VIM format to GUI format,
        and append to the server_dict
        '''
        raise vimconnNotImplemented("Should have implemented this")

    def get_hosts_info(self):
        '''Get the information of deployed hosts
        Returns the hosts content'''
        raise vimconnNotImplemented("Should have implemented this")

    def get_hosts(self, vim_tenant):
        '''Get the hosts and deployed instances
        Returns the hosts content'''
        raise vimconnNotImplemented("Should have implemented this")

    def get_processor_rankings(self):
        '''Get the processor rankings in the VIM database'''
        raise vimconnNotImplemented("Should have implemented this")

    def new_host(self, host_data):
        '''Adds a new host to VIM'''
        '''Returns status code of the VIM response'''
        raise vimconnNotImplemented("Should have implemented this")

    def new_external_port(self, port_data):
        '''Adds a external port to VIM'''
        '''Returns the port identifier'''
        raise vimconnNotImplemented("Should have implemented this")

    def new_external_network(self, net_name, net_type):
        '''Adds a external network to VIM (shared)'''
        '''Returns the network identifier'''
        raise vimconnNotImplemented("Should have implemented this")

    def connect_port_network(self, port_id, network_id, admin=False):
        '''Connects a external port to a network'''
        '''Returns status code of the VIM response'''
        raise vimconnNotImplemented("Should have implemented this")

    def new_vminstancefromJSON(self, vm_data):
        '''Adds a VM instance to VIM'''
        '''Returns the instance identifier'''
        raise vimconnNotImplemented("Should have implemented this")

    def get_network_name_by_id(self, network_name=None):
        """Method gets vcloud director network named based on supplied uuid.

        Args:
            network_name: network_id

        Returns:
            The return network name.
        """

        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")

        if network_name is None:
            return None

        try:
            org_network_dict = self.get_org(self.org_uuid)['networks']
            for net_uuid in org_network_dict:
                if org_network_dict[net_uuid] == network_name:
                    return net_uuid
        except:
            self.logger.debug("Exception in get_network_name_by_id")
            self.logger.debug(traceback.format_exc())

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
            vca - is active VCA connection.
            vdc_name - is a vdc name that will be used to query vms action

            Returns:
                The return dictionary and key for each entry vapp UUID
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
        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")

        if vdc_name is None:
            return vm_dict

        content = self.vms_view_action(vdc_name=vdc_name)
        try:
            vm_list_xmlroot = XmlElementTree.fromstring(content)
            for vm_xml in vm_list_xmlroot:
                if vm_xml.tag.split("}")[1] == 'VMRecord':
                    if isuuid:
                        # lookup done by UUID
                        if vapp_name in vm_xml.attrib['container']:
                            rawuuid = vm_xml.attrib['href'].split('/')[-1:]
                            if 'vm-' in rawuuid[0]:
                                # vm in format vm-e63d40e7-4ff5-4c6d-851f-96c1e4da86a5 we remove
                                #  vm and use raw UUID as key
                                vm_dict[rawuuid[0][3:]] = vm_xml.attrib
                        # lookup done by Name
                        else:
                            if vapp_name in vm_xml.attrib['name']:
                                rawuuid = vm_xml.attrib['href'].split('/')[-1:]
                                if 'vm-' in rawuuid[0]:
                                    vm_dict[rawuuid[0][3:]] = vm_xml.attrib
                                    # vm in format vm-e63d40e7-4ff5-4c6d-851f-96c1e4da86a5 we remove
                                    #  vm and use raw UUID as key
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

    def create_network(self, network_name=None, parent_network_uuid=None, isshared='true'):
        """
        Method create network in vCloud director

        Args:
            network_name - is network name to be created.
            parent_network_uuid - is parent provider vdc network that will be used for mapping.
            It optional attribute. by default if no parent network indicate the first available will be used.

            Returns:
                The return network uuid or return None
        """

        content = self.create_network_rest(network_name=network_name,
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

    def create_network_rest(self, network_name=None, parent_network_uuid=None, isshared='true'):
        """
        Method create network in vCloud director

        Args:
            network_name - is network name to be created.
            parent_network_uuid - is parent provider vdc network that will be used for mapping.
            It optional attribute. by default if no parent network indicate the first available will be used.

            Returns:
                The return network uuid or return None
        """

        vca = self.connect_as_admin()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")
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

            # either use client provided UUID or search for a first available
            #  if both are not defined we return none
            if parent_network_uuid is not None:
                url_list = [vca.host, '/api/admin/network/', parent_network_uuid]
                add_vdc_rest_url = ''.join(url_list)

            # return response.content
            data = """ <OrgVdcNetwork name="{0:s}" xmlns="http://www.vmware.com/vcloud/v1.5">
                            <Description>Openmano created</Description>
                                    <Configuration>
                                        <ParentNetwork href="{1:s}"/>
                                        <FenceMode>{2:s}</FenceMode>
                                    </Configuration>
                                    <IsShared>{3:s}</IsShared>
                        </OrgVdcNetwork> """.format(escape(network_name), available_networks, "bridged", isshared)

            headers = vca.vcloud_session.get_vcloud_headers()
            headers['Content-Type'] = 'application/vnd.vmware.vcloud.orgVdcNetwork+xml'
            response = Http.post(url=add_vdc_rest_url, headers=headers, data=data, verify=vca.verify, logger=vca.logger)

            # if we all ok we respond with content otherwise by default None
            if response.status_code == 201:
                return response.content
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
            print xml_content
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
        print ("Creating new vdc {}".format(vdc_name))

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
        print ("Creating new vdc {}".format(vdc_name))

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
                print response
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

                print "Add vdc {}".format(add_vdc_rest_url)
                print "Provider ref {}".format(provider_vdc_ref)
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

                    print data
                    headers = vca.vcloud_session.get_vcloud_headers()
                    headers['Content-Type'] = 'application/vnd.vmware.admin.createVdcParams+xml'
                    response = Http.post(url=add_vdc_rest_url, headers=headers, data=data, verify=vca.verify,
                                         logger=vca.logger)

                    print response.status_code
                    print response.content
                    # if we all ok we respond with content otherwise by default None
                    if response.status_code == 201:
                        return response.content
        return None
