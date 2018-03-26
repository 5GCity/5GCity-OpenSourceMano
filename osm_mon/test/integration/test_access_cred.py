# Copyright 2017 Intel Research and Development Ireland Limited
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Intel Corporation

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at

#         http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# For those usages not covered by the Apache License, Version 2.0 please
# contact: helena.mcgough@intel.com or adrian.hoban@intel.com

# __author__ = "Helena McGough"
"""Test an end to end Openstack access_credentials requests."""

import json
import logging
import unittest

import mock
from kafka import KafkaConsumer
from kafka import KafkaProducer
from kafka.errors import KafkaError
from keystoneclient.v3 import client

from osm_mon.plugins.OpenStack.Aodh import alarming
from osm_mon.plugins.OpenStack.common import Common

log = logging.getLogger(__name__)


# TODO: Remove this file
class AccessCredentialsTest(unittest.TestCase):
    def setUp(self):
        # Set up common and alarming class instances
        self.alarms = alarming.Alarming()
        self.openstack_auth = Common()

        try:
            self.producer = KafkaProducer(bootstrap_servers='localhost:9092')
            self.req_consumer = KafkaConsumer(bootstrap_servers='localhost:9092',
                                              group_id='osm_mon',
                                              consumer_timeout_ms=2000)
            self.req_consumer.subscribe(['access_credentials'])
        except KafkaError:
            self.skipTest('Kafka server not present.')

    @mock.patch.object(client, "Client")
    def test_access_cred_req(self, keyclient):
        """Test access credentials request message from KafkaProducer."""
        # Set-up message, producer and consumer for tests
        payload = {"vim_type": "OpenStack",
                   "access_config":
                       {"openstack_site": "my_site",
                        "user": "my_user",
                        "password": "my_password",
                        "vim_tenant_name": "my_tenant"}}

        self.producer.send('access_credentials', value=json.dumps(payload))

        for message in self.req_consumer:
            # Check the vim desired by the message
            vim_type = json.loads(message.value)["vim_type"].lower()
            if vim_type == "openstack":
                self.openstack_auth._authenticate(message=message)

                # A keystone client is created with the valid access_credentials
                keyclient.assert_called_with(
                    auth_url="my_site", username="my_user", password="my_password",
                    tenant_name="my_tenant")

                return
