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

import unittest

from BaseHTTPServer import BaseHTTPRequestHandler

import mock

from osm_mon.core.message_bus.producer import KafkaProducer

from osm_mon.plugins.OpenStack.Aodh.alarming import Alarming
from osm_mon.plugins.OpenStack.common import Common
from osm_mon.plugins.OpenStack.response import OpenStack_Response
from osm_mon.plugins.OpenStack.settings import Config

# Mock data from post request
post_data = json.dumps({"severity": "critical",
                        "alarm_name": "my_alarm",
                        "current": "current_state",
                        "alarm_id": "my_alarm_id",
                        "reason": "Threshold has been broken",
                        "reason_data": {"count": 1,
                                        "most_recent": "null",
                                        "type": "threshold",
                                        "disposition": "unknown"},
                        "previous": "previous_state"})

valid_get_resp = '{"gnocchi_resources_threshold_rule":\
                   {"resource_id": "my_resource_id"}}'

invalid_get_resp = '{"gnocchi_resources_threshold_rule":\
                     {"resource_id": "None"}}'

valid_notify_resp = '{"notify_details": {"status": "current_state",\
                                         "severity": "critical",\
                                         "resource_uuid": "my_resource_id",\
                                         "alarm_uuid": "my_alarm_id",\
                                         "vim_type": "OpenStack",\
                                         "start_date": "dd-mm-yyyy 00:00"},\
                      "schema_version": "1.0",\
                      "schema_type": "notify_alarm"}'

invalid_notify_resp = '{"notify_details": {"invalid":"mock_details"}'


class Response(object):
    """Mock a response class for generating responses."""

    def __init__(self, text):
        """Initialise a mock response with a text attribute."""
        self.text = text


class NotifierHandler(BaseHTTPRequestHandler):
    """Mock the NotifierHandler class for testing purposes."""

    def __init__(self, request, client_address, server):
        """Initilase mock NotifierHandler."""
        self.request = request
        self.client_address = client_address
        self.server = server
        self.setup()
        try:
            self.handle()
        finally:
            self.finish()

    def setup(self):
        """Mock setup function."""
        pass

    def handle(self):
        """Mock handle function."""
        pass

    def finish(self):
        """Mock finish function."""
        pass

    def _set_headers(self):
        """Mock getting the request headers."""
        pass

    def do_GET(self):
        """Mock functionality for GET request."""
        self._set_headers()
        pass

    def do_POST(self):
        """Mock functionality for a POST request."""
        self._set_headers()
        self.notify_alarm(json.loads(post_data))

    def notify_alarm(self, values):
        """Mock the notify_alarm functionality to generate a valid response."""
        config = Config.instance()
        config.read_environ("aodh")
        self._alarming = Alarming()
        self._common = Common()
        self._response = OpenStack_Response()
        self._producer = KafkaProducer('alarm_response')
        alarm_id = values['alarm_id']

        auth_token = self._common._authenticate()
        endpoint = self._common.get_endpoint("alarming")

        # If authenticated generate and send response message
        if (auth_token is not None and endpoint is not None):
            url = "{}/v2/alarms/%s".format(endpoint) % alarm_id

            # Get the resource_id of the triggered alarm and the date
            result = self._common._perform_request(
                url, auth_token, req_type="get")
            alarm_details = json.loads(result.text)
            gnocchi_rule = alarm_details['gnocchi_resources_threshold_rule']
            resource_id = gnocchi_rule['resource_id']
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


class TestNotifier(unittest.TestCase):
    """Test the NotifierHandler class for requests from aodh."""

    def setUp(self):
        """Setup tests."""
        super(TestNotifier, self).setUp()
        self.handler = NotifierHandler(
            "mock_request", "mock_address", "mock_server")

    @mock.patch.object(NotifierHandler, "_set_headers")
    def test_do_GET(self, set_head):
        """Test do_GET, generates headers for get request."""
        self.handler.do_GET()

        set_head.assert_called_once

    @mock.patch.object(NotifierHandler, "notify_alarm")
    @mock.patch.object(NotifierHandler, "_set_headers")
    def test_do_POST(self, set_head, notify):
        """Test do_POST functionality for a POST request."""
        self.handler.do_POST()

        set_head.assert_called_once
        notify.assert_called_with(json.loads(post_data))

    @mock.patch.object(Common, "get_endpoint")
    @mock.patch.object(Common, "_authenticate")
    @mock.patch.object(Common, "_perform_request")
    def test_notify_alarm_unauth(self, perf_req, auth, endpoint):
        """Test notify alarm when not authenticated with keystone."""
        # Response request will not be performed unless there is a valid
        # auth_token and endpoint
        # Invalid auth_token and endpoint
        auth.return_value = None
        endpoint.return_value = None
        self.handler.notify_alarm(json.loads(post_data))

        perf_req.assert_not_called

        # Valid endpoint
        auth.return_value = None
        endpoint.return_value = "my_endpoint"
        self.handler.notify_alarm(json.loads(post_data))

        perf_req.assert_not_called

        # Valid auth_token
        auth.return_value = "my_auth_token"
        endpoint.return_value = None
        self.handler.notify_alarm(json.loads(post_data))

        perf_req.assert_not_called

    @mock.patch.object(Common, "get_endpoint")
    @mock.patch.object(OpenStack_Response, "generate_response")
    @mock.patch.object(Common, "_authenticate")
    @mock.patch.object(Common, "_perform_request")
    def test_notify_alarm_invalid_alarm(self, perf_req, auth, resp, endpoint):
        """Test valid authentication, invalid alarm details."""
        # Mock valid auth_token and endpoint
        auth.return_value = "my_auth_token"
        endpoint.return_value = "my_endpoint"
        perf_req.return_value = Response(invalid_get_resp)

        self.handler.notify_alarm(json.loads(post_data))

        # Response is not generated
        resp.assert_not_called

    @mock.patch.object(Common, "get_endpoint")
    @mock.patch.object(OpenStack_Response, "generate_response")
    @mock.patch.object(Common, "_authenticate")
    @mock.patch.object(Common, "_perform_request")
    def test_notify_alarm_resp_call(self, perf_req, auth, response, endpoint):
        """Test notify_alarm tries to generate a response for SO."""
        # Mock valid auth token and endpoint, valid response from aodh
        auth.return_value = "my_auth_token"
        endpoint.returm_value = "my_endpoint"
        perf_req.return_value = Response(valid_get_resp)
        self.handler.notify_alarm(json.loads(post_data))

        response.assert_called_with('notify_alarm', a_id="my_alarm_id",
                                    r_id="my_resource_id", sev="critical",
                                    date="dd-mm-yyyy 00:00",
                                    state="current_state",
                                    vim_type="OpenStack")

    @mock.patch.object(Common, "get_endpoint")
    @mock.patch.object(KafkaProducer, "notify_alarm")
    @mock.patch.object(OpenStack_Response, "generate_response")
    @mock.patch.object(Common, "_authenticate")
    @mock.patch.object(Common, "_perform_request")
    def test_notify_alarm_invalid_resp(
            self, perf_req, auth, response, notify, endpoint):
        """Test the notify_alarm function, sends response to the producer."""
        # Generate return values for valid notify_alarm operation
        auth.return_value = "my_auth_token"
        endpoint.return_value = "my_endpoint"
        perf_req.return_value = Response(valid_get_resp)
        response.return_value = invalid_notify_resp

        self.handler.notify_alarm(json.loads(post_data))

        notify.assert_not_called

    @mock.patch.object(Common, "get_endpoint")
    @mock.patch.object(KafkaProducer, "notify_alarm")
    @mock.patch.object(OpenStack_Response, "generate_response")
    @mock.patch.object(Common, "_authenticate")
    @mock.patch.object(Common, "_perform_request")
    def test_notify_alarm_valid_resp(
            self, perf_req, auth, response, notify, endpoint):
        """Test the notify_alarm function, sends response to the producer."""
        # Generate return values for valid notify_alarm operation
        auth.return_value = "my_auth_token"
        endpoint.return_value = "my_endpoint"
        perf_req.return_value = Response(valid_get_resp)
        response.return_value = valid_notify_resp

        self.handler.notify_alarm(json.loads(post_data))

        notify.assert_called_with(
            "notify_alarm", valid_notify_resp, "alarm_response")
