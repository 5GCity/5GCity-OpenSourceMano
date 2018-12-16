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

"""This module contains the domain logic, and the implementation of the
required steps to perform VNF management and orchestration in a WAN
environment.

It works as an extension/complement to the main functions contained in the
``nfvo.py`` file and avoids interacting directly with the database, by relying
on the `persistence` module.

No http request handling/direct interaction with the database should be present
in this file.
"""
import json
import logging
from contextlib import contextmanager
from itertools import groupby
from operator import itemgetter
from sys import exc_info
from uuid import uuid4

from six import reraise

from ..utils import remove_none_items
from .actions import Action
from .errors import (
    DbBaseException,
    NoWimConnectedToDatacenters,
    UnexpectedDatabaseError,
    WimAccountNotActive
)
from .wim_thread import WimThread


class WimEngine(object):
    """Logic supporting the establishment of WAN links when NS spans across
    different datacenters.
    """
    def __init__(self, persistence, logger=None, ovim=None):
        self.persist = persistence
        self.logger = logger or logging.getLogger('openmano.wim.engine')
        self.threads = {}
        self.connectors = {}
        self.ovim = ovim

    def create_wim(self, properties):
        """Create a new wim record according to the properties

        Please check the wim schema to have more information about
        ``properties``.

        The ``config`` property might contain a ``wim_port_mapping`` dict,
        In this case, the method ``create_wim_port_mappings`` will be
        automatically invoked.

        Returns:
            str: uuid of the newly created WIM record
        """
        port_mapping = ((properties.get('config', {}) or {})
                        .pop('wim_port_mapping', {}))
        uuid = self.persist.create_wim(properties)

        if port_mapping:
            try:
                self.create_wim_port_mappings(uuid, port_mapping)
            except DbBaseException:
                # Rollback
                self.delete_wim(uuid)
                ex = UnexpectedDatabaseError('Failed to create port mappings'
                                             'Rolling back wim creation')
                self.logger.exception(str(ex))
                reraise(ex.__class__, ex, exc_info()[2])

        return uuid

    def get_wim(self, uuid_or_name, tenant_id=None):
        """Retrieve existing WIM record by name or id.

        If ``tenant_id`` is specified, the query will be
        limited to the WIM associated to the given tenant.
        """
        # Since it is a pure DB operation, we can delegate it directly
        return self.persist.get_wim(uuid_or_name, tenant_id)

    def update_wim(self, uuid_or_name, properties):
        """Edit an existing WIM record.

        ``properties`` is a dictionary with the properties being changed,
        if a property is not present, the old value will be preserved

        Similarly to create_wim, the ``config`` property might contain a
        ``wim_port_mapping`` dict, In this case, port mappings will be
        automatically updated.
        """
        port_mapping = ((properties.get('config', {}) or {})
                        .pop('wim_port_mapping', {}))
        orig_props = self.persist.get_by_name_or_uuid('wims', uuid_or_name)
        uuid = orig_props['uuid']

        response = self.persist.update_wim(uuid, properties)

        if port_mapping:
            try:
                # It is very complex to diff and update individually all the
                # port mappings. Therefore a practical approach is just delete
                # and create it again.
                self.persist.delete_wim_port_mappings(uuid)
                # ^  Calling from persistence avoid reloading twice the thread
                self.create_wim_port_mappings(uuid, port_mapping)
            except DbBaseException:
                # Rollback
                self.update_wim(uuid_or_name, orig_props)
                ex = UnexpectedDatabaseError('Failed to update port mappings'
                                             'Rolling back wim updates\n')
                self.logger.exception(str(ex))
                reraise(ex.__class__, ex, exc_info()[2])

        return response

    def delete_wim(self, uuid_or_name):
        """Kill the corresponding wim threads and erase the WIM record"""
        # Theoretically, we can rely on the database to drop the wim_accounts
        # automatically, since we have configures 'ON CASCADE DELETE'.
        # However, use use `delete_wim_accounts` to kill all the running
        # threads.
        self.delete_wim_accounts(uuid_or_name)
        return self.persist.delete_wim(uuid_or_name)

    def create_wim_account(self, wim, tenant, properties):
        """Create an account that associates a tenant to a WIM.

        As a side effect this function will spawn a new thread

        Arguments:
            wim (str): name or uuid of the WIM related to the account being
                created
            tenant (str): name or uuid of the nfvo tenant to which the account
                will be created
            properties (dict): properties of the account
                (eg. username, password, ...)

        Returns:
            dict: Created record
        """
        uuid = self.persist.create_wim_account(wim, tenant, properties)
        account = self.persist.get_wim_account_by(uuid=uuid)
        # ^  We need to use get_wim_account_by here, since this methods returns
        #    all the associations, and we need the wim to create the thread
        self._spawn_thread(account)
        return account

    def _update_single_wim_account(self, account, properties):
        """Update WIM Account, taking care to reload the corresponding thread

        Arguments:
            account (dict): Current account record
            properties (dict): Properties to be updated

        Returns:
            dict: updated record
        """
        account = self.persist.update_wim_account(account['uuid'], properties)
        self.threads[account['uuid']].reload()
        return account

    def update_wim_accounts(self, wim, tenant, properties):
        """Update all the accounts related to a WIM and a tenant,
        thanking care of reloading threads.

        Arguments:
            wim (str): uuid or name of a WIM record
            tenant (str): uuid or name of a NFVO tenant record
            properties (dict): attributes with values to be updated

        Returns
            list: Records that were updated
        """
        accounts = self.persist.get_wim_accounts_by(wim, tenant)
        return [self._update_single_wim_account(account, properties)
                for account in accounts]

    def _delete_single_wim_account(self, account):
        """Delete WIM Account, taking care to remove the corresponding thread
        and delete the internal WIM account, if it was automatically generated.

        Arguments:
            account (dict): Current account record
            properties (dict): Properties to be updated

        Returns:
            dict: current record (same as input)
        """
        self.persist.delete_wim_account(account['uuid'])

        if account['uuid'] not in self.threads:
            raise WimAccountNotActive(
                'Requests send to the WIM Account %s are not currently '
                'being processed.', account['uuid'])
        else:
            self.threads[account['uuid']].exit()
            del self.threads[account['uuid']]

        return account

    def delete_wim_accounts(self, wim, tenant=None, **kwargs):
        """Delete all the accounts related to a WIM (and a tenant),
        thanking care of threads and internal WIM accounts.

        Arguments:
            wim (str): uuid or name of a WIM record
            tenant (str): uuid or name of a NFVO tenant record

        Returns
            list: Records that were deleted
        """
        kwargs.setdefault('error_if_none', False)
        accounts = self.persist.get_wim_accounts_by(wim, tenant, **kwargs)
        return [self._delete_single_wim_account(a) for a in accounts]

    def _reload_wim_threads(self, wim_id):
        for thread in self.threads.values():
            if thread.wim_account['wim_id'] == wim_id:
                thread.reload()

    def create_wim_port_mappings(self, wim, properties, tenant=None):
        """Store information about port mappings from Database"""
        # TODO: Review tenants... WIMs can exist across different tenants,
        #       and the port_mappings are a WIM property, not a wim_account
        #       property, so the concepts are not related
        wim = self.persist.get_by_name_or_uuid('wims', wim)
        result = self.persist.create_wim_port_mappings(wim, properties, tenant)
        self._reload_wim_threads(wim['uuid'])
        return result

    def get_wim_port_mappings(self, wim):
        """Retrive information about port mappings from Database"""
        return self.persist.get_wim_port_mappings(wim)

    def delete_wim_port_mappings(self, wim):
        """Erase the port mapping records associated with the WIM"""
        wim = self.persist.get_by_name_or_uuid('wims', wim)
        message = self.persist.delete_wim_port_mappings(wim['uuid'])
        self._reload_wim_threads(wim['uuid'])
        return message

    def find_common_wims(self, datacenter_ids, tenant):
        """Find WIMs that are common to all datacenters listed"""
        mappings = self.persist.get_wim_port_mappings(
            datacenter=datacenter_ids, tenant=tenant, error_if_none=False)

        wim_id_of = itemgetter('wim_id')
        sorted_mappings = sorted(mappings, key=wim_id_of)  # needed by groupby
        grouped_mappings = groupby(sorted_mappings, key=wim_id_of)
        mapped_datacenters = {
            wim_id: [m['datacenter_id'] for m in mappings]
            for wim_id, mappings in grouped_mappings
        }

        return [
            wim_id
            for wim_id, connected_datacenters in mapped_datacenters.items()
            if set(connected_datacenters) >= set(datacenter_ids)
        ]

    def find_common_wim(self, datacenter_ids, tenant):
        """Find a single WIM that is able to connect all the datacenters
        listed

        Raises:
            NoWimConnectedToDatacenters: if no WIM connected to all datacenters
                at once is found
        """
        suitable_wim_ids = self.find_common_wims(datacenter_ids, tenant)

        if not suitable_wim_ids:
            raise NoWimConnectedToDatacenters(datacenter_ids)

        # TODO: use a criteria to determine which WIM is going to be used,
        #       instead of always using the first one (strategy pattern can be
        #       used here)
        return suitable_wim_ids[0]

    def find_suitable_wim_account(self, datacenter_ids, tenant):
        """Find a WIM account that is able to connect all the datacenters
        listed

        Arguments:
            datacenter_ids (list): List of UUIDs of all the datacenters (vims),
                that need to be connected.
            tenant (str): UUID of the OSM tenant

        Returns:
            str: UUID of the WIM account that is able to connect all the
                 datacenters.
        """
        wim_id = self.find_common_wim(datacenter_ids, tenant)
        return self.persist.get_wim_account_by(wim_id, tenant)['uuid']

    def derive_wan_link(self,
                        wim_usage,
                        instance_scenario_id, sce_net_id,
                        networks, tenant):
        """Create a instance_wim_nets record for the given information"""
        if sce_net_id in wim_usage:
            account_id = wim_usage[sce_net_id]
            account = self.persist.get_wim_account_by(uuid=account_id)
            wim_id = account['wim_id']
        else:
            datacenters = [n['datacenter_id'] for n in networks]
            wim_id = self.find_common_wim(datacenters, tenant)
            account = self.persist.get_wim_account_by(wim_id, tenant)

        return {
            'uuid': str(uuid4()),
            'instance_scenario_id': instance_scenario_id,
            'sce_net_id': sce_net_id,
            'wim_id': wim_id,
            'wim_account_id': account['uuid']
        }

    def derive_wan_links(self, wim_usage, networks, tenant=None):
        """Discover and return what are the wan_links that have to be created
        considering a set of networks (VLDs) required for a scenario instance
        (NSR).

        Arguments:
            wim_usage(dict): Mapping between sce_net_id and wim_id
            networks(list): Dicts containing the information about the networks
                that will be instantiated to materialize a Network Service
                (scenario) instance.
                Corresponding to the ``instance_net`` record.

        Returns:
            list: list of WAN links to be written to the database
        """
        # Group networks by key=(instance_scenario_id, sce_net_id)
        filtered = _filter_multi_vim(networks)
        grouped_networks = _group_networks(filtered)
        datacenters_per_group = _count_datacenters(grouped_networks)
        # For each group count the number of networks. If greater then 1,
        # we have to create a wan link connecting them.
        wan_groups = [key
                      for key, counter in datacenters_per_group
                      if counter > 1]

        return [
            self.derive_wan_link(wim_usage,
                                 key[0], key[1], grouped_networks[key], tenant)
            for key in wan_groups
        ]

    def create_action(self, wan_link):
        """For a single wan_link create the corresponding create action"""
        return {
            'action': 'CREATE',
            'status': 'SCHEDULED',
            'item': 'instance_wim_nets',
            'item_id': wan_link['uuid'],
            'wim_account_id': wan_link['wim_account_id']
        }

    def create_actions(self, wan_links):
        """For an array of wan_links, create all the corresponding actions"""
        return [self.create_action(l) for l in wan_links]

    def delete_action(self, wan_link):
        """For a single wan_link create the corresponding create action"""
        return {
            'action': 'DELETE',
            'status': 'SCHEDULED',
            'item': 'instance_wim_nets',
            'item_id': wan_link['uuid'],
            'wim_account_id': wan_link['wim_account_id'],
            'extra': json.dumps({'wan_link': wan_link})
            # We serialize and cache the wan_link here, because it can be
            # deleted during the delete process
        }

    def delete_actions(self, wan_links=(), instance_scenario_id=None):
        """Given a Instance Scenario, remove all the WAN Links created in the
        past"""
        if instance_scenario_id:
            wan_links = self.persist.get_wan_links(
                instance_scenario_id=instance_scenario_id)
        return [self.delete_action(l) for l in wan_links]

    def incorporate_actions(self, wim_actions, instance_action):
        """Make the instance action consider new WIM actions and make the WIM
        actions aware of the instance action
        """
        current = instance_action.setdefault('number_tasks', 0)
        for i, action in enumerate(wim_actions):
            action['task_index'] = current + i
            action['instance_action_id'] = instance_action['uuid']
        instance_action['number_tasks'] += len(wim_actions)

        return wim_actions, instance_action

    def dispatch(self, tasks):
        """Enqueue a list of tasks for further processing.

        This function is supposed to be called outside from the WIM Thread.
        """
        for task in tasks:
            if task['wim_account_id'] not in self.threads:
                error_msg = str(WimAccountNotActive(
                    'Requests send to the WIM Account %s are not currently '
                    'being processed.', task['wim_account_id']))
                Action(task, self.logger).fail(self.persist, error_msg)
                self.persist.update_wan_link(task['item_id'],
                                             {'status': 'ERROR',
                                              'error_msg': error_msg})
                self.logger.error('Task %s %s %s not dispatched.\n%s',
                                  task['action'], task['item'],
                                  task['instance_account_id'], error_msg)
            else:
                self.threads[task['wim_account_id']].insert_task(task)
                self.logger.debug('Task %s %s %s dispatched',
                                  task['action'], task['item'],
                                  task['instance_action_id'])

    def _spawn_thread(self, wim_account):
        """Spawn a WIM thread

        Arguments:
            wim_account (dict): WIM information (usually persisted)
                The `wim` field is required to be set with a valid WIM record
                inside the `wim_account` dict

        Return:
            threading.Thread: Thread object
        """
        thread = None
        try:
            thread = WimThread(self.persist, wim_account, ovim=self.ovim)
            self.threads[wim_account['uuid']] = thread
            thread.start()
        except:  # noqa
            self.logger.error('Error when spawning WIM thread for %s',
                              wim_account['uuid'], exc_info=True)

        return thread

    def start_threads(self):
        """Start the threads responsible for processing WIM Actions"""
        accounts = self.persist.get_wim_accounts(error_if_none=False)
        self.threads = remove_none_items(
            {a['uuid']: self._spawn_thread(a) for a in accounts})

    def stop_threads(self):
        """Stop the threads responsible for processing WIM Actions"""
        for uuid, thread in self.threads.items():
            thread.exit()
            del self.threads[uuid]

    @contextmanager
    def threads_running(self):
        """Ensure no thread will be left running"""
        # This method is particularly important for testing :)
        try:
            self.start_threads()
            yield
        finally:
            self.stop_threads()


def _filter_multi_vim(networks):
    """Ignore networks without sce_net_id (all VNFs go to the same VIM)"""
    return [n for n in networks if 'sce_net_id' in n and n['sce_net_id']]


def _group_networks(networks):
    """Group networks that correspond to the same instance_scenario_id and
    sce_net_id (NSR and VLD).

    Arguments:
        networks(list): Dicts containing the information about the networks
            that will be instantiated to materialize a Network Service
            (scenario) instance.
    Returns:
        dict: Keys are tuples (instance_scenario_id, sce_net_id) and values
            are lits of networks.
    """
    criteria = itemgetter('instance_scenario_id', 'sce_net_id')

    networks = sorted(networks, key=criteria)
    return {k: list(v) for k, v in groupby(networks, key=criteria)}


def _count_datacenters(grouped_networks):
    """Count the number of datacenters in each group of networks

    Returns:
        list of tuples: the first element is the group key, while the second
            element is the number of datacenters in each group.
    """
    return ((key, len(set(n['datacenter_id'] for n in group)))
            for key, group in grouped_networks.items())
