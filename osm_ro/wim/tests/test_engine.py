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

from mock import MagicMock

from . import fixtures as eg
from ...tests.db_helpers import TestCaseWithDatabasePerTest, uuid
from ..errors import NoWimConnectedToDatacenters
from ..engine import WimEngine
from ..persistence import WimPersistence


class TestWimEngineDbMethods(TestCaseWithDatabasePerTest):
    def setUp(self):
        super(TestWimEngineDbMethods, self).setUp()
        self.persist = WimPersistence(self.db)
        self.engine = WimEngine(persistence=self.persist)
        self.addCleanup(self.engine.stop_threads)

    def populate(self, seeds=None):
        super(TestWimEngineDbMethods, self).populate(
            seeds or eg.consistent_set())

    def test_find_common_wims(self):
        # Given we have 2 WIM, 3 datacenters, but just 1 of the WIMs have
        # access to them
        self.populate([{'nfvo_tenants': [eg.tenant(0)]}] +
                      eg.wim_set(0, 0) +
                      eg.wim_set(1, 0) +
                      eg.datacenter_set(0, 0) +
                      eg.datacenter_set(1, 0) +
                      eg.datacenter_set(2, 0) +
                      [{'wim_port_mappings': [
                          eg.wim_port_mapping(0, 0),
                          eg.wim_port_mapping(0, 1),
                          eg.wim_port_mapping(0, 2)]}])

        # When we retrieve the wims interconnecting some datacenters
        wim_ids = self.engine.find_common_wims(
            [uuid('dc0'), uuid('dc1'), uuid('dc2')], tenant='tenant0')

        # Then we should have just the first wim
        self.assertEqual(len(wim_ids), 1)
        self.assertEqual(wim_ids[0], uuid('wim0'))

    def test_find_common_wims_multiple(self):
        # Given we have 2 WIM, 3 datacenters, and all the WIMs have access to
        # all datacenters
        self.populate([{'nfvo_tenants': [eg.tenant(0)]}] +
                      eg.wim_set(0, 0) +
                      eg.wim_set(1, 0) +
                      eg.datacenter_set(0, 0) +
                      eg.datacenter_set(1, 0) +
                      eg.datacenter_set(2, 0) +
                      [{'wim_port_mappings': [
                          eg.wim_port_mapping(0, 0),
                          eg.wim_port_mapping(0, 1),
                          eg.wim_port_mapping(0, 2),
                          eg.wim_port_mapping(1, 0),
                          eg.wim_port_mapping(1, 1),
                          eg.wim_port_mapping(1, 2)]}])

        # When we retrieve the wims interconnecting tree datacenters
        wim_ids = self.engine.find_common_wims(
            [uuid('dc0'), uuid('dc1'), uuid('dc2')], tenant='tenant0')

        # Then we should have all the wims
        self.assertEqual(len(wim_ids), 2)
        self.assertItemsEqual(wim_ids, [uuid('wim0'), uuid('wim1')])

    def test_find_common_wim(self):
        # Given we have 1 WIM, 3 datacenters but the WIM have access to just 2
        # of them
        self.populate([{'nfvo_tenants': [eg.tenant(0)]}] +
                      eg.wim_set(0, 0) +
                      eg.datacenter_set(0, 0) +
                      eg.datacenter_set(1, 0) +
                      eg.datacenter_set(2, 0) +
                      [{'wim_port_mappings': [
                          eg.wim_port_mapping(0, 0),
                          eg.wim_port_mapping(0, 1)]}])

        # When we retrieve the common wim for the 2 datacenter that are
        # interconnected
        wim_id = self.engine.find_common_wim(
            [uuid('dc0'), uuid('dc1')], tenant='tenant0')

        # Then we should find the wim
        self.assertEqual(wim_id, uuid('wim0'))

        # When we try to retrieve the common wim for the all the datacenters
        # Then a NoWimConnectedToDatacenters exception should be raised
        with self.assertRaises(NoWimConnectedToDatacenters):
            self.engine.find_common_wim(
                [uuid('dc0'), uuid('dc1'), uuid('dc2')], tenant='tenant0')

    def test_find_common_wim__different_tenants(self):
        # Given we have 1 WIM and 2 datacenters connected but the WIMs don't
        # belong to the tenant we have access to...
        self.populate([{'nfvo_tenants': [eg.tenant(0), eg.tenant(1)]}] +
                      eg.wim_set(0, 0) +
                      eg.datacenter_set(0, 0) +
                      eg.datacenter_set(1, 0) +
                      [{'wim_port_mappings': [
                          eg.wim_port_mapping(0, 0),
                          eg.wim_port_mapping(0, 1)]}])

        # When we retrieve the common wim for the 2 datacenter that are
        # interconnected, but using another tenant,
        # Then we should get an exception
        with self.assertRaises(NoWimConnectedToDatacenters):
            self.engine.find_common_wim(
                [uuid('dc0'), uuid('dc1')], tenant='tenant1')


class TestWimEngine(unittest.TestCase):
    def test_derive_wan_link(self):
        # Given we have 2 datacenters connected by the same WIM, with port
        # mappings registered
        mappings = [eg.processed_port_mapping(0, 0),
                    eg.processed_port_mapping(0, 1)]
        persist = MagicMock(
            get_wim_port_mappings=MagicMock(return_value=mappings))

        engine = WimEngine(persistence=persist)
        self.addCleanup(engine.stop_threads)

        # When we receive a list of 4 instance nets, representing
        # 2 VLDs connecting 2 datacenters each
        instance_nets = eg.instance_nets(2, 2)
        wan_links = engine.derive_wan_links({}, instance_nets, uuid('tenant0'))

        # Then we should derive 2 wan_links with the same instance_scenario_id
        # and different scenario_network_id
        self.assertEqual(len(wan_links), 2)
        for link in wan_links:
            self.assertEqual(link['instance_scenario_id'], uuid('nsr0'))
        # Each VLD needs a network to be created in each datacenter
        self.assertItemsEqual([l['sce_net_id'] for l in wan_links],
                              [uuid('vld0'), uuid('vld1')])


if __name__ == '__main__':
    unittest.main()
