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

# Mock auth_token and endpoint
endpoint = mock.ANY
auth_token = mock.ANY

# Mock a valid metric list for some tests, and a resultant list
metric_list = [{"name": "disk.write.requests",
                "id": "metric_id",
                "unit": "units",
                "resource_id": "r_id"}]
result_list = ["metric_id", "r_id", "units", "disk_write_ops"]


class Response(object):
    """Mock a response object for requests."""

    def __init__(self):
        """Initialise test and status code values."""
        self.text = json.dumps([{"id": "test_id"}])
        self.status_code = "STATUS_CODE"


def perform_request_side_effect(*args, **kwargs):
    resp = Response()
    if 'marker' in args[0]:
        resp.text = json.dumps([])
    return resp


class TestMetricCalls(unittest.TestCase):
    """Integration test for metric request keys."""

    def setUp(self):
        """Setup the tests for metric request keys."""
        super(TestMetricCalls, self).setUp()
        self.metrics = metric_req.Metrics()
        self.metrics._common = Common()

    @mock.patch.object(metric_req.Metrics, "get_metric_name")
    @mock.patch.object(metric_req.Metrics, "get_metric_id")
    @mock.patch.object(Common, "perform_request")
    def test_invalid_config_metric_req(
            self, perf_req, get_metric, get_metric_name):
        """Test the configure metric function, for an invalid metric."""
        # Test invalid configuration for creating a metric
        values = {"metric_details": "invalid_metric"}

        m_id, r_id, status = self.metrics.configure_metric(
            endpoint, auth_token, values)

        perf_req.assert_not_called()
        self.assertEqual(m_id, None)
        self.assertEqual(r_id, None)
        self.assertEqual(status, False)

        # Test with an invalid metric name, will not perform request
        values = {"resource_uuid": "r_id"}
        get_metric_name.return_value = "metric_name", None

        m_id, r_id, status = self.metrics.configure_metric(
            endpoint, auth_token, values)

        perf_req.assert_not_called()
        self.assertEqual(m_id, None)
        self.assertEqual(r_id, "r_id")
        self.assertEqual(status, False)
        get_metric_name.reset_mock()

        # If metric exists, it won't be recreated
        get_metric_name.return_value = "metric_name", "norm_name"
        get_metric.return_value = "metric_id"

        m_id, r_id, status = self.metrics.configure_metric(
            endpoint, auth_token, values)

        perf_req.assert_not_called()
        self.assertEqual(m_id, "metric_id")
        self.assertEqual(r_id, "r_id")
        self.assertEqual(status, False)

    @mock.patch.object(metric_req.Metrics, "get_metric_name")
    @mock.patch.object(metric_req.Metrics, "get_metric_id")
    @mock.patch.object(Common, "perform_request")
    def test_valid_config_metric_req(
            self, perf_req, get_metric, get_metric_name):
        """Test the configure metric function, for a valid metric."""
        # Test valid configuration and payload for creating a metric
        values = {"resource_uuid": "r_id",
                  "metric_unit": "units"}
        get_metric_name.return_value = "norm_name", "metric_name"
        get_metric.return_value = None
        payload = {"id": "r_id",
                   "metrics": {"metric_name":
                                   {"archive_policy_name": "high",
                                    "name": "metric_name",
                                    "unit": "units"}}}

        self.metrics.configure_metric(endpoint, auth_token, values)

        perf_req.assert_called_with(
            "<ANY>/v1/resource/generic", auth_token, req_type="post",
            payload=json.dumps(payload))

    @mock.patch.object(Common, "perform_request")
    def test_delete_metric_req(self, perf_req):
        """Test the delete metric function."""
        self.metrics.delete_metric(endpoint, auth_token, "metric_id")

        perf_req.assert_called_with(
            "<ANY>/v1/metric/metric_id", auth_token, req_type="delete")

    @mock.patch.object(Common, "perform_request")
    def test_delete_metric_invalid_status(self, perf_req):
        """Test invalid response for delete request."""
        perf_req.return_value = "404"

        status = self.metrics.delete_metric(endpoint, auth_token, "metric_id")

        self.assertEqual(status, False)

    @mock.patch.object(metric_req.Metrics, "response_list")
    @mock.patch.object(Common, "perform_request")
    def test_complete_list_metric_req(self, perf_req, resp_list):
        """Test the complete list metric function."""
        # Test listing metrics without any configuration options
        values = {}
        perf_req.side_effect = perform_request_side_effect
        self.metrics.list_metrics(endpoint, auth_token, values)

        perf_req.assert_any_call(
            "<ANY>/v1/metric?sort=name:asc", auth_token, req_type="get")
        resp_list.assert_called_with([{u'id': u'test_id'}])

    @mock.patch.object(metric_req.Metrics, "response_list")
    @mock.patch.object(Common, "perform_request")
    def test_resource_list_metric_req(self, perf_req, resp_list):
        """Test the resource list metric function."""
        # Test listing metrics with a resource id specified
        values = {"resource_uuid": "resource_id"}
        perf_req.side_effect = perform_request_side_effect
        self.metrics.list_metrics(endpoint, auth_token, values)

        perf_req.assert_any_call(
            "<ANY>/v1/metric?sort=name:asc", auth_token, req_type="get")
        resp_list.assert_called_with(
            [{u'id': u'test_id'}], resource="resource_id")

    @mock.patch.object(metric_req.Metrics, "response_list")
    @mock.patch.object(Common, "perform_request")
    def test_name_list_metric_req(self, perf_req, resp_list):
        """Test the metric_name list metric function."""
        # Test listing metrics with a metric_name specified
        values = {"metric_name": "disk_write_bytes"}
        perf_req.side_effect = perform_request_side_effect
        self.metrics.list_metrics(endpoint, auth_token, values)

        perf_req.assert_any_call(
            "<ANY>/v1/metric?sort=name:asc", auth_token, req_type="get")
        resp_list.assert_called_with(
            [{u'id': u'test_id'}], metric_name="disk_write_bytes")

    @mock.patch.object(metric_req.Metrics, "response_list")
    @mock.patch.object(Common, "perform_request")
    def test_combined_list_metric_req(self, perf_req, resp_list):
        """Test the combined resource and metric list metric function."""
        # Test listing metrics with a resource id and metric name specified

        values = {"resource_uuid": "resource_id",
                  "metric_name": "packets_sent"}
        perf_req.side_effect = perform_request_side_effect
        self.metrics.list_metrics(endpoint, auth_token, values)

        perf_req.assert_any_call(
            "<ANY>/v1/metric?sort=name:asc", auth_token, req_type="get")
        resp_list.assert_called_with(
            [{u'id': u'test_id'}], resource="resource_id",
            metric_name="packets_sent")

    @mock.patch.object(Common, "perform_request")
    def test_get_metric_id(self, perf_req):
        """Test get_metric_id function."""
        self.metrics.get_metric_id(endpoint, auth_token, "my_metric", "r_id")

        perf_req.assert_called_with(
            "<ANY>/v1/resource/generic/r_id", auth_token, req_type="get")

    def test_get_metric_name(self):
        """Test the result from the get_metric_name function."""
        # test with a valid metric_name
        values = {"metric_name": "disk_write_ops"}

        metric_name, norm_name = self.metrics.get_metric_name(values)

        self.assertEqual(metric_name, "disk_write_ops")
        self.assertEqual(norm_name, "disk.write.requests")

        # test with an invalid metric name
        values = {"metric_name": "my_invalid_metric"}

        metric_name, norm_name = self.metrics.get_metric_name(values)

        self.assertEqual(metric_name, "my_invalid_metric")
        self.assertEqual(norm_name, None)

    @mock.patch.object(metric_req.Metrics, "get_metric_id")
    @mock.patch.object(Common, "perform_request")
    def test_valid_read_data_req(self, perf_req, get_metric):
        """Test the read metric data function, for a valid call."""
        values = {"metric_name": "disk_write_ops",
                  "resource_uuid": "resource_id",
                  "collection_unit": "DAY",
                  "collection_period": 1}

        get_metric.return_value = "metric_id"
        self.metrics.read_metric_data(endpoint, auth_token, values)

        perf_req.assert_called_once()

    @mock.patch.object(Common, "perform_request")
    def test_invalid_read_data_req(self, perf_req):
        """Test the read metric data function, for an invalid call."""
        # Teo empty lists wil be returned because the values are invalid
        values = {}

        times, data = self.metrics.read_metric_data(
            endpoint, auth_token, values)

        self.assertEqual(times, [])
        self.assertEqual(data, [])

    def test_complete_response_list(self):
        """Test the response list function for formating metric lists."""
        # Mock a list for testing purposes, with valid OSM metric
        resp_list = self.metrics.response_list(metric_list)

        # Check for the expected values in the resulting list
        for l in result_list:
            self.assertIn(l, resp_list[0].values())

    def test_name_response_list(self):
        """Test the response list with metric name configured."""
        # Mock the metric name to test a metric name list
        # Test with a name that is not in the list
        invalid_name = "my_metric"
        resp_list = self.metrics.response_list(
            metric_list, metric_name=invalid_name)

        self.assertEqual(resp_list, [])

        # Test with a name on the list
        valid_name = "disk_write_ops"
        resp_list = self.metrics.response_list(
            metric_list, metric_name=valid_name)

        # Check for the expected values in the resulting list
        for l in result_list:
            self.assertIn(l, resp_list[0].values())

    def test_resource_response_list(self):
        """Test the response list with resource_id configured."""
        # Mock a resource_id to test a resource list
        # Test with resource not on the list
        invalid_id = "mock_resource"
        resp_list = self.metrics.response_list(metric_list, resource=invalid_id)

        self.assertEqual(resp_list, [])

        # Test with a resource on the list
        valid_id = "r_id"
        resp_list = self.metrics.response_list(metric_list, resource=valid_id)

        # Check for the expected values in the resulting list
        for l in result_list:
            self.assertIn(l, resp_list[0].values())

    def test_combined_response_list(self):
        """Test the response list function with resource_id and metric_name."""
        # Test for a combined resource and name list
        # resource and name are on the list
        valid_name = "disk_write_ops"
        valid_id = "r_id"
        resp_list = self.metrics.response_list(
            metric_list, metric_name=valid_name, resource=valid_id)

        # Check for the expected values in the resulting list
        for l in result_list:
            self.assertIn(l, resp_list[0].values())

        # resource not on list
        invalid_id = "mock_resource"
        resp_list = self.metrics.response_list(
            metric_list, metric_name=valid_name, resource=invalid_id)

        self.assertEqual(resp_list, [])

        # metric name not on list
        invalid_name = "mock_metric"
        resp_list = self.metrics.response_list(
            metric_list, metric_name=invalid_name, resource=valid_id)

        self.assertEqual(resp_list, [])
