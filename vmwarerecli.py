# -*- coding: utf-8 -*-
##
# This file is standalone vmware vcloud director util
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
# contact with: mbayramov@vmware.com
##

'''

Provide standalone application to work with vCloud director rest api.

mbayramov@vmware.com
'''
import os
import requests
import logging
import sys
import argparse
import traceback

from xml.etree import ElementTree as ET

from pyvcloud import Http
from pyvcloud.vcloudair import VCA
from pyvcloud.schema.vcd.v1_5.schemas.vcloud.networkType import *
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
import urllib3
import requests

from vimconn_vmware import vimconnector
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from prettytable import PrettyTable
from xml.etree import ElementTree as XmlElementTree
from prettytable import PrettyTable

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

__author__ = "Mustafa Bayramov"
__date__ = "$16-Sep-2016 11:09:29$"


def delete_network_action(vca=None, network_uuid=None):
    """
    Method leverages vCloud director and query network based on network uuid

    Args:
        vca - is active VCA connection.
        network_uuid - is a network uuid

        Returns:
            The return XML respond
    """

    if vca is None or network_uuid is None:
        return None

    url_list = [vca.host, '/api/admin/network/', network_uuid]
    vm_list_rest_call = ''.join(url_list)

    if not (not vca.vcloud_session or not vca.vcloud_session.organization):
        response = Http.get(url=vm_list_rest_call,
                            headers=vca.vcloud_session.get_vcloud_headers(),
                            verify=vca.verify,
                            logger=vca.logger)
        if response.status_code == requests.codes.ok:
            print response.content
            return response.content

    return None


def print_vapp(vapp_dict=None):
    """ Method takes vapp_dict and print in tabular format

    Args:
        vapp_dict: container vapp object.

        Returns:
            The return nothing
    """

    # following key available to print

    # {'status': 'POWERED_OFF', 'storageProfileName': '*', 'hardwareVersion': '7', 'vmToolsVersion': '0',
    #  'memoryMB': '384',
    #  'href': 'https://172.16.254.206/api/vAppTemplate/vm-129e22e8-08dc-4cb6-8358-25f635e65d3b',
    #  'isBusy': 'false', 'isDeployed': 'false', 'isInMaintenanceMode': 'false', 'isVAppTemplate': 'true',
    #  'networkName': 'nat', 'isDeleted': 'false', 'catalogName': 'Cirros',
    #  'containerName': 'Cirros Template', #  'container': 'https://172.16.254.206/api/vAppTemplate/vappTemplate-b966453d-c361-4505-9e38-ccef45815e5d',
    #  'name': 'Cirros', 'pvdcHighestSupportedHardwareVersion': '11', 'isPublished': 'false',
    #  'numberOfCpus': '1', 'vdc': 'https://172.16.254.206/api/vdc/a5056f85-418c-4bfd-8041-adb0f48be9d9',
    #  'guestOs': 'Other (32-bit)', 'isVdcEnabled': 'true'}

    if vapp_dict is None:
        return

    vm_table = PrettyTable(['vapp uuid',
                            'vapp name',
                            'vdc uuid',
                            'network name',
                            'category name',
                            'storageProfileName',
                            'vcpu', 'memory', 'hw ver'])

    for k in vapp_dict:
        entry = []
        entry.append(k)
        entry.append(vapp_dict[k]['containerName'])
        entry.append(vapp_dict[k]['vdc'].split('/')[-1:][0])
        entry.append(vapp_dict[k]['networkName'])
        entry.append(vapp_dict[k]['catalogName'])
        entry.append(vapp_dict[k]['storageProfileName'])
        entry.append(vapp_dict[k]['numberOfCpus'])
        entry.append(vapp_dict[k]['memoryMB'])
        entry.append(vapp_dict[k]['pvdcHighestSupportedHardwareVersion'])

        vm_table.add_row(entry)

    print vm_table


def print_org(org_dict=None):
    """ Method takes vapp_dict and print in tabular format

    Args:
        org_dict:  dictionary of organization where key is org uuid.

        Returns:
            The return nothing
    """

    if org_dict is None:
        return

    org_table = PrettyTable(['org uuid', 'name'])
    for k in org_dict:
        entry = [k, org_dict[k]]
        org_table.add_row(entry)

    print org_table


def print_vm_list(vm_dict=None):
    """ Method takes vapp_dict and print in tabular format

    Args:
        org_dict:  dictionary of organization where key is org uuid.

        Returns:
            The return nothing
    """
    if vm_dict is None:
        return

    vm_table = PrettyTable(
        ['vm uuid', 'vm name', 'vapp uuid', 'vdc uuid', 'network name', 'is deployed', 'vcpu', 'memory', 'status'])

    try:
        for k in vm_dict:
            entry = []
            entry.append(k)
            entry.append(vm_dict[k]['name'])
            entry.append(vm_dict[k]['container'].split('/')[-1:][0][5:])
            entry.append(vm_dict[k]['vdc'].split('/')[-1:][0])
            entry.append(vm_dict[k]['networkName'])
            entry.append(vm_dict[k]['isDeployed'])
            entry.append(vm_dict[k]['numberOfCpus'])
            entry.append(vm_dict[k]['memoryMB'])
            entry.append(vm_dict[k]['status'])
            vm_table.add_row(entry)
        print vm_table
    except KeyError:
        logger.error("wrong key {}".format(KeyError.message))
        pass


def print_org_details(org_dict=None):
    """ Method takes vapp_dict and print in tabular format

    Args:
        org_dict:  dictionary of organization where key is org uuid.

        Returns:
            The return nothing
    """
    if org_dict is None:
        return
    try:
        network_dict = {}
        catalogs_dict = {}
        vdcs_dict = {}

        if org_dict.has_key('networks'):
            network_dict = org_dict['networks']

        if org_dict.has_key('vdcs'):
            vdcs_dict = org_dict['vdcs']

        if org_dict.has_key('catalogs'):
            catalogs_dict = org_dict['catalogs']

        vdc_table = PrettyTable(['vdc uuid', 'vdc name'])
        for k in vdcs_dict:
            entry = [k, vdcs_dict[k]]
            vdc_table.add_row(entry)

        network_table = PrettyTable(['network uuid', 'network name'])
        for k in network_dict:
            entry = [k, network_dict[k]]
            network_table.add_row(entry)

        catalog_table = PrettyTable(['catalog uuid', 'catalog name'])
        for k in catalogs_dict:
            entry = [k, catalogs_dict[k]]
            catalog_table.add_row(entry)

        print vdc_table
        print network_table
        print catalog_table

    except KeyError:
        logger.error("wrong key {}".format(KeyError.message))
        logger.logger.debug(traceback.format_exc())


def delete_actions(vim=None, action=None, namespace=None):
    if action == 'network' or namespace.action == 'network':
        logger.debug("Requesting delete for network {}".format(namespace.network_name))
        network_uuid = namespace.network_name
        # if request name based we need find UUID
        # TODO optimize it or move to external function
        if not namespace.uuid:
            org_dict = vim.get_org_list()
            for org in org_dict:
                org_net = vim.get_org(org)['networks']
                for network in org_net:
                    if org_net[network] == namespace.network_name:
                        network_uuid = network

        vim.delete_network_action(network_uuid=network_uuid)


def list_actions(vim=None, action=None, namespace=None):
    if action == 'vms' or namespace.action == 'vms':
        vm_dict = vim.get_vm_list(vdc_name=namespace.vcdvdc)
        print_vm_list(vm_dict=vm_dict)
    elif action == 'vapps' or namespace.action == 'vapps':
        vapp_dict = vim.get_vapp_list(vdc_name=namespace.vcdvdc)
        print_vapp(vapp_dict=vapp_dict)
    elif action == 'networks' or namespace.action == 'networks':
        print "Requesting networks"
        # var = OrgVdcNetworkType.get_status()
    elif action == 'vdc' or namespace.action == 'vdc':
        vm_dict = vim.get_vm_list(vdc_name=namespace.vcdvdc)
        print_vm_list(vm_dict=vm_dict)
    elif action == 'org' or namespace.action == 'org':
        logger.debug("Listing avaliable orgs")
        print_org(org_dict=vim.get_org_list())
    else:
        return None


def view_actions(vim=None, action=None, namespace=None):
    # view org
    if action == 'org' or namespace.action == 'org':
        org_id = None
        orgs = vim.get_org_list()
        if namespace.uuid:
            if namespace.org_name in orgs:
                org_id = namespace.org_name
        else:
            # we need find UUID based on name provided
            for org in orgs:
                if orgs[org] == namespace.org_name:
                    org_id = org
                    break

        logger.debug("Requesting view for orgs {}".format(org_id))
        print_org_details(vim.get_org(org_uuid=org_id))

    # view vapp action
    if action == 'vapp' or namespace.action == 'vapp':
        if namespace.vapp_name is not None and namespace.uuid == False:
            logger.debug("Requesting vapp {} for vdc {}".format(namespace.vapp_name, namespace.vcdvdc))

            vapp_dict = {}
            # if request based on just name we need get UUID
            if not namespace.uuid:
                vappid = vim.get_vappid(vdc=namespace.vcdvdc, vapp_name=namespace.vapp_name)

            vapp_dict = vim.get_vapp(vdc_name=namespace.vcdvdc, vapp_name=vappid, isuuid=True)
            print_vapp(vapp_dict=vapp_dict)

    # view network
    if action == 'network' or namespace.action == 'network':
        logger.debug("Requesting view for network {}".format(namespace.network_name))
        network_uuid = namespace.network_name
        # if request name based we need find UUID
        # TODO optimize it or move to external function
        if not namespace.uuid:
            org_dict = vim.get_org_list()
            for org in org_dict:
                org_net = vim.get_org(org)['networks']
                for network in org_net:
                    if org_net[network] == namespace.network_name:
                        network_uuid = network

            print vim.get_vcd_network(network_uuid=network_uuid)


def create_actions(vim=None, action=None, namespace=None):
    """Method gets provider vdc view from vcloud director

        Args:
            vim - is Cloud director vim connector
            action - action for create ( network / vdc etc)

        Returns:
            The return xml content of respond or None
    """
    if action == 'network' or namespace.action == 'network':
        logger.debug("Creating a network in vcloud director".format(namespace.network_name))
        network_uuid = vim.create_network(namespace.network_name)
        if network_uuid is not None:
            print ("Crated new network {} and uuid: {}".format(namespace.network_name, network_uuid))
        else:
            print ("Failed create a new network {}".format(namespace.network_name))
    elif action == 'vdc' or namespace.action == 'vdc':
        logger.debug("Creating a new vdc in vcloud director.".format(namespace.vdc_name))
        vdc_uuid = vim.create_vdc(namespace.vdc_name)
        if vdc_uuid is not None:
            print ("Crated new vdc {} and uuid: {}".format(namespace.vdc_name, vdc_uuid))
        else:
            print ("Failed create a new vdc {}".format(namespace.vdc_name))
    else:
        return None


def vmwarecli(command=None, action=None, namespace=None):
    print namespace

    urllib3.disable_warnings()
    vim = vimconnector('0cd19677-7517-11e6-aa08-000c29db3077',
                       'test',
                       'a5056f85-418c-4bfd-8041-adb0f48be9d9',
                       namespace.vcdvdc,
                       'https://172.16.254.206',
                       'https://172.16.254.206',
                       'admin',
                       'qwerty123',
                       "DEBUG", config={'admin_username': 'Administrator', 'admin_password': 'qwerty123'})

    vim.vca = vim.connect()
    #
    #     "{'status': 'ACTIVE'}
    # 2016-09-26 13:06:33,989 - mano.vim.vmware - DEBUG - Adding  4d2e9ec6-e3d8-4014-a1ab-8b622524bd9c to a list vcd id a5056f85-418c-4bfd-8041-adb0f48be9d9 network tefexternal
    # Dict contains {'status': 'ACTIVE'}
    # 2016-09-26 13:06:33,989 - mano.vim.vmware - DEBUG - Adding  93729eaa-4159-4d18-ac28-b000f91bd331 to a list vcd id a5056f85-418c-4bfd-8041-adb0f48be9d9 network default
    # Dict contains {'status': 'ACTIVE'}

    vim.get_network_list(filter_dict={'status': 'ACTIVE', 'type': 'bridge'})
    # vim.get_network_list(filter_dict={'status' : 'ACTIVE'})

    #    print vim.get_vminstance('7e06889a-50c4-4b08-8877-c1ef001eb030')
    #   vim.get_network_name_by_id()

    #  exit()
    # get_network_action(vca=vca, network_uuid="123")

    # list
    if command == 'list' or namespace.command == 'list':
        logger.debug("Client requested list action")
        # route request to list actions
        list_actions(vim=vim, action=action, namespace=namespace)

    # view action
    if command == 'view' or namespace.command == 'view':
        logger.debug("Client requested view action")
        view_actions(vim=vim, action=action, namespace=namespace)

    # delete action
    if command == 'delete' or namespace.command == 'delete':
        logger.debug("Client requested delete action")
        delete_actions(vim=vim, action=action, namespace=namespace)

    # create action
    if command == 'create' or namespace.command == 'create':
        logger.debug("Client requested create action")
        create_actions(vim=vim, action=action, namespace=namespace)


# def get_vappid(vdc, vapp_name):
#     refs = filter(lambda ref: ref.name == vapp_name and ref.type_ == 'application/vnd.vmware.vcloud.vApp+xml',vdc.ResourceEntities.ResourceEntity)
#     if len(refs) == 1:
#         return refs[0].href.split("vapp")[1][1:]
#     return None

if __name__ == '__main__':
    defaults = {'vcdvdc': 'default',
                'vcduser': 'admin',
                'vcdpassword': 'admin',
                'vcdhost': 'https://localhost',
                'vcdorg': 'default',
                'debug': 'INFO'}

    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--vcduser', help='vcloud director username', type=str)
    parser.add_argument('-p', '--vcdpassword', help='vcloud director password', type=str)
    parser.add_argument('-c', '--vcdhost', help='vcloud director host', type=str)
    parser.add_argument('-o', '--vcdorg', help='vcloud director org', type=str)
    parser.add_argument('-v', '--vcdvdc', help='vcloud director vdc', type=str)
    parser.add_argument('-d', '--debug', help='debug level', type=int)

    parser_subparsers = parser.add_subparsers(help='commands', dest='command')
    sub = parser_subparsers.add_parser('list', help='List objects (VMs, vApps, networks)')
    sub_subparsers = sub.add_subparsers(dest='action')
    view_vms = sub_subparsers.add_parser('vms', help='list - all vm deployed in vCloud director')
    view_vapps = sub_subparsers.add_parser('vapps', help='list - all vapps deployed in vCloud director')
    view_network = sub_subparsers.add_parser('networks', help='list - all networks deployed')
    view_vdc = sub_subparsers.add_parser('vdc', help='list - list all vdc for organization accessible to you')
    view_vdc = sub_subparsers.add_parser('org', help='list - list of organizations accessible to you.')

    create_sub = parser_subparsers.add_parser('create')
    create_sub_subparsers = create_sub.add_subparsers(dest='action')
    create_vms = create_sub_subparsers.add_parser('vms')
    create_vapp = create_sub_subparsers.add_parser('vapp')
    create_vapp.add_argument('uuid')

    # add network
    create_network = create_sub_subparsers.add_parser('network')
    create_network.add_argument('network_name', action='store', help='create a network for a vdc')

    # add VDC
    create_vdc = create_sub_subparsers.add_parser('vdc')
    create_vdc.add_argument('vdc_name', action='store', help='create a new VDC for org')

    delete_sub = parser_subparsers.add_parser('delete')
    del_sub_subparsers = delete_sub.add_subparsers(dest='action')
    del_vms = del_sub_subparsers.add_parser('vms')
    del_vapp = del_sub_subparsers.add_parser('vapp')
    del_vapp.add_argument('uuid', help='view vapp based on UUID')

    # delete network
    del_network = del_sub_subparsers.add_parser('network')
    del_network.add_argument('network_name', action='store',
                             help='- delete network for vcloud director by provided name')
    del_network.add_argument('-u', '--uuid', default=False, action='store_true',
                             help='delete network for vcloud director by provided uuid')

    # delete vdc
    del_vdc = del_sub_subparsers.add_parser('vdc')

    view_sub = parser_subparsers.add_parser('view')
    view_sub_subparsers = view_sub.add_subparsers(dest='action')

    view_vms_parser = view_sub_subparsers.add_parser('vms')
    view_vms_parser.add_argument('uuid', default=False, action='store_true',
                                 help='- View VM for specific uuid in vcloud director')
    view_vms_parser.add_argument('name', default=False, action='store_true',
                                 help='- View VM for specific vapp name in vcloud director')

    # view vapp
    view_vapp_parser = view_sub_subparsers.add_parser('vapp')
    view_vapp_parser.add_argument('vapp_name', action='store',
                                  help='- view vapp for specific vapp name in vcloud director')
    view_vapp_parser.add_argument('-u', '--uuid', default=False, action='store_true', help='view vapp based on uuid')

    # view network
    view_network = view_sub_subparsers.add_parser('network')
    view_network.add_argument('network_name', action='store',
                              help='- view network for specific network name in vcloud director')
    view_network.add_argument('-u', '--uuid', default=False, action='store_true', help='view network based on uuid')

    # view VDC command and actions
    view_vdc = view_sub_subparsers.add_parser('vdc')
    view_vdc.add_argument('vdc_name', action='store',
                          help='- View VDC based and action based on provided vdc uuid')
    view_vdc.add_argument('-u', '--uuid', default=False, action='store_true', help='view vdc based on uuid')

    # view organization command and actions
    view_org = view_sub_subparsers.add_parser('org')
    view_org.add_argument('org_name', action='store',
                          help='- View VDC based and action based on provided vdc uuid')
    view_org.add_argument('-u', '--uuid', default=False, action='store_true', help='view org based on uuid')

    #
    # view_org.add_argument('uuid', default=False, action='store',
    #                       help='- View Organization and action based on provided uuid.')
    # view_org.add_argument('name', default=False, action='store_true',
    #                       help='- View Organization and action based on provided name')

    namespace = parser.parse_args()
    # put command_line args to mapping
    command_line_args = {k: v for k, v in vars(namespace).items() if v}

    d = defaults.copy()
    d.update(os.environ)
    d.update(command_line_args)

    logger = logging.getLogger('mano.vim.vmware')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(str.upper(d['debug']))
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.setLevel(getattr(logging, str.upper(d['debug'])))
    logger.info(
        "Connecting {} username: {} org: {} vdc: {} ".format(d['vcdhost'], d['vcduser'], d['vcdorg'], d['vcdvdc']))

    logger.debug("command: \"{}\" actio: \"{}\"".format(d['command'], d['action']))
    vmwarecli(namespace=namespace)

