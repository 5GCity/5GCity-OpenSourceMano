# Copyright 2017 iIntel Research and Development Ireland Limited
# **************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Intel Corporation

# Licensed under the Apache License, Version 2.0 (the 'License'); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at

#         http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
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

from osm_mon.core.auth import AuthManager
from osm_mon.core.database import VimCredentials, DatabaseManager
from osm_mon.core.message_bus.producer import KafkaProducer
from osm_mon.plugins.OpenStack.Aodh import alarming as alarm_req
from osm_mon.plugins.OpenStack.common import Common

log = logging.getLogger(__name__)

mock_creds = VimCredentials()
mock_creds.config = '{}'


class Message(object):
    """A class to mock a message object value for alarm requests."""

    def __init__(self):
        """Initialize a mocked message instance."""
        self.topic = 'alarm_request'
        self.key = None
        self.value = json.dumps({'mock_value': 'mock_details'})


@mock.patch.object(KafkaProducer, 'publish', mock.Mock())
class TestAlarmKeys(unittest.TestCase):
    """Integration test for alarm request keys."""

    def setUp(self):
        """Setup the tests for alarm request keys."""
        super(TestAlarmKeys, self).setUp()
        self.alarming = alarm_req.Alarming()
        self.alarming.common = Common()

    @mock.patch.object(AuthManager, 'get_credentials')
    @mock.patch.object(Common, 'get_endpoint')
    @mock.patch.object(Common, 'get_auth_token')
    def test_alarming_authentication(self, get_token, get_endpoint, get_creds):
        """Test getting an auth_token and endpoint for alarm requests."""
        # if auth_token is None environment variables are used to authenticate
        message = Message()

        get_creds.return_value = mock_creds

        self.alarming.alarming(message, 'test_id')

        get_token.assert_called_with('test_id')
        get_endpoint.assert_any_call('alarming', 'test_id')

    @mock.patch.object(Common, 'get_endpoint', mock.Mock())
    @mock.patch.object(Common, 'get_auth_token', mock.Mock())
    @mock.patch.object(AuthManager, 'get_credentials')
    @mock.patch.object(alarm_req.Alarming, 'delete_alarm')
    def test_delete_alarm_key(self, del_alarm, get_creds):
        """Test the functionality for a create alarm request."""
        # Mock a message value and key
        message = Message()
        message.key = 'delete_alarm_request'
        message.value = json.dumps({'alarm_delete_request': {
            'correlation_id': 1,
            'alarm_uuid': 'my_alarm_id'
        }})

        get_creds.return_value = mock_creds
        del_alarm.return_value = {}

        # Call the alarming functionality and check delete request
        self.alarming.alarming(message, 'test_id')
        del_alarm.assert_called_with(mock.ANY, mock.ANY, 'my_alarm_id')

    @mock.patch.object(Common, 'get_endpoint', mock.Mock())
    @mock.patch.object(Common, 'get_auth_token', mock.Mock())
    @mock.patch.object(AuthManager, 'get_credentials')
    @mock.patch.object(alarm_req.Alarming, 'list_alarms')
    def test_list_alarm_key(self, list_alarm, get_creds):
        """Test the functionality for a list alarm request."""
        # Mock a message with list alarm key and value
        message = Message()
        message.key = 'list_alarm_request'
        message.value = json.dumps({'alarm_list_request': {'correlation_id': 1}})

        get_creds.return_value = mock_creds

        list_alarm.return_value = []

        # Call the alarming functionality and check list functionality
        self.alarming.alarming(message, 'test_id')
        list_alarm.assert_called_with(mock.ANY, mock.ANY, {'correlation_id': 1})

    @mock.patch.object(Common, 'get_auth_token', mock.Mock())
    @mock.patch.object(Common, 'get_endpoint', mock.Mock())
    @mock.patch.object(AuthManager, 'get_credentials')
    @mock.patch.object(alarm_req.Alarming, 'update_alarm_state')
    def test_ack_alarm_key(self, ack_alarm, get_creds):
        """Test the functionality for an acknowledge alarm request."""
        # Mock a message with acknowledge alarm key and value
        message = Message()
        message.key = 'acknowledge_alarm'
        message.value = json.dumps({'ack_details':
                                        {'alarm_uuid': 'my_alarm_id'}})

        get_creds.return_value = mock_creds

        # Call alarming functionality and check acknowledge functionality
        self.alarming.alarming(message, 'test_id')
        ack_alarm.assert_called_with(mock.ANY, mock.ANY, 'my_alarm_id')

    @mock.patch.object(Common, 'get_auth_token', mock.Mock())
    @mock.patch.object(Common, 'get_endpoint', mock.Mock())
    @mock.patch.object(DatabaseManager, 'save_alarm', mock.Mock())
    @mock.patch.object(Common, "perform_request")
    @mock.patch.object(AuthManager, 'get_credentials')
    @mock.patch.object(alarm_req.Alarming, 'configure_alarm')
    def test_config_alarm_key(self, config_alarm, get_creds, perf_req):
        """Test the functionality for a create alarm request."""
        # Mock a message with config alarm key and value
        message = Message()
        message.key = 'create_alarm_request'
        message.value = json.dumps({'alarm_create_request': {'correlation_id': 1, 'threshold_value': 50,
                                                             'operation': 'GT', 'metric_name': 'cpu_utilization',
                                                             'vdu_name': 'vdu',
                                                             'vnf_member_index': '1',
                                                             'ns_id': '1',
                                                             'resource_uuid': '123'}})
        mock_perf_req_return_value = {"metrics": {"cpu_util": 123}}
        perf_req.return_value = type('obj', (object,), {'text': json.dumps(mock_perf_req_return_value, sort_keys=True)})
        get_creds.return_value = mock_creds

        # Call alarming functionality and check config alarm call
        config_alarm.return_value = 'my_alarm_id'
        self.alarming.alarming(message, 'test_id')
        config_alarm.assert_called_with(mock.ANY, mock.ANY, {'correlation_id': 1, 'threshold_value': 50,
                                                             'operation': 'GT',
                                                             'metric_name': 'cpu_utilization',
                                                             'vdu_name': 'vdu',
                                                             'vnf_member_index': '1', 'ns_id': '1',
                                                             'resource_uuid': '123'}, {})
