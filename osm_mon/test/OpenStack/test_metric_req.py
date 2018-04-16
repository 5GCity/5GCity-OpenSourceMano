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

from osm_mon.plugins.OpenStack.Gnocchi import metrics as metric_req

from osm_mon.plugins.OpenStack.common import Common

log = logging.getLogger(__name__)


class Message(object):
    """A class to mock a message object value for metric requests."""

    def __init__(self):
        """Initialize a mocked message instance."""
        self.topic = "metric_request"
        self.key = None
        self.value = json.dumps({"vim_uuid": "test_id", "mock_message": "message_details"})


class TestMetricReq(unittest.TestCase):
    """Integration test for metric request keys."""

    def setUp(self):
        """Setup the tests for metric request keys."""
        super(TestMetricReq, self).setUp()
        self.metrics = metric_req.Metrics()

    @mock.patch.object(Common, 'get_endpoint')
    @mock.patch.object(Common, "get_auth_token")
    def test_access_cred_metric_auth(self, get_token, get_endpoint):
        """Test authentication with access credentials."""
        message = Message()

        self.metrics.metric_calls(message)

        get_token.assert_called_with('test_id')
        get_endpoint.assert_any_call('metric', 'test_id')

    @mock.patch.object(Common, "get_auth_token", mock.Mock())
    @mock.patch.object(Common, 'get_endpoint', mock.Mock())
    @mock.patch.object(metric_req.Metrics, "delete_metric")
    @mock.patch.object(metric_req.Metrics, "get_metric_id")
    def test_delete_metric_key(self, get_metric_id, del_metric):
        """Test the functionality for a delete metric request."""
        # Mock a message value and key
        message = Message()
        message.key = "delete_metric_request"
        message.value = json.dumps({"vim_uuid": "test_id", "metric_name": "disk_write_ops", "resource_uuid": "my_r_id"})

        # Call the metric functionality and check delete request
        get_metric_id.return_value = "my_metric_id"
        self.metrics.metric_calls(message)
        del_metric.assert_called_with(mock.ANY, mock.ANY, "my_metric_id")

    @mock.patch.object(Common, "get_auth_token", mock.Mock())
    @mock.patch.object(Common, 'get_endpoint', mock.Mock())
    @mock.patch.object(metric_req.Metrics, "list_metrics")
    def test_list_metric_key(self, list_metrics):
        """Test the functionality for a list metric request."""
        # Mock a message with list metric key and value
        message = Message()
        message.key = "list_metric_request"
        message.value = json.dumps({"vim_uuid": "test_id", "metrics_list_request": "metric_details"})

        # Call the metric functionality and check list functionality
        self.metrics.metric_calls(message)
        list_metrics.assert_called_with(mock.ANY, mock.ANY, "metric_details")

    @mock.patch.object(Common, "get_auth_token", mock.Mock())
    @mock.patch.object(Common, 'get_endpoint', mock.Mock())
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
        message.value = json.dumps({"vim_uuid": "test_id",
                                    "metric_create":
                                        {"metric_name": "my_metric",
                                         "resource_uuid": "my_r_id"}})

        # Call metric functionality and confirm no function is called
        # Gnocchi does not support updating a metric configuration
        self.metrics.metric_calls(message)
        config_metric.assert_not_called()
        list_metrics.assert_not_called()
        delete_metric.assert_not_called()
        read_data.assert_not_called()

    @mock.patch.object(Common, "get_auth_token", mock.Mock())
    @mock.patch.object(Common, 'get_endpoint', mock.Mock())
    @mock.patch.object(metric_req.Metrics, "configure_metric")
    def test_config_metric_key(self, config_metric):
        """Test the functionality for a create metric request."""
        # Mock a message with create metric key and value
        message = Message()
        message.key = "create_metric_request"
        message.value = json.dumps({"vim_uuid": "test_id", "metric_create": "metric_details"})

        # Call metric functionality and check config metric
        config_metric.return_value = "metric_id", "resource_id", True
        self.metrics.metric_calls(message)
        config_metric.assert_called_with(mock.ANY, mock.ANY, "metric_details")

    @mock.patch.object(Common, "get_auth_token", mock.Mock())
    @mock.patch.object(Common, 'get_endpoint', mock.Mock())
    @mock.patch.object(metric_req.Metrics, "read_metric_data")
    def test_read_data_key(self, read_data):
        """Test the functionality for a read metric data request."""
        # Mock a message with a read data key and value
        message = Message()
        message.key = "read_metric_data_request"
        message.value = json.dumps({"vim_uuid": "test_id", "alarm_uuid": "alarm_id"})

        # Call metric functionality and check read data metrics
        read_data.return_value = "time_stamps", "data_values"
        self.metrics.metric_calls(message)
        read_data.assert_called_with(
            mock.ANY, mock.ANY, json.loads(message.value))
