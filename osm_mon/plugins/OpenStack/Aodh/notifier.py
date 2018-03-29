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
# __author__ = Helena McGough
#
"""A Webserver to send alarm notifications from Aodh to the SO."""
import json
import logging
import sys
import time

import os
from six.moves.BaseHTTPServer import BaseHTTPRequestHandler
from six.moves.BaseHTTPServer import HTTPServer

# Initialise a logger for alarm notifier

logging.basicConfig(stream=sys.stdout,
                    format='%(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.INFO)
log = logging.getLogger(__name__)

sys.path.append(os.path.abspath(os.path.join(os.path.realpath(__file__), '..', '..', '..', '..', '..')))

from osm_mon.core.database import DatabaseManager
from osm_mon.core.message_bus.producer import KafkaProducer

from osm_mon.plugins.OpenStack.common import Common
from osm_mon.plugins.OpenStack.response import OpenStack_Response
from osm_mon.plugins.OpenStack.settings import Config


class NotifierHandler(BaseHTTPRequestHandler):
    """Handler class for alarm_actions triggered by OSM alarms."""

    def _set_headers(self):
        """Set the headers for a request."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        """Get request functionality."""
        self._set_headers()
        self.wfile.write("<html><body><h1>hi!</h1></body></html>")

    def do_POST(self):
        """POST request function."""
        # Gets header and data from the post request and records info
        self._set_headers()
        # Gets the size of data
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        self.wfile.write("<html><body><h1>POST!</h1></body></tml>")
        log.info("This alarm was triggered: %s", json.loads(post_data))

        # Generate a notify_alarm response for the SO
        self.notify_alarm(json.loads(post_data))

    def notify_alarm(self, values):
        """Send a notification response message to the SO."""

        try:
            # Initialise configuration and authentication for response message
            config = Config.instance()
            config.read_environ()
            response = OpenStack_Response()
            producer = KafkaProducer('alarm_response')

            database_manager = DatabaseManager()

            alarm_id = values['alarm_id']
            # Get vim_uuid associated to alarm
            creds = database_manager.get_credentials_for_alarm_id(alarm_id, 'openstack')
            auth_token = Common.get_auth_token(creds.uuid)
            endpoint = Common.get_endpoint("alarming", creds.uuid)

            # If authenticated generate and send response message
            if auth_token is not None and endpoint is not None:
                url = "{}/v2/alarms/%s".format(endpoint) % alarm_id

                # Get the resource_id of the triggered alarm
                result = Common.perform_request(
                    url, auth_token, req_type="get")
                alarm_details = json.loads(result.text)
                gnocchi_rule = alarm_details['gnocchi_resources_threshold_rule']
                resource_id = gnocchi_rule['resource_id']

                # Process an alarm notification if resource_id is valid
                if resource_id is not None:
                    # Get date and time for response message
                    a_date = time.strftime("%d-%m-%Y") + " " + time.strftime("%X")
                    # Try generate and send response
                    try:
                        resp_message = response.generate_response(
                            'notify_alarm', a_id=alarm_id,
                            r_id=resource_id,
                            sev=values['severity'], date=a_date,
                            state=values['current'], vim_type="openstack")
                        producer.notify_alarm(
                            'notify_alarm', resp_message, 'alarm_response')
                        log.info("Sent an alarm response to SO: %s", resp_message)
                    except Exception as exc:
                        log.exception("Couldn't notify SO of the alarm:")
                else:
                    log.warn("No resource_id for alarm; no SO response sent.")
            else:
                log.warn("Authentication failure; SO notification not sent.")
        except:
            log.exception("Could not notify alarm.")


def run(server_class=HTTPServer, handler_class=NotifierHandler, port=8662):
    """Run the webserver application to retrieve alarm notifications."""
    try:
        server_address = ('', port)
        httpd = server_class(server_address, handler_class)
        print('Starting alarm notifier...')
        log.info("Starting alarm notifier server on port: %s", port)
        httpd.serve_forever()
    except Exception as exc:
        log.warn("Failed to start webserver, %s", exc)


if __name__ == "__main__":
    from sys import argv

    # Runs the webserver
    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
