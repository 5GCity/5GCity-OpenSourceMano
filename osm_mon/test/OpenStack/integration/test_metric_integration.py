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
"""Test an end to end Openstack metric requests."""

import json

import logging
import unittest

from kafka.errors import KafkaError

from osm_mon.core.message_bus.producer import KafkaProducer as prod

from kafka import KafkaConsumer
from kafka import KafkaProducer

import mock

from osm_mon.plugins.OpenStack import response

from osm_mon.plugins.OpenStack.Gnocchi import metrics

from osm_mon.plugins.OpenStack.common import Common

log = logging.getLogger(__name__)


class MetricIntegrationTest(unittest.TestCase):
    def setUp(self):
        # Set up common and alarming class instances
        self.metric_req = metrics.Metrics()
        self.openstack_auth = Common()

        try:
            self.producer = KafkaProducer(bootstrap_servers='localhost:9092',
                                          key_serializer=str.encode,
                                          value_serializer=str.encode
                                          )
            self.req_consumer = KafkaConsumer(bootstrap_servers='localhost:9092',
                                              key_deserializer=bytes.decode,
                                              value_deserializer=bytes.decode,
                                              auto_offset_reset='earliest',
                                              consumer_timeout_ms=60000)
            self.req_consumer.subscribe(['metric_request'])
        except KafkaError:
            self.skipTest('Kafka server not present.')

    @mock.patch.object(Common, "get_auth_token", mock.Mock())
    @mock.patch.object(Common, "get_endpoint", mock.Mock())
    @mock.patch.object(metrics.Metrics, "configure_metric")
    @mock.patch.object(prod, "create_metrics_resp")
    @mock.patch.object(response.OpenStack_Response, "generate_response")
    def test_create_metric_req(self, resp, create_resp, config_metric):
        """Test Gnocchi create metric request message from producer."""
        # Set-up message, producer and consumer for tests
        payload = {"vim_type": "OpenSTACK",
                   "vim_uuid": "1",
                   "correlation_id": 123,
                   "metric_create":
                       {"metric_name": "cpu_utilization",
                        "resource_uuid": "resource_id"}}

        self.producer.send('metric_request', key="create_metric_request",
                           value=json.dumps(payload))

        for message in self.req_consumer:
            # Check the vim desired by the message
            vim_type = json.loads(message.value)["vim_type"].lower()
            if vim_type == "openstack":
                # A valid metric is created
                config_metric.return_value = "metric_id", "resource_id", True
                self.metric_req.metric_calls(message)

                # A response message is generated and sent by MON's producer
                resp.assert_called_with(
                    'create_metric_response', status=True, cor_id=123,
                    metric_id="metric_id", r_id="resource_id")
                create_resp.assert_called_with(
                    'create_metric_response', resp.return_value)

                return
        self.fail("No message received in consumer")

    @mock.patch.object(Common, "get_auth_token", mock.Mock())
    @mock.patch.object(Common, "get_endpoint", mock.Mock())
    @mock.patch.object(metrics.Metrics, "delete_metric")
    @mock.patch.object(prod, "delete_metric_response")
    @mock.patch.object(response.OpenStack_Response, "generate_response")
    def test_delete_metric_req(self, resp, del_resp, del_metric):
        """Test Gnocchi delete metric request message from producer."""
        # Set-up message, producer and consumer for tests
        payload = {"vim_type": "OpenSTACK",
                   "vim_uuid": "1",
                   "correlation_id": 123,
                   "metric_name": "cpu_utilization",
                   "resource_uuid": "resource_id"}

        self.producer.send('metric_request', key="delete_metric_request",
                           value=json.dumps(payload))

        for message in self.req_consumer:
            if message.key == "delete_metric_request":
                # Metric has been deleted
                del_metric.return_value = True
                self.metric_req.metric_calls(message)

                # A response message is generated and sent by MON's producer
                resp.assert_called_with(
                    'delete_metric_response', m_id=None,
                    m_name="cpu_utilization", status=True, r_id="resource_id",
                    cor_id=123)
                del_resp.assert_called_with(
                    'delete_metric_response', resp.return_value)

                return
        self.fail("No message received in consumer")

    @mock.patch.object(Common, "get_auth_token", mock.Mock())
    @mock.patch.object(Common, "get_endpoint", mock.Mock())
    @mock.patch.object(metrics.Metrics, "read_metric_data")
    @mock.patch.object(prod, "read_metric_data_response")
    @mock.patch.object(response.OpenStack_Response, "generate_response")
    def test_read_metric_data_req(self, resp, read_resp, read_data):
        """Test Gnocchi read metric data request message from producer."""
        # Set-up message, producer and consumer for tests
        payload = {"vim_type": "OpenSTACK",
                   "vim_uuid": "test_id",
                   "correlation_id": 123,
                   "metric_name": "cpu_utilization",
                   "resource_uuid": "resource_id"}

        self.producer.send('metric_request', key="read_metric_data_request",
                           value=json.dumps(payload))

        for message in self.req_consumer:
            # Check the vim desired by the message
            if message.key == "read_metric_data_request":
                # Mock empty lists generated by the request message
                read_data.return_value = [], []
                self.metric_req.metric_calls(message)

                # A response message is generated and sent by MON's producer
                resp.assert_called_with(
                    'read_metric_data_response', m_id=None,
                    m_name="cpu_utilization", r_id="resource_id", cor_id=123, times=[],
                    metrics=[])
                read_resp.assert_called_with(
                    'read_metric_data_response', resp.return_value)

                return
        self.fail("No message received in consumer")

    @mock.patch.object(Common, "get_auth_token", mock.Mock())
    @mock.patch.object(Common, "get_endpoint", mock.Mock())
    @mock.patch.object(metrics.Metrics, "list_metrics")
    @mock.patch.object(prod, "list_metric_response")
    @mock.patch.object(response.OpenStack_Response, "generate_response")
    def test_list_metrics_req(self, resp, list_resp, list_metrics):
        """Test Gnocchi list metrics request message from producer."""
        # Set-up message, producer and consumer for tests
        payload = {"vim_type": "OpenSTACK",
                   "vim_uuid": "1",
                   "metrics_list_request":
                       {"correlation_id": 123, }}

        self.producer.send('metric_request', key="list_metric_request",
                           value=json.dumps(payload))

        for message in self.req_consumer:
            # Check the vim desired by the message
            if message.key == "list_metric_request":
                # Mock an empty list generated by the request
                list_metrics.return_value = []
                self.metric_req.metric_calls(message)

                # A response message is generated and sent by MON's producer
                resp.assert_called_with(
                    'list_metric_response', m_list=[], cor_id=123)
                list_resp.assert_called_with(
                    'list_metric_response', resp.return_value)

                return
        self.fail("No message received in consumer")

    @mock.patch.object(Common, "get_auth_token", mock.Mock())
    @mock.patch.object(Common, "get_endpoint", mock.Mock())
    @mock.patch.object(metrics.Metrics, "get_metric_id")
    @mock.patch.object(prod, "update_metric_response")
    @mock.patch.object(response.OpenStack_Response, "generate_response")
    def test_update_metrics_req(self, resp, update_resp, get_id):
        """Test Gnocchi update metric request message from KafkaProducer."""
        # Set-up message, producer and consumer for tests
        payload = {"vim_type": "OpenSTACK",
                   "vim_uuid": "test_id",
                   "correlation_id": 123,
                   "metric_create":
                       {"metric_name": "my_metric",
                        "resource_uuid": "resource_id", }}

        self.producer.send('metric_request', key="update_metric_request",
                           value=json.dumps(payload))

        for message in self.req_consumer:
            # Check the vim desired by the message
            if message.key == "update_metric_request":
                # Gnocchi doesn't support metric updates
                get_id.return_value = "metric_id"
                self.metric_req.metric_calls(message)

                # Response message is generated and sent via MON's producer
                # No metric update has taken place
                resp.assert_called_with(
                    'update_metric_response', status=False, cor_id=123,
                    r_id="resource_id", m_id="metric_id")
                update_resp.assert_called_with(
                    'update_metric_response', resp.return_value)

                return
        self.fail("No message received in consumer")
