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
import requests


from xml.etree import ElementTree as ET

from pyvcloud import Http
from pyvcloud.vcloudair import VCA
from pyvcloud.schema.vcd.v1_5.schemas.vcloud import sessionType, organizationType, \
    vAppType, organizationListType, vdcType, catalogType, queryRecordViewType, \
    networkType, vcloudType, taskType, diskType, vmsType, vdcTemplateListType, mediaType
from xml.sax.saxutils import escape

import logging
import json
import vimconn
import time
import uuid
import httplib


__author__="Mustafa Bayramov"
__date__ ="$26-Aug-2016 11:09:29$"


#Error variables
HTTP_Bad_Request = 400
HTTP_Unauthorized = 401
HTTP_Not_Found = 404
HTTP_Method_Not_Allowed = 405
HTTP_Request_Timeout = 408
HTTP_Conflict = 409
HTTP_Not_Implemented = 501
HTTP_Service_Unavailable = 503
HTTP_Internal_Server_Error = 500

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
    def __init__(self, uuid, name, tenant_id, tenant_name, url, url_admin=None, user=None, passwd=None, log_level="ERROR", config={}):
        self.id        = uuid
        self.name      = name
        self.url       = url
        self.url_admin = url_admin
        self.tenant_id = tenant_id
        self.tenant_name = tenant_name
        self.user      = user
        self.passwd    = passwd
        self.config    = config
        self.logger = logging.getLogger('openmano.vim.vmware')

#         formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#         ch = logging.StreamHandler()
#         ch.setLevel(log_level)
#         ch.setFormatter(formatter)
#         self.logger.addHandler(ch)
#         self.logger.setLevel( getattr(logging, log_level))

#        self.logger = logging.getLogger('mano.vim.vmware')

        self.logger.debug("Vmware tenant from VIM filter: '%s'", user)
        self.logger.debug("Vmware tenant from VIM filter: '%s'", passwd)

        if not url:
            raise TypeError, 'url param can not be NoneType'

        if not self.url_admin:  #try to use normal url
            self.url_admin = self.url

        self.vcaversion = '5.6'

        print "Calling constructor with following paramters"
        print "          UUID:   {} ".format(uuid)
        print "          name:   {} ".format(name)
        print "     tenant_id:   {} ".format(tenant_id)
        print "     tenant_name: {} ".format(tenant_name)
        print "     url:         {} ".format(url)
        print "     url_admin:   {} ".format(url_admin)
        print "     user:        {} ".format(user)
        print "     passwd:      {} ".format(passwd)
        print "     debug:       {} ".format(log_level)

    def __getitem__(self,index):
        if index=='tenant_id':
            return self.tenant_id
        if index=='tenant_name':
            return self.tenant_name
        elif index=='id':
            return self.id
        elif index=='name':
            return self.name
        elif index=='user':
            return self.user
        elif index=='passwd':
            return self.passwd
        elif index=='url':
            return self.url
        elif index=='url_admin':
            return self.url_admin
        elif index=="config":
            return self.config
        else:
            raise KeyError("Invalid key '%s'" %str(index))

    def __setitem__(self,index, value):
        if index=='tenant_id':
            self.tenant_id = value
        if index=='tenant_name':
            self.tenant_name = value
        elif index=='id':
            self.id = value
        elif index=='name':
            self.name = value
        elif index=='user':
            self.user = value
        elif index=='passwd':
            self.passwd = value
        elif index=='url':
            self.url = value
        elif index=='url_admin':
            self.url_admin = value
        else:
            raise KeyError("Invalid key '%s'" %str(index))

    def connect(self):

        service_type = 'standalone'
        version = '5.6'

        self.logger.debug("Logging in to a VCA '%s'", self.name)

        vca = VCA(host=self.url, username=self.user, service_type=service_type, version=version, verify=False, log=True)
        result = vca.login(password=self.passwd, org=self.name)
        if not result:
            raise KeyError("Can't connect to a vCloud director.")
        result = vca.login(token=vca.token, org=self.name, org_url=vca.vcloud_session.org_url)
        if result is True:
            self.logger.debug("Successfully logged to a VCA '%s'", self.name)

        # vca = VCA(host='172.16.254.206', username=self.user, service_type='standalone', version='5.6', verify=False, log=True)
        # vca.login(password=self.passwd, org=self.name)
        # vca.login(token=vca.token, org=self.name, org_url=vca.vcloud_session.org_url)

        # if not result:
        #     result = vca.login(token=vca.token, org=self.name, org_url=vca.vcloud_session.org_url)
        #     if not result:
        #         raise KeyError("Can't connect to a vcloud director")
        #     else:
        #         print "Logged to VCA via existing token"
        # else:
        #     print "Logged to VCA"

        return vca


    def new_tenant(self,tenant_name,tenant_description):
        '''Adds a new tenant to VIM with this name and description,
        returns the tenant identifier'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def delete_tenant(self,tenant_id,):
        '''Delete a tenant from VIM'''
        '''Returns the tenant identifier'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def get_tenant_list(self, filter_dict={}):
        '''Obtain tenants of VIM
        filter_dict can contain the following keys:
            name: filter by tenant name
            id: filter by tenant uuid/id
            <other VIM specific>
        Returns the tenant list of dictionaries: 
            [{'name':'<name>, 'id':'<id>, ...}, ...]
        '''
        raise vimconnNotImplemented( "Should have implemented this" )

    def new_network(self,net_name, net_type, ip_profile=None, shared=False):
        '''Adds a tenant network to VIM
            net_name is the name
            net_type can be 'bridge','data'.'ptp'.  TODO: this need to be revised
            ip_profile is a dict containing the IP parameters of the network 
            shared is a boolean
        Returns the network identifier'''

        self.logger.debug("Vmware tenant from VIM filter: '%s'", net_name)
        self.logger.debug("Vmware tenant from VIM filter: '%s'", net_type)
        self.logger.debug("Vmware tenant from VIM filter: '%s'", ip_profile)
        self.logger.debug("Vmware tenant from VIM filter: '%s'", shared)

        raise vimconnNotImplemented( "Should have implemented this" )

    def get_network_list(self, filter_dict={}):
        '''Obtain tenant networks of VIM
        Filter_dict can be:
            name: network name
            id: network uuid
            shared: boolean
            tenant_id: tenant
            admin_state_up: boolean
            status: 'ACTIVE'
        Returns the network list of dictionaries:
            [{<the fields at Filter_dict plus some VIM specific>}, ...]
            List can be empty
        '''

        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed")

        vdc = vca.get_vdc(self.tenant_name)
        vdcid = vdc.get_id().split(":")

        networks = vca.get_networks(vdc.get_name())
        network_list = []
        for network in networks:
            filter_dict = {}
            netid = network.get_id().split(":")
            self.logger.debug ("Adding  {} to a list".format(netid[3]))
            self.logger.debug ("VDC ID  {} to a list".format(vdcid[3]))
            self.logger.debug ("Network {} to a list".format(network.get_name()))

            filter_dict["name"] = network.get_name()
            filter_dict["id"] = netid[3]
            filter_dict["shared"] = network.get_IsShared()
            filter_dict["tenant_id"] = vdcid[3]
            if network.get_status() == 1:
                filter_dict["admin_state_up"] = True
            else:
                filter_dict["admin_state_up"] = False
            filter_dict["status"] = "ACTIVE"
            filter_dict["type"] = "bridge"
            network_list.append(filter_dict)

        self.logger.debug("Returning {}".format(network_list))
        return network_list

    def get_network(self, net_id):
        '''Obtain network details of net_id VIM network'
           Return a dict with  the fields at filter_dict (see get_network_list) plus some VIM specific>}, ...]'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def delete_network(self, net_id):
        '''Deletes a tenant network from VIM, provide the network id.
        Returns the network identifier or raise an exception'''
        raise vimconnNotImplemented( "Should have implemented this" )

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
        raise vimconnNotImplemented( "Should have implemented this" )

    def get_flavor(self, flavor_id):
        '''Obtain flavor details from the  VIM
            Returns the flavor dict details {'id':<>, 'name':<>, other vim specific } #TODO to concrete
        '''

        print " get_flavor contains {}".format(flavor_id)

        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed.")

    def new_flavor(self, flavor_data):
        '''Adds a tenant flavor to VIM
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
        Returns the flavor identifier'''

        flavor_uuid = uuid.uuid4()
        flavorlist[flavor_uuid] = flavor_data

        print " new_flavor contains  {}".format(flavor_data)
        print " flavor list contains {}".format(flavorlist)

        return flavor_uuid

    def delete_flavor(self, flavor_id):
        '''Deletes a tenant flavor from VIM identify by its id
        Returns the used id or raise an exception'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def new_image(self,image_dict):
        '''
        Adds a tenant image to VIM
        Returns:
            200, image-id        if the image is created
            <0, message          if there is an error
        '''

        print " ################################################################### "
        print " new_image contains  {}".format(image_dict)
        print " ################################################################### "


    def delete_image(self, image_id):
        '''Deletes a tenant image from VIM'''
        '''Returns the HTTP response code and a message indicating details of the success or fail'''

        print " ################################################################### "
        print " delete_image contains  {}".format(image_id)
        print " ################################################################### "

        raise vimconnNotImplemented( "Should have implemented this" )

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
                catalogItem = ET.fromstring(response.content)
                entity = [child for child in catalogItem if
                          child.get("type") == "application/vnd.vmware.vcloud.vAppTemplate+xml"][0]
                href = entity.get('href')
                template = href
                response = Http.get(href, headers=vca.vcloud_session.get_vcloud_headers(),
                                    verify=vca.verify, logger=self.logger)

                if response.status_code == requests.codes.ok:
                    media = mediaType.parseString(response.content, True)
                    link = filter(lambda link: link.get_rel() == 'upload:default', media.get_Files().get_File()[0].get_Link())[0]
                    headers = vca.vcloud_session.get_vcloud_headers()
                    headers['Content-Type'] = 'Content-Type text/xml'
                    response = Http.put(link.get_href(), data=open(media_file_name, 'rb'), headers=headers, verify=vca.verify,logger=self.logger)
                    if response.status_code != requests.codes.ok:
                        self.logger.debug("Failed create vApp template for catalog name {} and image {}".format(catalog_name, media_file_name))
                        return False

                time.sleep(5)

                self.logger.debug("Failed create vApp template for catalog name {} and image {}".
                                  format(catalog_name, media_file_name))

                # uploading VMDK file
                # check status of OVF upload
                response = Http.get(template, headers=vca.vcloud_session.get_vcloud_headers(), verify=vca.verify, logger=self.logger)
                if response.status_code == requests.codes.ok:
                    media = mediaType.parseString(response.content, True)
                    link = filter(lambda link: link.get_rel() == 'upload:default', media.get_Files().get_File()[0].get_Link())[0]

                    # The OVF file and VMDK must be in a same directory
                    head, tail = os.path.split(media_file_name)
                    filevmdk = head + '/' + os.path.basename(link.get_href())

                    os.path.isfile(filevmdk)
                    statinfo = os.stat(filevmdk)

                    # TODO debug output remove it
                    #print media.get_Files().get_File()[0].get_Link()[0].get_href()
                    #print media.get_Files().get_File()[1].get_Link()[0].get_href()
                    #print link.get_href()

                    # in case first element is pointer to OVF.
                    hrefvmdk = link.get_href().replace("descriptor.ovf","Cirros-disk1.vmdk")

                    f = open(filevmdk, 'rb')
                    bytes_transferred = 0
                    while bytes_transferred < statinfo.st_size:
                        my_bytes = f.read(chunk_bytes)
                        if len(my_bytes) <= chunk_bytes:
                            headers = vca.vcloud_session.get_vcloud_headers()
                            headers['Content-Range'] = 'bytes %s-%s/%s' % (bytes_transferred, len(my_bytes) - 1, statinfo.st_size)
                            headers['Content-Length'] = str(len(my_bytes))
                            response = Http.put(hrefvmdk, headers=headers, data=my_bytes, verify=vca.verify,logger=None)
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

    def upload_vimimage(self,vca, catalog_name, media_name, medial_file_name):
        """Upload media file"""
        return self.upload_ovf(vca, catalog_name, media_name.split(".")[0], medial_file_name, medial_file_name, True)

    def get_catalogid(self, catalog_name, catalogs):
        for catalog in catalogs:
            if catalog.name == catalog_name:
                print catalog.name
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
                    self.logger.debug("Found existing catalog entry for {} catalog id {}".format(catalog_name, self.get_catalogid(catalog_name, catalogs)))
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

    def get_vappid(self, vdc, vapp_name):
        """ Take vdc object and vApp name and returns vapp uuid or None
        """
        #UUID has following format https://host/api/vApp/vapp-30da58a3-e7c7-4d09-8f68-d4c8201169cf

        try:
            refs = filter(lambda ref: ref.name == vapp_name and ref.type_ == 'application/vnd.vmware.vcloud.vApp+xml',
                      vdc.ResourceEntities.ResourceEntity)

            if len(refs) == 1:
                return refs[0].href.split("vapp")[1][1:]
        except:
            return None
        return None

    def get_vappbyid(self, vdc, vapp_id):
        refs = filter(lambda ref: ref.type_ == 'application/vnd.vmware.vcloud.vApp+xml',
                      vdc.ResourceEntities.ResourceEntity)
        for ref in refs:
            print ref.href

        if len(refs) == 1:
            return refs[0].href.split("vapp")[1][1:]

    def new_vminstance(self,name,description,start,image_id,flavor_id,net_list,cloud_config=None):
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

        # TODO following attribute need be featched from flavor / OVF file must contain same data.
        # task = self.vca.create_vapp(vdc_name, vapp_name, template, catalog,
        #                             vm_name=vm_name,
        #                             vm_cpus=cpu,
        #                             vm_memory=memory)
        #

        catalogs = vca.get_catalogs()
        #image upload creates template name as catalog name space Template.
        templateName = self.get_catalogbyid(image_id, catalogs) + ' Template'
        task = vca.create_vapp(self.tenant_name, name, templateName, self.get_catalogbyid(image_id,catalogs), vm_name=name)
        if task is False:
            return -1, " Failed deploy vApp {}".format(name)

        result = vca.block_until_completed(task)
        if result:
            vappID = self.get_vappid(vca.get_vdc(self.tenant_name), name)
            if vappID is None:
                return -1, " Failed featch UUID for vApp {}".format(name)
            else:
                return vappID

        return -1, " Failed create vApp {}".format(name)

    def get_vminstance(self,vm_id):
        '''Returns the VM instance information from VIM'''

        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed.")


        raise vimconnNotImplemented( "Should have implemented this" )

    def delete_vminstance(self, vm_id):
        '''Removes a VM instance from VIM'''
        '''Returns the instance identifier'''

        print " ###### {} ".format(vm_id)

        vca = self.connect()
        if not vca:
            raise vimconn.vimconnConnectionException("self.connect() is failed.")

        thevdc = vca.get_vdc(self.tenant_name)
        self.get_vappid(vca.get_vdc(self.tenant_name), name)




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
        '''
        raise vimconnNotImplemented( "Should have implemented this" )

    def action_vminstance(self, vm_id, action_dict):
        '''Send and action over a VM instance from VIM
        Returns the vm_id if the action was successfully sent to the VIM'''
        raise vimconnNotImplemented( "Should have implemented this" )

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
        raise vimconnNotImplemented( "Should have implemented this" )

#NOT USED METHODS in current version

    def host_vim2gui(self, host, server_dict):
        '''Transform host dictionary from VIM format to GUI format,
        and append to the server_dict
        '''
        raise vimconnNotImplemented( "Should have implemented this" )

    def get_hosts_info(self):
        '''Get the information of deployed hosts
        Returns the hosts content'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def get_hosts(self, vim_tenant):
        '''Get the hosts and deployed instances
        Returns the hosts content'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def get_processor_rankings(self):
        '''Get the processor rankings in the VIM database'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def new_host(self, host_data):
        '''Adds a new host to VIM'''
        '''Returns status code of the VIM response'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def new_external_port(self, port_data):
        '''Adds a external port to VIM'''
        '''Returns the port identifier'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def new_external_network(self,net_name,net_type):
        '''Adds a external network to VIM (shared)'''
        '''Returns the network identifier'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def connect_port_network(self, port_id, network_id, admin=False):
        '''Connects a external port to a network'''
        '''Returns status code of the VIM response'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def new_vminstancefromJSON(self, vm_data):
        '''Adds a VM instance to VIM'''
        '''Returns the instance identifier'''
        raise vimconnNotImplemented( "Should have implemented this" )

