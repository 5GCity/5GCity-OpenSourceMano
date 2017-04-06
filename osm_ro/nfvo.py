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
NFVO engine, implementing all the methods for the creation, deletion and management of vnfs, scenarios and instances
'''
__author__="Alfonso Tierno, Gerardo Garcia, Pablo Montes"
__date__ ="$16-sep-2014 22:05:01$"

import imp
#import json
import yaml
import utils
import vim_thread
from db_base import HTTP_Unauthorized, HTTP_Bad_Request, HTTP_Internal_Server_Error, HTTP_Not_Found,\
    HTTP_Conflict, HTTP_Method_Not_Allowed
import console_proxy_thread as cli
import vimconn
import logging
import collections
from db_base import db_base_Exception
import nfvo_db
from threading import Lock
from time import time

global global_config
global vimconn_imported
global logger
global default_volume_size
default_volume_size = '5' #size in GB


vimconn_imported = {}   # dictionary with VIM type as key, loaded module as value
vim_threads = {"running":{}, "deleting": {}, "names": []}      # threads running for attached-VIMs
vim_persistent_info = {}
logger = logging.getLogger('openmano.nfvo')
task_lock = Lock()
task_dict = {}
last_task_id = 0.0
db=None
db_lock=Lock()

class NfvoException(Exception):
    def __init__(self, message, http_code):
        self.http_code = http_code
        Exception.__init__(self, message)


def get_task_id():
    global last_task_id
    task_id = time()
    if task_id <= last_task_id:
        task_id = last_task_id + 0.000001
    last_task_id = task_id
    return "TASK.{:.6f}".format(task_id)


def new_task(name, params, store=True, depends=None):
    task_id = get_task_id()
    task = {"status": "enqueued", "id": task_id, "name": name, "params": params}
    if depends:
        task["depends"] = depends
    if store:
        task_dict[task_id] = task
    return task


def is_task_id(id):
    return True if id[:5] == "TASK." else False


def get_non_used_vim_name(datacenter_name, datacenter_id, tenant_name, tenant_id):
    name = datacenter_name[:16]
    if name not in vim_threads["names"]:
        vim_threads["names"].append(name)
        return name
    name = datacenter_name[:16] + "." + tenant_name[:16]
    if name not in vim_threads["names"]:
        vim_threads["names"].append(name)
        return name
    name = datacenter_id + "-" + tenant_id
    vim_threads["names"].append(name)
    return name


def start_service(mydb):
    global db, global_config
    db = nfvo_db.nfvo_db()
    db.connect(global_config['db_host'], global_config['db_user'], global_config['db_passwd'], global_config['db_name'])
    from_= 'tenants_datacenters as td join datacenters as d on td.datacenter_id=d.uuid join datacenter_tenants as dt on td.datacenter_tenant_id=dt.uuid'
    select_ = ('type','d.config as config','d.uuid as datacenter_id', 'vim_url', 'vim_url_admin', 'd.name as datacenter_name',
                   'dt.uuid as datacenter_tenant_id','dt.vim_tenant_name as vim_tenant_name','dt.vim_tenant_id as vim_tenant_id',
                   'user','passwd', 'dt.config as dt_config', 'nfvo_tenant_id')
    try:
        vims = mydb.get_rows(FROM=from_, SELECT=select_)
        for vim in vims:
            extra={'datacenter_tenant_id': vim.get('datacenter_tenant_id')}
            if vim["config"]:
                extra.update(yaml.load(vim["config"]))
            if vim.get('dt_config'):
                extra.update(yaml.load(vim["dt_config"]))
            if vim["type"] not in vimconn_imported:
                module_info=None
                try:
                    module = "vimconn_" + vim["type"]
                    module_info = imp.find_module(module)
                    vim_conn = imp.load_module(vim["type"], *module_info)
                    vimconn_imported[vim["type"]] = vim_conn
                except (IOError, ImportError) as e:
                    if module_info and module_info[0]:
                        file.close(module_info[0])
                    raise NfvoException("Unknown vim type '{}'. Can not open file '{}.py'; {}: {}".format(
                        vim["type"], module, type(e).__name__, str(e)), HTTP_Bad_Request)

            thread_id = vim["datacenter_id"] + "." + vim['nfvo_tenant_id']
            vim_persistent_info[thread_id] = {}
            try:
                #if not tenant:
                #    return -HTTP_Bad_Request, "You must provide a valid tenant name or uuid for VIM  %s" % ( vim["type"])
                myvim = vimconn_imported[ vim["type"] ].vimconnector(
                    uuid=vim['datacenter_id'], name=vim['datacenter_name'],
                    tenant_id=vim['vim_tenant_id'], tenant_name=vim['vim_tenant_name'],
                    url=vim['vim_url'], url_admin=vim['vim_url_admin'],
                    user=vim['user'], passwd=vim['passwd'],
                    config=extra, persistent_info=vim_persistent_info[thread_id]
                )
            except Exception as e:
                raise NfvoException("Error at VIM  {}; {}: {}".format(vim["type"], type(e).__name__, str(e)), HTTP_Internal_Server_Error)
            thread_name = get_non_used_vim_name(vim['datacenter_name'], vim['vim_tenant_id'], vim['vim_tenant_name'], vim['vim_tenant_id'])
            new_thread = vim_thread.vim_thread(myvim, task_lock, thread_name, vim['datacenter_name'],
                                               vim.get('datacenter_tenant_id'), db=db, db_lock=db_lock)
            new_thread.start()
            vim_threads["running"][thread_id] = new_thread
    except db_base_Exception as e:
        raise NfvoException(str(e) + " at nfvo.get_vim", e.http_code)


def stop_service():
    for thread_id,thread in vim_threads["running"].items():
        thread.insert_task(new_task("exit", None, store=False))
        vim_threads["deleting"][thread_id] = thread
    vim_threads["running"] = {}


def get_flavorlist(mydb, vnf_id, nfvo_tenant=None):
    '''Obtain flavorList
    return result, content:
        <0, error_text upon error
        nb_records, flavor_list on success
    '''
    WHERE_dict={}
    WHERE_dict['vnf_id'] = vnf_id
    if nfvo_tenant is not None:
        WHERE_dict['nfvo_tenant_id'] = nfvo_tenant

    #result, content = mydb.get_table(FROM='vms join vnfs on vms.vnf_id = vnfs.uuid',SELECT=('uuid'),WHERE=WHERE_dict )
    #result, content = mydb.get_table(FROM='vms',SELECT=('vim_flavor_id',),WHERE=WHERE_dict )
    flavors = mydb.get_rows(FROM='vms join flavors on vms.flavor_id=flavors.uuid',SELECT=('flavor_id',),WHERE=WHERE_dict )
    #print "get_flavor_list result:", result
    #print "get_flavor_list content:", content
    flavorList=[]
    for flavor in flavors:
        flavorList.append(flavor['flavor_id'])
    return flavorList


def get_imagelist(mydb, vnf_id, nfvo_tenant=None):
    '''Obtain imageList
    return result, content:
        <0, error_text upon error
        nb_records, flavor_list on success
    '''
    WHERE_dict={}
    WHERE_dict['vnf_id'] = vnf_id
    if nfvo_tenant is not None:
        WHERE_dict['nfvo_tenant_id'] = nfvo_tenant

    #result, content = mydb.get_table(FROM='vms join vnfs on vms-vnf_id = vnfs.uuid',SELECT=('uuid'),WHERE=WHERE_dict )
    images = mydb.get_rows(FROM='vms join images on vms.image_id=images.uuid',SELECT=('image_id',),WHERE=WHERE_dict )
    imageList=[]
    for image in images:
        imageList.append(image['image_id'])
    return imageList


def get_vim(mydb, nfvo_tenant=None, datacenter_id=None, datacenter_name=None, datacenter_tenant_id=None,
            vim_tenant=None, vim_tenant_name=None, vim_user=None, vim_passwd=None):
    '''Obtain a dictionary of VIM (datacenter) classes with some of the input parameters
    return dictionary with {datacenter_id: vim_class, ... }. vim_class contain:
            'nfvo_tenant_id','datacenter_id','vim_tenant_id','vim_url','vim_url_admin','datacenter_name','type','user','passwd'
        raise exception upon error
    '''
    WHERE_dict={}
    if nfvo_tenant     is not None:  WHERE_dict['nfvo_tenant_id'] = nfvo_tenant
    if datacenter_id   is not None:  WHERE_dict['d.uuid']  = datacenter_id
    if datacenter_tenant_id is not None:  WHERE_dict['datacenter_tenant_id']  = datacenter_tenant_id
    if datacenter_name is not None:  WHERE_dict['d.name']  = datacenter_name
    if vim_tenant      is not None:  WHERE_dict['dt.vim_tenant_id']  = vim_tenant
    if vim_tenant_name is not None:  WHERE_dict['vim_tenant_name']  = vim_tenant_name
    if nfvo_tenant or vim_tenant or vim_tenant_name or datacenter_tenant_id:
        from_= 'tenants_datacenters as td join datacenters as d on td.datacenter_id=d.uuid join datacenter_tenants as dt on td.datacenter_tenant_id=dt.uuid'
        select_ = ('type','d.config as config','d.uuid as datacenter_id', 'vim_url', 'vim_url_admin', 'd.name as datacenter_name',
                   'dt.uuid as datacenter_tenant_id','dt.vim_tenant_name as vim_tenant_name','dt.vim_tenant_id as vim_tenant_id',
                   'user','passwd', 'dt.config as dt_config')
    else:
        from_ = 'datacenters as d'
        select_ = ('type','config','d.uuid as datacenter_id', 'vim_url', 'vim_url_admin', 'd.name as datacenter_name')
    try:
        vims = mydb.get_rows(FROM=from_, SELECT=select_, WHERE=WHERE_dict )
        vim_dict={}
        for vim in vims:
            extra={'datacenter_tenant_id': vim.get('datacenter_tenant_id')}
            if vim["config"]:
                extra.update(yaml.load(vim["config"]))
            if vim.get('dt_config'):
                extra.update(yaml.load(vim["dt_config"]))
            if vim["type"] not in vimconn_imported:
                module_info=None
                try:
                    module = "vimconn_" + vim["type"]
                    module_info = imp.find_module(module)
                    vim_conn = imp.load_module(vim["type"], *module_info)
                    vimconn_imported[vim["type"]] = vim_conn
                except (IOError, ImportError) as e:
                    if module_info and module_info[0]:
                        file.close(module_info[0])
                    raise NfvoException("Unknown vim type '{}'. Can not open file '{}.py'; {}: {}".format(
                                            vim["type"], module, type(e).__name__, str(e)), HTTP_Bad_Request)

            try:
                if 'nfvo_tenant_id' in vim:
                    thread_id = vim["datacenter_id"] + "." + vim['nfvo_tenant_id']
                    if thread_id not in vim_persistent_info:
                        vim_persistent_info[thread_id] = {}
                    persistent_info = vim_persistent_info[thread_id]
                else:
                    persistent_info = {}
                #if not tenant:
                #    return -HTTP_Bad_Request, "You must provide a valid tenant name or uuid for VIM  %s" % ( vim["type"])
                vim_dict[ vim['datacenter_id'] ] = vimconn_imported[ vim["type"] ].vimconnector(
                                uuid=vim['datacenter_id'], name=vim['datacenter_name'],
                                tenant_id=vim.get('vim_tenant_id',vim_tenant),
                                tenant_name=vim.get('vim_tenant_name',vim_tenant_name),
                                url=vim['vim_url'], url_admin=vim['vim_url_admin'],
                                user=vim.get('user',vim_user), passwd=vim.get('passwd',vim_passwd),
                                config=extra, persistent_info=persistent_info
                        )
            except Exception as e:
                raise NfvoException("Error at VIM  {}; {}: {}".format(vim["type"], type(e).__name__, str(e)), HTTP_Internal_Server_Error)
        return vim_dict
    except db_base_Exception as e:
        raise NfvoException(str(e) + " at nfvo.get_vim", e.http_code)


def rollback(mydb,  vims, rollback_list):
    undeleted_items=[]
    #delete things by reverse order
    for i in range(len(rollback_list)-1, -1, -1):
        item = rollback_list[i]
        if item["where"]=="vim":
            if item["vim_id"] not in vims:
                continue
            vim=vims[ item["vim_id"] ]
            try:
                if item["what"]=="image":
                    vim.delete_image(item["uuid"])
                    mydb.delete_row(FROM="datacenters_images", WHERE={"datacenter_id": vim["id"], "vim_id":item["uuid"]})
                elif item["what"]=="flavor":
                    vim.delete_flavor(item["uuid"])
                    mydb.delete_row(FROM="datacenters_flavors", WHERE={"datacenter_id": vim["id"], "vim_id":item["uuid"]})
                elif item["what"]=="network":
                    vim.delete_network(item["uuid"])
                elif item["what"]=="vm":
                    vim.delete_vminstance(item["uuid"])
            except vimconn.vimconnException as e:
                logger.error("Error in rollback. Not possible to delete VIM %s '%s'. Message: %s", item['what'], item["uuid"], str(e))
                undeleted_items.append("{} {} from VIM {}".format(item['what'], item["uuid"], vim["name"]))
            except db_base_Exception as e:
                logger.error("Error in rollback. Not possible to delete %s '%s' from DB.datacenters Message: %s", item['what'], item["uuid"], str(e))

        else: # where==mano
            try:
                if item["what"]=="image":
                    mydb.delete_row(FROM="images", WHERE={"uuid": item["uuid"]})
                elif item["what"]=="flavor":
                    mydb.delete_row(FROM="flavors", WHERE={"uuid": item["uuid"]})
            except db_base_Exception as e:
                logger.error("Error in rollback. Not possible to delete %s '%s' from DB. Message: %s", item['what'], item["uuid"], str(e))
                undeleted_items.append("{} '{}'".format(item['what'], item["uuid"]))
    if len(undeleted_items)==0:
        return True," Rollback successful."
    else:
        return False," Rollback fails to delete: " + str(undeleted_items)


def check_vnf_descriptor(vnf_descriptor, vnf_descriptor_version=1):
    global global_config
    #create a dictionary with vnfc-name: vnfc:interface-list  key:values pairs
    vnfc_interfaces={}
    for vnfc in vnf_descriptor["vnf"]["VNFC"]:
        name_dict = {}
        #dataplane interfaces
        for numa in vnfc.get("numas",() ):
            for interface in numa.get("interfaces",()):
                if interface["name"] in name_dict:
                    raise NfvoException(
                        "Error at vnf:VNFC[name:'{}']:numas:interfaces:name, interface name '{}' already used in this VNFC".format(
                            vnfc["name"], interface["name"]),
                        HTTP_Bad_Request)
                name_dict[ interface["name"] ] = "underlay"
        #bridge interfaces
        for interface in vnfc.get("bridge-ifaces",() ):
            if interface["name"] in name_dict:
                raise NfvoException(
                    "Error at vnf:VNFC[name:'{}']:bridge-ifaces:name, interface name '{}' already used in this VNFC".format(
                        vnfc["name"], interface["name"]),
                    HTTP_Bad_Request)
            name_dict[ interface["name"] ] = "overlay"
        vnfc_interfaces[ vnfc["name"] ] = name_dict
        # check bood-data info
        if "boot-data" in vnfc:
            # check that user-data is incompatible with users and config-files
            if (vnfc["boot-data"].get("users") or vnfc["boot-data"].get("config-files")) and vnfc["boot-data"].get("user-data"):
                raise NfvoException(
                    "Error at vnf:VNFC:boot-data, fields 'users' and 'config-files' are not compatible with 'user-data'",
                    HTTP_Bad_Request)

    #check if the info in external_connections matches with the one in the vnfcs
    name_list=[]
    for external_connection in vnf_descriptor["vnf"].get("external-connections",() ):
        if external_connection["name"] in name_list:
            raise NfvoException(
                "Error at vnf:external-connections:name, value '{}' already used as an external-connection".format(
                    external_connection["name"]),
                HTTP_Bad_Request)
        name_list.append(external_connection["name"])
        if external_connection["VNFC"] not in vnfc_interfaces:
            raise NfvoException(
                "Error at vnf:external-connections[name:'{}']:VNFC, value '{}' does not match any VNFC".format(
                    external_connection["name"], external_connection["VNFC"]),
                HTTP_Bad_Request)

        if external_connection["local_iface_name"] not in vnfc_interfaces[ external_connection["VNFC"] ]:
            raise NfvoException(
                "Error at vnf:external-connections[name:'{}']:local_iface_name, value '{}' does not match any interface of this VNFC".format(
                    external_connection["name"],
                    external_connection["local_iface_name"]),
                HTTP_Bad_Request )

    #check if the info in internal_connections matches with the one in the vnfcs
    name_list=[]
    for internal_connection in vnf_descriptor["vnf"].get("internal-connections",() ):
        if internal_connection["name"] in name_list:
            raise NfvoException(
                "Error at vnf:internal-connections:name, value '%s' already used as an internal-connection".format(
                    internal_connection["name"]),
                HTTP_Bad_Request)
        name_list.append(internal_connection["name"])
        #We should check that internal-connections of type "ptp" have only 2 elements

        if len(internal_connection["elements"])>2 and (internal_connection.get("type") == "ptp" or internal_connection.get("type") == "e-line"):
            raise NfvoException(
                "Error at 'vnf:internal-connections[name:'{}']:elements', size must be 2 for a '{}' type. Consider change it to '{}' type".format(
                    internal_connection["name"],
                    'ptp' if vnf_descriptor_version==1 else 'e-line',
                    'data' if vnf_descriptor_version==1 else "e-lan"),
                HTTP_Bad_Request)
        for port in internal_connection["elements"]:
            vnf = port["VNFC"]
            iface = port["local_iface_name"]
            if vnf not in vnfc_interfaces:
                raise NfvoException(
                    "Error at vnf:internal-connections[name:'{}']:elements[]:VNFC, value '{}' does not match any VNFC".format(
                        internal_connection["name"], vnf),
                    HTTP_Bad_Request)
            if iface not in vnfc_interfaces[ vnf ]:
                raise NfvoException(
                    "Error at vnf:internal-connections[name:'{}']:elements[]:local_iface_name, value '{}' does not match any interface of this VNFC".format(
                        internal_connection["name"], iface),
                    HTTP_Bad_Request)
                return -HTTP_Bad_Request,
            if vnf_descriptor_version==1 and "type" not in internal_connection:
                if vnfc_interfaces[vnf][iface] == "overlay":
                    internal_connection["type"] = "bridge"
                else:
                    internal_connection["type"] = "data"
            if vnf_descriptor_version==2 and "implementation" not in internal_connection:
                if vnfc_interfaces[vnf][iface] == "overlay":
                    internal_connection["implementation"] = "overlay"
                else:
                    internal_connection["implementation"] = "underlay"
            if (internal_connection.get("type") == "data" or internal_connection.get("type") == "ptp" or \
                internal_connection.get("implementation") == "underlay") and vnfc_interfaces[vnf][iface] == "overlay":
                raise NfvoException(
                    "Error at vnf:internal-connections[name:'{}']:elements[]:{}, interface of type {} connected to an {} network".format(
                        internal_connection["name"],
                        iface, 'bridge' if vnf_descriptor_version==1 else 'overlay',
                        'data' if vnf_descriptor_version==1 else 'underlay'),
                    HTTP_Bad_Request)
            if (internal_connection.get("type") == "bridge" or internal_connection.get("implementation") == "overlay") and \
                vnfc_interfaces[vnf][iface] == "underlay":
                raise NfvoException(
                    "Error at vnf:internal-connections[name:'{}']:elements[]:{}, interface of type {} connected to an {} network".format(
                        internal_connection["name"], iface,
                        'data' if vnf_descriptor_version==1 else 'underlay',
                        'bridge' if vnf_descriptor_version==1 else 'overlay'),
                    HTTP_Bad_Request)


def create_or_use_image(mydb, vims, image_dict, rollback_list, only_create_at_vim=False, return_on_error = None):
    #look if image exist
    if only_create_at_vim:
        image_mano_id = image_dict['uuid']
        if return_on_error == None:
            return_on_error = True
    else:
        if image_dict['location']:
            images = mydb.get_rows(FROM="images", WHERE={'location':image_dict['location'], 'metadata':image_dict['metadata']})
        else:
            images = mydb.get_rows(FROM="images", WHERE={'universal_name':image_dict['universal_name'], 'checksum':image_dict['checksum']})
        if len(images)>=1:
            image_mano_id = images[0]['uuid']
        else:
            #create image in MANO DB
            temp_image_dict={'name':image_dict['name'],         'description':image_dict.get('description',None),
                            'location':image_dict['location'],  'metadata':image_dict.get('metadata',None),
                            'universal_name':image_dict['universal_name'] , 'checksum':image_dict['checksum']
                            }
            #temp_image_dict['location'] = image_dict.get('new_location') if image_dict['location'] is None
            image_mano_id = mydb.new_row('images', temp_image_dict, add_uuid=True)
            rollback_list.append({"where":"mano", "what":"image","uuid":image_mano_id})
    #create image at every vim
    for vim_id,vim in vims.iteritems():
        image_created="false"
        #look at database
        image_db = mydb.get_rows(FROM="datacenters_images", WHERE={'datacenter_id':vim_id, 'image_id':image_mano_id})
        #look at VIM if this image exist
        try:
            if image_dict['location'] is not None:
                image_vim_id = vim.get_image_id_from_path(image_dict['location'])
            else:
                filter_dict = {}
                filter_dict['name'] = image_dict['universal_name']
                if image_dict.get('checksum') != None:
                    filter_dict['checksum'] = image_dict['checksum']
                #logger.debug('>>>>>>>> Filter dict: %s', str(filter_dict))
                vim_images = vim.get_image_list(filter_dict)
                #logger.debug('>>>>>>>> VIM images: %s', str(vim_images))
                if len(vim_images) > 1:
                    raise vimconn.vimconnException("More than one candidate VIM image found for filter: {}".format(str(filter_dict)), HTTP_Conflict)
                elif len(vim_images) == 0:
                    raise vimconn.vimconnNotFoundException("Image not found at VIM with filter: '{}'".format(str(filter_dict)))
                else:
                    #logger.debug('>>>>>>>> VIM image 0: %s', str(vim_images[0]))
                    image_vim_id = vim_images[0]['id']

        except vimconn.vimconnNotFoundException as e:
            #Create the image in VIM only if image_dict['location'] or image_dict['new_location'] is not None
            try:
                #image_dict['location']=image_dict.get('new_location') if image_dict['location'] is None
                if image_dict['location']:
                    image_vim_id = vim.new_image(image_dict)
                    rollback_list.append({"where":"vim", "vim_id": vim_id, "what":"image","uuid":image_vim_id})
                    image_created="true"
                else:
                    #If we reach this point, then the image has image name, and optionally checksum, and could not be found
                    raise vimconn.vimconnException(str(e))
            except vimconn.vimconnException as e:
                if return_on_error:
                    logger.error("Error creating image at VIM '%s': %s", vim["name"], str(e))
                    raise
                image_vim_id = None
                logger.warn("Error creating image at VIM '%s': %s", vim["name"], str(e))
                continue
        except vimconn.vimconnException as e:
            if return_on_error:
                logger.error("Error contacting VIM to know if the image exists at VIM: %s", str(e))
                raise
            logger.warn("Error contacting VIM to know if the image exists at VIM: %s", str(e))
            image_vim_id = None
            continue
        #if we reach here, the image has been created or existed
        if len(image_db)==0:
            #add new vim_id at datacenters_images
            mydb.new_row('datacenters_images', {'datacenter_id':vim_id, 'image_id':image_mano_id, 'vim_id': image_vim_id, 'created':image_created})
        elif image_db[0]["vim_id"]!=image_vim_id:
            #modify existing vim_id at datacenters_images
            mydb.update_rows('datacenters_images', UPDATE={'vim_id':image_vim_id}, WHERE={'datacenter_id':vim_id, 'image_id':image_mano_id})

    return image_vim_id if only_create_at_vim else image_mano_id


def create_or_use_flavor(mydb, vims, flavor_dict, rollback_list, only_create_at_vim=False, return_on_error = None):
    temp_flavor_dict= {'disk':flavor_dict.get('disk',1),
            'ram':flavor_dict.get('ram'),
            'vcpus':flavor_dict.get('vcpus'),
        }
    if 'extended' in flavor_dict and flavor_dict['extended']==None:
        del flavor_dict['extended']
    if 'extended' in flavor_dict:
        temp_flavor_dict['extended']=yaml.safe_dump(flavor_dict['extended'],default_flow_style=True,width=256)

    #look if flavor exist
    if only_create_at_vim:
        flavor_mano_id = flavor_dict['uuid']
        if return_on_error == None:
            return_on_error = True
    else:
        flavors = mydb.get_rows(FROM="flavors", WHERE=temp_flavor_dict)
        if len(flavors)>=1:
            flavor_mano_id = flavors[0]['uuid']
        else:
            #create flavor
            #create one by one the images of aditional disks
            dev_image_list=[] #list of images
            if 'extended' in flavor_dict and flavor_dict['extended']!=None:
                dev_nb=0
                for device in flavor_dict['extended'].get('devices',[]):
                    if "image" not in device and "image name" not in device:
                        continue
                    image_dict={}
                    image_dict['name']=device.get('image name',flavor_dict['name']+str(dev_nb)+"-img")
                    image_dict['universal_name']=device.get('image name')
                    image_dict['description']=flavor_dict['name']+str(dev_nb)+"-img"
                    image_dict['location']=device.get('image')
                    #image_dict['new_location']=vnfc.get('image location')
                    image_dict['checksum']=device.get('image checksum')
                    image_metadata_dict = device.get('image metadata', None)
                    image_metadata_str = None
                    if image_metadata_dict != None:
                        image_metadata_str = yaml.safe_dump(image_metadata_dict,default_flow_style=True,width=256)
                    image_dict['metadata']=image_metadata_str
                    image_id = create_or_use_image(mydb, vims, image_dict, rollback_list)
                    #print "Additional disk image id for VNFC %s: %s" % (flavor_dict['name']+str(dev_nb)+"-img", image_id)
                    dev_image_list.append(image_id)
                    dev_nb += 1
            temp_flavor_dict['name'] = flavor_dict['name']
            temp_flavor_dict['description'] = flavor_dict.get('description',None)
            content = mydb.new_row('flavors', temp_flavor_dict, add_uuid=True)
            flavor_mano_id= content
            rollback_list.append({"where":"mano", "what":"flavor","uuid":flavor_mano_id})
    #create flavor at every vim
    if 'uuid' in flavor_dict:
        del flavor_dict['uuid']
    flavor_vim_id=None
    for vim_id,vim in vims.items():
        flavor_created="false"
        #look at database
        flavor_db = mydb.get_rows(FROM="datacenters_flavors", WHERE={'datacenter_id':vim_id, 'flavor_id':flavor_mano_id})
        #look at VIM if this flavor exist  SKIPPED
        #res_vim, flavor_vim_id = vim.get_flavor_id_from_path(flavor_dict['location'])
        #if res_vim < 0:
        #    print "Error contacting VIM to know if the flavor %s existed previously." %flavor_vim_id
        #    continue
        #elif res_vim==0:

        #Create the flavor in VIM
        #Translate images at devices from MANO id to VIM id
        disk_list = []
        if 'extended' in flavor_dict and flavor_dict['extended']!=None and "devices" in flavor_dict['extended']:
            #make a copy of original devices
            devices_original=[]

            for device in flavor_dict["extended"].get("devices",[]):
                dev={}
                dev.update(device)
                devices_original.append(dev)
                if 'image' in device:
                    del device['image']
                if 'image metadata' in device:
                    del device['image metadata']
            dev_nb=0
            for index in range(0,len(devices_original)) :
                device=devices_original[index]
                if "image" not in device and "image name" not in device:
                    if 'size' in device:
                        disk_list.append({'size': device.get('size', default_volume_size)})
                    continue
                image_dict={}
                image_dict['name']=device.get('image name',flavor_dict['name']+str(dev_nb)+"-img")
                image_dict['universal_name']=device.get('image name')
                image_dict['description']=flavor_dict['name']+str(dev_nb)+"-img"
                image_dict['location']=device.get('image')
                #image_dict['new_location']=device.get('image location')
                image_dict['checksum']=device.get('image checksum')
                image_metadata_dict = device.get('image metadata', None)
                image_metadata_str = None
                if image_metadata_dict != None:
                    image_metadata_str = yaml.safe_dump(image_metadata_dict,default_flow_style=True,width=256)
                image_dict['metadata']=image_metadata_str
                image_mano_id=create_or_use_image(mydb, vims, image_dict, rollback_list, only_create_at_vim=False, return_on_error=return_on_error )
                image_dict["uuid"]=image_mano_id
                image_vim_id=create_or_use_image(mydb, vims, image_dict, rollback_list, only_create_at_vim=True, return_on_error=return_on_error)

                #save disk information (image must be based on and size
                disk_list.append({'image_id': image_vim_id, 'size': device.get('size', default_volume_size)})

                flavor_dict["extended"]["devices"][index]['imageRef']=image_vim_id
                dev_nb += 1
        if len(flavor_db)>0:
            #check that this vim_id exist in VIM, if not create
            flavor_vim_id=flavor_db[0]["vim_id"]
            try:
                vim.get_flavor(flavor_vim_id)
                continue #flavor exist
            except vimconn.vimconnException:
                pass
        #create flavor at vim
        logger.debug("nfvo.create_or_use_flavor() adding flavor to VIM %s", vim["name"])
        try:
            flavor_vim_id = None
            flavor_vim_id=vim.get_flavor_id_from_data(flavor_dict)
            flavor_create="false"
        except vimconn.vimconnException as e:
            pass
        try:
            if not flavor_vim_id:
                flavor_vim_id = vim.new_flavor(flavor_dict)
                rollback_list.append({"where":"vim", "vim_id": vim_id, "what":"flavor","uuid":flavor_vim_id})
                flavor_created="true"
        except vimconn.vimconnException as e:
            if return_on_error:
                logger.error("Error creating flavor at VIM %s: %s.", vim["name"], str(e))
                raise
            logger.warn("Error creating flavor at VIM %s: %s.", vim["name"], str(e))
            flavor_vim_id = None
            continue
        #if reach here the flavor has been create or exist
        if len(flavor_db)==0:
            #add new vim_id at datacenters_flavors
            extended_devices_yaml = None
            if len(disk_list) > 0:
                extended_devices = dict()
                extended_devices['disks'] = disk_list
                extended_devices_yaml = yaml.safe_dump(extended_devices,default_flow_style=True,width=256)
            mydb.new_row('datacenters_flavors',
                        {'datacenter_id':vim_id, 'flavor_id':flavor_mano_id, 'vim_id': flavor_vim_id,
                        'created':flavor_created,'extended': extended_devices_yaml})
        elif flavor_db[0]["vim_id"]!=flavor_vim_id:
            #modify existing vim_id at datacenters_flavors
            mydb.update_rows('datacenters_flavors', UPDATE={'vim_id':flavor_vim_id}, WHERE={'datacenter_id':vim_id, 'flavor_id':flavor_mano_id})

    return flavor_vim_id if only_create_at_vim else flavor_mano_id


def new_vnf(mydb, tenant_id, vnf_descriptor):
    global global_config

    # Step 1. Check the VNF descriptor
    check_vnf_descriptor(vnf_descriptor, vnf_descriptor_version=1)
    # Step 2. Check tenant exist
    vims = {}
    if tenant_id != "any":
        check_tenant(mydb, tenant_id)
        if "tenant_id" in vnf_descriptor["vnf"]:
            if vnf_descriptor["vnf"]["tenant_id"] != tenant_id:
                raise NfvoException("VNF can not have a different tenant owner '{}', must be '{}'".format(vnf_descriptor["vnf"]["tenant_id"], tenant_id),
                                    HTTP_Unauthorized)
        else:
            vnf_descriptor['vnf']['tenant_id'] = tenant_id
        # Step 3. Get the URL of the VIM from the nfvo_tenant and the datacenter
        if global_config["auto_push_VNF_to_VIMs"]:
            vims = get_vim(mydb, tenant_id)

    # Step 4. Review the descriptor and add missing  fields
    #print vnf_descriptor
    #logger.debug("Refactoring VNF descriptor with fields: description, public (default: true)")
    vnf_name = vnf_descriptor['vnf']['name']
    vnf_descriptor['vnf']['description'] = vnf_descriptor['vnf'].get("description", vnf_name)
    if "physical" in vnf_descriptor['vnf']:
        del vnf_descriptor['vnf']['physical']
    #print vnf_descriptor

    # Step 6. For each VNFC in the descriptor, flavors and images are created in the VIM
    logger.debug('BEGIN creation of VNF "%s"' % vnf_name)
    logger.debug("VNF %s: consisting of %d VNFC(s)" % (vnf_name,len(vnf_descriptor['vnf']['VNFC'])))

    #For each VNFC, we add it to the VNFCDict and we  create a flavor.
    VNFCDict = {}     # Dictionary, key: VNFC name, value: dict with the relevant information to create the VNF and VMs in the MANO database
    rollback_list = []    # It will contain the new images created in mano. It is used for rollback
    try:
        logger.debug("Creating additional disk images and new flavors in the VIM for each VNFC")
        for vnfc in vnf_descriptor['vnf']['VNFC']:
            VNFCitem={}
            VNFCitem["name"] = vnfc['name']
            VNFCitem["description"] = vnfc.get("description", 'VM %s of the VNF %s' %(vnfc['name'],vnf_name))

            #print "Flavor name: %s. Description: %s" % (VNFCitem["name"]+"-flv", VNFCitem["description"])

            myflavorDict = {}
            myflavorDict["name"] = vnfc['name']+"-flv"   #Maybe we could rename the flavor by using the field "image name" if exists
            myflavorDict["description"] = VNFCitem["description"]
            myflavorDict["ram"] = vnfc.get("ram", 0)
            myflavorDict["vcpus"] = vnfc.get("vcpus", 0)
            myflavorDict["disk"] = vnfc.get("disk", 1)
            myflavorDict["extended"] = {}

            devices = vnfc.get("devices")
            if devices != None:
                myflavorDict["extended"]["devices"] = devices

            # TODO:
            # Mapping from processor models to rankings should be available somehow in the NFVO. They could be taken from VIM or directly from a new database table
            # Another option is that the processor in the VNF descriptor specifies directly the ranking of the host

            # Previous code has been commented
            #if vnfc['processor']['model'] == "Intel(R) Xeon(R) CPU E5-4620 0 @ 2.20GHz" :
            #    myflavorDict["flavor"]['extended']['processor_ranking'] = 200
            #elif vnfc['processor']['model'] == "Intel(R) Xeon(R) CPU E5-2697 v2 @ 2.70GHz" :
            #    myflavorDict["flavor"]['extended']['processor_ranking'] = 300
            #else:
            #    result2, message = rollback(myvim, myvimURL, myvim_tenant, flavorList, imageList)
            #    if result2:
            #        print "Error creating flavor: unknown processor model. Rollback successful."
            #        return -HTTP_Bad_Request, "Error creating flavor: unknown processor model. Rollback successful."
            #    else:
            #        return -HTTP_Bad_Request, "Error creating flavor: unknown processor model. Rollback fail: you need to access VIM and delete the following %s" % message
            myflavorDict['extended']['processor_ranking'] = 100  #Hardcoded value, while we decide when the mapping is done

            if 'numas' in vnfc and len(vnfc['numas'])>0:
                myflavorDict['extended']['numas'] = vnfc['numas']

            #print myflavorDict

            # Step 6.2 New flavors are created in the VIM
            flavor_id = create_or_use_flavor(mydb, vims, myflavorDict, rollback_list)

            #print "Flavor id for VNFC %s: %s" % (vnfc['name'],flavor_id)
            VNFCitem["flavor_id"] = flavor_id
            VNFCDict[vnfc['name']] = VNFCitem

        logger.debug("Creating new images in the VIM for each VNFC")
        # Step 6.3 New images are created in the VIM
        #For each VNFC, we must create the appropriate image.
        #This "for" loop might be integrated with the previous one
        #In case this integration is made, the VNFCDict might become a VNFClist.
        for vnfc in vnf_descriptor['vnf']['VNFC']:
            #print "Image name: %s. Description: %s" % (vnfc['name']+"-img", VNFCDict[vnfc['name']]['description'])
            image_dict={}
            image_dict['name']=vnfc.get('image name',vnf_name+"-"+vnfc['name']+"-img")
            image_dict['universal_name']=vnfc.get('image name')
            image_dict['description']=vnfc.get('image name', VNFCDict[vnfc['name']]['description'])
            image_dict['location']=vnfc.get('VNFC image')
            #image_dict['new_location']=vnfc.get('image location')
            image_dict['checksum']=vnfc.get('image checksum')
            image_metadata_dict = vnfc.get('image metadata', None)
            image_metadata_str = None
            if image_metadata_dict is not None:
                image_metadata_str = yaml.safe_dump(image_metadata_dict,default_flow_style=True,width=256)
            image_dict['metadata']=image_metadata_str
            #print "create_or_use_image", mydb, vims, image_dict, rollback_list
            image_id = create_or_use_image(mydb, vims, image_dict, rollback_list)
            #print "Image id for VNFC %s: %s" % (vnfc['name'],image_id)
            VNFCDict[vnfc['name']]["image_id"] = image_id
            VNFCDict[vnfc['name']]["image_path"] = vnfc.get('VNFC image')
            if vnfc.get("boot-data"):
                VNFCDict[vnfc['name']]["boot_data"] = yaml.safe_dump(vnfc["boot-data"], default_flow_style=True, width=256)


        # Step 7. Storing the VNF descriptor in the repository
        if "descriptor" not in vnf_descriptor["vnf"]:
            vnf_descriptor["vnf"]["descriptor"] = yaml.safe_dump(vnf_descriptor, indent=4, explicit_start=True, default_flow_style=False)

        # Step 8. Adding the VNF to the NFVO DB
        vnf_id = mydb.new_vnf_as_a_whole(tenant_id,vnf_name,vnf_descriptor,VNFCDict)
        return vnf_id
    except (db_base_Exception, vimconn.vimconnException, KeyError) as e:
        _, message = rollback(mydb, vims, rollback_list)
        if isinstance(e, db_base_Exception):
            error_text = "Exception at database"
        elif isinstance(e, KeyError):
            error_text = "KeyError exception "
            e.http_code = HTTP_Internal_Server_Error
        else:
            error_text = "Exception at VIM"
        error_text += " {} {}. {}".format(type(e).__name__, str(e), message)
        #logger.error("start_scenario %s", error_text)
        raise NfvoException(error_text, e.http_code)


def new_vnf_v02(mydb, tenant_id, vnf_descriptor):
    global global_config

    # Step 1. Check the VNF descriptor
    check_vnf_descriptor(vnf_descriptor, vnf_descriptor_version=2)
    # Step 2. Check tenant exist
    vims = {}
    if tenant_id != "any":
        check_tenant(mydb, tenant_id)
        if "tenant_id" in vnf_descriptor["vnf"]:
            if vnf_descriptor["vnf"]["tenant_id"] != tenant_id:
                raise NfvoException("VNF can not have a different tenant owner '{}', must be '{}'".format(vnf_descriptor["vnf"]["tenant_id"], tenant_id),
                                    HTTP_Unauthorized)
        else:
            vnf_descriptor['vnf']['tenant_id'] = tenant_id
        # Step 3. Get the URL of the VIM from the nfvo_tenant and the datacenter
        if global_config["auto_push_VNF_to_VIMs"]:
            vims = get_vim(mydb, tenant_id)

    # Step 4. Review the descriptor and add missing  fields
    #print vnf_descriptor
    #logger.debug("Refactoring VNF descriptor with fields: description, public (default: true)")
    vnf_name = vnf_descriptor['vnf']['name']
    vnf_descriptor['vnf']['description'] = vnf_descriptor['vnf'].get("description", vnf_name)
    if "physical" in vnf_descriptor['vnf']:
        del vnf_descriptor['vnf']['physical']
    #print vnf_descriptor

    # Step 6. For each VNFC in the descriptor, flavors and images are created in the VIM
    logger.debug('BEGIN creation of VNF "%s"' % vnf_name)
    logger.debug("VNF %s: consisting of %d VNFC(s)" % (vnf_name,len(vnf_descriptor['vnf']['VNFC'])))

    #For each VNFC, we add it to the VNFCDict and we  create a flavor.
    VNFCDict = {}     # Dictionary, key: VNFC name, value: dict with the relevant information to create the VNF and VMs in the MANO database
    rollback_list = []    # It will contain the new images created in mano. It is used for rollback
    try:
        logger.debug("Creating additional disk images and new flavors in the VIM for each VNFC")
        for vnfc in vnf_descriptor['vnf']['VNFC']:
            VNFCitem={}
            VNFCitem["name"] = vnfc['name']
            VNFCitem["description"] = vnfc.get("description", 'VM %s of the VNF %s' %(vnfc['name'],vnf_name))

            #print "Flavor name: %s. Description: %s" % (VNFCitem["name"]+"-flv", VNFCitem["description"])

            myflavorDict = {}
            myflavorDict["name"] = vnfc['name']+"-flv"   #Maybe we could rename the flavor by using the field "image name" if exists
            myflavorDict["description"] = VNFCitem["description"]
            myflavorDict["ram"] = vnfc.get("ram", 0)
            myflavorDict["vcpus"] = vnfc.get("vcpus", 0)
            myflavorDict["disk"] = vnfc.get("disk", 1)
            myflavorDict["extended"] = {}

            devices = vnfc.get("devices")
            if devices != None:
                myflavorDict["extended"]["devices"] = devices

            # TODO:
            # Mapping from processor models to rankings should be available somehow in the NFVO. They could be taken from VIM or directly from a new database table
            # Another option is that the processor in the VNF descriptor specifies directly the ranking of the host

            # Previous code has been commented
            #if vnfc['processor']['model'] == "Intel(R) Xeon(R) CPU E5-4620 0 @ 2.20GHz" :
            #    myflavorDict["flavor"]['extended']['processor_ranking'] = 200
            #elif vnfc['processor']['model'] == "Intel(R) Xeon(R) CPU E5-2697 v2 @ 2.70GHz" :
            #    myflavorDict["flavor"]['extended']['processor_ranking'] = 300
            #else:
            #    result2, message = rollback(myvim, myvimURL, myvim_tenant, flavorList, imageList)
            #    if result2:
            #        print "Error creating flavor: unknown processor model. Rollback successful."
            #        return -HTTP_Bad_Request, "Error creating flavor: unknown processor model. Rollback successful."
            #    else:
            #        return -HTTP_Bad_Request, "Error creating flavor: unknown processor model. Rollback fail: you need to access VIM and delete the following %s" % message
            myflavorDict['extended']['processor_ranking'] = 100  #Hardcoded value, while we decide when the mapping is done

            if 'numas' in vnfc and len(vnfc['numas'])>0:
                myflavorDict['extended']['numas'] = vnfc['numas']

            #print myflavorDict

            # Step 6.2 New flavors are created in the VIM
            flavor_id = create_or_use_flavor(mydb, vims, myflavorDict, rollback_list)

            #print "Flavor id for VNFC %s: %s" % (vnfc['name'],flavor_id)
            VNFCitem["flavor_id"] = flavor_id
            VNFCDict[vnfc['name']] = VNFCitem

        logger.debug("Creating new images in the VIM for each VNFC")
        # Step 6.3 New images are created in the VIM
        #For each VNFC, we must create the appropriate image.
        #This "for" loop might be integrated with the previous one
        #In case this integration is made, the VNFCDict might become a VNFClist.
        for vnfc in vnf_descriptor['vnf']['VNFC']:
            #print "Image name: %s. Description: %s" % (vnfc['name']+"-img", VNFCDict[vnfc['name']]['description'])
            image_dict={}
            image_dict['name']=vnfc.get('image name',vnf_name+"-"+vnfc['name']+"-img")
            image_dict['universal_name']=vnfc.get('image name')
            image_dict['description']=vnfc.get('image name', VNFCDict[vnfc['name']]['description'])
            image_dict['location']=vnfc.get('VNFC image')
            #image_dict['new_location']=vnfc.get('image location')
            image_dict['checksum']=vnfc.get('image checksum')
            image_metadata_dict = vnfc.get('image metadata', None)
            image_metadata_str = None
            if image_metadata_dict is not None:
                image_metadata_str = yaml.safe_dump(image_metadata_dict,default_flow_style=True,width=256)
            image_dict['metadata']=image_metadata_str
            #print "create_or_use_image", mydb, vims, image_dict, rollback_list
            image_id = create_or_use_image(mydb, vims, image_dict, rollback_list)
            #print "Image id for VNFC %s: %s" % (vnfc['name'],image_id)
            VNFCDict[vnfc['name']]["image_id"] = image_id
            VNFCDict[vnfc['name']]["image_path"] = vnfc.get('VNFC image')
            if vnfc.get("boot-data"):
                VNFCDict[vnfc['name']]["boot_data"] = yaml.safe_dump(vnfc["boot-data"], default_flow_style=True, width=256)

        # Step 7. Storing the VNF descriptor in the repository
        if "descriptor" not in vnf_descriptor["vnf"]:
            vnf_descriptor["vnf"]["descriptor"] = yaml.safe_dump(vnf_descriptor, indent=4, explicit_start=True, default_flow_style=False)

        # Step 8. Adding the VNF to the NFVO DB
        vnf_id = mydb.new_vnf_as_a_whole2(tenant_id,vnf_name,vnf_descriptor,VNFCDict)
        return vnf_id
    except (db_base_Exception, vimconn.vimconnException, KeyError) as e:
        _, message = rollback(mydb, vims, rollback_list)
        if isinstance(e, db_base_Exception):
            error_text = "Exception at database"
        elif isinstance(e, KeyError):
            error_text = "KeyError exception "
            e.http_code = HTTP_Internal_Server_Error
        else:
            error_text = "Exception at VIM"
        error_text += " {} {}. {}".format(type(e).__name__, str(e), message)
        #logger.error("start_scenario %s", error_text)
        raise NfvoException(error_text, e.http_code)


def get_vnf_id(mydb, tenant_id, vnf_id):
    #check valid tenant_id
    check_tenant(mydb, tenant_id)
    #obtain data
    where_or = {}
    if tenant_id != "any":
        where_or["tenant_id"] = tenant_id
        where_or["public"] = True
    vnf = mydb.get_table_by_uuid_name('vnfs', vnf_id, "VNF", WHERE_OR=where_or, WHERE_AND_OR="AND")

    vnf_id=vnf["uuid"]
    filter_keys = ('uuid','name','description','public', "tenant_id", "created_at")
    filtered_content = dict( (k,v) for k,v in vnf.iteritems() if k in filter_keys )
    #change_keys_http2db(filtered_content, http2db_vnf, reverse=True)
    data={'vnf' : filtered_content}
    #GET VM
    content = mydb.get_rows(FROM='vnfs join vms on vnfs.uuid=vms.vnf_id',
            SELECT=('vms.uuid as uuid','vms.name as name', 'vms.description as description', 'boot_data'),
            WHERE={'vnfs.uuid': vnf_id} )
    if len(content)==0:
        raise NfvoException("vnf '{}' not found".format(vnf_id), HTTP_Not_Found)
    # change boot_data into boot-data
    for vm in content:
        if vm.get("boot_data"):
            vm["boot-data"] = yaml.safe_load(vm["boot_data"])
            del vm["boot_data"]

    data['vnf']['VNFC'] = content
    #TODO: GET all the information from a VNFC and include it in the output.

    #GET NET
    content = mydb.get_rows(FROM='vnfs join nets on vnfs.uuid=nets.vnf_id',
                                    SELECT=('nets.uuid as uuid','nets.name as name','nets.description as description', 'nets.type as type', 'nets.multipoint as multipoint'),
                                    WHERE={'vnfs.uuid': vnf_id} )
    data['vnf']['nets'] = content

    #GET ip-profile for each net
    for net in data['vnf']['nets']:
        ipprofiles = mydb.get_rows(FROM='ip_profiles',
                                   SELECT=('ip_version','subnet_address','gateway_address','dns_address','dhcp_enabled','dhcp_start_address','dhcp_count'),
                                   WHERE={'net_id': net["uuid"]} )
        if len(ipprofiles)==1:
            net["ip_profile"] = ipprofiles[0]
        elif len(ipprofiles)>1:
            raise NfvoException("More than one ip-profile found with this criteria: net_id='{}'".format(net['uuid']), HTTP_Bad_Request)


    #TODO: For each net, GET its elements and relevant info per element (VNFC, iface, ip_address) and include them in the output.

    #GET External Interfaces
    content = mydb.get_rows(FROM='vnfs join vms on vnfs.uuid=vms.vnf_id join interfaces on vms.uuid=interfaces.vm_id',\
                                    SELECT=('interfaces.uuid as uuid','interfaces.external_name as external_name', 'vms.name as vm_name', 'interfaces.vm_id as vm_id', \
                                            'interfaces.internal_name as internal_name', 'interfaces.type as type', 'interfaces.vpci as vpci','interfaces.bw as bw'),\
                                    WHERE={'vnfs.uuid': vnf_id},
                                    WHERE_NOT={'interfaces.external_name': None} )
    #print content
    data['vnf']['external-connections'] = content

    return data


def delete_vnf(mydb,tenant_id,vnf_id,datacenter=None,vim_tenant=None):
    # Check tenant exist
    if tenant_id != "any":
        check_tenant(mydb, tenant_id)
        # Get the URL of the VIM from the nfvo_tenant and the datacenter
        vims = get_vim(mydb, tenant_id)
    else:
        vims={}

    # Checking if it is a valid uuid and, if not, getting the uuid assuming that the name was provided"
    where_or = {}
    if tenant_id != "any":
        where_or["tenant_id"] = tenant_id
        where_or["public"] = True
    vnf = mydb.get_table_by_uuid_name('vnfs', vnf_id, "VNF", WHERE_OR=where_or, WHERE_AND_OR="AND")
    vnf_id = vnf["uuid"]

    # "Getting the list of flavors and tenants of the VNF"
    flavorList = get_flavorlist(mydb, vnf_id)
    if len(flavorList)==0:
        logger.warn("delete_vnf error. No flavors found for the VNF id '%s'", vnf_id)

    imageList = get_imagelist(mydb, vnf_id)
    if len(imageList)==0:
        logger.warn( "delete_vnf error. No images found for the VNF id '%s'", vnf_id)

    deleted = mydb.delete_row_by_id('vnfs', vnf_id)
    if deleted == 0:
        raise NfvoException("vnf '{}' not found".format(vnf_id), HTTP_Not_Found)

    undeletedItems = []
    for flavor in flavorList:
        #check if flavor is used by other vnf
        try:
            c = mydb.get_rows(FROM='vms', WHERE={'flavor_id':flavor} )
            if len(c) > 0:
                logger.debug("Flavor '%s' not deleted because it is being used by another VNF", flavor)
                continue
            #flavor not used, must be deleted
            #delelte at VIM
            c = mydb.get_rows(FROM='datacenters_flavors', WHERE={'flavor_id':flavor})
            for flavor_vim in c:
                if flavor_vim["datacenter_id"] not in vims:
                    continue
                if flavor_vim['created']=='false': #skip this flavor because not created by openmano
                    continue
                myvim=vims[ flavor_vim["datacenter_id"] ]
                try:
                    myvim.delete_flavor(flavor_vim["vim_id"])
                except vimconn.vimconnNotFoundException as e:
                    logger.warn("VIM flavor %s not exist at datacenter %s", flavor_vim["vim_id"], flavor_vim["datacenter_id"] )
                except vimconn.vimconnException as e:
                    logger.error("Not possible to delete VIM flavor %s from datacenter %s: %s %s",
                            flavor_vim["vim_id"], flavor_vim["datacenter_id"], type(e).__name__, str(e))
                    undeletedItems.append("flavor {} from VIM {}".format(flavor_vim["vim_id"], flavor_vim["datacenter_id"] ))
            #delete flavor from Database, using table flavors and with cascade foreign key also at datacenters_flavors
            mydb.delete_row_by_id('flavors', flavor)
        except db_base_Exception as e:
            logger.error("delete_vnf_error. Not possible to get flavor details and delete '%s'. %s", flavor, str(e))
            undeletedItems.append("flavor %s" % flavor)


    for image in imageList:
        try:
            #check if image is used by other vnf
            c = mydb.get_rows(FROM='vms', WHERE={'image_id':image} )
            if len(c) > 0:
                logger.debug("Image '%s' not deleted because it is being used by another VNF", image)
                continue
            #image not used, must be deleted
            #delelte at VIM
            c = mydb.get_rows(FROM='datacenters_images', WHERE={'image_id':image})
            for image_vim in c:
                if image_vim["datacenter_id"] not in vims:
                    continue
                if image_vim['created']=='false': #skip this image because not created by openmano
                    continue
                myvim=vims[ image_vim["datacenter_id"] ]
                try:
                    myvim.delete_image(image_vim["vim_id"])
                except vimconn.vimconnNotFoundException as e:
                    logger.warn("VIM image %s not exist at datacenter %s", image_vim["vim_id"], image_vim["datacenter_id"] )
                except vimconn.vimconnException as e:
                    logger.error("Not possible to delete VIM image %s from datacenter %s: %s %s",
                            image_vim["vim_id"], image_vim["datacenter_id"], type(e).__name__, str(e))
                    undeletedItems.append("image {} from VIM {}".format(image_vim["vim_id"], image_vim["datacenter_id"] ))
            #delete image from Database, using table images and with cascade foreign key also at datacenters_images
            mydb.delete_row_by_id('images', image)
        except db_base_Exception as e:
            logger.error("delete_vnf_error. Not possible to get image details and delete '%s'. %s", image, str(e))
            undeletedItems.append("image %s" % image)

    return vnf_id + " " + vnf["name"]
    #if undeletedItems:
    #    return "delete_vnf. Undeleted: %s" %(undeletedItems)


def get_hosts_info(mydb, nfvo_tenant_id, datacenter_name=None):
    result, vims = get_vim(mydb, nfvo_tenant_id, None, datacenter_name)
    if result < 0:
        return result, vims
    elif result == 0:
        return -HTTP_Not_Found, "datacenter '%s' not found" % datacenter_name
    myvim = vims.values()[0]
    result,servers =  myvim.get_hosts_info()
    if result < 0:
        return result, servers
    topology = {'name':myvim['name'] , 'servers': servers}
    return result, topology


def get_hosts(mydb, nfvo_tenant_id):
    vims = get_vim(mydb, nfvo_tenant_id)
    if len(vims) == 0:
        raise NfvoException("No datacenter found for tenant '{}'".format(str(nfvo_tenant_id)), HTTP_Not_Found)
    elif len(vims)>1:
        #print "nfvo.datacenter_action() error. Several datacenters found"
        raise NfvoException("More than one datacenters found, try to identify with uuid", HTTP_Conflict)
    myvim = vims.values()[0]
    try:
        hosts =  myvim.get_hosts()
        logger.debug('VIM hosts response: '+ yaml.safe_dump(hosts, indent=4, default_flow_style=False))

        datacenter = {'Datacenters': [ {'name':myvim['name'],'servers':[]} ] }
        for host in hosts:
            server={'name':host['name'], 'vms':[]}
            for vm in host['instances']:
                #get internal name and model
                try:
                    c = mydb.get_rows(SELECT=('name',), FROM='instance_vms as iv join vms on iv.vm_id=vms.uuid',\
                        WHERE={'vim_vm_id':vm['id']} )
                    if len(c) == 0:
                        logger.warn("nfvo.get_hosts virtual machine at VIM '{}' not found at tidnfvo".format(vm['id']))
                        continue
                    server['vms'].append( {'name':vm['name'] , 'model':c[0]['name']} )

                except db_base_Exception as e:
                    logger.warn("nfvo.get_hosts virtual machine at VIM '{}' error {}".format(vm['id'], str(e)))
            datacenter['Datacenters'][0]['servers'].append(server)
        #return -400, "en construccion"

        #print 'datacenters '+ json.dumps(datacenter, indent=4)
        return datacenter
    except vimconn.vimconnException as e:
        raise NfvoException("Not possible to get_host_list from VIM: {}".format(str(e)), e.http_code)


def new_scenario(mydb, tenant_id, topo):

#    result, vims = get_vim(mydb, tenant_id)
#    if result < 0:
#        return result, vims
#1: parse input
    if tenant_id != "any":
        check_tenant(mydb, tenant_id)
        if "tenant_id" in topo:
            if topo["tenant_id"] != tenant_id:
                raise NfvoException("VNF can not have a different tenant owner '{}', must be '{}'".format(topo["tenant_id"], tenant_id),
                                    HTTP_Unauthorized)
    else:
        tenant_id=None

#1.1: get VNFs and external_networks (other_nets).
    vnfs={}
    other_nets={}  #external_networks, bridge_networks and data_networkds
    nodes = topo['topology']['nodes']
    for k in nodes.keys():
        if nodes[k]['type'] == 'VNF':
            vnfs[k] = nodes[k]
            vnfs[k]['ifaces'] = {}
        elif nodes[k]['type'] == 'other_network' or nodes[k]['type'] == 'external_network':
            other_nets[k] = nodes[k]
            other_nets[k]['external']=True
        elif nodes[k]['type'] == 'network':
            other_nets[k] = nodes[k]
            other_nets[k]['external']=False


#1.2: Check that VNF are present at database table vnfs. Insert uuid, description and external interfaces
    for name,vnf in vnfs.items():
        where={}
        where_or={"tenant_id": tenant_id, 'public': "true"}
        error_text = ""
        error_pos = "'topology':'nodes':'" + name + "'"
        if 'vnf_id' in vnf:
            error_text += " 'vnf_id' " +  vnf['vnf_id']
            where['uuid'] = vnf['vnf_id']
        if 'VNF model' in vnf:
            error_text += " 'VNF model' " +  vnf['VNF model']
            where['name'] = vnf['VNF model']
        if len(where) == 0:
            raise NfvoException("Descriptor need a 'vnf_id' or 'VNF model' field at " + error_pos, HTTP_Bad_Request)

        vnf_db = mydb.get_rows(SELECT=('uuid','name','description'),
                               FROM='vnfs',
                               WHERE=where,
                               WHERE_OR=where_or,
                               WHERE_AND_OR="AND")
        if len(vnf_db)==0:
            raise NfvoException("unknown" + error_text + " at " + error_pos, HTTP_Not_Found)
        elif len(vnf_db)>1:
            raise NfvoException("more than one" + error_text + " at " + error_pos + " Concrete with 'vnf_id'", HTTP_Conflict)
        vnf['uuid']=vnf_db[0]['uuid']
        vnf['description']=vnf_db[0]['description']
        #get external interfaces
        ext_ifaces = mydb.get_rows(SELECT=('external_name as name','i.uuid as iface_uuid', 'i.type as type'),
            FROM='vnfs join vms on vnfs.uuid=vms.vnf_id join interfaces as i on vms.uuid=i.vm_id',
            WHERE={'vnfs.uuid':vnf['uuid']}, WHERE_NOT={'external_name':None} )
        for ext_iface in ext_ifaces:
            vnf['ifaces'][ ext_iface['name'] ] = {'uuid':ext_iface['iface_uuid'], 'type':ext_iface['type']}

#1.4 get list of connections
    conections = topo['topology']['connections']
    conections_list = []
    conections_list_name = []
    for k in conections.keys():
        if type(conections[k]['nodes'])==dict: #dict with node:iface pairs
            ifaces_list = conections[k]['nodes'].items()
        elif type(conections[k]['nodes'])==list: #list with dictionary
            ifaces_list=[]
            conection_pair_list = map(lambda x: x.items(), conections[k]['nodes'] )
            for k2 in conection_pair_list:
                ifaces_list += k2

        con_type = conections[k].get("type", "link")
        if con_type != "link":
            if k in other_nets:
                raise NfvoException("Format error. Reapeted network name at 'topology':'connections':'{}'".format(str(k)), HTTP_Bad_Request)
            other_nets[k] = {'external': False}
            if conections[k].get("graph"):
                other_nets[k]["graph"] =   conections[k]["graph"]
            ifaces_list.append( (k, None) )


        if con_type == "external_network":
            other_nets[k]['external'] = True
            if conections[k].get("model"):
                other_nets[k]["model"] =   conections[k]["model"]
            else:
                other_nets[k]["model"] =   k
        if con_type == "dataplane_net" or con_type == "bridge_net":
            other_nets[k]["model"] = con_type

        conections_list_name.append(k)
        conections_list.append(set(ifaces_list)) #from list to set to operate as a set (this conversion removes elements that are repeated in a list)
        #print set(ifaces_list)
    #check valid VNF and iface names
        for iface in ifaces_list:
            if iface[0] not in vnfs and iface[0] not in other_nets :
                raise NfvoException("format error. Invalid VNF name at 'topology':'connections':'{}':'nodes':'{}'".format(
                                                                                        str(k), iface[0]), HTTP_Not_Found)
            if iface[0] in vnfs and iface[1] not in vnfs[ iface[0] ]['ifaces']:
                raise NfvoException("format error. Invalid interface name at 'topology':'connections':'{}':'nodes':'{}':'{}'".format(
                                                                                        str(k), iface[0], iface[1]), HTTP_Not_Found)

#1.5 unify connections from the pair list to a consolidated list
    index=0
    while index < len(conections_list):
        index2 = index+1
        while index2 < len(conections_list):
            if len(conections_list[index] & conections_list[index2])>0: #common interface, join nets
                conections_list[index] |= conections_list[index2]
                del conections_list[index2]
                del conections_list_name[index2]
            else:
                index2 += 1
        conections_list[index] = list(conections_list[index])  # from set to list again
        index += 1
    #for k in conections_list:
    #    print k



#1.6 Delete non external nets
#    for k in other_nets.keys():
#        if other_nets[k]['model']=='bridge' or other_nets[k]['model']=='dataplane_net' or other_nets[k]['model']=='bridge_net':
#            for con in conections_list:
#                delete_indexes=[]
#                for index in range(0,len(con)):
#                    if con[index][0] == k: delete_indexes.insert(0,index) #order from higher to lower
#                for index in delete_indexes:
#                    del con[index]
#            del other_nets[k]
#1.7: Check external_ports are present at database table datacenter_nets
    for k,net in other_nets.items():
        error_pos = "'topology':'nodes':'" + k + "'"
        if net['external']==False:
            if 'name' not in net:
                net['name']=k
            if 'model' not in net:
                raise NfvoException("needed a 'model' at " + error_pos, HTTP_Bad_Request)
            if net['model']=='bridge_net':
                net['type']='bridge';
            elif net['model']=='dataplane_net':
                net['type']='data';
            else:
                raise NfvoException("unknown 'model' '"+ net['model'] +"' at " + error_pos, HTTP_Not_Found)
        else: #external
#IF we do not want to check that external network exist at datacenter
            pass
#ELSE
#             error_text = ""
#             WHERE_={}
#             if 'net_id' in net:
#                 error_text += " 'net_id' " +  net['net_id']
#                 WHERE_['uuid'] = net['net_id']
#             if 'model' in net:
#                 error_text += " 'model' " +  net['model']
#                 WHERE_['name'] = net['model']
#             if len(WHERE_) == 0:
#                 return -HTTP_Bad_Request, "needed a 'net_id' or 'model' at " + error_pos
#             r,net_db = mydb.get_table(SELECT=('uuid','name','description','type','shared'),
#                 FROM='datacenter_nets', WHERE=WHERE_ )
#             if r<0:
#                 print "nfvo.new_scenario Error getting datacenter_nets",r,net_db
#             elif r==0:
#                 print "nfvo.new_scenario Error" +error_text+ " is not present at database"
#                 return -HTTP_Bad_Request, "unknown " +error_text+ " at " + error_pos
#             elif r>1:
#                 print "nfvo.new_scenario Error more than one external_network for " +error_text+ " is present at database"
#                 return -HTTP_Bad_Request, "more than one external_network for " +error_text+ "at "+ error_pos + " Concrete with 'net_id'"
#             other_nets[k].update(net_db[0])
#ENDIF
    net_list={}
    net_nb=0  #Number of nets
    for con in conections_list:
        #check if this is connected to a external net
        other_net_index=-1
        #print
        #print "con", con
        for index in range(0,len(con)):
            #check if this is connected to a external net
            for net_key in other_nets.keys():
                if con[index][0]==net_key:
                    if other_net_index>=0:
                        error_text="There is some interface connected both to net '%s' and net '%s'" % (con[other_net_index][0], net_key)
                        #print "nfvo.new_scenario " + error_text
                        raise NfvoException(error_text, HTTP_Bad_Request)
                    else:
                        other_net_index = index
                        net_target = net_key
                    break
        #print "other_net_index", other_net_index
        try:
            if other_net_index>=0:
                del con[other_net_index]
#IF we do not want to check that external network exist at datacenter
                if other_nets[net_target]['external'] :
                    if "name" not in other_nets[net_target]:
                        other_nets[net_target]['name'] =  other_nets[net_target]['model']
                    if other_nets[net_target]["type"] == "external_network":
                        if vnfs[ con[0][0] ]['ifaces'][ con[0][1] ]["type"] == "data":
                            other_nets[net_target]["type"] =  "data"
                        else:
                            other_nets[net_target]["type"] =  "bridge"
#ELSE
#                 if other_nets[net_target]['external'] :
#                     type_='data' if len(con)>1 else 'ptp'  #an external net is connected to a external port, so it is ptp if only one connection is done to this net
#                     if type_=='data' and other_nets[net_target]['type']=="ptp":
#                         error_text = "Error connecting %d nodes on a not multipoint net %s" % (len(con), net_target)
#                         print "nfvo.new_scenario " + error_text
#                         return -HTTP_Bad_Request, error_text
#ENDIF
                for iface in con:
                    vnfs[ iface[0] ]['ifaces'][ iface[1] ]['net_key'] = net_target
            else:
                #create a net
                net_type_bridge=False
                net_type_data=False
                net_target = "__-__net"+str(net_nb)
                net_list[net_target] = {'name': conections_list_name[net_nb],  #"net-"+str(net_nb),
                    'description':"net-%s in scenario %s" %(net_nb,topo['name']),
                    'external':False}
                for iface in con:
                    vnfs[ iface[0] ]['ifaces'][ iface[1] ]['net_key'] = net_target
                    iface_type = vnfs[ iface[0] ]['ifaces'][ iface[1] ]['type']
                    if iface_type=='mgmt' or iface_type=='bridge':
                        net_type_bridge = True
                    else:
                        net_type_data = True
                if net_type_bridge and net_type_data:
                    error_text = "Error connection interfaces of bridge type with data type. Firs node %s, iface %s" % (iface[0], iface[1])
                    #print "nfvo.new_scenario " + error_text
                    raise NfvoException(error_text, HTTP_Bad_Request)
                elif net_type_bridge:
                    type_='bridge'
                else:
                    type_='data' if len(con)>2 else 'ptp'
                net_list[net_target]['type'] = type_
                net_nb+=1
        except Exception:
            error_text = "Error connection node %s : %s does not match any VNF or interface" % (iface[0], iface[1])
            #print "nfvo.new_scenario " + error_text
            #raise e
            raise NfvoException(error_text, HTTP_Bad_Request)

#1.8: Connect to management net all not already connected interfaces of type 'mgmt'
    #1.8.1 obtain management net
    mgmt_net = mydb.get_rows(SELECT=('uuid','name','description','type','shared'),
        FROM='datacenter_nets', WHERE={'name':'mgmt'} )
    #1.8.2 check all interfaces from all vnfs
    if len(mgmt_net)>0:
        add_mgmt_net = False
        for vnf in vnfs.values():
            for iface in vnf['ifaces'].values():
                if iface['type']=='mgmt' and 'net_key' not in iface:
                    #iface not connected
                    iface['net_key'] = 'mgmt'
                    add_mgmt_net = True
        if add_mgmt_net and 'mgmt' not in net_list:
            net_list['mgmt']=mgmt_net[0]
            net_list['mgmt']['external']=True
            net_list['mgmt']['graph']={'visible':False}

    net_list.update(other_nets)
    #print
    #print 'net_list', net_list
    #print
    #print 'vnfs', vnfs
    #print

#2: insert scenario. filling tables scenarios,sce_vnfs,sce_interfaces,sce_nets
    c = mydb.new_scenario( { 'vnfs':vnfs, 'nets':net_list,
        'tenant_id':tenant_id, 'name':topo['name'],
         'description':topo.get('description',topo['name']),
         'public': topo.get('public', False)
         })

    return c


def new_scenario_v02(mydb, tenant_id, scenario_dict, version):
    """ This creates a new scenario for version 0.2 and 0.3"""
    scenario = scenario_dict["scenario"]
    if tenant_id != "any":
        check_tenant(mydb, tenant_id)
        if "tenant_id" in scenario:
            if scenario["tenant_id"] != tenant_id:
                # print "nfvo.new_scenario_v02() tenant '%s' not found" % tenant_id
                raise NfvoException("VNF can not have a different tenant owner '{}', must be '{}'".format(
                                                    scenario["tenant_id"], tenant_id), HTTP_Unauthorized)
    else:
        tenant_id=None

    # 1: Check that VNF are present at database table vnfs and update content into scenario dict
    for name,vnf in scenario["vnfs"].iteritems():
        where={}
        where_or={"tenant_id": tenant_id, 'public': "true"}
        error_text = ""
        error_pos = "'scenario':'vnfs':'" + name + "'"
        if 'vnf_id' in vnf:
            error_text += " 'vnf_id' " + vnf['vnf_id']
            where['uuid'] = vnf['vnf_id']
        if 'vnf_name' in vnf:
            error_text += " 'vnf_name' " + vnf['vnf_name']
            where['name'] = vnf['vnf_name']
        if len(where) == 0:
            raise NfvoException("Needed a 'vnf_id' or 'vnf_name' at " + error_pos, HTTP_Bad_Request)
        vnf_db = mydb.get_rows(SELECT=('uuid', 'name', 'description'),
                               FROM='vnfs',
                               WHERE=where,
                               WHERE_OR=where_or,
                               WHERE_AND_OR="AND")
        if len(vnf_db) == 0:
            raise NfvoException("Unknown" + error_text + " at " + error_pos, HTTP_Not_Found)
        elif len(vnf_db) > 1:
            raise NfvoException("More than one" + error_text + " at " + error_pos + " Concrete with 'vnf_id'", HTTP_Conflict)
        vnf['uuid'] = vnf_db[0]['uuid']
        vnf['description'] = vnf_db[0]['description']
        vnf['ifaces'] = {}
        # get external interfaces
        ext_ifaces = mydb.get_rows(SELECT=('external_name as name', 'i.uuid as iface_uuid', 'i.type as type'),
                                   FROM='vnfs join vms on vnfs.uuid=vms.vnf_id join interfaces as i on vms.uuid=i.vm_id',
                                   WHERE={'vnfs.uuid':vnf['uuid']}, WHERE_NOT={'external_name': None} )
        for ext_iface in ext_ifaces:
            vnf['ifaces'][ ext_iface['name'] ] = {'uuid':ext_iface['iface_uuid'], 'type': ext_iface['type']}
        # TODO? get internal-connections from db.nets and their profiles, and update scenario[vnfs][internal-connections] accordingly

    # 2: Insert net_key and ip_address at every vnf interface
    for net_name, net in scenario["networks"].items():
        net_type_bridge = False
        net_type_data = False
        for iface_dict in net["interfaces"]:
            if version == "0.2":
                temp_dict = iface_dict
                ip_address = None
            elif version == "0.3":
                temp_dict = {iface_dict["vnf"] : iface_dict["vnf_interface"]}
                ip_address = iface_dict.get('ip_address', None)
            for vnf, iface in temp_dict.items():
                if vnf not in scenario["vnfs"]:
                    error_text = "Error at 'networks':'{}':'interfaces' VNF '{}' not match any VNF at 'vnfs'".format(
                        net_name, vnf)
                    # logger.debug("nfvo.new_scenario_v02 " + error_text)
                    raise NfvoException(error_text, HTTP_Not_Found)
                if iface not in scenario["vnfs"][vnf]['ifaces']:
                    error_text = "Error at 'networks':'{}':'interfaces':'{}' interface not match any VNF interface"\
                        .format(net_name, iface)
                    # logger.debug("nfvo.new_scenario_v02 " + error_text)
                    raise NfvoException(error_text, HTTP_Bad_Request)
                if "net_key" in scenario["vnfs"][vnf]['ifaces'][iface]:
                    error_text = "Error at 'networks':'{}':'interfaces':'{}' interface already connected at network"\
                                 "'{}'".format(net_name, iface,scenario["vnfs"][vnf]['ifaces'][iface]['net_key'])
                    # logger.debug("nfvo.new_scenario_v02 " + error_text)
                    raise NfvoException(error_text, HTTP_Bad_Request)
                scenario["vnfs"][vnf]['ifaces'][ iface ]['net_key'] = net_name
                scenario["vnfs"][vnf]['ifaces'][iface]['ip_address'] = ip_address
                iface_type = scenario["vnfs"][vnf]['ifaces'][iface]['type']
                if iface_type == 'mgmt' or iface_type == 'bridge':
                    net_type_bridge = True
                else:
                    net_type_data = True

        if net_type_bridge and net_type_data:
            error_text = "Error connection interfaces of 'bridge' type and 'data' type at 'networks':'{}':'interfaces'"\
                .format(net_name)
            # logger.debug("nfvo.new_scenario " + error_text)
            raise NfvoException(error_text, HTTP_Bad_Request)
        elif net_type_bridge:
            type_ = 'bridge'
        else:
            type_ = 'data' if len(net["interfaces"]) > 2 else 'ptp'

        if net.get("implementation"):     # for v0.3
            if type_ == "bridge" and net["implementation"] == "underlay":
                error_text = "Error connecting interfaces of data type to a network declared as 'underlay' at "\
                             "'network':'{}'".format(net_name)
                # logger.debug(error_text)
                raise NfvoException(error_text, HTTP_Bad_Request)
            elif type_ != "bridge" and net["implementation"] == "overlay":
                error_text = "Error connecting interfaces of data type to a network declared as 'overlay' at "\
                             "'network':'{}'".format(net_name)
                # logger.debug(error_text)
                raise NfvoException(error_text, HTTP_Bad_Request)
            net.pop("implementation")
        if "type" in net and version == "0.3":   # for v0.3
            if type_ == "data" and net["type"] == "e-line":
                error_text = "Error connecting more than 2 interfaces of data type to a network declared as type "\
                             "'e-line' at 'network':'{}'".format(net_name)
                # logger.debug(error_text)
                raise NfvoException(error_text, HTTP_Bad_Request)
            elif type_ == "ptp" and net["type"] == "e-lan":
                type_ = "data"

        net['type'] = type_
        net['name'] = net_name
        net['external'] = net.get('external', False)

    # 3: insert at database
    scenario["nets"] = scenario["networks"]
    scenario['tenant_id'] = tenant_id
    scenario_id = mydb.new_scenario(scenario)
    return scenario_id


def edit_scenario(mydb, tenant_id, scenario_id, data):
    data["uuid"] = scenario_id
    data["tenant_id"] = tenant_id
    c = mydb.edit_scenario( data )
    return c


def start_scenario(mydb, tenant_id, scenario_id, instance_scenario_name, instance_scenario_description, datacenter=None,vim_tenant=None, startvms=True):
    #print "Checking that nfvo_tenant_id exists and getting the VIM URI and the VIM tenant_id"
    datacenter_id, myvim = get_datacenter_by_name_uuid(mydb, tenant_id, datacenter, vim_tenant=vim_tenant)
    vims = {datacenter_id: myvim}
    myvim_tenant = myvim['tenant_id']
    datacenter_name = myvim['name']

    rollbackList=[]
    try:
        #print "Checking that the scenario_id exists and getting the scenario dictionary"
        scenarioDict = mydb.get_scenario(scenario_id, tenant_id, datacenter_id)
        scenarioDict['datacenter2tenant'] = { datacenter_id: myvim['config']['datacenter_tenant_id'] }
        scenarioDict['datacenter_id'] = datacenter_id
        #print '================scenarioDict======================='
        #print json.dumps(scenarioDict, indent=4)
        #print 'BEGIN launching instance scenario "%s" based on "%s"' % (instance_scenario_name,scenarioDict['name'])

        logger.debug("start_scenario Scenario %s: consisting of %d VNF(s)", scenarioDict['name'],len(scenarioDict['vnfs']))
        #print yaml.safe_dump(scenarioDict, indent=4, default_flow_style=False)

        auxNetDict = {}   #Auxiliar dictionary. First key:'scenario' or sce_vnf uuid. Second Key: uuid of the net/sce_net. Value: vim_net_id
        auxNetDict['scenario'] = {}

        logger.debug("start_scenario 1. Creating new nets (sce_nets) in the VIM")
        for sce_net in scenarioDict['nets']:
            #print "Net name: %s. Description: %s" % (sce_net["name"], sce_net["description"])

            myNetName = "%s.%s" % (instance_scenario_name, sce_net['name'])
            myNetName = myNetName[0:255] #limit length
            myNetType = sce_net['type']
            myNetDict = {}
            myNetDict["name"] = myNetName
            myNetDict["type"] = myNetType
            myNetDict["tenant_id"] = myvim_tenant
            myNetIPProfile = sce_net.get('ip_profile', None)
            #TODO:
            #We should use the dictionary as input parameter for new_network
            #print myNetDict
            if not sce_net["external"]:
                network_id = myvim.new_network(myNetName, myNetType, myNetIPProfile)
                #print "New VIM network created for scenario %s. Network id:  %s" % (scenarioDict['name'],network_id)
                sce_net['vim_id'] = network_id
                auxNetDict['scenario'][sce_net['uuid']] = network_id
                rollbackList.append({'what':'network','where':'vim','vim_id':datacenter_id,'uuid':network_id})
                sce_net["created"] = True
            else:
                if sce_net['vim_id'] == None:
                    error_text = "Error, datacenter '%s' does not have external network '%s'." % (datacenter_name, sce_net['name'])
                    _, message = rollback(mydb, vims, rollbackList)
                    logger.error("nfvo.start_scenario: %s", error_text)
                    raise NfvoException(error_text, HTTP_Bad_Request)
                logger.debug("Using existent VIM network for scenario %s. Network id %s", scenarioDict['name'],sce_net['vim_id'])
                auxNetDict['scenario'][sce_net['uuid']] = sce_net['vim_id']

        logger.debug("start_scenario 2. Creating new nets (vnf internal nets) in the VIM")
        #For each vnf net, we create it and we add it to instanceNetlist.
        for sce_vnf in scenarioDict['vnfs']:
            for net in sce_vnf['nets']:
                #print "Net name: %s. Description: %s" % (net["name"], net["description"])

                myNetName = "%s.%s" % (instance_scenario_name,net['name'])
                myNetName = myNetName[0:255] #limit length
                myNetType = net['type']
                myNetDict = {}
                myNetDict["name"] = myNetName
                myNetDict["type"] = myNetType
                myNetDict["tenant_id"] = myvim_tenant
                myNetIPProfile = net.get('ip_profile', None)
                #print myNetDict
                #TODO:
                #We should use the dictionary as input parameter for new_network
                network_id = myvim.new_network(myNetName, myNetType, myNetIPProfile)
                #print "VIM network id for scenario %s: %s" % (scenarioDict['name'],network_id)
                net['vim_id'] = network_id
                if sce_vnf['uuid'] not in auxNetDict:
                    auxNetDict[sce_vnf['uuid']] = {}
                auxNetDict[sce_vnf['uuid']][net['uuid']] = network_id
                rollbackList.append({'what':'network','where':'vim','vim_id':datacenter_id,'uuid':network_id})
                net["created"] = True

        #print "auxNetDict:"
        #print yaml.safe_dump(auxNetDict, indent=4, default_flow_style=False)

        logger.debug("start_scenario 3. Creating new vm instances in the VIM")
        #myvim.new_vminstance(self,vimURI,tenant_id,name,description,image_id,flavor_id,net_dict)
        i = 0
        for sce_vnf in scenarioDict['vnfs']:
            for vm in sce_vnf['vms']:
                i += 1
                myVMDict = {}
                #myVMDict['name'] = "%s-%s-%s" % (scenarioDict['name'],sce_vnf['name'], vm['name'])
                myVMDict['name'] = "{}.{}.{}".format(instance_scenario_name,sce_vnf['name'],chr(96+i))
                #myVMDict['description'] = vm['description']
                myVMDict['description'] = myVMDict['name'][0:99]
                if not startvms:
                    myVMDict['start'] = "no"
                myVMDict['name'] = myVMDict['name'][0:255] #limit name length
                #print "VM name: %s. Description: %s" % (myVMDict['name'], myVMDict['name'])

                #create image at vim in case it not exist
                image_dict = mydb.get_table_by_uuid_name("images", vm['image_id'])
                image_id = create_or_use_image(mydb, vims, image_dict, [], True)
                vm['vim_image_id'] = image_id

                #create flavor at vim in case it not exist
                flavor_dict = mydb.get_table_by_uuid_name("flavors", vm['flavor_id'])
                if flavor_dict['extended']!=None:
                    flavor_dict['extended']= yaml.load(flavor_dict['extended'])
                flavor_id = create_or_use_flavor(mydb, vims, flavor_dict, [], True)
                vm['vim_flavor_id'] = flavor_id


                myVMDict['imageRef'] = vm['vim_image_id']
                myVMDict['flavorRef'] = vm['vim_flavor_id']
                myVMDict['networks'] = []
                for iface in vm['interfaces']:
                    netDict = {}
                    if iface['type']=="data":
                        netDict['type'] = iface['model']
                    elif "model" in iface and iface["model"]!=None:
                        netDict['model']=iface['model']
                    #TODO in future, remove this because mac_address will not be set, and the type of PV,VF is obtained from iterface table model
                    #discover type of interface looking at flavor
                    for numa in flavor_dict.get('extended',{}).get('numas',[]):
                        for flavor_iface in numa.get('interfaces',[]):
                            if flavor_iface.get('name') == iface['internal_name']:
                                if flavor_iface['dedicated'] == 'yes':
                                    netDict['type']="PF"    #passthrough
                                elif flavor_iface['dedicated'] == 'no':
                                    netDict['type']="VF"    #siov
                                elif flavor_iface['dedicated'] == 'yes:sriov':
                                    netDict['type']="VFnotShared"   #sriov but only one sriov on the PF
                                netDict["mac_address"] = flavor_iface.get("mac_address")
                                break;
                    netDict["use"]=iface['type']
                    if netDict["use"]=="data" and not netDict.get("type"):
                        #print "netDict", netDict
                        #print "iface", iface
                        e_text = "Cannot determine the interface type PF or VF of VNF '%s' VM '%s' iface '%s'" %(sce_vnf['name'], vm['name'], iface['internal_name'])
                        if flavor_dict.get('extended')==None:
                            raise NfvoException(e_text  + "After database migration some information is not available. \
                                    Try to delete and create the scenarios and VNFs again", HTTP_Conflict)
                        else:
                            raise NfvoException(e_text, HTTP_Internal_Server_Error)
                    if netDict["use"]=="mgmt" or netDict["use"]=="bridge":
                        netDict["type"]="virtual"
                    if "vpci" in iface and iface["vpci"] is not None:
                        netDict['vpci'] = iface['vpci']
                    if "mac" in iface and iface["mac"] is not None:
                        netDict['mac_address'] = iface['mac']
                    if "port-security" in iface and iface["port-security"] is not None:
                        netDict['port_security'] = iface['port-security']
                    if "floating-ip" in iface and iface["floating-ip"] is not None:
                        netDict['floating_ip'] = iface['floating-ip']
                    netDict['name'] = iface['internal_name']
                    if iface['net_id'] is None:
                        for vnf_iface in sce_vnf["interfaces"]:
                            #print iface
                            #print vnf_iface
                            if vnf_iface['interface_id']==iface['uuid']:
                                netDict['net_id'] = auxNetDict['scenario'][ vnf_iface['sce_net_id'] ]
                                break
                    else:
                        netDict['net_id'] = auxNetDict[ sce_vnf['uuid'] ][ iface['net_id'] ]
                    #skip bridge ifaces not connected to any net
                    #if 'net_id' not in netDict or netDict['net_id']==None:
                    #    continue
                    myVMDict['networks'].append(netDict)
                #print ">>>>>>>>>>>>>>>>>>>>>>>>>>>"
                #print myVMDict['name']
                #print "networks", yaml.safe_dump(myVMDict['networks'], indent=4, default_flow_style=False)
                #print "interfaces", yaml.safe_dump(vm['interfaces'], indent=4, default_flow_style=False)
                #print ">>>>>>>>>>>>>>>>>>>>>>>>>>>"
                vm_id = myvim.new_vminstance(myVMDict['name'],myVMDict['description'],myVMDict.get('start', None),
                        myVMDict['imageRef'],myVMDict['flavorRef'],myVMDict['networks'])
                #print "VIM vm instance id (server id) for scenario %s: %s" % (scenarioDict['name'],vm_id)
                vm['vim_id'] = vm_id
                rollbackList.append({'what':'vm','where':'vim','vim_id':datacenter_id,'uuid':vm_id})
                #put interface uuid back to scenario[vnfs][vms[[interfaces]
                for net in myVMDict['networks']:
                    if "vim_id" in net:
                        for iface in vm['interfaces']:
                            if net["name"]==iface["internal_name"]:
                                iface["vim_id"]=net["vim_id"]
                                break

        logger.debug("start scenario Deployment done")
        #print yaml.safe_dump(scenarioDict, indent=4, default_flow_style=False)
        #r,c = mydb.new_instance_scenario_as_a_whole(nfvo_tenant,scenarioDict['name'],scenarioDict)
        instance_id = mydb.new_instance_scenario_as_a_whole(tenant_id,instance_scenario_name, instance_scenario_description, scenarioDict)
        return mydb.get_instance_scenario(instance_id)

    except (db_base_Exception, vimconn.vimconnException) as e:
        _, message = rollback(mydb, vims, rollbackList)
        if isinstance(e, db_base_Exception):
            error_text = "Exception at database"
        else:
            error_text = "Exception at VIM"
        error_text += " {} {}. {}".format(type(e).__name__, str(e), message)
        #logger.error("start_scenario %s", error_text)
        raise NfvoException(error_text, e.http_code)


def unify_cloud_config(cloud_config_preserve, cloud_config):
    ''' join the cloud config information into cloud_config_preserve.
    In case of conflict cloud_config_preserve preserves
    None is admited
    '''
    if not cloud_config_preserve and not cloud_config:
        return None

    new_cloud_config = {"key-pairs":[], "users":[]}
    # key-pairs
    if cloud_config_preserve:
        for key in cloud_config_preserve.get("key-pairs", () ):
            if key not in new_cloud_config["key-pairs"]:
                new_cloud_config["key-pairs"].append(key)
    if cloud_config:
        for key in cloud_config.get("key-pairs", () ):
            if key not in new_cloud_config["key-pairs"]:
                new_cloud_config["key-pairs"].append(key)
    if not new_cloud_config["key-pairs"]:
        del new_cloud_config["key-pairs"]

    # users
    if cloud_config:
        new_cloud_config["users"] += cloud_config.get("users", () )
    if cloud_config_preserve:
        new_cloud_config["users"] += cloud_config_preserve.get("users", () )
    index_to_delete = []
    users = new_cloud_config.get("users", [])
    for index0 in range(0,len(users)):
        if index0 in index_to_delete:
            continue
        for index1 in range(index0+1,len(users)):
            if index1 in index_to_delete:
                continue
            if users[index0]["name"] == users[index1]["name"]:
                index_to_delete.append(index1)
                for key in users[index1].get("key-pairs",()):
                    if "key-pairs" not in users[index0]:
                        users[index0]["key-pairs"] = [key]
                    elif key not in users[index0]["key-pairs"]:
                        users[index0]["key-pairs"].append(key)
    index_to_delete.sort(reverse=True)
    for index in index_to_delete:
        del users[index]
    if not new_cloud_config["users"]:
        del new_cloud_config["users"]

    #boot-data-drive
    if cloud_config and cloud_config.get("boot-data-drive") != None:
        new_cloud_config["boot-data-drive"] = cloud_config["boot-data-drive"]
    if cloud_config_preserve and cloud_config_preserve.get("boot-data-drive") != None:
        new_cloud_config["boot-data-drive"] = cloud_config_preserve["boot-data-drive"]

    # user-data
    if cloud_config and cloud_config.get("user-data") != None:
        new_cloud_config["user-data"] = cloud_config["user-data"]
    if cloud_config_preserve and cloud_config_preserve.get("user-data") != None:
        new_cloud_config["user-data"] = cloud_config_preserve["user-data"]

    # config files
    new_cloud_config["config-files"] = []
    if cloud_config and cloud_config.get("config-files") != None:
        new_cloud_config["config-files"] += cloud_config["config-files"]
    if cloud_config_preserve:
        for file in cloud_config_preserve.get("config-files", ()):
            for index in range(0, len(new_cloud_config["config-files"])):
                if new_cloud_config["config-files"][index]["dest"] == file["dest"]:
                    new_cloud_config["config-files"][index] = file
                    break
            else:
                new_cloud_config["config-files"].append(file)
    if not new_cloud_config["config-files"]:
        del new_cloud_config["config-files"]
    return new_cloud_config


def get_vim_thread(tenant_id, datacenter_id_name=None, datacenter_tenant_id=None):
    datacenter_id = None
    datacenter_name = None
    thread = None
    if datacenter_id_name:
        if utils.check_valid_uuid(datacenter_id_name):
            datacenter_id = datacenter_id_name
        else:
            datacenter_name = datacenter_id_name
    if datacenter_id:
        thread = vim_threads["running"].get(datacenter_id + "." + tenant_id)
    else:
        for k, v in vim_threads["running"].items():
            datacenter_tenant = k.split(".")
            if datacenter_tenant[0] == datacenter_id and datacenter_tenant[1] == tenant_id:
                if thread:
                    raise NfvoException("More than one datacenters found, try to identify with uuid", HTTP_Conflict)
                thread = v
            elif not datacenter_id and datacenter_tenant[1] == tenant_id:
                if thread.datacenter_name == datacenter_name:
                    if thread:
                        raise NfvoException("More than one datacenters found, try to identify with uuid", HTTP_Conflict)
                    thread = v
    if not thread:
        raise NfvoException("datacenter '{}' not found".format(str(datacenter_id_name)), HTTP_Not_Found)
    return thread


def get_datacenter_by_name_uuid(mydb, tenant_id, datacenter_id_name=None, **extra_filter):
    datacenter_id = None
    datacenter_name = None
    if datacenter_id_name:
        if utils.check_valid_uuid(datacenter_id_name):
            datacenter_id = datacenter_id_name
        else:
            datacenter_name = datacenter_id_name
    vims = get_vim(mydb, tenant_id, datacenter_id, datacenter_name, **extra_filter)
    if len(vims) == 0:
        raise NfvoException("datacenter '{}' not found".format(str(datacenter_id_name)), HTTP_Not_Found)
    elif len(vims)>1:
        #print "nfvo.datacenter_action() error. Several datacenters found"
        raise NfvoException("More than one datacenters found, try to identify with uuid", HTTP_Conflict)
    return vims.keys()[0], vims.values()[0]


def update(d, u):
    '''Takes dict d and updates it with the values in dict u.'''
    '''It merges all depth levels'''
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def create_instance(mydb, tenant_id, instance_dict):
    # print "Checking that nfvo_tenant_id exists and getting the VIM URI and the VIM tenant_id"
    # logger.debug("Creating instance...")
    scenario = instance_dict["scenario"]

    #find main datacenter
    myvims = {}
    myvim_threads = {}
    datacenter2tenant = {}
    datacenter = instance_dict.get("datacenter")
    default_datacenter_id, vim = get_datacenter_by_name_uuid(mydb, tenant_id, datacenter)
    myvims[default_datacenter_id] = vim
    myvim_threads[default_datacenter_id] = get_vim_thread(tenant_id, default_datacenter_id)
    datacenter2tenant[default_datacenter_id] = vim['config']['datacenter_tenant_id']
    #myvim_tenant = myvim['tenant_id']
#    default_datacenter_name = vim['name']
    rollbackList=[]

    #print "Checking that the scenario exists and getting the scenario dictionary"
    scenarioDict = mydb.get_scenario(scenario, tenant_id, default_datacenter_id)

    #logger.debug(">>>>>>> Dictionaries before merging")
    #logger.debug(">>>>>>> InstanceDict:\n{}".format(yaml.safe_dump(instance_dict,default_flow_style=False, width=256)))
    #logger.debug(">>>>>>> ScenarioDict:\n{}".format(yaml.safe_dump(scenarioDict,default_flow_style=False, width=256)))

    scenarioDict['datacenter_id'] = default_datacenter_id

    auxNetDict = {}   #Auxiliar dictionary. First key:'scenario' or sce_vnf uuid. Second Key: uuid of the net/sce_net. Value: vim_net_id
    auxNetDict['scenario'] = {}

    logger.debug("Creating instance from scenario-dict:\n%s", yaml.safe_dump(scenarioDict, indent=4, default_flow_style=False))  #TODO remove
    instance_name = instance_dict["name"]
    instance_description = instance_dict.get("description")
    instance_tasks={}
    try:
        # 0 check correct parameters
        for net_name, net_instance_desc in instance_dict.get("networks",{}).iteritems():
            found = False
            for scenario_net in scenarioDict['nets']:
                if net_name == scenario_net["name"]:
                    found = True
                    break
            if not found:
                raise NfvoException("Invalid scenario network name '{}' at instance:networks".format(net_name), HTTP_Bad_Request)
            if "sites" not in net_instance_desc:
                net_instance_desc["sites"] = [ {} ]
            site_without_datacenter_field = False
            for site in net_instance_desc["sites"]:
                if site.get("datacenter"):
                    if site["datacenter"] not in myvims:
                        #Add this datacenter to myvims
                        d, v = get_datacenter_by_name_uuid(mydb, tenant_id, site["datacenter"])
                        myvims[d] = v
                        myvim_threads[d] = get_vim_thread(tenant_id, site["datacenter"])
                        datacenter2tenant[d] = v['config']['datacenter_tenant_id']
                        site["datacenter"] = d #change name to id
                else:
                    if site_without_datacenter_field:
                        raise NfvoException("Found more than one entries without datacenter field at instance:networks:{}:sites".format(net_name), HTTP_Bad_Request)
                    site_without_datacenter_field = True
                    site["datacenter"] = default_datacenter_id #change name to id

        for vnf_name, vnf_instance_desc in instance_dict.get("vnfs",{}).iteritems():
            found=False
            for scenario_vnf in scenarioDict['vnfs']:
                if vnf_name == scenario_vnf['name']:
                    found = True
                    break
            if not found:
                raise NfvoException("Invalid vnf name '{}' at instance:vnfs".format(vnf_instance_desc), HTTP_Bad_Request)
            if "datacenter" in vnf_instance_desc:
            # Add this datacenter to myvims
                if vnf_instance_desc["datacenter"] not in myvims:
                    d, v = get_datacenter_by_name_uuid(mydb, tenant_id, vnf_instance_desc["datacenter"])
                    myvims[d] = v
                    myvim_threads[d] = get_vim_thread(tenant_id, vnf_instance_desc["datacenter"])
                    datacenter2tenant[d] = v['config']['datacenter_tenant_id']
                scenario_vnf["datacenter"] = vnf_instance_desc["datacenter"]

    #0.1 parse cloud-config parameters
        cloud_config = unify_cloud_config(instance_dict.get("cloud-config"), scenarioDict.get("cloud-config"))

    #0.2 merge instance information into scenario
        #Ideally, the operation should be as simple as: update(scenarioDict,instance_dict)
        #However, this is not possible yet.
        for net_name, net_instance_desc in instance_dict.get("networks",{}).iteritems():
            for scenario_net in scenarioDict['nets']:
                if net_name == scenario_net["name"]:
                    if 'ip-profile' in net_instance_desc:
                        ipprofile = net_instance_desc['ip-profile']
                        ipprofile['subnet_address'] = ipprofile.pop('subnet-address',None)
                        ipprofile['ip_version'] = ipprofile.pop('ip-version','IPv4')
                        ipprofile['gateway_address'] = ipprofile.pop('gateway-address',None)
                        ipprofile['dns_address'] = ipprofile.pop('dns-address',None)
                        if 'dhcp' in ipprofile:
                            ipprofile['dhcp_start_address'] = ipprofile['dhcp'].get('start-address',None)
                            ipprofile['dhcp_enabled'] = ipprofile['dhcp'].get('enabled',True)
                            ipprofile['dhcp_count'] = ipprofile['dhcp'].get('count',None)
                            del ipprofile['dhcp']
                        if 'ip_profile' not in scenario_net:
                            scenario_net['ip_profile'] = ipprofile
                        else:
                            update(scenario_net['ip_profile'],ipprofile)
            for interface in net_instance_desc.get('interfaces', () ):
                if 'ip_address' in interface:
                    for vnf in scenarioDict['vnfs']:
                        if interface['vnf'] == vnf['name']:
                            for vnf_interface in vnf['interfaces']:
                                if interface['vnf_interface'] == vnf_interface['external_name']:
                                    vnf_interface['ip_address']=interface['ip_address']

        #logger.debug(">>>>>>>> Merged dictionary")
        logger.debug("Creating instance scenario-dict MERGED:\n%s", yaml.safe_dump(scenarioDict, indent=4, default_flow_style=False))


        # 1. Creating new nets (sce_nets) in the VIM"
        for sce_net in scenarioDict['nets']:
            sce_net["vim_id_sites"]={}
            descriptor_net =  instance_dict.get("networks",{}).get(sce_net["name"],{})
            net_name = descriptor_net.get("vim-network-name")
            auxNetDict['scenario'][sce_net['uuid']] = {}

            sites = descriptor_net.get("sites", [ {} ])
            for site in sites:
                if site.get("datacenter"):
                    vim = myvims[ site["datacenter"] ]
                    datacenter_id = site["datacenter"]
                    myvim_thread = myvim_threads[ site["datacenter"] ]
                else:
                    vim = myvims[ default_datacenter_id ]
                    datacenter_id = default_datacenter_id
                    myvim_thread = myvim_threads[default_datacenter_id]
                net_type = sce_net['type']
                lookfor_filter = {'admin_state_up': True, 'status': 'ACTIVE'} #'shared': True
                if sce_net["external"]:
                    if not net_name:
                        net_name = sce_net["name"]
                    if "netmap-use" in site or "netmap-create" in site:
                        create_network = False
                        lookfor_network = False
                        if "netmap-use" in site:
                            lookfor_network = True
                            if utils.check_valid_uuid(site["netmap-use"]):
                                filter_text = "scenario id '%s'" % site["netmap-use"]
                                lookfor_filter["id"] = site["netmap-use"]
                            else:
                                filter_text = "scenario name '%s'" % site["netmap-use"]
                                lookfor_filter["name"] = site["netmap-use"]
                        if "netmap-create" in site:
                            create_network = True
                            net_vim_name = net_name
                            if site["netmap-create"]:
                                net_vim_name = site["netmap-create"]

                    elif sce_net['vim_id'] != None:
                        #there is a netmap at datacenter_nets database   #TODO REVISE!!!!
                        create_network = False
                        lookfor_network = True
                        lookfor_filter["id"] = sce_net['vim_id']
                        filter_text = "vim_id '%s' datacenter_netmap name '%s'. Try to reload vims with datacenter-net-update" % (sce_net['vim_id'], sce_net["name"])
                        #look for network at datacenter and return error
                    else:
                        #There is not a netmap, look at datacenter for a net with this name and create if not found
                        create_network = True
                        lookfor_network = True
                        lookfor_filter["name"] = sce_net["name"]
                        net_vim_name = sce_net["name"]
                        filter_text = "scenario name '%s'" % sce_net["name"]
                else:
                    if not net_name:
                        net_name = "%s.%s" %(instance_name, sce_net["name"])
                        net_name = net_name[:255]     #limit length
                    net_vim_name = net_name
                    create_network = True
                    lookfor_network = False

                if lookfor_network:
                    vim_nets = vim.get_network_list(filter_dict=lookfor_filter)
                    if len(vim_nets) > 1:
                        raise NfvoException("More than one candidate VIM network found for " + filter_text, HTTP_Bad_Request )
                    elif len(vim_nets) == 0:
                        if not create_network:
                            raise NfvoException("No candidate VIM network found for " + filter_text, HTTP_Bad_Request )
                    else:
                        sce_net["vim_id_sites"][datacenter_id] = vim_nets[0]['id']
                        auxNetDict['scenario'][sce_net['uuid']][datacenter_id] = vim_nets[0]['id']
                        create_network = False
                if create_network:
                    #if network is not external
                    task = new_task("new-net", (net_vim_name, net_type, sce_net.get('ip_profile',None)))
                    task_id = myvim_thread.insert_task(task)
                    instance_tasks[task_id] = task
                    #network_id = vim.new_network(net_vim_name, net_type, sce_net.get('ip_profile',None))
                    sce_net["vim_id_sites"][datacenter_id] = task_id
                    auxNetDict['scenario'][sce_net['uuid']][datacenter_id] = task_id
                    rollbackList.append({'what':'network', 'where':'vim', 'vim_id':datacenter_id, 'uuid':task_id})
                    sce_net["created"] = True

        # 2. Creating new nets (vnf internal nets) in the VIM"
        #For each vnf net, we create it and we add it to instanceNetlist.
        for sce_vnf in scenarioDict['vnfs']:
            for net in sce_vnf['nets']:
                if sce_vnf.get("datacenter"):
                    vim = myvims[ sce_vnf["datacenter"] ]
                    datacenter_id = sce_vnf["datacenter"]
                    myvim_thread = myvim_threads[ sce_vnf["datacenter"]]
                else:
                    vim = myvims[ default_datacenter_id ]
                    datacenter_id = default_datacenter_id
                    myvim_thread = myvim_threads[default_datacenter_id]
                descriptor_net =  instance_dict.get("vnfs",{}).get(sce_vnf["name"],{})
                net_name = descriptor_net.get("name")
                if not net_name:
                    net_name = "%s.%s" %(instance_name, net["name"])
                    net_name = net_name[:255]     #limit length
                net_type = net['type']
                task = new_task("new-net", (net_name, net_type, net.get('ip_profile',None)))
                task_id = myvim_thread.insert_task(task)
                instance_tasks[task_id] = task
                # network_id = vim.new_network(net_name, net_type, net.get('ip_profile',None))
                net['vim_id'] = task_id
                if sce_vnf['uuid'] not in auxNetDict:
                    auxNetDict[sce_vnf['uuid']] = {}
                auxNetDict[sce_vnf['uuid']][net['uuid']] = task_id
                rollbackList.append({'what':'network','where':'vim','vim_id':datacenter_id,'uuid':task_id})
                net["created"] = True


        #print "auxNetDict:"
        #print yaml.safe_dump(auxNetDict, indent=4, default_flow_style=False)

        # 3. Creating new vm instances in the VIM
        #myvim.new_vminstance(self,vimURI,tenant_id,name,description,image_id,flavor_id,net_dict)
        for sce_vnf in scenarioDict['vnfs']:
            if sce_vnf.get("datacenter"):
                vim = myvims[ sce_vnf["datacenter"] ]
                myvim_thread = myvim_threads[ sce_vnf["datacenter"] ]
                datacenter_id = sce_vnf["datacenter"]
            else:
                vim = myvims[ default_datacenter_id ]
                myvim_thread = myvim_threads[ default_datacenter_id ]
                datacenter_id = default_datacenter_id
            sce_vnf["datacenter_id"] =  datacenter_id
            i = 0
            for vm in sce_vnf['vms']:
                i += 1
                myVMDict = {}
                myVMDict['name'] = "{}.{}.{}".format(instance_name,sce_vnf['name'],chr(96+i))
                myVMDict['description'] = myVMDict['name'][0:99]
#                if not startvms:
#                    myVMDict['start'] = "no"
                myVMDict['name'] = myVMDict['name'][0:255] #limit name length
                #create image at vim in case it not exist
                image_dict = mydb.get_table_by_uuid_name("images", vm['image_id'])
                image_id = create_or_use_image(mydb, {datacenter_id: vim}, image_dict, [], True)
                vm['vim_image_id'] = image_id

                #create flavor at vim in case it not exist
                flavor_dict = mydb.get_table_by_uuid_name("flavors", vm['flavor_id'])
                if flavor_dict['extended']!=None:
                    flavor_dict['extended']= yaml.load(flavor_dict['extended'])
                flavor_id = create_or_use_flavor(mydb, {datacenter_id: vim}, flavor_dict, rollbackList, True)

                #Obtain information for additional disks
                extended_flavor_dict = mydb.get_rows(FROM='datacenters_flavors', SELECT=('extended',), WHERE={'vim_id': flavor_id})
                if not extended_flavor_dict:
                    raise NfvoException("flavor '{}' not found".format(flavor_id), HTTP_Not_Found)
                    return

                #extended_flavor_dict_yaml = yaml.load(extended_flavor_dict[0])
                myVMDict['disks'] = None
                extended_info = extended_flavor_dict[0]['extended']
                if extended_info != None:
                    extended_flavor_dict_yaml = yaml.load(extended_info)
                    if 'disks' in extended_flavor_dict_yaml:
                        myVMDict['disks'] = extended_flavor_dict_yaml['disks']

                vm['vim_flavor_id'] = flavor_id
                myVMDict['imageRef'] = vm['vim_image_id']
                myVMDict['flavorRef'] = vm['vim_flavor_id']
                myVMDict['networks'] = []
                task_depends = {}
                #TODO ALF. connect_mgmt_interfaces. Connect management interfaces if this is true
                for iface in vm['interfaces']:
                    netDict = {}
                    if iface['type']=="data":
                        netDict['type'] = iface['model']
                    elif "model" in iface and iface["model"]!=None:
                        netDict['model']=iface['model']
                    #TODO in future, remove this because mac_address will not be set, and the type of PV,VF is obtained from iterface table model
                    #discover type of interface looking at flavor
                    for numa in flavor_dict.get('extended',{}).get('numas',[]):
                        for flavor_iface in numa.get('interfaces',[]):
                            if flavor_iface.get('name') == iface['internal_name']:
                                if flavor_iface['dedicated'] == 'yes':
                                    netDict['type']="PF"    #passthrough
                                elif flavor_iface['dedicated'] == 'no':
                                    netDict['type']="VF"    #siov
                                elif flavor_iface['dedicated'] == 'yes:sriov':
                                    netDict['type']="VFnotShared"   #sriov but only one sriov on the PF
                                netDict["mac_address"] = flavor_iface.get("mac_address")
                                break;
                    netDict["use"]=iface['type']
                    if netDict["use"]=="data" and not netDict.get("type"):
                        #print "netDict", netDict
                        #print "iface", iface
                        e_text = "Cannot determine the interface type PF or VF of VNF '%s' VM '%s' iface '%s'" %(sce_vnf['name'], vm['name'], iface['internal_name'])
                        if flavor_dict.get('extended')==None:
                            raise NfvoException(e_text + "After database migration some information is not available. \
                                    Try to delete and create the scenarios and VNFs again", HTTP_Conflict)
                        else:
                            raise NfvoException(e_text, HTTP_Internal_Server_Error)
                    if netDict["use"]=="mgmt" or netDict["use"]=="bridge":
                        netDict["type"]="virtual"
                    if "vpci" in iface and iface["vpci"] is not None:
                        netDict['vpci'] = iface['vpci']
                    if "mac" in iface and iface["mac"] is not None:
                        netDict['mac_address'] = iface['mac']
                    if "port-security" in iface and iface["port-security"] is not None:
                        netDict['port_security'] = iface['port-security']
                    if "floating-ip" in iface and iface["floating-ip"] is not None:
                        netDict['floating_ip'] = iface['floating-ip']
                    netDict['name'] = iface['internal_name']
                    if iface['net_id'] is None:
                        for vnf_iface in sce_vnf["interfaces"]:
                            #print iface
                            #print vnf_iface
                            if vnf_iface['interface_id']==iface['uuid']:
                                netDict['net_id'] = auxNetDict['scenario'][ vnf_iface['sce_net_id'] ][datacenter_id]
                                break
                    else:
                        netDict['net_id'] = auxNetDict[ sce_vnf['uuid'] ][ iface['net_id'] ]
                    if is_task_id(netDict['net_id']):
                        task_depends[netDict['net_id']] = instance_tasks[netDict['net_id']]
                    #skip bridge ifaces not connected to any net
                    #if 'net_id' not in netDict or netDict['net_id']==None:
                    #    continue
                    myVMDict['networks'].append(netDict)
                #print ">>>>>>>>>>>>>>>>>>>>>>>>>>>"
                #print myVMDict['name']
                #print "networks", yaml.safe_dump(myVMDict['networks'], indent=4, default_flow_style=False)
                #print "interfaces", yaml.safe_dump(vm['interfaces'], indent=4, default_flow_style=False)
                #print ">>>>>>>>>>>>>>>>>>>>>>>>>>>"
                if vm.get("boot_data"):
                    cloud_config_vm = unify_cloud_config(vm["boot_data"], cloud_config)
                else:
                    cloud_config_vm = cloud_config
                task = new_task("new-vm", (myVMDict['name'], myVMDict['description'], myVMDict.get('start', None),
                                           myVMDict['imageRef'], myVMDict['flavorRef'], myVMDict['networks'],
                                           cloud_config_vm, myVMDict['disks']), depends=task_depends)
                vm_id = myvim_thread.insert_task(task)
                instance_tasks[vm_id] = task

                vm['vim_id'] = vm_id
                rollbackList.append({'what':'vm','where':'vim','vim_id':datacenter_id,'uuid':vm_id})
                #put interface uuid back to scenario[vnfs][vms[[interfaces]
                for net in myVMDict['networks']:
                    if "vim_id" in net:
                        for iface in vm['interfaces']:
                            if net["name"]==iface["internal_name"]:
                                iface["vim_id"]=net["vim_id"]
                                break
        scenarioDict["datacenter2tenant"] = datacenter2tenant
        logger.debug("create_instance Deployment done scenarioDict: %s",
                    yaml.safe_dump(scenarioDict, indent=4, default_flow_style=False) )
        instance_id = mydb.new_instance_scenario_as_a_whole(tenant_id,instance_name, instance_description, scenarioDict)
        # Update database with those ended tasks
        for task in instance_tasks.values():
            if task["status"] == "ok":
                if task["name"] == "new-vm":
                    mydb.update_rows("instance_vms", UPDATE={"vim_vm_id": task["result"]},
                                     WHERE={"vim_vm_id": task["id"]})
                elif task["name"] == "new-net":
                    mydb.update_rows("instance_nets", UPDATE={"vim_net_id": task["result"]},
                                     WHERE={"vim_net_id": task["id"]})
        return mydb.get_instance_scenario(instance_id)
    except (NfvoException, vimconn.vimconnException,db_base_Exception)  as e:
        message = rollback(mydb, myvims, rollbackList)
        if isinstance(e, db_base_Exception):
            error_text = "database Exception"
        elif isinstance(e, vimconn.vimconnException):
            error_text = "VIM Exception"
        else:
            error_text = "Exception"
        error_text += " {} {}. {}".format(type(e).__name__, str(e), message)
        #logger.error("create_instance: %s", error_text)
        raise NfvoException(error_text, e.http_code)


def delete_instance(mydb, tenant_id, instance_id):
    #print "Checking that the instance_id exists and getting the instance dictionary"
    instanceDict = mydb.get_instance_scenario(instance_id, tenant_id)
    #print yaml.safe_dump(instanceDict, indent=4, default_flow_style=False)
    tenant_id = instanceDict["tenant_id"]
    #print "Checking that nfvo_tenant_id exists and getting the VIM URI and the VIM tenant_id"

    #1. Delete from Database
    message = mydb.delete_instance_scenario(instance_id, tenant_id)

    #2. delete from VIM
    error_msg = ""
    myvims = {}
    myvim_threads = {}

    #2.1 deleting VMs
    #vm_fail_list=[]
    for sce_vnf in instanceDict['vnfs']:
        datacenter_key = (sce_vnf["datacenter_id"], sce_vnf["datacenter_tenant_id"])
        if datacenter_key not in myvims:
            try:
                myvim_thread = get_vim_thread(tenant_id, sce_vnf["datacenter_id"], sce_vnf["datacenter_tenant_id"])
            except NfvoException as e:
                logger.error(str(e))
                myvim_thread = None
            myvim_threads[datacenter_key] = myvim_thread
            vims = get_vim(mydb, tenant_id, datacenter_id=sce_vnf["datacenter_id"],
                       datacenter_tenant_id=sce_vnf["datacenter_tenant_id"])
            if len(vims) == 0:
                logger.error("datacenter '{}' with datacenter_tenant_id '{}' not found".format(sce_vnf["datacenter_id"],
                                                                                        sce_vnf["datacenter_tenant_id"]))
                myvims[datacenter_key] = None
            else:
                myvims[datacenter_key] = vims.values()[0]
        myvim = myvims[datacenter_key]
        myvim_thread = myvim_threads[datacenter_key]
        for vm in sce_vnf['vms']:
            if not myvim:
                error_msg += "\n    VM id={} cannot be deleted because datacenter={} not found".format(vm['vim_vm_id'], sce_vnf["datacenter_id"])
                continue
            try:
                task=None
                if is_task_id(vm['vim_vm_id']):
                    task_id = vm['vim_vm_id']
                    old_task = task_dict.get(task_id)
                    if not old_task:
                        error_msg += "\n    VM was scheduled for create, but task {} is not found".format(task_id)
                        continue
                    with task_lock:
                        if old_task["status"] == "enqueued":
                            old_task["status"] = "deleted"
                        elif old_task["status"] == "error":
                            continue
                        elif old_task["status"] == "processing":
                            task = new_task("del-vm", task_id, depends={task_id: old_task})
                        else: #ok
                            task = new_task("del-vm", old_task["result"])
                else:
                    task = new_task("del-vm", vm['vim_vm_id'], store=False)
                if task:
                    myvim_thread.insert_task(task)
            except vimconn.vimconnNotFoundException as e:
                error_msg+="\n    VM VIM_id={} not found at datacenter={}".format(vm['vim_vm_id'], sce_vnf["datacenter_id"])
                logger.warn("VM instance '%s'uuid '%s', VIM id '%s', from VNF_id '%s' not found",
                    vm['name'], vm['uuid'], vm['vim_vm_id'], sce_vnf['vnf_id'])
            except vimconn.vimconnException as e:
                error_msg+="\n    VM VIM_id={} at datacenter={} Error: {} {}".format(vm['vim_vm_id'], sce_vnf["datacenter_id"], e.http_code, str(e))
                logger.error("Error %d deleting VM instance '%s'uuid '%s', VIM_id '%s', from VNF_id '%s': %s",
                    e.http_code, vm['name'], vm['uuid'], vm['vim_vm_id'], sce_vnf['vnf_id'], str(e))

    #2.2 deleting NETS
    #net_fail_list=[]
    for net in instanceDict['nets']:
        if not net['created']:
            continue #skip not created nets
        datacenter_key = (net["datacenter_id"], net["datacenter_tenant_id"])
        if datacenter_key not in myvims:
            try:
                myvim_thread = get_vim_thread(tenant_id, sce_vnf["datacenter_id"], sce_vnf["datacenter_tenant_id"])
            except NfvoException as e:
                logger.error(str(e))
                myvim_thread = None
            myvim_threads[datacenter_key] = myvim_thread
            vims = get_vim(mydb, tenant_id, datacenter_id=net["datacenter_id"],
                           datacenter_tenant_id=net["datacenter_tenant_id"])
            if len(vims) == 0:
                logger.error("datacenter '{}' with datacenter_tenant_id '{}' not found".format(net["datacenter_id"], net["datacenter_tenant_id"]))
                myvims[datacenter_key] = None
            else:
                myvims[datacenter_key] = vims.values()[0]
        myvim = myvims[datacenter_key]
        myvim_thread = myvim_threads[datacenter_key]

        if not myvim:
            error_msg += "\n    Net VIM_id={} cannot be deleted because datacenter={} not found".format(net['vim_net_id'], net["datacenter_id"])
            continue
        try:
            task = None
            if is_task_id(net['vim_net_id']):
                task_id = net['vim_net_id']
                old_task = task_dict.get(task_id)
                if not old_task:
                    error_msg += "\n    NET was scheduled for create, but task {} is not found".format(task_id)
                    continue
                with task_lock:
                    if old_task["status"] == "enqueued":
                        old_task["status"] = "deleted"
                    elif old_task["status"] == "error":
                        continue
                    elif old_task["status"] == "processing":
                        task = new_task("del-net", task_id, depends={task_id: old_task})
                    else:  # ok
                        task = new_task("del-net", old_task["result"])
            else:
                task = new_task("del-net", net['vim_net_id'], store=False)
            if task:
                myvim_thread.insert_task(task)
        except vimconn.vimconnNotFoundException as e:
            error_msg += "\n    NET VIM_id={} not found at datacenter={}".format(net['vim_net_id'], net["datacenter_id"])
            logger.warn("NET '%s', VIM_id '%s', from VNF_net_id '%s' not found",
                        net['uuid'], net['vim_net_id'], str(net['vnf_net_id']))
        except vimconn.vimconnException as e:
            error_msg += "\n    NET VIM_id={} at datacenter={} Error: {} {}".format(net['vim_net_id'],
                                                                                    net["datacenter_id"],
                                                                                    e.http_code, str(e))
            logger.error("Error %d deleting NET '%s', VIM_id '%s', from VNF_net_id '%s': %s",
                         e.http_code, net['uuid'], net['vim_net_id'], str(net['vnf_net_id']), str(e))
    if len(error_msg) > 0:
        return 'instance ' + message + ' deleted but some elements could not be deleted, or already deleted (error: 404) from VIM: ' + error_msg
    else:
        return 'instance ' + message + ' deleted'


def refresh_instance(mydb, nfvo_tenant, instanceDict, datacenter=None, vim_tenant=None):
    '''Refreshes a scenario instance. It modifies instanceDict'''
    '''Returns:
         - result: <0 if there is any unexpected error, n>=0 if no errors where n is the number of vms and nets that couldn't be updated in the database
         - error_msg
    '''
    # Assumption: nfvo_tenant and instance_id were checked before entering into this function
    #print "nfvo.refresh_instance begins"
    #print json.dumps(instanceDict, indent=4)

    #print "Getting the VIM URL and the VIM tenant_id"
    myvims={}

    # 1. Getting VIM vm and net list
    vms_updated = [] #List of VM instance uuids in openmano that were updated
    vms_notupdated=[]
    vm_list = {}
    for sce_vnf in instanceDict['vnfs']:
        datacenter_key = (sce_vnf["datacenter_id"], sce_vnf["datacenter_tenant_id"])
        if datacenter_key not in vm_list:
            vm_list[datacenter_key] = []
        if datacenter_key not in myvims:
            vims = get_vim(mydb, nfvo_tenant, datacenter_id=sce_vnf["datacenter_id"],
                           datacenter_tenant_id=sce_vnf["datacenter_tenant_id"])
            if len(vims) == 0:
                logger.error("datacenter '{}' with datacenter_tenant_id '{}' not found".format(sce_vnf["datacenter_id"], sce_vnf["datacenter_tenant_id"]))
                myvims[datacenter_key] = None
            else:
                myvims[datacenter_key] = vims.values()[0]
        for vm in sce_vnf['vms']:
            vm_list[datacenter_key].append(vm['vim_vm_id'])
            vms_notupdated.append(vm["uuid"])

    nets_updated = [] #List of VM instance uuids in openmano that were updated
    nets_notupdated=[]
    net_list = {}
    for net in instanceDict['nets']:
        datacenter_key = (net["datacenter_id"], net["datacenter_tenant_id"])
        if datacenter_key not in net_list:
            net_list[datacenter_key] = []
        if datacenter_key not in myvims:
            vims = get_vim(mydb, nfvo_tenant, datacenter_id=net["datacenter_id"],
                           datacenter_tenant_id=net["datacenter_tenant_id"])
            if len(vims) == 0:
                logger.error("datacenter '{}' with datacenter_tenant_id '{}' not found".format(net["datacenter_id"], net["datacenter_tenant_id"]))
                myvims[datacenter_key] = None
            else:
                myvims[datacenter_key] = vims.values()[0]

        net_list[datacenter_key].append(net['vim_net_id'])
        nets_notupdated.append(net["uuid"])

    # 1. Getting the status of all VMs
    vm_dict={}
    for datacenter_key in myvims:
        if not vm_list.get(datacenter_key):
            continue
        failed = True
        failed_message=""
        if not myvims[datacenter_key]:
            failed_message = "datacenter '{}' with datacenter_tenant_id '{}' not found".format(net["datacenter_id"], net["datacenter_tenant_id"])
        else:
            try:
                vm_dict.update(myvims[datacenter_key].refresh_vms_status(vm_list[datacenter_key]) )
                failed = False
            except vimconn.vimconnException as e:
                logger.error("VIM exception %s %s", type(e).__name__, str(e))
                failed_message = str(e)
        if failed:
            for vm in vm_list[datacenter_key]:
                vm_dict[vm] = {'status': "VIM_ERROR", 'error_msg': failed_message}

    # 2. Update the status of VMs in the instanceDict, while collects the VMs whose status changed
    for sce_vnf in instanceDict['vnfs']:
        for vm in sce_vnf['vms']:
            vm_id = vm['vim_vm_id']
            interfaces = vm_dict[vm_id].pop('interfaces', [])
            #2.0 look if contain manamgement interface, and if not change status from ACTIVE:NoMgmtIP to ACTIVE
            has_mgmt_iface = False
            for iface in vm["interfaces"]:
                if iface["type"]=="mgmt":
                    has_mgmt_iface = True
            if vm_dict[vm_id]['status'] == "ACTIVE:NoMgmtIP" and not has_mgmt_iface:
                vm_dict[vm_id]['status'] = "ACTIVE"
            if vm_dict[vm_id].get('error_msg') and len(vm_dict[vm_id]['error_msg']) >= 1024:
                vm_dict[vm_id]['error_msg'] = vm_dict[vm_id]['error_msg'][:516] + " ... " + vm_dict[vm_id]['error_msg'][-500:]
            if vm['status'] != vm_dict[vm_id]['status'] or vm.get('error_msg')!=vm_dict[vm_id].get('error_msg') or vm.get('vim_info')!=vm_dict[vm_id].get('vim_info'):
                vm['status']    = vm_dict[vm_id]['status']
                vm['error_msg'] = vm_dict[vm_id].get('error_msg')
                vm['vim_info']  = vm_dict[vm_id].get('vim_info')
                # 2.1. Update in openmano DB the VMs whose status changed
                try:
                    updates = mydb.update_rows('instance_vms', UPDATE=vm_dict[vm_id], WHERE={'uuid':vm["uuid"]})
                    vms_notupdated.remove(vm["uuid"])
                    if updates>0:
                        vms_updated.append(vm["uuid"])
                except db_base_Exception as e:
                    logger.error("nfvo.refresh_instance error database update: %s", str(e))
            # 2.2. Update in openmano DB the interface VMs
            for interface in interfaces:
                #translate from vim_net_id to instance_net_id
                network_id_list=[]
                for net in instanceDict['nets']:
                    if net["vim_net_id"] == interface["vim_net_id"]:
                        network_id_list.append(net["uuid"])
                if not network_id_list:
                    continue
                del interface["vim_net_id"]
                try:
                    for network_id in network_id_list:
                        mydb.update_rows('instance_interfaces', UPDATE=interface, WHERE={'instance_vm_id':vm["uuid"], "instance_net_id":network_id})
                except db_base_Exception as e:
                    logger.error( "nfvo.refresh_instance error with vm=%s, interface_net_id=%s", vm["uuid"], network_id)

    # 3. Getting the status of all nets
    net_dict = {}
    for datacenter_key in myvims:
        if not net_list.get(datacenter_key):
            continue
        failed = True
        failed_message = ""
        if not myvims[datacenter_key]:
            failed_message = "datacenter '{}' with datacenter_tenant_id '{}' not found".format(net["datacenter_id"], net["datacenter_tenant_id"])
        else:
            try:
                net_dict.update(myvims[datacenter_key].refresh_nets_status(net_list[datacenter_key]) )
                failed = False
            except vimconn.vimconnException as e:
                logger.error("VIM exception %s %s", type(e).__name__, str(e))
                failed_message = str(e)
        if failed:
            for net in net_list[datacenter_key]:
                net_dict[net] = {'status': "VIM_ERROR", 'error_msg': failed_message}

    # 4. Update the status of nets in the instanceDict, while collects the nets whose status changed
    # TODO: update nets inside a vnf
    for net in instanceDict['nets']:
        net_id = net['vim_net_id']
        if net_dict[net_id].get('error_msg') and len(net_dict[net_id]['error_msg']) >= 1024:
            net_dict[net_id]['error_msg'] = net_dict[net_id]['error_msg'][:516] + " ... " + net_dict[vm_id]['error_msg'][-500:]
        if net['status'] != net_dict[net_id]['status'] or net.get('error_msg')!=net_dict[net_id].get('error_msg') or net.get('vim_info')!=net_dict[net_id].get('vim_info'):
            net['status']    = net_dict[net_id]['status']
            net['error_msg'] = net_dict[net_id].get('error_msg')
            net['vim_info']  = net_dict[net_id].get('vim_info')
            # 5.1. Update in openmano DB the nets whose status changed
            try:
                updated = mydb.update_rows('instance_nets', UPDATE=net_dict[net_id], WHERE={'uuid':net["uuid"]})
                nets_notupdated.remove(net["uuid"])
                if updated>0:
                    nets_updated.append(net["uuid"])
            except db_base_Exception as e:
                logger.error("nfvo.refresh_instance error database update: %s", str(e))

    # Returns appropriate output
    #print "nfvo.refresh_instance finishes"
    logger.debug("VMs updated in the database: %s; nets updated in the database %s; VMs not updated: %s; nets not updated: %s",
                str(vms_updated), str(nets_updated), str(vms_notupdated), str(nets_notupdated))
    instance_id = instanceDict['uuid']
    if len(vms_notupdated)+len(nets_notupdated)>0:
        error_msg = "VMs not updated: " + str(vms_notupdated) + "; nets not updated: " + str(nets_notupdated)
        return len(vms_notupdated)+len(nets_notupdated), 'Scenario instance ' + instance_id + ' refreshed but some elements could not be updated in the database: ' + error_msg

    return 0, 'Scenario instance ' + instance_id + ' refreshed.'


def instance_action(mydb,nfvo_tenant,instance_id, action_dict):
    #print "Checking that the instance_id exists and getting the instance dictionary"
    instanceDict = mydb.get_instance_scenario(instance_id, nfvo_tenant)
    #print yaml.safe_dump(instanceDict, indent=4, default_flow_style=False)

    #print "Checking that nfvo_tenant_id exists and getting the VIM URI and the VIM tenant_id"
    vims = get_vim(mydb, nfvo_tenant, instanceDict['datacenter_id'])
    if len(vims) == 0:
        raise NfvoException("datacenter '{}' not found".format(str(instanceDict['datacenter_id'])), HTTP_Not_Found)
    myvim = vims.values()[0]


    input_vnfs = action_dict.pop("vnfs", [])
    input_vms = action_dict.pop("vms", [])
    action_over_all = True if len(input_vnfs)==0 and len (input_vms)==0 else False
    vm_result = {}
    vm_error = 0
    vm_ok = 0
    for sce_vnf in instanceDict['vnfs']:
        for vm in sce_vnf['vms']:
            if not action_over_all:
                if sce_vnf['uuid'] not in input_vnfs and sce_vnf['vnf_name'] not in input_vnfs and \
                    vm['uuid'] not in input_vms and vm['name'] not in input_vms:
                    continue
            try:
                data = myvim.action_vminstance(vm['vim_vm_id'], action_dict)
                if "console" in action_dict:
                    if not global_config["http_console_proxy"]:
                        vm_result[ vm['uuid'] ] = {"vim_result": 200,
                                                   "description": "{protocol}//{ip}:{port}/{suffix}".format(
                                                                                protocol=data["protocol"],
                                                                                ip = data["server"],
                                                                                port = data["port"],
                                                                                suffix = data["suffix"]),
                                                   "name":vm['name']
                                                }
                        vm_ok +=1
                    elif data["server"]=="127.0.0.1" or data["server"]=="localhost":
                        vm_result[ vm['uuid'] ] = {"vim_result": -HTTP_Unauthorized,
                                                   "description": "this console is only reachable by local interface",
                                                   "name":vm['name']
                                                }
                        vm_error+=1
                    else:
                    #print "console data", data
                        try:
                            console_thread = create_or_use_console_proxy_thread(data["server"], data["port"])
                            vm_result[ vm['uuid'] ] = {"vim_result": 200,
                                                       "description": "{protocol}//{ip}:{port}/{suffix}".format(
                                                                                    protocol=data["protocol"],
                                                                                    ip = global_config["http_console_host"],
                                                                                    port = console_thread.port,
                                                                                    suffix = data["suffix"]),
                                                       "name":vm['name']
                                                    }
                            vm_ok +=1
                        except NfvoException as e:
                            vm_result[ vm['uuid'] ] = {"vim_result": e.http_code, "name":vm['name'], "description": str(e)}
                            vm_error+=1

                else:
                    vm_result[ vm['uuid'] ] = {"vim_result": 200, "description": "ok", "name":vm['name']}
                    vm_ok +=1
            except vimconn.vimconnException as e:
                vm_result[ vm['uuid'] ] = {"vim_result": e.http_code, "name":vm['name'], "description": str(e)}
                vm_error+=1

    if vm_ok==0: #all goes wrong
        return vm_result
    else:
        return vm_result


def create_or_use_console_proxy_thread(console_server, console_port):
    #look for a non-used port
    console_thread_key = console_server + ":" + str(console_port)
    if console_thread_key in global_config["console_thread"]:
        #global_config["console_thread"][console_thread_key].start_timeout()
        return global_config["console_thread"][console_thread_key]

    for port in  global_config["console_port_iterator"]():
        #print "create_or_use_console_proxy_thread() port:", port
        if port in global_config["console_ports"]:
            continue
        try:
            clithread = cli.ConsoleProxyThread(global_config['http_host'], port, console_server, console_port)
            clithread.start()
            global_config["console_thread"][console_thread_key] = clithread
            global_config["console_ports"][port] = console_thread_key
            return clithread
        except cli.ConsoleProxyExceptionPortUsed as e:
            #port used, try with onoher
            continue
        except cli.ConsoleProxyException as e:
            raise NfvoException(str(e), HTTP_Bad_Request)
    raise NfvoException("Not found any free 'http_console_ports'", HTTP_Conflict)


def check_tenant(mydb, tenant_id):
    '''check that tenant exists at database'''
    tenant = mydb.get_rows(FROM='nfvo_tenants', SELECT=('uuid',), WHERE={'uuid': tenant_id})
    if not tenant:
        raise NfvoException("tenant '{}' not found".format(tenant_id), HTTP_Not_Found)
    return


def new_tenant(mydb, tenant_dict):
    tenant_id = mydb.new_row("nfvo_tenants", tenant_dict, add_uuid=True)
    return tenant_id


def delete_tenant(mydb, tenant):
    #get nfvo_tenant info

    tenant_dict = mydb.get_table_by_uuid_name('nfvo_tenants', tenant, 'tenant')
    mydb.delete_row_by_id("nfvo_tenants", tenant_dict['uuid'])
    return tenant_dict['uuid'] + " " + tenant_dict["name"]


def new_datacenter(mydb, datacenter_descriptor):
    if "config" in datacenter_descriptor:
        datacenter_descriptor["config"]=yaml.safe_dump(datacenter_descriptor["config"],default_flow_style=True,width=256)
    #Check that datacenter-type is correct
    datacenter_type = datacenter_descriptor.get("type", "openvim");
    module_info = None
    try:
        module = "vimconn_" + datacenter_type
        module_info = imp.find_module(module)
    except (IOError, ImportError):
        if module_info and module_info[0]:
            file.close(module_info[0])
        raise NfvoException("Incorrect datacenter type '{}'. Plugin '{}'.py not installed".format(datacenter_type, module), HTTP_Bad_Request)

    datacenter_id = mydb.new_row("datacenters", datacenter_descriptor, add_uuid=True)
    return datacenter_id


def edit_datacenter(mydb, datacenter_id_name, datacenter_descriptor):
    #obtain data, check that only one exist
    datacenter = mydb.get_table_by_uuid_name('datacenters', datacenter_id_name)
    #edit data
    datacenter_id = datacenter['uuid']
    where={'uuid': datacenter['uuid']}
    if "config" in datacenter_descriptor:
        if datacenter_descriptor['config']!=None:
            try:
                new_config_dict = datacenter_descriptor["config"]
                #delete null fields
                to_delete=[]
                for k in new_config_dict:
                    if new_config_dict[k]==None:
                        to_delete.append(k)

                config_dict = yaml.load(datacenter["config"])
                config_dict.update(new_config_dict)
                #delete null fields
                for k in to_delete:
                    del config_dict[k]
            except Exception as e:
                raise NfvoException("Bad format at datacenter:config " + str(e), HTTP_Bad_Request)
        datacenter_descriptor["config"]= yaml.safe_dump(config_dict,default_flow_style=True,width=256) if len(config_dict)>0 else None
    mydb.update_rows('datacenters', datacenter_descriptor, where)
    return datacenter_id


def delete_datacenter(mydb, datacenter):
    #get nfvo_tenant info
    datacenter_dict = mydb.get_table_by_uuid_name('datacenters', datacenter, 'datacenter')
    mydb.delete_row_by_id("datacenters", datacenter_dict['uuid'])
    return datacenter_dict['uuid'] + " " + datacenter_dict['name']


def associate_datacenter_to_tenant(mydb, nfvo_tenant, datacenter, vim_tenant_id=None, vim_tenant_name=None, vim_username=None, vim_password=None, config=None):
    #get datacenter info
    datacenter_id, myvim = get_datacenter_by_name_uuid(mydb, None, datacenter)
    datacenter_name = myvim["name"]

    create_vim_tenant = True if not vim_tenant_id and not vim_tenant_name else False

    # get nfvo_tenant info
    tenant_dict = mydb.get_table_by_uuid_name('nfvo_tenants', nfvo_tenant)
    if vim_tenant_name==None:
        vim_tenant_name=tenant_dict['name']

    #check that this association does not exist before
    tenants_datacenter_dict={"nfvo_tenant_id":tenant_dict['uuid'], "datacenter_id":datacenter_id }
    tenants_datacenters = mydb.get_rows(FROM='tenants_datacenters', WHERE=tenants_datacenter_dict)
    if len(tenants_datacenters)>0:
        raise NfvoException("datacenter '{}' and tenant'{}' are already attached".format(datacenter_id, tenant_dict['uuid']), HTTP_Conflict)

    vim_tenant_id_exist_atdb=False
    if not create_vim_tenant:
        where_={"datacenter_id": datacenter_id}
        if vim_tenant_id!=None:
            where_["vim_tenant_id"] = vim_tenant_id
        if vim_tenant_name!=None:
            where_["vim_tenant_name"] = vim_tenant_name
        #check if vim_tenant_id is already at database
        datacenter_tenants_dict = mydb.get_rows(FROM='datacenter_tenants', WHERE=where_)
        if len(datacenter_tenants_dict)>=1:
            datacenter_tenants_dict = datacenter_tenants_dict[0]
            vim_tenant_id_exist_atdb=True
            #TODO check if a field has changed and edit entry at datacenter_tenants at DB
        else: #result=0
            datacenter_tenants_dict = {}
            #insert at table datacenter_tenants
    else: #if vim_tenant_id==None:
        #create tenant at VIM if not provided
        try:
            vim_tenant_id = myvim.new_tenant(vim_tenant_name, "created by openmano for datacenter "+datacenter_name)
        except vimconn.vimconnException as e:
            raise NfvoException("Not possible to create vim_tenant {} at VIM: {}".format(vim_tenant_id, str(e)), HTTP_Internal_Server_Error)
        datacenter_tenants_dict = {}
        datacenter_tenants_dict["created"]="true"

    #fill datacenter_tenants table
    if not vim_tenant_id_exist_atdb:
        datacenter_tenants_dict["vim_tenant_id"] = vim_tenant_id
        datacenter_tenants_dict["vim_tenant_name"] = vim_tenant_name
        datacenter_tenants_dict["user"] = vim_username
        datacenter_tenants_dict["passwd"] = vim_password
        datacenter_tenants_dict["datacenter_id"] = datacenter_id
        if config:
            datacenter_tenants_dict["config"] = yaml.safe_dump(config, default_flow_style=True, width=256)
        id_ = mydb.new_row('datacenter_tenants', datacenter_tenants_dict, add_uuid=True)
        datacenter_tenants_dict["uuid"] = id_

    #fill tenants_datacenters table
    tenants_datacenter_dict["datacenter_tenant_id"]=datacenter_tenants_dict["uuid"]
    mydb.new_row('tenants_datacenters', tenants_datacenter_dict)
    # create thread
    datacenter_id, myvim = get_datacenter_by_name_uuid(mydb, tenant_dict['uuid'], datacenter_id)  # reload data
    thread_name = get_non_used_vim_name(datacenter_name, datacenter_id, tenant_dict['name'], tenant_dict['uuid'])
    new_thread = vim_thread.vim_thread(myvim, task_lock, thread_name, datacenter_name, db=db, db_lock=db_lock)
    new_thread.start()
    thread_id = datacenter_id + "." + tenant_dict['uuid']
    vim_threads["running"][thread_id] = new_thread
    return datacenter_id


def deassociate_datacenter_to_tenant(mydb, tenant_id, datacenter, vim_tenant_id=None):
    #get datacenter info
    datacenter_id, myvim = get_datacenter_by_name_uuid(mydb, None, datacenter)

    #get nfvo_tenant info
    if not tenant_id or tenant_id=="any":
        tenant_uuid = None
    else:
        tenant_dict = mydb.get_table_by_uuid_name('nfvo_tenants', tenant_id)
        tenant_uuid = tenant_dict['uuid']

    #check that this association exist before
    tenants_datacenter_dict={"datacenter_id":datacenter_id }
    if tenant_uuid:
        tenants_datacenter_dict["nfvo_tenant_id"] = tenant_uuid
    tenant_datacenter_list = mydb.get_rows(FROM='tenants_datacenters', WHERE=tenants_datacenter_dict)
    if len(tenant_datacenter_list)==0 and tenant_uuid:
        raise NfvoException("datacenter '{}' and tenant '{}' are not attached".format(datacenter_id, tenant_dict['uuid']), HTTP_Not_Found)

    #delete this association
    mydb.delete_row(FROM='tenants_datacenters', WHERE=tenants_datacenter_dict)

    #get vim_tenant info and deletes
    warning=''
    for tenant_datacenter_item in tenant_datacenter_list:
        vim_tenant_dict = mydb.get_table_by_uuid_name('datacenter_tenants', tenant_datacenter_item['datacenter_tenant_id'])
        #try to delete vim:tenant
        try:
            mydb.delete_row_by_id('datacenter_tenants', tenant_datacenter_item['datacenter_tenant_id'])
            if vim_tenant_dict['created']=='true':
                #delete tenant at VIM if created by NFVO
                try:
                    myvim.delete_tenant(vim_tenant_dict['vim_tenant_id'])
                except vimconn.vimconnException as e:
                    warning = "Not possible to delete vim_tenant_id {} from VIM: {} ".format(vim_tenant_dict['vim_tenant_id'], str(e))
                    logger.warn(warning)
        except db_base_Exception as e:
            logger.error("Cannot delete datacenter_tenants " + str(e))
            pass  # the error will be caused because dependencies, vim_tenant can not be deleted
        thread_id = datacenter_id + "." + tenant_datacenter_item["nfvo_tenant_id"]
        thread = vim_threads["running"][thread_id]
        thread.insert_task(new_task("exit", None, store=False))
        vim_threads["deleting"][thread_id] = thread
    return "datacenter {} detached. {}".format(datacenter_id, warning)


def datacenter_action(mydb, tenant_id, datacenter, action_dict):
    #DEPRECATED
    #get datacenter info
    datacenter_id, myvim  = get_datacenter_by_name_uuid(mydb, tenant_id, datacenter)

    if 'net-update' in action_dict:
        try:
            nets = myvim.get_network_list(filter_dict={'shared': True, 'admin_state_up': True, 'status': 'ACTIVE'})
            #print content
        except vimconn.vimconnException as e:
            #logger.error("nfvo.datacenter_action() Not possible to get_network_list from VIM: %s ", str(e))
            raise NfvoException(str(e), HTTP_Internal_Server_Error)
        #update nets Change from VIM format to NFVO format
        net_list=[]
        for net in nets:
            net_nfvo={'datacenter_id': datacenter_id}
            net_nfvo['name']       = net['name']
            #net_nfvo['description']= net['name']
            net_nfvo['vim_net_id'] = net['id']
            net_nfvo['type']       = net['type'][0:6] #change from ('ptp','data','bridge_data','bridge_man')  to ('bridge','data','ptp')
            net_nfvo['shared']     = net['shared']
            net_nfvo['multipoint'] = False if net['type']=='ptp' else True
            net_list.append(net_nfvo)
        inserted, deleted = mydb.update_datacenter_nets(datacenter_id, net_list)
        logger.info("Inserted %d nets, deleted %d old nets", inserted, deleted)
        return inserted
    elif 'net-edit' in action_dict:
        net = action_dict['net-edit'].pop('net')
        what = 'vim_net_id' if utils.check_valid_uuid(net) else 'name'
        result = mydb.update_rows('datacenter_nets', action_dict['net-edit'],
                                WHERE={'datacenter_id':datacenter_id, what: net})
        return result
    elif 'net-delete' in action_dict:
        net = action_dict['net-deelte'].get('net')
        what = 'vim_net_id' if utils.check_valid_uuid(net) else 'name'
        result = mydb.delete_row(FROM='datacenter_nets',
                                WHERE={'datacenter_id':datacenter_id, what: net})
        return result

    else:
        raise NfvoException("Unknown action " + str(action_dict), HTTP_Bad_Request)


def datacenter_edit_netmap(mydb, tenant_id, datacenter, netmap, action_dict):
    #get datacenter info
    datacenter_id, _  = get_datacenter_by_name_uuid(mydb, tenant_id, datacenter)

    what = 'uuid' if utils.check_valid_uuid(netmap) else 'name'
    result = mydb.update_rows('datacenter_nets', action_dict['netmap'],
                            WHERE={'datacenter_id':datacenter_id, what: netmap})
    return result


def datacenter_new_netmap(mydb, tenant_id, datacenter, action_dict=None):
    #get datacenter info
    datacenter_id, myvim  = get_datacenter_by_name_uuid(mydb, tenant_id, datacenter)
    filter_dict={}
    if action_dict:
        action_dict = action_dict["netmap"]
        if 'vim_id' in action_dict:
            filter_dict["id"] = action_dict['vim_id']
        if 'vim_name' in action_dict:
            filter_dict["name"] = action_dict['vim_name']
    else:
        filter_dict["shared"] = True

    try:
        vim_nets = myvim.get_network_list(filter_dict=filter_dict)
    except vimconn.vimconnException as e:
        #logger.error("nfvo.datacenter_new_netmap() Not possible to get_network_list from VIM: %s ", str(e))
        raise NfvoException(str(e), HTTP_Internal_Server_Error)
    if len(vim_nets)>1 and action_dict:
        raise NfvoException("more than two networks found, specify with vim_id", HTTP_Conflict)
    elif len(vim_nets)==0: # and action_dict:
        raise NfvoException("Not found a network at VIM with " + str(filter_dict), HTTP_Not_Found)
    net_list=[]
    for net in vim_nets:
        net_nfvo={'datacenter_id': datacenter_id}
        if action_dict and "name" in action_dict:
            net_nfvo['name']       = action_dict['name']
        else:
            net_nfvo['name']       = net['name']
        #net_nfvo['description']= net['name']
        net_nfvo['vim_net_id'] = net['id']
        net_nfvo['type']       = net['type'][0:6] #change from ('ptp','data','bridge_data','bridge_man')  to ('bridge','data','ptp')
        net_nfvo['shared']     = net['shared']
        net_nfvo['multipoint'] = False if net['type']=='ptp' else True
        try:
            net_id = mydb.new_row("datacenter_nets", net_nfvo, add_uuid=True)
            net_nfvo["status"] = "OK"
            net_nfvo["uuid"] = net_id
        except db_base_Exception as e:
            if action_dict:
                raise
            else:
                net_nfvo["status"] = "FAIL: " + str(e)
        net_list.append(net_nfvo)
    return net_list


def vim_action_get(mydb, tenant_id, datacenter, item, name):
    #get datacenter info
    datacenter_id, myvim  = get_datacenter_by_name_uuid(mydb, tenant_id, datacenter)
    filter_dict={}
    if name:
        if utils.check_valid_uuid(name):
            filter_dict["id"] = name
        else:
            filter_dict["name"] = name
    try:
        if item=="networks":
            #filter_dict['tenant_id'] = myvim['tenant_id']
            content = myvim.get_network_list(filter_dict=filter_dict)
        elif item=="tenants":
            content = myvim.get_tenant_list(filter_dict=filter_dict)
        elif item == "images":
            content = myvim.get_image_list(filter_dict=filter_dict)
        else:
            raise NfvoException(item + "?", HTTP_Method_Not_Allowed)
        logger.debug("vim_action response %s", content) #update nets Change from VIM format to NFVO format
        if name and len(content)==1:
            return {item[:-1]: content[0]}
        elif name and len(content)==0:
            raise NfvoException("No {} found with ".format(item[:-1]) + " and ".join(map(lambda x: str(x[0])+": "+str(x[1]), filter_dict.iteritems())),
                 datacenter)
        else:
            return {item: content}
    except vimconn.vimconnException as e:
        print "vim_action Not possible to get_%s_list from VIM: %s " % (item, str(e))
        raise NfvoException("Not possible to get_{}_list from VIM: {}".format(item, str(e)), e.http_code)


def vim_action_delete(mydb, tenant_id, datacenter, item, name):
    #get datacenter info
    if tenant_id == "any":
        tenant_id=None

    datacenter_id, myvim  = get_datacenter_by_name_uuid(mydb, tenant_id, datacenter)
    #get uuid name
    content = vim_action_get(mydb, tenant_id, datacenter, item, name)
    logger.debug("vim_action_delete vim response: " + str(content))
    items = content.values()[0]
    if type(items)==list and len(items)==0:
        raise NfvoException("Not found " + item, HTTP_Not_Found)
    elif type(items)==list and len(items)>1:
        raise NfvoException("Found more than one {} with this name. Use uuid.".format(item), HTTP_Not_Found)
    else: # it is a dict
        item_id = items["id"]
        item_name = str(items.get("name"))

    try:
        if item=="networks":
            content = myvim.delete_network(item_id)
        elif item=="tenants":
            content = myvim.delete_tenant(item_id)
        elif item == "images":
            content = myvim.delete_image(item_id)
        else:
            raise NfvoException(item + "?", HTTP_Method_Not_Allowed)
    except vimconn.vimconnException as e:
        #logger.error( "vim_action Not possible to delete_{} {}from VIM: {} ".format(item, name, str(e)))
        raise NfvoException("Not possible to delete_{} {} from VIM: {}".format(item, name, str(e)), e.http_code)

    return "{} {} {} deleted".format(item[:-1], item_id,item_name)


def vim_action_create(mydb, tenant_id, datacenter, item, descriptor):
    #get datacenter info
    logger.debug("vim_action_create descriptor %s", str(descriptor))
    if tenant_id == "any":
        tenant_id=None
    datacenter_id, myvim  = get_datacenter_by_name_uuid(mydb, tenant_id, datacenter)
    try:
        if item=="networks":
            net = descriptor["network"]
            net_name = net.pop("name")
            net_type = net.pop("type", "bridge")
            net_public = net.pop("shared", False)
            net_ipprofile = net.pop("ip_profile", None)
            net_vlan = net.pop("vlan", None)
            content = myvim.new_network(net_name, net_type, net_ipprofile, shared=net_public, vlan=net_vlan) #, **net)
        elif item=="tenants":
            tenant = descriptor["tenant"]
            content = myvim.new_tenant(tenant["name"], tenant.get("description"))
        else:
            raise NfvoException(item + "?", HTTP_Method_Not_Allowed)
    except vimconn.vimconnException as e:
        raise NfvoException("Not possible to create {} at VIM: {}".format(item, str(e)), e.http_code)

    return vim_action_get(mydb, tenant_id, datacenter, item, content)
