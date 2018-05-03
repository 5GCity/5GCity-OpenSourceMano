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
import unittest

from osm_mon.core.auth import AuthManager
from osm_mon.core.database import DatabaseManager

log = logging.getLogger(__name__)


class VimAccountTest(unittest.TestCase):
    def setUp(self):
        self.auth_manager = AuthManager()
        self.database_manager = DatabaseManager()
        self.database_manager.create_tables()

    def test_create_edit_delete_vim_account(self):
        """Test vim_account creation message from KafkaProducer."""
        # Set-up message, producer and consumer for tests
        create_payload = {
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
        self.auth_manager.store_auth_credentials(create_payload)

        creds = self.auth_manager.get_credentials('test_id')

        self.assertIsNotNone(creds)
        self.assertEqual(creds.name, create_payload['name'])
        self.assertEqual(json.loads(creds.config), create_payload['config'])

        # Set-up message, producer and consumer for tests
        edit_payload = {
            "_id": "test_id",
            "name": "test_name_edited",
            "vim_type": "openstack",
            "vim_url": "auth_url",
            "vim_user": "user",
            "vim_password": "password",
            "vim_tenant_name": "tenant",
            "config":
                {
                    "foo_edited": "bar_edited"
                }
        }

        self.auth_manager.store_auth_credentials(edit_payload)

        creds = self.auth_manager.get_credentials('test_id')

        self.assertEqual(creds.name, edit_payload['name'])
        self.assertEqual(json.loads(creds.config), edit_payload['config'])

        delete_payload = {
            "_id": "test_id"
        }

        self.auth_manager.delete_auth_credentials(delete_payload)

        creds = self.auth_manager.get_credentials('test_id')
        self.assertIsNone(creds)
