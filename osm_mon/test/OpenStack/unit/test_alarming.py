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

from osm_mon.core.settings import Config
from osm_mon.plugins.OpenStack.Aodh import alarming as alarm_req
from osm_mon.plugins.OpenStack.common import Common

log = logging.getLogger(__name__)

auth_token = mock.ANY
alarm_endpoint = "alarm_endpoint"
metric_endpoint = "metric_endpoint"


class Response(object):
    """Mock a response message class."""

    def __init__(self, result):
        """Initialise the response text and status code."""
        self.text = json.dumps(result)
        self.status_code = "MOCK_STATUS_CODE"


class TestAlarming(unittest.TestCase):
    """Tests for alarming class functions."""

    maxDiff = None

    def setUp(self):
        """Setup for tests."""
        super(TestAlarming, self).setUp()
        self.alarming = alarm_req.Alarming()

    @mock.patch.object(alarm_req.Alarming, "check_payload")
    @mock.patch.object(alarm_req.Alarming, "check_for_metric")
    @mock.patch.object(Common, "perform_request")
    def test_config_invalid_alarm_req(self, perf_req, check_metric, check_pay):
        """Test configure an invalid alarm request."""
        # Configuring with invalid alarm name results in failure
        values = {"alarm_name": "my_alarm",
                  "metric_name": "my_metric",
                  "resource_uuid": "my_r_id"}
        self.alarming.configure_alarm(alarm_endpoint, metric_endpoint, auth_token, values, {})
        perf_req.assert_not_called()
        perf_req.reset_mock()

        # Correct alarm_name will check for metric in Gnocchi
        # If there isn't one an alarm won;t be created
        values = {"alarm_name": "disk_write_ops",
                  "metric_name": "disk_write_ops",
                  "resource_uuid": "my_r_id"}

        check_metric.return_value = None

        self.alarming.configure_alarm(alarm_endpoint, metric_endpoint, auth_token, values, {})
        perf_req.assert_not_called()

    @mock.patch.object(alarm_req.Alarming, "check_payload")
    @mock.patch.object(alarm_req.Alarming, "check_for_metric")
    @mock.patch.object(Common, "perform_request")
    def test_config_valid_alarm_req(self, perf_req, check_metric, check_pay):
        """Test config a valid alarm."""
        # Correct alarm_name will check for metric in Gnocchi
        # And conform that the payload is configured correctly
        values = {"alarm_name": "disk_write_ops",
                  "metric_name": "disk_write_ops",
                  "resource_uuid": "my_r_id"}

        check_metric.return_value = "my_metric_id"
        check_pay.return_value = "my_payload"

        perf_req.return_value = type('obj', (object,), {'text': '{"alarm_id":"1"}'})

        self.alarming.configure_alarm(alarm_endpoint, metric_endpoint, auth_token, values, {})
        perf_req.assert_called_with(
            "alarm_endpoint/v2/alarms/", auth_token,
            req_type="post", payload="my_payload")

    @mock.patch.object(Common, "perform_request")
    def test_delete_alarm_req(self, perf_req):
        """Test delete alarm request."""
        self.alarming.delete_alarm(alarm_endpoint, auth_token, "my_alarm_id")

        perf_req.assert_called_with(
            "alarm_endpoint/v2/alarms/my_alarm_id", auth_token, req_type="delete")

    @mock.patch.object(Common, "perform_request")
    def test_invalid_list_alarm_req(self, perf_req):
        """Test invalid list alarm_req."""
        # Request will not be performed with out a resoure_id
        list_details = {"mock_details": "invalid_details"}
        self.alarming.list_alarms(alarm_endpoint, auth_token, list_details)

        perf_req.assert_not_called()

    @mock.patch.object(Common, "perform_request")
    def test_valid_list_alarm_req(self, perf_req):
        """Test valid list alarm request."""
        # Minimum requirement for an alarm list is resource_id
        list_details = {"resource_uuid": "mock_r_id"}
        self.alarming.list_alarms(alarm_endpoint, auth_token, list_details)

        perf_req.assert_called_with(
            "alarm_endpoint/v2/alarms/", auth_token, req_type="get")
        perf_req.reset_mock()

        # Check list with alarm_name defined
        list_details = {"resource_uuid": "mock_r_id",
                        "alarm_name": "my_alarm",
                        "severity": "critical"}
        self.alarming.list_alarms(alarm_endpoint, auth_token, list_details)

        perf_req.assert_called_with(
            "alarm_endpoint/v2/alarms/", auth_token, req_type="get")

    @mock.patch.object(Common, "perform_request")
    def test_ack_alarm_req(self, perf_req):
        """Test update alarm state for acknowledge alarm request."""
        self.alarming.update_alarm_state(alarm_endpoint, auth_token, "my_alarm_id")

        perf_req.assert_called_with(
            "alarm_endpoint/v2/alarms/my_alarm_id/state", auth_token, req_type="put",
            payload=json.dumps("ok"))

    @mock.patch.object(alarm_req.Alarming, "check_payload")
    @mock.patch.object(Common, "perform_request")
    def test_update_alarm_invalid(self, perf_req, check_pay):
        """Test update alarm with invalid get response."""
        values = {"alarm_uuid": "my_alarm_id"}

        perf_req.return_value = type('obj', (object,), {'invalid_prop': 'Invalid response'})

        self.alarming.update_alarm(alarm_endpoint, auth_token, values, {})

        perf_req.assert_called_with(mock.ANY, auth_token, req_type="get")
        check_pay.assert_not_called()

    @mock.patch.object(alarm_req.Alarming, "check_payload")
    @mock.patch.object(Common, "perform_request")
    def test_update_alarm_invalid_payload(self, perf_req, check_pay):
        """Test update alarm with invalid payload."""
        resp = Response({"name": "my_alarm",
                         "state": "alarm",
                         "gnocchi_resources_threshold_rule":
                             {"resource_id": "my_resource_id",
                              "metric": "my_metric"}})
        perf_req.return_value = resp
        check_pay.return_value = None
        values = {"alarm_uuid": "my_alarm_id"}

        self.alarming.update_alarm(alarm_endpoint, auth_token, values, {})

        perf_req.assert_called_with(mock.ANY, auth_token, req_type="get")
        self.assertEqual(perf_req.call_count, 1)

    @mock.patch.object(alarm_req.Alarming, "check_payload")
    @mock.patch.object(Common, "perform_request")
    def test_update_alarm_valid(self, perf_req, check_pay):
        """Test valid update alarm request."""
        resp = Response({"alarm_id": "1",
                         "name": "my_alarm",
                         "state": "alarm",
                         "gnocchi_resources_threshold_rule":
                             {"resource_id": "my_resource_id",
                              "metric": "disk.write.requests"}})
        perf_req.return_value = resp
        values = {"alarm_uuid": "my_alarm_id"}

        self.alarming.update_alarm(alarm_endpoint, auth_token, values, {})

        check_pay.assert_called_with(values, "disk_write_ops", "my_resource_id",
                                     "my_alarm", alarm_state="alarm")

        self.assertEqual(perf_req.call_count, 2)
        # Second call is the update request
        perf_req.assert_called_with(
            'alarm_endpoint/v2/alarms/my_alarm_id', auth_token,
            req_type="put", payload=check_pay.return_value)

    @mock.patch.object(Config, "instance")
    def test_check_valid_payload(self, cfg):
        """Test the check payload function for a valid payload."""
        values = {"severity": "warning",
                  "statistic": "COUNT",
                  "threshold_value": 12,
                  "operation": "GT",
                  "granularity": 300,
                  "resource_type": "generic"}
        cfg.return_value.OS_NOTIFIER_URI = "http://localhost:8662"
        payload = self.alarming.check_payload(
            values, "disk_write_ops", "r_id", "alarm_name")

        self.assertDictEqual(
            json.loads(payload), {"name": "alarm_name",
                                  "gnocchi_resources_threshold_rule":
                                      {"resource_id": "r_id",
                                       "metric": "disk.write.requests",
                                       "comparison_operator": "gt",
                                       "aggregation_method": "count",
                                       "threshold": 12,
                                       "granularity": 300,
                                       "resource_type": "generic"},
                                  "severity": "low",
                                  "state": "ok",
                                  "type": "gnocchi_resources_threshold",
                                  "alarm_actions": ["http://localhost:8662"]})

    @mock.patch.object(Config, "instance")
    @mock.patch.object(Common, "perform_request")
    def test_check_valid_state_payload(self, perform_req, cfg):
        """Test the check payload function for a valid payload with state."""
        values = {"severity": "warning",
                  "statistic": "COUNT",
                  "threshold_value": 12,
                  "operation": "GT",
                  "granularity": 300,
                  "resource_type": "generic"}
        cfg.return_value.OS_NOTIFIER_URI = "http://localhost:8662"
        payload = self.alarming.check_payload(
            values, "disk_write_ops", "r_id", "alarm_name", alarm_state="alarm")

        self.assertEqual(
            json.loads(payload), {"name": "alarm_name",
                                  "gnocchi_resources_threshold_rule":
                                      {"resource_id": "r_id",
                                       "metric": "disk.write.requests",
                                       "comparison_operator": "gt",
                                       "aggregation_method": "count",
                                       "threshold": 12,
                                       "granularity": 300,
                                       "resource_type": "generic"},
                                  "severity": "low",
                                  "state": "alarm",
                                  "type": "gnocchi_resources_threshold",
                                  "alarm_actions": ["http://localhost:8662"]})

    def test_check_invalid_payload(self):
        """Test the check payload function for an invalid payload."""
        values = {"alarm_values": "mock_invalid_details"}
        payload = self.alarming.check_payload(
            values, "my_metric", "r_id", "alarm_name")

        self.assertEqual(payload, None)

    @mock.patch.object(Common, "perform_request")
    def test_get_alarm_state(self, perf_req):
        """Test the get alarm state function."""
        perf_req.return_value = type('obj', (object,), {'text': '{"alarm_id":"1"}'})

        self.alarming.get_alarm_state(alarm_endpoint, auth_token, "alarm_id")

        perf_req.assert_called_with(
            "alarm_endpoint/v2/alarms/alarm_id/state", auth_token, req_type="get")

    @mock.patch.object(Common, "get_endpoint")
    @mock.patch.object(Common, "perform_request")
    def test_check_for_metric(self, perf_req, get_endpoint):
        """Test the check for metric function."""
        get_endpoint.return_value = "gnocchi_endpoint"

        self.alarming.check_for_metric(auth_token, metric_endpoint, "metric_name", "r_id")

        perf_req.assert_called_with(
            "metric_endpoint/v1/resource/generic/r_id", auth_token, req_type="get")
