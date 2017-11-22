# Copyright 2017 iIntel Research and Development Ireland Limited
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
##
"""Tests for all metric request message keys."""

import json

import logging

import unittest

import mock

from plugins.OpenStack.Gnocchi import metrics as metric_req

from plugins.OpenStack.common import Common

__author__ = "Helena McGough"

log = logging.getLogger(__name__)


class Message(object):
    """A class to mock a message object value for metric requests."""

    def __init__(self):
        """Initialize a mocked message instance."""
        self.topic = "metric_request"
        self.key = None
        self.value = json.dumps({"mock_message": "message_details"})


class TestMetricReq(unittest.TestCase):
    """Integration test for metric request keys."""

    def setUp(self):
        """Setup the tests for metric request keys."""
        super(TestMetricReq, self).setUp()
        self.common = Common()
        self.metrics = metric_req.Metrics()

    @mock.patch.object(Common, "_authenticate")
    def test_access_cred_metric_auth(self, auth):
        """Test authentication with access credentials."""
        message = Message()

        self.metrics.metric_calls(message, self.common, "my_auth_token")

        auth.assert_not_called
        self.assertEqual(self.metrics.auth_token, "my_auth_token")

    @mock.patch.object(Common, "_authenticate")
    def test_env_metric_auth(self, auth):
        """Test authentication with environment variables."""
        message = Message()

        self.metrics.metric_calls(message, self.common, None)

        auth.assert_called_with()

    @mock.patch.object(metric_req.Metrics, "delete_metric")
    def test_delete_metric_key(self, del_metric):
        """Test the functionality for a delete metric request."""
        # Mock a message value and key
        message = Message()
        message.key = "delete_metric_request"
        message.value = json.dumps({"metric_uuid": "my_metric_id"})

        # Call the metric functionality and check delete request
        self.metrics.metric_calls(message, self.common, "my_auth_token")

        del_metric.assert_called_with(mock.ANY, mock.ANY, "my_metric_id")

    @mock.patch.object(metric_req.Metrics, "list_metrics")
    def test_list_metric_key(self, list_metrics):
        """Test the functionality for a list metric request."""
        # Mock a message with list metric key and value
        message = Message()
        message.key = "list_metric_request"
        message.value = json.dumps({"metrics_list_request": "metric_details"})

        # Call the metric functionality and check list functionality
        self.metrics.metric_calls(message, self.common, "my_auth_token")
        list_metrics.assert_called_with(mock.ANY, mock.ANY, "metric_details")

    @mock.patch.object(metric_req.Metrics, "read_metric_data")
    @mock.patch.object(metric_req.Metrics, "list_metrics")
    @mock.patch.object(metric_req.Metrics, "delete_metric")
    @mock.patch.object(metric_req.Metrics, "configure_metric")
    def test_update_metric_key(self, config_metric, delete_metric, list_metrics,
                               read_data):
        """Test the functionality for an update metric request."""
        # Mock a message with update metric key and value
        message = Message()
        message.key = "update_metric_request"
        message.value = json.dumps({"metric_create":
                                    {"metric_name": "my_metric",
                                     "resource_uuid": "my_r_id"}})

        # Call metric functionality and confirm no function is called
        # Gnocchi does not support updating a metric configuration
        self.metrics.metric_calls(message, self.common, "my_auth_token")
        config_metric.assert_not_called
        list_metrics.assert_not_called
        delete_metric.assert_not_called
        read_data.assert_not_called

    @mock.patch.object(metric_req.Metrics, "configure_metric")
    def test_config_metric_key(self, config_metric):
        """Test the functionality for a create metric request."""
        # Mock a message with create metric key and value
        message = Message()
        message.key = "create_metric_request"
        message.value = json.dumps({"metric_create": "metric_details"})

        # Call metric functionality and check config metric
        config_metric.return_value = "metric_id", "resource_id", True
        self.metrics.metric_calls(message, self.common, "my_auth_token")
        config_metric.assert_called_with(mock.ANY, mock.ANY, "metric_details")

    @mock.patch.object(metric_req.Metrics, "read_metric_data")
    def test_read_data_key(self, read_data):
        """Test the functionality for a read metric data request."""
        # Mock a message with a read data key and value
        message = Message()
        message.key = "read_metric_data_request"
        message.value = json.dumps({"alarm_uuid": "alarm_id"})

        # Call metric functionality and check read data metrics
        read_data.return_value = "time_stamps", "data_values"
        self.metrics.metric_calls(message, self.common, "my_auth_token")
        read_data.assert_called_with(
            mock.ANY, mock.ANY, json.loads(message.value))
