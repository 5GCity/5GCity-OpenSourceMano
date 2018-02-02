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


from pyvcloud.vcloudair import VCA
from pyvcloud import Http
from xml.etree import ElementTree as XmlElementTree
from pyvcloud.schema.vcd.v1_5.schemas.vcloud import mediaType
import sys,os
import logging
import requests
import time
import re


STANDALONE = 'standalone'
VCAVERSION = '5.9'

class vCloudconfig(object):
    def __init__(self, host=None, user=None, password=None,orgname=None, logger=None):
        self.url = host
        self.user = user
        self.password = password
        self.org = orgname
        self.logger = logger

    def connect(self):
        """ Method connect as normal user to vCloud director.

            Returns:
                The return vca object that letter can be used to connect to vCloud director as admin for VDC
        """

        try:
            self.logger.debug("Logging in to a vca {} as {} to datacenter {}.".format(self.org,
                                                                                      self.user,
                                                                                      self.org))
            vca = VCA(host=self.url,
                      username=self.user,
                      service_type=STANDALONE,
                      version=VCAVERSION,
                      verify=False,
                      log=False)

            result = vca.login(password=self.password, org=self.org)
            if not result:
                raise vimconn.vimconnConnectionException("Can't connect to a vCloud director as: {}".format(self.user))
            result = vca.login(token=vca.token, org=self.org, org_url=vca.vcloud_session.org_url)
            if result is True:
                self.logger.info(
                    "Successfully logged to a vcloud direct org: {} as user: {}".format(self.org, self.user))

        except:
            raise vimconn.vimconnConnectionException("Can't connect to a vCloud director org: "
                                                     "{} as user: {}".format(self.org, self.user))

        return vca

    def upload_ovf(self, catalog_name=None, image_name=None, media_file_name=None,
                   description='', progress=False, chunk_bytes=128 * 1024):
        """
        Uploads a OVF file to a vCloud catalog

        catalog_name: (str): The name of the catalog to upload the media.
        media_file_name: (str): The name of the local media file to upload.
        return: (bool) True if the media file was successfully uploaded, false otherwise.
        """
        vca = self.connect()   

        # Creating new catalog in vCD
        task = vca.create_catalog(catalog_name, catalog_name)
        result = vca.block_until_completed(task)
        if not result:
            return False

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
                <UploadVAppTemplateParams name="{}" xmlns="http://www.vmware.com/vcloud/v1.5" xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1"><Description>{} vApp Template</Description></UploadVAppTemplateParams>
                """.format(catalog_name, catalog_name)
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
                                time.sleep(15)
                        self.logger.debug("OVF image sucessfully uploaded to the VMware vCloud Director")
                        return True
                    else:
                        self.logger.debug("Failed retrieve vApp template for catalog name {} for OVF {}".
                                          format(catalog_name, media_file_name))
                        return False
        except Exception as exp:
            self.logger.debug("Failed while uploading OVF to catalog {} for OVF file {} with Exception {}"
                .format(catalog_name,media_file_name, exp))
            raise Exception("Failed while uploading OVF to catalog {} for OVF file {} with Exception {}" \
                .format(catalog_name,media_file_name, exp))


if __name__ == "__main__":

    # vmware vcloud director credentials
    vcd_hostname = sys.argv[1]
    vcd_username = sys.argv[2]
    vcd_password = sys.argv[3]
    orgname = sys.argv[4]
    # OVF image path to be upload to vCD
    ovf_file_path = sys.argv[5]

    # changing virtual system type in ovf file
    fh = open(ovf_file_path,'r')
    content = fh.read()
    content = content.replace('<vssd:VirtualSystemType>vmx-7','<vssd:VirtualSystemType>vmx-07')
    fh.close() 
    fh1 = open(ovf_file_path,'w')
    fh1.write(content)
    fh1.close() 
     

    logging.basicConfig(filename='ovf_upload.log',level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    obj = vCloudconfig(vcd_hostname, vcd_username, vcd_password, orgname, logger)

    dirpath, filename = os.path.split(ovf_file_path)
    filename_name, file_extension = os.path.splitext(filename)

    # Get image name from cirros vnfd
    cirros_yaml = '../descriptor-packages/vnfd/cirros_vnf/src/cirros_vnfd.yaml'
    rh = open(cirros_yaml,'r')
    match = re.search("image:\s'(.*?)'\n",rh.read())
    if match: catalog = match.group(1)


    if file_extension == '.ovf':
        result = obj.upload_ovf(catalog_name=catalog, image_name='linux',
                                                media_file_name=ovf_file_path,
                                               description='', progress=False,
                                                       chunk_bytes=128 * 1024)
    
