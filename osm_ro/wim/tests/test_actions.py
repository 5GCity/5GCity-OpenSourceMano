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
# pylint: disable=E1101

from __future__ import unicode_literals, print_function

import json
import unittest
from time import time

from mock import MagicMock, patch

from . import fixtures as eg
from ...tests.db_helpers import (
    TestCaseWithDatabasePerTest,
    disable_foreign_keys,
    uuid,
)
from ..persistence import WimPersistence, preprocess_record
from ..wan_link_actions import WanLinkCreate, WanLinkDelete
from ..wimconn import WimConnectorError


class TestActionsWithDb(TestCaseWithDatabasePerTest):
    def setUp(self):
        super(TestActionsWithDb, self).setUp()
        self.persist = WimPersistence(self.db)
        self.connector = MagicMock()
        self.ovim = MagicMock()


class TestCreate(TestActionsWithDb):
    @disable_foreign_keys
    def test_process__instance_nets_on_build(self):
        # Given we want 1 WAN link between 2 datacenters
        # and the local network in each datacenter is still being built
        wan_link = eg.instance_wim_nets()
        instance_nets = eg.instance_nets(num_datacenters=2, num_links=1)
        for net in instance_nets:
            net['status'] = 'BUILD'
        self.populate([{'instance_nets': instance_nets,
                        'instance_wim_nets': wan_link}])

        # When we try to process a CREATE action that refers to the same
        # instance_scenario_id and sce_net_id
        now = time()
        action = WanLinkCreate(eg.wim_actions('CREATE')[0])
        action.instance_scenario_id = instance_nets[0]['instance_scenario_id']
        action.sce_net_id = instance_nets[0]['sce_net_id']
        # -- ensure it is in the database for updates --> #
        action_record = action.as_record()
        action_record['extra'] = json.dumps(action_record['extra'])
        self.populate([{'vim_wim_actions': action_record}])
        # <-- #
        action.process(self.connector, self.persist, self.ovim)

        # Then the action should be defered
        assert action.is_scheduled
        self.assertEqual(action.extra['attempts'], 1)
        self.assertGreater(action.extra['last_attempted_at'], now)

    @disable_foreign_keys
    def test_process__instance_nets_on_error(self):
        # Given we want 1 WAN link between 2 datacenters
        # and at least one local network is in a not good state (error, or
        # being deleted)
        instance_nets = eg.instance_nets(num_datacenters=2, num_links=1)
        instance_nets[1]['status'] = 'SCHEDULED_DELETION'
        wan_link = eg.instance_wim_nets()
        self.populate([{'instance_nets': instance_nets,
                        'instance_wim_nets': wan_link}])

        # When we try to process a CREATE action that refers to the same
        # instance_scenario_id and sce_net_id
        action = WanLinkCreate(eg.wim_actions('CREATE')[0])
        action.instance_scenario_id = instance_nets[0]['instance_scenario_id']
        action.sce_net_id = instance_nets[0]['sce_net_id']
        # -- ensure it is in the database for updates --> #
        action_record = action.as_record()
        action_record['extra'] = json.dumps(action_record['extra'])
        self.populate([{'vim_wim_actions': action_record}])
        # <-- #
        action.process(self.connector, self.persist, self.ovim)

        # Then the action should fail
        assert action.is_failed
        self.assertIn('issue with the local networks', action.error_msg)
        self.assertIn('SCHEDULED_DELETION', action.error_msg)

    def prepare_create__rules(self):
        db_state = eg.consistent_set(num_wims=1, num_tenants=1,
                                     num_datacenters=2,
                                     external_ports_config=True)

        instance_nets = eg.instance_nets(num_datacenters=2, num_links=1,
                                         status='ACTIVE')
        for i, net in enumerate(instance_nets):
            net['vim_info'] = {}
            net['vim_info']['provider:physical_network'] = 'provider'
            net['vim_info']['encapsulation_type'] = 'vlan'
            net['vim_info']['encapsulation_id'] = i
            net['sdn_net_id'] = uuid('sdn-net%d' % i)

        instance_action = eg.instance_action(action_id='ACTION-000')

        db_state += [
            {'instance_wim_nets': eg.instance_wim_nets()},
            {'instance_nets': [preprocess_record(r) for r in instance_nets]},
            {'instance_actions': instance_action}]

        action = WanLinkCreate(
            eg.wim_actions('CREATE', action_id='ACTION-000')[0])
        # --> ensure it is in the database for updates --> #
        action_record = action.as_record()
        action_record['extra'] = json.dumps(action_record['extra'])
        db_state += [{'vim_wim_actions': action_record}]

        return db_state, action

    @disable_foreign_keys
    def test_process__rules(self):
        # Given we want 1 WAN link between 2 datacenters
        # and the local network in each datacenter is already created
        db_state, action = self.prepare_create__rules()
        self.populate(db_state)

        instance_action = self.persist.get_by_uuid(
            'instance_actions', action.instance_action_id)
        number_done = instance_action['number_done']
        number_failed = instance_action['number_failed']

        # If the connector works fine
        with patch.object(self.connector, 'create_connectivity_service',
                          lambda *_, **__: (uuid('random-id'), None)):
            # When we try to process a CREATE action that refers to the same
            # instance_scenario_id and sce_net_id
            action.process(self.connector, self.persist, self.ovim)

        # Then the action should be succeeded
        db_action = self.persist.query_one('vim_wim_actions', WHERE={
            'instance_action_id': action.instance_action_id,
            'task_index': action.task_index})
        self.assertEqual(db_action['status'], 'DONE')

        instance_action = self.persist.get_by_uuid(
            'instance_actions', action.instance_action_id)
        self.assertEqual(instance_action['number_done'], number_done + 1)
        self.assertEqual(instance_action['number_failed'], number_failed)

    @disable_foreign_keys
    def test_process__rules_fail(self):
        # Given we want 1 WAN link between 2 datacenters
        # and the local network in each datacenter is already created
        db_state, action = self.prepare_create__rules()
        self.populate(db_state)

        instance_action = self.persist.get_by_uuid(
            'instance_actions', action.instance_action_id)
        number_done = instance_action['number_done']
        number_failed = instance_action['number_failed']

        # If the connector raises an error
        with patch.object(self.connector, 'create_connectivity_service',
                          MagicMock(side_effect=WimConnectorError('foobar'))):
            # When we try to process a CREATE action that refers to the same
            # instance_scenario_id and sce_net_id
            action.process(self.connector, self.persist, self.ovim)

        # Then the action should be fail
        db_action = self.persist.query_one('vim_wim_actions', WHERE={
            'instance_action_id': action.instance_action_id,
            'task_index': action.task_index})
        self.assertEqual(db_action['status'], 'FAILED')

        instance_action = self.persist.get_by_uuid(
            'instance_actions', action.instance_action_id)
        self.assertEqual(instance_action['number_done'], number_done)
        self.assertEqual(instance_action['number_failed'], number_failed + 1)

    def prepare_create__sdn(self):
        db_state = eg.consistent_set(num_wims=1, num_tenants=1,
                                     num_datacenters=2,
                                     external_ports_config=False)

        # Make sure all port_mappings are predictable
        switch = 'AA:AA:AA:AA:AA:AA:AA:AA'
        port = 1
        port_mappings = next(r['wim_port_mappings']
                             for r in db_state if 'wim_port_mappings' in r)
        for mapping in port_mappings:
            mapping['pop_switch_dpid'] = switch
            mapping['pop_switch_port'] = port

        instance_action = eg.instance_action(action_id='ACTION-000')
        instance_nets = eg.instance_nets(num_datacenters=2, num_links=1,
                                         status='ACTIVE')
        for i, net in enumerate(instance_nets):
            net['sdn_net_id'] = uuid('sdn-net%d' % i)

        db_state += [{'instance_nets': instance_nets},
                     {'instance_wim_nets': eg.instance_wim_nets()},
                     {'instance_actions': instance_action}]

        action = WanLinkCreate(
            eg.wim_actions('CREATE', action_id='ACTION-000')[0])
        # --> ensure it is in the database for updates --> #
        action_record = action.as_record()
        action_record['extra'] = json.dumps(action_record['extra'])
        db_state += [{'vim_wim_actions': action_record}]

        ovim_patch = patch.object(
            self.ovim, 'get_ports', MagicMock(return_value=[{
                'switch_dpid': switch,
                'switch_port': port,
            }]))

        return db_state, action, ovim_patch

    @disable_foreign_keys
    def test_process__sdn(self):
        # Given we want 1 WAN link between 2 datacenters
        # and the local network in each datacenter is already created
        db_state, action, ovim_patch = self.prepare_create__sdn()
        self.populate(db_state)

        instance_action = self.persist.get_by_uuid(
            'instance_actions', action.instance_action_id)
        number_done = instance_action['number_done']
        number_failed = instance_action['number_failed']

        connector_patch = patch.object(
            self.connector, 'create_connectivity_service',
            lambda *_, **__: (uuid('random-id'), None))

        # If the connector works fine
        with connector_patch, ovim_patch:
            # When we try to process a CREATE action that refers to the same
            # instance_scenario_id and sce_net_id
            action.process(self.connector, self.persist, self.ovim)

        # Then the action should be succeeded
        db_action = self.persist.query_one('vim_wim_actions', WHERE={
            'instance_action_id': action.instance_action_id,
            'task_index': action.task_index})
        self.assertEqual(db_action['status'], 'DONE')

        instance_action = self.persist.get_by_uuid(
            'instance_actions', action.instance_action_id)
        self.assertEqual(instance_action['number_done'], number_done + 1)
        self.assertEqual(instance_action['number_failed'], number_failed)

    @disable_foreign_keys
    def test_process__sdn_fail(self):
        # Given we want 1 WAN link between 2 datacenters
        # and the local network in each datacenter is already created
        db_state, action, ovim_patch = self.prepare_create__sdn()
        self.populate(db_state)

        instance_action = self.persist.get_by_uuid(
            'instance_actions', action.instance_action_id)
        number_done = instance_action['number_done']
        number_failed = instance_action['number_failed']

        connector_patch = patch.object(
            self.connector, 'create_connectivity_service',
            MagicMock(side_effect=WimConnectorError('foobar')))

        # If the connector throws an error
        with connector_patch, ovim_patch:
            # When we try to process a CREATE action that refers to the same
            # instance_scenario_id and sce_net_id
            action.process(self.connector, self.persist, self.ovim)

        # Then the action should be fail
        db_action = self.persist.query_one('vim_wim_actions', WHERE={
            'instance_action_id': action.instance_action_id,
            'task_index': action.task_index})
        self.assertEqual(db_action['status'], 'FAILED')

        instance_action = self.persist.get_by_uuid(
            'instance_actions', action.instance_action_id)
        self.assertEqual(instance_action['number_done'], number_done)
        self.assertEqual(instance_action['number_failed'], number_failed + 1)


class TestDelete(TestActionsWithDb):
    @disable_foreign_keys
    def test_process__no_internal_id(self):
        # Given no WAN link was created yet,
        # when we try to process a DELETE action, with no wim_internal_id
        action = WanLinkDelete(eg.wim_actions('DELETE')[0])
        action.wim_internal_id = None
        # -- ensure it is in the database for updates --> #
        action_record = action.as_record()
        action_record['extra'] = json.dumps(action_record['extra'])
        self.populate([{'vim_wim_actions': action_record,
                        'instance_wim_nets': eg.instance_wim_nets()}])
        # <-- #
        action.process(self.connector, self.persist, self.ovim)

        # Then the action should succeed
        assert action.is_done

    def prepare_delete(self):
        db_state = eg.consistent_set(num_wims=1, num_tenants=1,
                                     num_datacenters=2,
                                     external_ports_config=True)

        instance_nets = eg.instance_nets(num_datacenters=2, num_links=1,
                                         status='ACTIVE')
        for i, net in enumerate(instance_nets):
            net['vim_info'] = {}
            net['vim_info']['provider:physical_network'] = 'provider'
            net['vim_info']['encapsulation_type'] = 'vlan'
            net['vim_info']['encapsulation_id'] = i
            net['sdn_net_id'] = uuid('sdn-net%d' % i)

        instance_action = eg.instance_action(action_id='ACTION-000')

        db_state += [
            {'instance_wim_nets': eg.instance_wim_nets()},
            {'instance_nets': [preprocess_record(r) for r in instance_nets]},
            {'instance_actions': instance_action}]

        action = WanLinkDelete(
            eg.wim_actions('DELETE', action_id='ACTION-000')[0])
        # --> ensure it is in the database for updates --> #
        action_record = action.as_record()
        action_record['extra'] = json.dumps(action_record['extra'])
        db_state += [{'vim_wim_actions': action_record}]

        return db_state, action

    @disable_foreign_keys
    def test_process(self):
        # Given we want to delete 1 WAN link between 2 datacenters
        db_state, action = self.prepare_delete()
        self.populate(db_state)

        instance_action = self.persist.get_by_uuid(
            'instance_actions', action.instance_action_id)
        number_done = instance_action['number_done']
        number_failed = instance_action['number_failed']

        connector_patch = patch.object(
            self.connector, 'delete_connectivity_service')

        # If the connector works fine
        with connector_patch:
            # When we try to process a DELETE action that refers to the same
            # instance_scenario_id and sce_net_id
            action.process(self.connector, self.persist, self.ovim)

        # Then the action should be succeeded
        db_action = self.persist.query_one('vim_wim_actions', WHERE={
            'instance_action_id': action.instance_action_id,
            'task_index': action.task_index})
        self.assertEqual(db_action['status'], 'DONE')

        instance_action = self.persist.get_by_uuid(
            'instance_actions', action.instance_action_id)
        self.assertEqual(instance_action['number_done'], number_done + 1)
        self.assertEqual(instance_action['number_failed'], number_failed)

    @disable_foreign_keys
    def test_process__wan_link_error(self):
        # Given we have a delete action that targets a wan link with an error
        db_state, action = self.prepare_delete()
        wan_link = [tables for tables in db_state
                    if tables.get('instance_wim_nets')][0]['instance_wim_nets']
        from pprint import pprint
        pprint(wan_link)
        wan_link[0]['status'] = 'ERROR'
        self.populate(db_state)

        # When we try to process it
        action.process(self.connector, self.persist, self.ovim)

        # Then it should fail
        assert action.is_failed

    def create_action(self):
        action = WanLinkCreate(
            eg.wim_actions('CREATE', action_id='ACTION-000')[0])
        # --> ensure it is in the database for updates --> #
        action_record = action.as_record()
        action_record['extra'] = json.dumps(action_record['extra'])
        self.populate([{'vim_wim_actions': action_record}])

        return action

    @disable_foreign_keys
    def test_create_and_delete(self):
        # Given a CREATE action was well succeeded
        db_state, delete_action = self.prepare_delete()
        self.populate(db_state)

        delete_action.save(self.persist, task_index=1)
        create_action = self.create_action()

        connector_patch = patch.multiple(
            self.connector,
            delete_connectivity_service=MagicMock(),
            create_connectivity_service=(
                lambda *_, **__: (uuid('random-id'), None)))

        with connector_patch:  # , ovim_patch:
            create_action.process(self.connector, self.persist, self.ovim)

        # When we try to process a CREATE action that refers to the same
        # instance_scenario_id and sce_net_id
        with connector_patch:
            delete_action.process(self.connector, self.persist, self.ovim)

        # Then the DELETE action should be successful
        db_action = self.persist.query_one('vim_wim_actions', WHERE={
            'instance_action_id': delete_action.instance_action_id,
            'task_index': delete_action.task_index})
        self.assertEqual(db_action['status'], 'DONE')


if __name__ == '__main__':
    unittest.main()
