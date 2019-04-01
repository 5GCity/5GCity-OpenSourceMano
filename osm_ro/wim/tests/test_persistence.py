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

from __future__ import unicode_literals

import unittest
from itertools import chain
from types import StringType

from six.moves import range

from . import fixtures as eg
from ...tests.db_helpers import (
    TestCaseWithDatabasePerTest,
    disable_foreign_keys,
    uuid
)
from ..persistence import (
    WimPersistence,
    hide_confidential_fields,
    serialize_fields,
    unserialize_fields
)


class TestPersistenceUtils(unittest.TestCase):
    def test_hide_confidential_fields(self):
        example = {
            'password': '123456',
            'nested.password': '123456',
            'nested.secret': None,
        }
        result = hide_confidential_fields(example,
                                          fields=('password', 'secret'))
        for field in 'password', 'nested.password':
            assert result[field].startswith('***')
        self.assertIs(result['nested.secret'], None)

    def test_serialize_fields(self):
        example = {
            'config': dict(x=1),
            'nested.info': [1, 2, 3],
            'nested.config': None
        }
        result = serialize_fields(example, fields=('config', 'info'))
        for field in 'config', 'nested.info':
            self.assertIsInstance(result[field], StringType)
        self.assertIs(result['nested.config'], None)

    def test_unserialize_fields(self):
        example = {
            'config': '{"x": 1}',
            'nested.info': '[1,2,3]',
            'nested.config': None,
            'confidential.info': '{"password": "abcdef"}'
        }
        result = unserialize_fields(example, fields=('config', 'info'))
        self.assertEqual(result['config'], dict(x=1))
        self.assertEqual(result['nested.info'], [1, 2, 3])
        self.assertIs(result['nested.config'], None)
        self.assertNotEqual(result['confidential.info']['password'], 'abcdef')
        assert result['confidential.info']['password'].startswith('***')


class TestWimPersistence(TestCaseWithDatabasePerTest):
    def setUp(self):
        super(TestWimPersistence, self).setUp()
        self.persist = WimPersistence(self.db)

    def populate(self, seeds=None):
        super(TestWimPersistence, self).populate(seeds or eg.consistent_set())

    def test_query_offset(self):
        # Given a database contains 4 records
        self.populate([{'wims': [eg.wim(i) for i in range(4)]}])

        # When we query using a limit of 2 and a offset of 1
        results = self.persist.query('wims',
                                     ORDER_BY='name', LIMIT=2, OFFSET=1)
        # Then we should have 2 results, skipping the first record
        names = [r['name'] for r in results]
        self.assertItemsEqual(names, ['wim1', 'wim2'])

    def test_get_wim_account_by_wim_tenant(self):
        # Given a database contains WIM accounts associated to Tenants
        self.populate()

        # when we retrieve the account using wim and tenant
        wim_account = self.persist.get_wim_account_by(
            uuid('wim0'), uuid('tenant0'))

        # then the right record should be returned
        self.assertEqual(wim_account['uuid'], uuid('wim-account00'))
        self.assertEqual(wim_account['name'], 'wim-account00')
        self.assertEqual(wim_account['user'], 'user00')

    def test_get_wim_account_by_wim_tenant__names(self):
        # Given a database contains WIM accounts associated to Tenants
        self.populate()

        # when we retrieve the account using wim and tenant
        wim_account = self.persist.get_wim_account_by(
            'wim0', 'tenant0')

        # then the right record should be returned
        self.assertEqual(wim_account['uuid'], uuid('wim-account00'))
        self.assertEqual(wim_account['name'], 'wim-account00')
        self.assertEqual(wim_account['user'], 'user00')

    def test_get_wim_accounts_by_wim(self):
        # Given a database contains WIM accounts associated to Tenants
        self.populate()

        # when we retrieve the accounts using wim
        wim_accounts = self.persist.get_wim_accounts_by(uuid('wim0'))

        # then the right records should be returned
        self.assertEqual(len(wim_accounts), eg.NUM_TENANTS)
        for account in wim_accounts:
            self.assertEqual(account['wim_id'], uuid('wim0'))

    def test_get_wim_port_mappings(self):
        # Given a database with WIMs, datacenters and port-mappings
        self.populate()

        # when we retrieve the port mappings for a list of datacenters
        # using either names or uuids
        for criteria in ([uuid('dc0'), uuid('dc1')], ['dc0', 'dc1']):
            mappings = self.persist.get_wim_port_mappings(datacenter=criteria)

            # then each result should have a datacenter_id
            datacenters = [m['datacenter_id'] for m in mappings]
            for datacenter in datacenters:
                self.assertIn(datacenter, [uuid('dc0'), uuid('dc1')])

            # a wim_id
            wims = [m['wim_id'] for m in mappings]
            for wim in wims:
                self.assertIsNot(wim, None)

            # and a array of pairs 'wan' <> 'pop' connections
            pairs = chain(*(m['pop_wan_mappings'] for m in mappings))
            self.assertEqual(len(list(pairs)), 2 * eg.NUM_WIMS)

    def test_get_wim_port_mappings_multiple(self):
        # Given we have more then one connection in a datacenter managed by the
        # WIM
        self.populate()
        self.populate([{
            'wim_port_mappings': [
                eg.wim_port_mapping(
                    0, 0,
                    pop_dpid='CC:CC:CC:CC:CC:CC:CC:CC',
                    wan_dpid='DD:DD:DD:DD:DD:DD:DD:DD'),
                eg.wim_port_mapping(
                    0, 0,
                    pop_dpid='EE:EE:EE:EE:EE:EE:EE:EE',
                    wan_dpid='FF:FF:FF:FF:FF:FF:FF:FF')]}])

        # when we retrieve the port mappings for the wim and datacenter:
        mappings = (
            self.persist.get_wim_port_mappings(wim='wim0', datacenter='dc0'))

        # then it should return just a single result, grouped by wim and
        # datacenter
        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings[0]['wim_id'], uuid('wim0'))
        self.assertEqual(mappings[0]['datacenter_id'], uuid('dc0'))

        self.assertEqual(len(mappings[0]['pop_wan_mappings']), 3)

        # when we retreive the mappings for more then one wim/datacenter
        # the grouping should still work properly
        mappings = self.persist.get_wim_port_mappings(
            wim=['wim0', 'wim1'], datacenter=['dc0', 'dc1'])
        self.assertEqual(len(mappings), 4)
        pairs = chain(*(m['pop_wan_mappings'] for m in mappings))
        self.assertEqual(len(list(pairs)), 6)

    def test_get_actions_in_group(self):
        # Given a good number of wim actions exist in the database
        kwargs = {'action_id': uuid('action0')}
        actions = (eg.wim_actions('CREATE', num_links=8, **kwargs) +
                   eg.wim_actions('FIND', num_links=8, **kwargs) +
                   eg.wim_actions('START', num_links=8, **kwargs))
        for i, action in enumerate(actions):
            action['task_index'] = i

        self.populate([
            {'nfvo_tenants': eg.tenant()}
        ] + eg.wim_set() + [
            {'instance_actions': eg.instance_action(**kwargs)},
            {'vim_wim_actions': actions}
        ])

        # When we retrieve them in groups
        limit = 5
        results = self.persist.get_actions_in_groups(
            uuid('wim-account00'), ['instance_wim_nets'], group_limit=limit)

        # Then we should have N groups where N == limit
        self.assertEqual(len(results), limit)
        for _, task_list in results:
            # And since for each link we have create 3 actions (create, find,
            # start), we should find them in each group
            self.assertEqual(len(task_list), 3)

    @disable_foreign_keys
    def test_update_instance_action_counters(self):
        # Given we have one instance action in the database with 2 incomplete
        # tasks
        action = eg.instance_action(num_tasks=2)
        self.populate([{'instance_actions': action}])
        # When we update the done counter by 0, nothing should happen
        self.persist.update_instance_action_counters(action['uuid'], done=0)
        result = self.persist.get_by_uuid('instance_actions', action['uuid'])
        self.assertEqual(result['number_done'], 0)
        self.assertEqual(result['number_failed'], 0)
        # When we update the done counter by 2, number_done should be 2
        self.persist.update_instance_action_counters(action['uuid'], done=2)
        result = self.persist.get_by_uuid('instance_actions', action['uuid'])
        self.assertEqual(result['number_done'], 2)
        self.assertEqual(result['number_failed'], 0)
        # When we update the done counter by -1, and the failed counter by 1
        self.persist.update_instance_action_counters(
            action['uuid'], done=-1, failed=1)
        # Then we should see 1 and 1
        result = self.persist.get_by_uuid('instance_actions', action['uuid'])
        self.assertEqual(result['number_done'], 1)
        self.assertEqual(result['number_failed'], 1)


if __name__ == '__main__':
    unittest.main()
