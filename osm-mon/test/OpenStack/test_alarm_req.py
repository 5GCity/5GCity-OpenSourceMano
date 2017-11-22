# Copyright 2017 iIntel Research and Development Ireland Limited
# **************************************************************

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
##
"""Tests for all alarm request message keys."""

import json

import logging

import unittest

import mock

from plugins.OpenStack.Aodh import alarming as alarm_req
from plugins.OpenStack.common import Common

__author__ = "Helena McGough"

log = logging.getLogger(__name__)


class Message(object):
    """A class to mock a message object value for alarm requests."""

    def __init__(self):
        """Initialize a mocked message instance."""
        self.topic = "alarm_request"
        self.key = None
        self.value = json.dumps({"mock_value": "mock_details"})


class TestAlarmKeys(unittest.TestCase):
    """Integration test for alarm request keys."""

    def setUp(self):
        """Setup the tests for alarm request keys."""
        super(TestAlarmKeys, self).setUp()
        self.alarming = alarm_req.Alarming()
        self.alarming.common = Common()

    @mock.patch.object(Common, "_authenticate")
    def test_alarming_env_authentication(self, auth):
        """Test getting an auth_token and endpoint for alarm requests."""
        # if auth_token is None environment variables are used to authenticare
        message = Message()

        self.alarming.alarming(message, self.alarming.common, None)

        auth.assert_called_with()

    @mock.patch.object(Common, "_authenticate")
    def test_acccess_cred_auth(self, auth):
        """Test receiving auth_token from access creds."""
        message = Message()

        self.alarming.alarming(message, self.alarming.common, "my_auth_token")

        auth.assert_not_called
        self.assertEqual(self.alarming.auth_token, "my_auth_token")

    @mock.patch.object(alarm_req.Alarming, "delete_alarm")
    def test_delete_alarm_key(self, del_alarm):
        """Test the functionality for a create alarm request."""
        # Mock a message value and key
        message = Message()
        message.key = "delete_alarm_request"
        message.value = json.dumps({"alarm_delete_request":
                                   {"alarm_uuid": "my_alarm_id"}})

        # Call the alarming functionality and check delete request
        self.alarming.alarming(message, self.alarming.common, "my_auth_token")

        del_alarm.assert_called_with(mock.ANY, mock.ANY, "my_alarm_id")

    @mock.patch.object(alarm_req.Alarming, "list_alarms")
    def test_list_alarm_key(self, list_alarm):
        """Test the functionality for a list alarm request."""
        # Mock a message with list alarm key and value
        message = Message()
        message.key = "list_alarm_request"
        message.value = json.dumps({"alarm_list_request": "my_alarm_details"})

        # Call the alarming functionality and check list functionality
        self.alarming.alarming(message, self.alarming.common, "my_auth_token")
        list_alarm.assert_called_with(mock.ANY, mock.ANY, "my_alarm_details")

    @mock.patch.object(alarm_req.Alarming, "update_alarm_state")
    def test_ack_alarm_key(self, ack_alarm):
        """Test the functionality for an acknowledge alarm request."""
        # Mock a message with acknowledge alarm key and value
        message = Message()
        message.key = "acknowledge_alarm"
        message.value = json.dumps({"ack_details":
                                    {"alarm_uuid": "my_alarm_id"}})

        # Call alarming functionality and check acknowledge functionality
        self.alarming.alarming(message, self.alarming.common, "my_auth_token")
        ack_alarm.assert_called_with(mock.ANY, mock.ANY, "my_alarm_id")

    @mock.patch.object(alarm_req.Alarming, "configure_alarm")
    def test_config_alarm_key(self, config_alarm):
        """Test the functionality for a create alarm request."""
        # Mock a message with config alarm key and value
        message = Message()
        message.key = "create_alarm_request"
        message.value = json.dumps({"alarm_create_request": "alarm_details"})

        # Call alarming functionality and check config alarm call
        config_alarm.return_value = "my_alarm_id", True
        self.alarming.alarming(message, self.alarming.common, "my_auth_token")
        config_alarm.assert_called_with(mock.ANY, mock.ANY, "alarm_details")
