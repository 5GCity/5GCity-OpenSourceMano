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
##
"""Tests for all common OpenStack methods."""

import json
import logging
import socket
import unittest
from threading import Thread

import mock
import requests
from six.moves.BaseHTTPServer import BaseHTTPRequestHandler
from six.moves.BaseHTTPServer import HTTPServer

from osm_mon.core.message_bus.producer import KafkaProducer
from osm_mon.core.settings import Config
from osm_mon.plugins.OpenStack.Aodh.alarming import Alarming
from osm_mon.plugins.OpenStack.common import Common
from osm_mon.plugins.OpenStack.response import OpenStack_Response

log = logging.getLogger(__name__)

# Create an instance of the common openstack class, producer and consumer
openstack_auth = Common()

# Mock a valid get_response for alarm details
valid_get_resp = '{"gnocchi_resources_threshold_rule":\
                  {"resource_id": "my_resource_id"}}'


class MockResponse(object):
    """Mock a response class for generating responses."""

    def __init__(self, text):
        """Initialise a mock response with a text attribute."""
        self.text = text


class MockNotifierHandler(BaseHTTPRequestHandler):
    """Mock the NotifierHandler class for testing purposes."""

    def _set_headers(self):
        """Set the headers for a request."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        """Mock functionality for GET request."""
        #        self.send_response(requests.codes.ok)
        self._set_headers()
        pass

    def do_POST(self):
        """Mock functionality for a POST request."""
        self._set_headers()
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        self.notify_alarm(json.loads(post_data))

    def notify_alarm(self, values):
        """Mock the notify_alarm functionality to generate a valid response."""
        config = Config.instance()
        config.read_environ()
        self._alarming = Alarming()
        self._common = Common()
        self._response = OpenStack_Response()
        self._producer = KafkaProducer('alarm_response')
        alarm_id = values['alarm_id']

        auth_token = Common.get_auth_token('test_id')
        endpoint = Common.get_endpoint('alarming', 'test_id')

        # If authenticated generate and send response message
        if auth_token is not None and endpoint is not None:
            url = "{}/v2/alarms/%s".format(endpoint) % alarm_id

            # Get the resource_id of the triggered alarm and the date
            result = Common.perform_request(
                url, auth_token, req_type="get")
            alarm_details = json.loads(result.text)
            gnocchi_rule = alarm_details['gnocchi_resources_threshold_rule']
            resource_id = gnocchi_rule['resource_id']
            # Mock a date for testing purposes
            a_date = "dd-mm-yyyy 00:00"

            # Process an alarm notification if resource_id is valid
            if resource_id is not None:
                # Try generate and send response
                try:
                    resp_message = self._response.generate_response(
                        'notify_alarm', a_id=alarm_id,
                        r_id=resource_id,
                        sev=values['severity'], date=a_date,
                        state=values['current'], vim_type="OpenStack")
                    self._producer.notify_alarm(
                        'notify_alarm', resp_message, 'alarm_response')
                except Exception:
                    pass


def get_free_port():
    """Function to get a free port to run the test webserver on."""
    s = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    address, port = s.getsockname()
    s.close()
    return port


# Create the webserver, port and run it on its own thread
mock_server_port = get_free_port()
mock_server = HTTPServer(('localhost', mock_server_port), MockNotifierHandler)
mock_server_thread = Thread(target=mock_server.serve_forever)
mock_server_thread.setDaemon(True)
mock_server_thread.start()


def test_do_get():
    """Integration test for get request on notifier webserver."""
    url = 'http://localhost:{port}/users'.format(port=mock_server_port)

    # Send a request to the mock API server and store the response.
    response = requests.get(url)

    # Confirm that the request-response cycle completed successfully.
    assert response.ok


class AlarmNotificationTest(unittest.TestCase):
    @mock.patch.object(KafkaProducer, "notify_alarm")
    @mock.patch.object(OpenStack_Response, "generate_response")
    @mock.patch.object(Common, "perform_request")
    @mock.patch.object(Common, "get_endpoint")
    @mock.patch.object(Common, "get_auth_token")
    def test_post_notify_alarm(self, auth, endpoint, perf_req, resp, notify):
        """Integration test for notify_alarm."""
        url = 'http://localhost:{port}/users'.format(port=mock_server_port)
        payload = {"severity": "critical",
                   "alarm_name": "my_alarm",
                   "current": "current_state",
                   "alarm_id": "my_alarm_id",
                   "reason": "Threshold has been broken",
                   "reason_data": {"count": 1,
                                   "most_recent": "null",
                                   "type": "threshold",
                                   "disposition": "unknown"},
                   "previous": "previous_state"}

        # Mock authenticate and request response for testing
        auth.return_value = "my_auth_token"
        endpoint.return_value = "my_endpoint"
        perf_req.return_value = MockResponse(valid_get_resp)

        # Generate a post request for testing
        response = requests.post(url, json.dumps(payload))
        self.assertEqual(response.status_code, 200)
        # A response message is generated with the following details
        resp.assert_called_with(
            "notify_alarm", a_id="my_alarm_id", r_id="my_resource_id",
            sev="critical", date='dd-mm-yyyy 00:00', state="current_state",
            vim_type="OpenStack")

        # Response message is sent back to the SO via MON's producer
        notify.assert_called_with("notify_alarm", mock.ANY, "alarm_response")
