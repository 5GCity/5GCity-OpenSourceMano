# -*- coding: utf-8 -*-
##
# Copyright 2018 University of Bristol - High Performance Networks Research
# Group
# All Rights Reserved.
#
# Contributors: Anderson Bravalheri, Dimitrios Gkounis, Abubakar Siddique
# Muqaddas, Navdeep Uniyal, Reza Nejabati and Dimitra Simeonidou
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
# contact with: <highperformance-networks@bristol.ac.uk>
#
# Neither the name of the University of Bristol nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# This work has been performed in the context of DCMS UK 5G Testbeds
# & Trials Programme and in the framework of the Metro-Haul project -
# funded by the European Commission under Grant number 761727 through the
# Horizon 2020 and 5G-PPP programmes.
##
# pylint: disable=W0621

from __future__ import unicode_literals

import json
from time import time

from six.moves import range

from ...tests.db_helpers import uuid, sha1

NUM_WIMS = 3
NUM_TENANTS = 2
NUM_DATACENTERS = 2


# In the following functions, the identifiers should be simple integers


def wim(identifier=0):
    return {'name': 'wim%d' % identifier,
            'uuid': uuid('wim%d' % identifier),
            'wim_url': 'localhost',
            'type': 'tapi'}


def tenant(identifier=0):
    return {'name': 'tenant%d' % identifier,
            'uuid': uuid('tenant%d' % identifier)}


def wim_account(wim, tenant):
    return {'name': 'wim-account%d%d' % (tenant, wim),
            'uuid': uuid('wim-account%d%d' % (tenant, wim)),
            'user': 'user%d%d' % (tenant, wim),
            'password': 'password%d%d' % (tenant, wim),
            'wim_id': uuid('wim%d' % wim),
            'created': 'true'}


def wim_tenant_association(wim, tenant):
    return {'nfvo_tenant_id': uuid('tenant%d' % tenant),
            'wim_id': uuid('wim%d' % wim),
            'wim_account_id': uuid('wim-account%d%d' % (tenant, wim))}


def wim_set(identifier=0, tenant=0):
    """Records necessary to create a WIM and connect it to a tenant"""
    return [
        {'wims': [wim(identifier)]},
        {'wim_accounts': [wim_account(identifier, tenant)]},
        {'wim_nfvo_tenants': [wim_tenant_association(identifier, tenant)]}
    ]


def datacenter(identifier):
    return {'uuid': uuid('dc%d' % identifier),
            'name': 'dc%d' % identifier,
            'type': 'openvim',
            'vim_url': 'localhost'}


def datacenter_account(datacenter, tenant):
    return {'name': 'dc-account%d%d' % (tenant, datacenter),
            'uuid': uuid('dc-account%d%d' % (tenant, datacenter)),
            'datacenter_id': uuid('dc%d' % datacenter),
            'created': 'true'}


def datacenter_tenant_association(datacenter, tenant):
    return {'nfvo_tenant_id': uuid('tenant%d' % tenant),
            'datacenter_id':  uuid('dc%d' % datacenter),
            'datacenter_tenant_id':
                uuid('dc-account%d%d' % (tenant, datacenter))}


def datacenter_set(identifier, tenant):
    """Records necessary to create a datacenter and connect it to a tenant"""
    return [
        {'datacenters': [datacenter(identifier)]},
        {'datacenter_tenants': [datacenter_account(identifier, tenant)]},
        {'tenants_datacenters': [
            datacenter_tenant_association(identifier, tenant)
        ]}
    ]


def wim_port_mapping(wim, datacenter,
                     pop_dpid='AA:AA:AA:AA:AA:AA:AA:AA', pop_port=0,
                     wan_dpid='BB:BB:BB:BB:BB:BB:BB:BB', wan_port=0):
    mapping_info = {'mapping_type': 'dpid-port',
                    'wan_switch_dpid': wan_dpid,
                    'wan_switch_port': wan_port + datacenter + 1}
    id_ = 'dpid-port|' + sha1(json.dumps(mapping_info, sort_keys=True))

    return {'wim_id': uuid('wim%d' % wim),
            'datacenter_id': uuid('dc%d' % datacenter),
            'pop_switch_dpid': pop_dpid,
            'pop_switch_port': pop_port + wim + 1,
            # ^  Datacenter router have one port managed by each WIM
            'wan_service_endpoint_id': id_,
            # ^  WIM managed router have one port connected to each DC
            'wan_service_mapping_info': json.dumps(mapping_info)}


def processed_port_mapping(wim, datacenter,
                           num_pairs=1,
                           pop_dpid='AA:AA:AA:AA:AA:AA:AA:AA',
                           wan_dpid='BB:BB:BB:BB:BB:BB:BB:BB'):
    """Emulate the response of the Persistence class, where the records in the
    data base are grouped by wim and datacenter
    """
    return {
        'wim_id': uuid('wim%d' % wim),
        'datacenter_id': uuid('dc%d' % datacenter),
        'wan_pop_port_mappings': [
            {'pop_switch_dpid': pop_dpid,
             'pop_switch_port': wim + 1 + i,
             'wan_service_endpoint_id':
                 sha1('dpid-port|%s|%d' % (wan_dpid, datacenter + 1 + i)),
             'wan_service_mapping_info': {
                 'mapping_type': 'dpid-port',
                 'wan_switch_dpid': wan_dpid,
                 'wan_switch_port': datacenter + 1 + i}}
            for i in range(num_pairs)
        ]
    }


def consistent_set(num_wims=NUM_WIMS, num_tenants=NUM_TENANTS,
                   num_datacenters=NUM_DATACENTERS):
    return [
        {'nfvo_tenants': [tenant(i) for i in range(num_tenants)]},
        {'wims': [wim(j) for j in range(num_wims)]},
        {'wim_accounts': [
            wim_account(j, i)
            for i in range(num_tenants)
            for j in range(num_wims)
        ]},
        {'wim_nfvo_tenants': [
            wim_tenant_association(j, i)
            for i in range(num_tenants)
            for j in range(num_wims)
        ]},
        {'datacenters': [
            datacenter(k)
            for k in range(num_datacenters)
        ]},
        {'datacenter_tenants': [
            datacenter_account(k, i)
            for i in range(num_tenants)
            for k in range(num_datacenters)
        ]},
        {'tenants_datacenters': [
            datacenter_tenant_association(k, i)
            for i in range(num_tenants)
            for k in range(num_datacenters)
        ]},
        {'wim_port_mappings': [
            wim_port_mapping(j, k)
            for j in range(num_wims)
            for k in range(num_datacenters)
        ]},
    ]


def instance_nets(num_datacenters=2, num_links=2):
    """Example of multi-site deploy with N datacenters and M WAN links between
    them (e.g M = 2 -> back and forth)
    """
    return [
        {'uuid': uuid('net%d%d' % (k, l)),
         'datacenter_id': uuid('dc%d' % k),
         'datacenter_tenant_id': uuid('dc-account0%d' % k),
         'instance_scenario_id': uuid('nsr0'),
         # ^  instance_scenario_id == NS Record id
         'sce_net_id': uuid('vld%d' % l),
         # ^  scenario net id == VLD id
         'status': 'BUILD',
         'vim_net_id': None,
         'created': True}
        for k in range(num_datacenters)
        for l in range(num_links)
    ]


def wim_actions(action='CREATE', status='SCHEDULED',
                action_id=None, instance=0,
                wim=0, tenant=0, num_links=1):
    """Create a list of actions for the WIM,

    Arguments:
        action: type of action (CREATE) by default
        wim: WIM fixture index to create actions for
        tenant: tenant fixture index to create actions for
        num_links: number of WAN links to be established by each WIM
    """

    action_id = action_id or 'ACTION-{}'.format(time())

    return [
        {
            'action': action,
            'wim_internal_id': uuid('-wim-net%d%d%d' % (wim, instance, link)),
            'wim_account_id': uuid('wim-account%d%d' % (tenant, wim)),
            'instance_action_id': action_id,
            'item': 'instance_wim_nets',
            'item_id': uuid('wim-net%d%d%d' % (wim, instance, link)),
            'status': status,
            'task_index': link,
            'created_at': time(),
            'modified_at': time(),
            'extra': None
        }
        for link in range(num_links)
    ]


def instance_action(tenant=0, instance=0, action_id=None,
                    num_tasks=1, num_done=0, num_failed=0):
    action_id = action_id or 'ACTION-{}'.format(time())

    return {
        'uuid': action_id,
        'tenant_id': uuid('tenant%d' % tenant),
        'instance_id': uuid('nsr%d' % instance),
        'number_tasks': num_tasks,
        'number_done': num_done,
        'number_failed': num_failed,
    }


def instance_wim_nets(instance=0, wim=0, num_links=1,
                      status='SCHEDULED_CREATION'):
    """Example of multi-site deploy with N wims and M WAN links between
    them (e.g M = 2 -> back and forth)
    VIM nets
    """
    return [
        {'uuid': uuid('wim-net%d%d%d' % (wim, instance, l)),
         'wim_id': uuid('wim%d' % wim),
         'wim_account_id': uuid('wim-account%d' % wim),
         'wim_internal_id': uuid('-net%d%d' % (wim, l)),
         'instance_scenario_id': uuid('nsr%d' % instance),
         # ^  instance_scenario_id == NS Record id
         'sce_net_id': uuid('vld%d' % l),
         # ^  scenario net id == VLD id
         'status': status,
         'created': False}
        for l in range(num_links)
    ]


def instance_vm(instance=0, vim_info=None):
    vim_info = {'OS-EXT-SRV-ATTR:hypervisor_hostname': 'host%d' % instance}
    return {
        'uuid': uuid('vm%d' % instance),
        'instance_vnf_id': uuid('vnf%d' % instance),
        'vm_id': uuid('vm%d' % instance),
        'vim_vm_id': uuid('vm%d' % instance),
        'status': 'ACTIVE',
        'vim_info': vim_info,
    }


def instance_interface(instance=0, interface=0, datacenter=0, link=0):
    return {
        'uuid': uuid('interface%d%d' % (instance, interface)),
        'instance_vm_id': uuid('vm%d' % instance),
        'instance_net_id': uuid('net%d%d' % (datacenter, link)),
        'interface_id': uuid('iface%d' % interface),
        'type': 'external',
        'vlan': 3
    }
