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

import bottle
from mock import MagicMock, patch
from webtest import TestApp

from . import fixtures as eg  # "examples"
from ...http_tools.errors import Conflict, Not_Found
from ...tests.db_helpers import TestCaseWithDatabasePerTest, uuid
from ...utils import merge_dicts
from ..http_handler import WimHandler

OK = 200


@patch('osm_ro.wim.wim_thread.CONNECTORS', MagicMock())  # Avoid external calls
@patch('osm_ro.wim.wim_thread.WimThread.start', MagicMock())  # Avoid running
class TestHttpHandler(TestCaseWithDatabasePerTest):
    def setUp(self):
        super(TestHttpHandler, self).setUp()
        bottle.debug(True)
        handler = WimHandler(db=self.db)
        self.engine = handler.engine
        self.addCleanup(self.engine.stop_threads)
        self.app = TestApp(handler.wsgi_app)

    def populate(self, seeds=None):
        super(TestHttpHandler, self).populate(seeds or eg.consistent_set())

    def test_list_wims(self):
        # Given some wims are registered in the database
        self.populate()
        # when a GET /<tenant_id>/wims request arrives
        tenant_id = uuid('tenant0')
        response = self.app.get('/{}/wims'.format(tenant_id))

        # then the request should be well succeeded
        self.assertEqual(response.status_code, OK)
        # and all the registered wims should be present
        retrieved_wims = {v['name']: v for v in response.json['wims']}
        for name in retrieved_wims:
            identifier = int(name.replace('wim', ''))
            self.assertDictContainsSubset(
                eg.wim(identifier), retrieved_wims[name])

    def test_show_wim(self):
        # Given some wims are registered in the database
        self.populate()
        # when a GET /<tenant_id>/wims/<wim_id> request arrives
        tenant_id = uuid('tenant0')
        wim_id = uuid('wim1')
        response = self.app.get('/{}/wims/{}'.format(tenant_id, wim_id))

        # then the request should be well succeeded
        self.assertEqual(response.status_code, OK)
        # and the registered wim (wim1) should be present
        self.assertDictContainsSubset(eg.wim(1), response.json['wim'])
        # Moreover, it also works with tenant_id =  all
        response = self.app.get('/any/wims/{}'.format(wim_id))
        self.assertEqual(response.status_code, OK)
        self.assertDictContainsSubset(eg.wim(1), response.json['wim'])

    def test_show_wim__wim_doesnt_exists(self):
        # Given wim_id does not refer to any already registered wim
        self.populate()
        # when a GET /<tenant_id>/wims/<wim_id> request arrives
        tenant_id = uuid('tenant0')
        wim_id = uuid('wim999')
        response = self.app.get(
            '/{}/wims/{}'.format(tenant_id, wim_id),
            expect_errors=True)

        # then the result should not be well succeeded
        self.assertEqual(response.status_code, Not_Found)

    def test_show_wim__tenant_doesnt_exists(self):
        # Given wim_id does not refer to any already registered wim
        self.populate()
        # when a GET /<tenant_id>/wims/<wim_id> request arrives
        tenant_id = uuid('tenant999')
        wim_id = uuid('wim0')
        response = self.app.get(
            '/{}/wims/{}'.format(tenant_id, wim_id),
            expect_errors=True)

        # then the result should not be well succeeded
        self.assertEqual(response.status_code, Not_Found)

    def test_edit_wim(self):
        # Given a WIM exists in the database
        self.populate()
        # when a PUT /wims/<wim_id> request arrives
        wim_id = uuid('wim1')
        response = self.app.put_json('/wims/{}'.format(wim_id), {
            'wim': {'name': 'My-New-Name'}})

        # then the request should be well succeeded
        self.assertEqual(response.status_code, OK)
        # and the registered wim (wim1) should be present
        self.assertDictContainsSubset(
            merge_dicts(eg.wim(1), name='My-New-Name'),
            response.json['wim'])

    def test_delete_wim(self):
        # Given a WIM exists in the database
        self.populate()
        num_accounts = self.count('wim_accounts')
        num_associations = self.count('wim_nfvo_tenants')
        num_mappings = self.count('wim_port_mappings')

        with self.engine.threads_running():
            num_threads = len(self.engine.threads)
            # when a DELETE /wims/<wim_id> request arrives
            wim_id = uuid('wim1')
            response = self.app.delete('/wims/{}'.format(wim_id))
            num_threads_after = len(self.engine.threads)

        # then the request should be well succeeded
        self.assertEqual(response.status_code, OK)
        self.assertIn('deleted', response.json['result'])
        # and the registered wim1 should be deleted
        response = self.app.get(
            '/any/wims/{}'.format(wim_id),
            expect_errors=True)
        self.assertEqual(response.status_code, Not_Found)
        # and all the dependent records in other tables should be deleted:
        # wim_accounts, wim_nfvo_tenants, wim_port_mappings
        self.assertEqual(self.count('wim_nfvo_tenants'),
                         num_associations - eg.NUM_TENANTS)
        self.assertLess(self.count('wim_port_mappings'), num_mappings)
        self.assertEqual(self.count('wim_accounts'),
                         num_accounts - eg.NUM_TENANTS)
        # And the threads associated with the wim accounts should be stopped
        self.assertEqual(num_threads_after, num_threads - eg.NUM_TENANTS)

    def test_create_wim(self):
        # Given no WIM exists yet
        # when a POST /wims request arrives with the right payload
        response = self.app.post_json('/wims', {'wim': eg.wim(999)})

        # then the request should be well succeeded
        self.assertEqual(response.status_code, OK)
        self.assertEqual(response.json['wim']['name'], 'wim999')

    def test_create_wim_account(self):
        # Given a WIM and a NFVO tenant exist but are not associated
        self.populate([{'wims': [eg.wim(0)]},
                       {'nfvo_tenants': [eg.tenant(0)]}])

        with self.engine.threads_running():
            num_threads = len(self.engine.threads)
            # when a POST /<tenant_id>/wims/<wim_id> arrives
            response = self.app.post_json(
                '/{}/wims/{}'.format(uuid('tenant0'), uuid('wim0')),
                {'wim_account': eg.wim_account(0, 0)})

            num_threads_after = len(self.engine.threads)

        # then a new thread should be created
        self.assertEqual(num_threads_after, num_threads + 1)

        # and the request should be well succeeded
        self.assertEqual(response.status_code, OK)
        self.assertEqual(response.json['wim_account']['name'], 'wim-account00')

        # and a new association record should be created
        association = self.db.get_rows(FROM='wim_nfvo_tenants')
        assert association
        self.assertEqual(len(association), 1)
        self.assertEqual(association[0]['wim_id'], uuid('wim0'))
        self.assertEqual(association[0]['nfvo_tenant_id'], uuid('tenant0'))
        self.assertEqual(association[0]['wim_account_id'],
                         response.json['wim_account']['uuid'])

    def test_create_wim_account__existing_account(self):
        # Given a WIM, a WIM account and a NFVO tenants exist
        # But the NFVO and the WIM are not associated
        self.populate([
            {'wims': [eg.wim(0)]},
            {'nfvo_tenants': [eg.tenant(0)]},
            {'wim_accounts': [eg.wim_account(0, 0)]}])

        # when a POST /<tenant_id>/wims/<wim_id> arrives
        # and it refers to an existing wim account
        response = self.app.post_json(
            '/{}/wims/{}'.format(uuid('tenant0'), uuid('wim0')),
            {'wim_account': {'name': 'wim-account00'}})

        # then the request should be well succeeded
        self.assertEqual(response.status_code, OK)
        # and the association should be created
        association = self.db.get_rows(
            FROM='wim_nfvo_tenants',
            WHERE={'wim_id': uuid('wim0'),
                   'nfvo_tenant_id': uuid('tenant0')})
        assert association
        self.assertEqual(len(association), 1)
        # but no new wim_account should be created
        wim_accounts = self.db.get_rows(FROM='wim_accounts')
        self.assertEqual(len(wim_accounts), 1)
        self.assertEqual(wim_accounts[0]['name'], 'wim-account00')

    def test_create_wim_account__existing_account__differing(self):
        # Given a WIM, a WIM account and a NFVO tenants exist
        # But the NFVO and the WIM are not associated
        self.populate([
            {'wims': [eg.wim(0)]},
            {'nfvo_tenants': [eg.tenant(0)]},
            {'wim_accounts': [eg.wim_account(0, 0)]}])

        # when a POST /<tenant_id>/wims/<wim_id> arrives
        # and it refers to an existing wim account,
        # but with different fields
        response = self.app.post_json(
            '/{}/wims/{}'.format(uuid('tenant0'), uuid('wim0')), {
                'wim_account': {
                    'name': 'wim-account00',
                    'user': 'john',
                    'password': 'abc123'}},
            expect_errors=True)

        # then the request should not be well succeeded
        self.assertEqual(response.status_code, Conflict)
        # some useful message should be displayed
        response.mustcontain('attempt to overwrite', 'user', 'password')
        # and the association should not be created
        association = self.db.get_rows(
            FROM='wim_nfvo_tenants',
            WHERE={'wim_id': uuid('wim0'),
                   'nfvo_tenant_id': uuid('tenant0')})
        assert not association

    def test_create_wim_account__association_already_exists(self):
        # Given a WIM, a WIM account and a NFVO tenants exist
        # and are correctly associated
        self.populate()
        num_assoc_before = self.count('wim_nfvo_tenants')

        # when a POST /<tenant_id>/wims/<wim_id> arrives trying to connect a
        # WIM and a tenant for the second time
        response = self.app.post_json(
            '/{}/wims/{}'.format(uuid('tenant0'), uuid('wim0')), {
                'wim_account': {
                    'user': 'user999',
                    'password': 'password999'}},
            expect_errors=True)

        # then the request should not be well succeeded
        self.assertEqual(response.status_code, Conflict)
        # the message should be useful
        response.mustcontain('There is already', uuid('wim0'), uuid('tenant0'))

        num_assoc_after = self.count('wim_nfvo_tenants')

        # and the number of association record should not be increased
        self.assertEqual(num_assoc_before, num_assoc_after)

    def test_create_wim__tenant_doesnt_exist(self):
        # Given a tenant not exists
        self.populate()

        # But the user tries to create a wim_account anyway
        response = self.app.post_json(
            '/{}/wims/{}'.format(uuid('tenant999'), uuid('wim0')), {
                'wim_account': {
                    'user': 'user999',
                    'password': 'password999'}},
            expect_errors=True)

        # then the request should not be well succeeded
        self.assertEqual(response.status_code, Not_Found)
        # the message should be useful
        response.mustcontain('No record was found', uuid('tenant999'))

    def test_create_wim__wim_doesnt_exist(self):
        # Given a tenant not exists
        self.populate()

        # But the user tries to create a wim_account anyway
        response = self.app.post_json(
            '/{}/wims/{}'.format(uuid('tenant0'), uuid('wim999')), {
                'wim_account': {
                    'user': 'user999',
                    'password': 'password999'}},
            expect_errors=True)

        # then the request should not be well succeeded
        self.assertEqual(response.status_code, Not_Found)
        # the message should be useful
        response.mustcontain('No record was found', uuid('wim999'))

    def test_update_wim_account(self):
        # Given a WIM account connecting a tenant and a WIM exists
        self.populate()

        with self.engine.threads_running():
            num_threads = len(self.engine.threads)

            thread = self.engine.threads[uuid('wim-account00')]
            reload = MagicMock(wraps=thread.reload)

            with patch.object(thread, 'reload', reload):
                # when a PUT /<tenant_id>/wims/<wim_id> arrives
                response = self.app.put_json(
                    '/{}/wims/{}'.format(uuid('tenant0'), uuid('wim0')), {
                        'wim_account': {
                            'name': 'account888',
                            'user': 'user888'}})

            num_threads_after = len(self.engine.threads)

        # then the wim thread should be restarted
        reload.assert_called_once()
        # and no thread should be added or removed
        self.assertEqual(num_threads_after, num_threads)

        # and the request should be well succeeded
        self.assertEqual(response.status_code, OK)
        self.assertEqual(response.json['wim_account']['name'], 'account888')
        self.assertEqual(response.json['wim_account']['user'], 'user888')

    def test_update_wim_account__multiple(self):
        # Given a WIM account connected to several tenants
        self.populate()

        with self.engine.threads_running():
            # when a PUT /any/wims/<wim_id> arrives
            response = self.app.put_json(
                '/any/wims/{}'.format(uuid('wim0')), {
                    'wim_account': {
                        'user': 'user888',
                        'config': {'x': 888}}})

        # then the request should be well succeeded
        self.assertEqual(response.status_code, OK)
        self.assertEqual(len(response.json['wim_accounts']), eg.NUM_TENANTS)

        for account in response.json['wim_accounts']:
            self.assertEqual(account['user'], 'user888')
            self.assertEqual(account['config']['x'], 888)

    def test_delete_wim_account(self):
        # Given a WIM account exists and it is connected to a tenant
        self.populate()

        num_accounts_before = self.count('wim_accounts')

        with self.engine.threads_running():
            thread = self.engine.threads[uuid('wim-account00')]
            exit = MagicMock(wraps=thread.exit)
            num_threads = len(self.engine.threads)

            with patch.object(thread, 'exit', exit):
                # when a PUT /<tenant_id>/wims/<wim_id> arrives
                response = self.app.delete_json(
                    '/{}/wims/{}'.format(uuid('tenant0'), uuid('wim0')))

            num_threads_after = len(self.engine.threads)

        # then the wim thread should exit
        self.assertEqual(num_threads_after, num_threads - 1)
        exit.assert_called_once()

        # and the request should be well succeeded
        self.assertEqual(response.status_code, OK)
        response.mustcontain('account `wim-account00` deleted')

        # and the number of wim_accounts should decrease
        num_accounts_after = self.count('wim_accounts')
        self.assertEqual(num_accounts_after, num_accounts_before - 1)

    def test_delete_wim_account__multiple(self):
        # Given a WIM account exists and it is connected to several tenants
        self.populate()

        num_accounts_before = self.count('wim_accounts')

        with self.engine.threads_running():
            # when a PUT /<tenant_id>/wims/<wim_id> arrives
            response = self.app.delete_json(
                '/any/wims/{}'.format(uuid('wim0')))

        # then the request should be well succeeded
        self.assertEqual(response.status_code, OK)
        response.mustcontain('account `wim-account00` deleted')
        response.mustcontain('account `wim-account10` deleted')

        # and the number of wim_accounts should decrease
        num_accounts_after = self.count('wim_accounts')
        self.assertEqual(num_accounts_after,
                         num_accounts_before - eg.NUM_TENANTS)

    def test_delete_wim_account__doesnt_exist(self):
        # Given we have a tenant that is not connected to a WIM
        self.populate()
        tenant = {'uuid': uuid('tenant888'), 'name': 'tenant888'}
        self.populate([{'nfvo_tenants': [tenant]}])

        num_accounts_before = self.count('wim_accounts')

        # when a PUT /<tenant_id>/wims/<wim_id> arrives
        response = self.app.delete(
            '/{}/wims/{}'.format(uuid('tenant888'), uuid('wim0')),
            expect_errors=True)

        # then the request should not succeed
        self.assertEqual(response.status_code, Not_Found)

        # and the number of wim_accounts should not decrease
        num_accounts_after = self.count('wim_accounts')
        self.assertEqual(num_accounts_after, num_accounts_before)

    def test_create_port_mappings(self):
        # Given we have a wim and datacenter without any port mappings
        self.populate([{'nfvo_tenants': eg.tenant(0)}] +
                      eg.datacenter_set(888, 0) +
                      eg.wim_set(999, 0))

        # when a POST /<tenant_id>/wims/<wim_id>/port_mapping arrives
        response = self.app.post_json(
            '/{}/wims/{}/port_mapping'.format(uuid('tenant0'), uuid('wim999')),
            {'wim_port_mapping': [{
                'datacenter_name': 'dc888',
                'pop_wan_mappings': [
                    {'pop_switch_dpid': 'AA:AA:AA:AA:AA:AA:AA:AA',
                     'pop_switch_port': 1,
                     'wan_service_mapping_info': {
                         'mapping_type': 'dpid-port',
                         'wan_switch_dpid': 'BB:BB:BB:BB:BB:BB:BB:BB',
                         'wan_switch_port': 1
                     }}
                ]}
            ]})

        # the request should be well succeeded
        self.assertEqual(response.status_code, OK)
        # and port mappings should be stored in the database
        port_mapping = self.db.get_rows(FROM='wim_port_mappings')
        self.assertEqual(len(port_mapping), 1)

    def test_get_port_mappings(self):
        # Given WIMS and datacenters exist with port mappings between them
        self.populate()
        # when a GET /<tenant_id>/wims/<wim_id>/port_mapping arrives
        response = self.app.get(
            '/{}/wims/{}/port_mapping'.format(uuid('tenant0'), uuid('wim0')))
        # the request should be well succeeded
        self.assertEqual(response.status_code, OK)
        # and we should see port mappings for each WIM, datacenter pair
        mappings = response.json['wim_port_mapping']
        self.assertEqual(len(mappings), eg.NUM_DATACENTERS)
        # ^  In the fixture set all the datacenters are connected to all wims

    def test_delete_port_mappings(self):
        # Given WIMS and datacenters exist with port mappings between them
        self.populate()
        num_mappings_before = self.count('wim_port_mappings')

        # when a DELETE /<tenant_id>/wims/<wim_id>/port_mapping arrives
        response = self.app.delete(
            '/{}/wims/{}/port_mapping'.format(uuid('tenant0'), uuid('wim0')))
        # the request should be well succeeded
        self.assertEqual(response.status_code, OK)
        # and the number of port mappings should decrease
        num_mappings_after = self.count('wim_port_mappings')
        self.assertEqual(num_mappings_after,
                         num_mappings_before - eg.NUM_DATACENTERS)
        # ^  In the fixture set all the datacenters are connected to all wims


if __name__ == '__main__':
    unittest.main()
