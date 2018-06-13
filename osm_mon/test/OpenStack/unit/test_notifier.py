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

import mock

from osm_mon.core.database import DatabaseManager, Alarm
from osm_mon.core.message_bus.producer import KafkaProducer
from osm_mon.plugins.OpenStack.Aodh.notifier import NotifierHandler

post_data = {"severity": "critical",
             "alarm_name": "my_alarm",
             "current": "current_state",
             "alarm_id": "my_alarm_id",
             "reason": "Threshold has been broken",
             "reason_data": {"count": 1,
                             "most_recent": "null",
                             "type": "threshold",
                             "disposition": "unknown"},
             "previous": "previous_state"}


class Response(object):
    """Mock a response class for generating responses."""

    def __init__(self, text):
        """Initialise a mock response with a text attribute."""
        self.text = text


class RFile():
    def read(self, content_length):
        return post_data


class MockNotifierHandler(NotifierHandler):
    """Mock the NotifierHandler class for testing purposes."""

    def __init__(self):
        """Initialise mock NotifierHandler."""
        self.headers = {'Content-Length': '20'}
        self.rfile = RFile()

    def setup(self):
        """Mock setup function."""
        pass

    def handle(self):
        """Mock handle function."""
        pass

    def finish(self):
        """Mock finish function."""
        pass


class TestNotifier(unittest.TestCase):
    """Test the NotifierHandler class for requests from aodh."""

    def setUp(self):
        """Setup tests."""
        super(TestNotifier, self).setUp()
        self.handler = MockNotifierHandler()

    @mock.patch.object(NotifierHandler, "_set_headers")
    def test_do_GET(self, set_head):
        """Tests do_GET. Validates _set_headers has been called."""
        self.handler.do_GET()

        set_head.assert_called_once()

    @mock.patch.object(NotifierHandler, "notify_alarm")
    @mock.patch.object(NotifierHandler, "_set_headers")
    def test_do_POST(self, set_head, notify):
        """Tests do_POST. Validates notify_alarm has been called."""
        self.handler.do_POST()

        set_head.assert_called_once()
        notify.assert_called_with(json.dumps(post_data))

    @mock.patch.object(KafkaProducer, "notify_alarm")
    @mock.patch.object(DatabaseManager, "get_alarm")
    def test_notify_alarm_valid_alarm(
            self, get_alarm, notify):
        """
        Tests notify_alarm when request from OpenStack references an existing alarm in the DB.
        Validates KafkaProducer.notify_alarm has been called.
        """
        # Generate return values for valid notify_alarm operation
        mock_alarm = Alarm()
        get_alarm.return_value = mock_alarm

        self.handler.notify_alarm(post_data)

        notify.assert_called_with("notify_alarm", mock.ANY)

    @mock.patch.object(KafkaProducer, "notify_alarm")
    @mock.patch.object(DatabaseManager, "get_alarm")
    def test_notify_alarm_invalid_alarm(
            self, get_alarm, notify):
        """
        Tests notify_alarm when request from OpenStack references a non existing alarm in the DB.
        Validates Exception is thrown and KafkaProducer.notify_alarm has not been called.
        """
        # Generate return values for valid notify_alarm operation
        get_alarm.return_value = None

        with self.assertRaises(Exception):
            self.handler.notify_alarm(post_data)
        notify.assert_not_called()
