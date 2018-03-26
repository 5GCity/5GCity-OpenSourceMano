# -*- coding: utf-8 -*-

# Copyright 2018 Whitestack, LLC
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Whitestack, LLC

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
# contact: bdiaz@whitestack.com or glavado@whitestack.com
##

"""Test an end to end Openstack vim_account requests."""

import json
import logging
import time
import unittest

from kafka import KafkaConsumer
from kafka import KafkaProducer
from kafka.errors import KafkaError

from osm_mon.core.auth import AuthManager

log = logging.getLogger(__name__)


class VimAccountTest(unittest.TestCase):
    def setUp(self):
        try:
            self.producer = KafkaProducer(bootstrap_servers='localhost:9092')
            self.consumer = KafkaConsumer(bootstrap_servers='localhost:9092',
                                          group_id='osm_mon')
            self.consumer.subscribe(['vim_account'])
            self.auth_manager = AuthManager()
        except KafkaError:
            self.skipTest('Kafka server not present.')

    def test_create_vim_account(self):
        """Test vim_account creation message from KafkaProducer."""
        # Set-up message, producer and consumer for tests
        payload = {
            "_id": "test_id",
            "name": "test_name",
            "vim_type": "openstack",
            "vim_url": "auth_url",
            "vim_user": "user",
            "vim_password": "password",
            "vim_tenant_name": "tenant",
            "config":
                {
                    "foo": "bar"
                }
        }

        self.producer.send('vim_account', key=b'create', value=json.dumps(payload))

        self.producer.flush()

        # FIXME: Create a schema for a vim_account_create_response, so we can test it
        time.sleep(5)
        creds = self.auth_manager.get_credentials(payload['_id'])
        self.assertEqual(creds.name, payload['name'])
        self.assertEqual(json.loads(creds.config), payload['config'])
