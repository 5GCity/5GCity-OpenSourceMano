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
"""Carry out alarming requests via Aodh API."""

import json
import logging as log

from core.message_bus.producer import KafkaProducer

from kafka import KafkaConsumer

from plugins.OpenStack.common import Common
from plugins.OpenStack.response import OpenStack_Response

__author__ = "Helena McGough"

ALARM_NAMES = [
    "Average_Memory_Usage_Above_Threshold",
    "Read_Latency_Above_Threshold",
    "Write_Latency_Above_Threshold",
    "DISK_READ_OPS",
    "DISK_WRITE_OPS",
    "DISK_READ_BYTES",
    "DISK_WRITE_BYTES",
    "Net_Packets_Dropped",
    "Packets_in_Above_Threshold",
    "Packets_out_Above_Threshold",
    "CPU_Utilization_Above_Threshold"]

SEVERITIES = {
    "WARNING": "low",
    "MINOR": "low",
    "MAJOR": "moderate",
    "CRITICAL": "critical",
    "INDETERMINATE": "critical"}


class Alarming(object):
    """Carries out alarming requests and responses via Aodh API."""

    def __init__(self):
        """Create the OpenStack alarming instance."""
        self._common = Common()

        # TODO(mcgoughh): Remove hardcoded kafkaconsumer
        # Initialize a generic consumer object to consume message from the SO
        server = {'server': 'localhost:9092', 'topic': 'alarm_request'}
        self._consumer = KafkaConsumer(server['topic'],
                                       group_id='osm_mon',
                                       bootstrap_servers=server['server'])

        # Use the Response class to generate valid json response messages
        self._response = OpenStack_Response()

        # Initializer a producer to send responses back to SO
        self._producer = KafkaProducer("alarm_response")

    def alarming(self):
        """Consume info from the message bus to manage alarms."""
        # Check the alarming functionlity that needs to be performed
        for message in self._consumer:

            values = json.loads(message.value)
            vim_type = values['vim_type'].lower()

            if vim_type == "openstack":
                log.info("Alarm action required: %s" % (message.topic))

                # Generate and auth_token and endpoint for request
                auth_token, endpoint = self.authenticate(values)

                if message.key == "create_alarm_request":
                    # Configure/Update an alarm
                    alarm_details = values['alarm_create_request']

                    alarm_id, alarm_status = self.configure_alarm(
                        endpoint, auth_token, alarm_details)

                    # Generate a valid response message, send via producer
                    try:
                        resp_message = self._response.generate_response(
                            'create_alarm_response', status=alarm_status,
                            alarm_id=alarm_id,
                            cor_id=alarm_details['correlation_id'])
                        self._producer.create_alarm_response(
                            'create_alarm_resonse', resp_message,
                            'alarm_response')
                    except Exception as exc:
                        log.warn("Response creation failed: %s", exc)

                elif message.key == "list_alarm_request":
                    # Check for a specifed: alarm_name, resource_uuid, severity
                    # and generate the appropriate list
                    list_details = values['alarm_list_request']
                    try:
                        name = list_details['alarm_name']
                        alarm_list = self.list_alarms(
                            endpoint, auth_token, alarm_name=name)
                    except Exception as a_name:
                        log.debug("No name specified for list:%s", a_name)
                        try:
                            resource = list_details['resource_uuid']
                            alarm_list = self.list_alarms(
                                endpoint, auth_token, resource_id=resource)
                        except Exception as r_id:
                            log.debug("No resource id specified for this list:\
                                       %s", r_id)
                            try:
                                severe = list_details['severity']
                                alarm_list = self.list_alarms(
                                    endpoint, auth_token, severity=severe)
                            except Exception as exc:
                                log.warn("No severity specified for list: %s.\
                                           will return full list.", exc)
                                alarm_list = self.list_alarms(
                                    endpoint, auth_token)

                    try:
                        # Generate and send a list response back
                        resp_message = self._response.generate_response(
                            'list_alarm_response', alarm_list=alarm_list,
                            cor_id=list_details['correlation_id'])
                        self._producer.list_alarm_response(
                            'list_alarm_response', resp_message,
                            'alarm_response')
                    except Exception as exc:
                        log.warn("Failed to send a valid response back.")

                elif message.key == "delete_alarm_request":
                    request_details = values['alarm_delete_request']
                    alarm_id = request_details['alarm_uuid']

                    resp_status = self.delete_alarm(
                        endpoint, auth_token, alarm_id)

                    # Generate and send a response message
                    try:
                        resp_message = self._response.generate_response(
                            'delete_alarm_response', alarm_id=alarm_id,
                            status=resp_status,
                            cor_id=request_details['correlation_id'])
                        self._producer.delete_alarm_response(
                            'delete_alarm_response', resp_message,
                            'alarm_response')
                    except Exception as exc:
                        log.warn("Failed to create delete reponse:%s", exc)

                elif message.key == "acknowledge_alarm":
                    # Acknowledge that an alarm has been dealt with by the SO
                    alarm_id = values['ack_details']['alarm_uuid']

                    response = self.update_alarm_state(
                        endpoint, auth_token, alarm_id)

                    # Log if an alarm was reset
                    if response is True:
                        log.info("Acknowledged the alarm and cleared it.")
                    else:
                        log.warn("Failed to acknowledge/clear the alarm.")

                elif message.key == "update_alarm_request":
                    # Update alarm configurations
                    alarm_details = values['alarm_update_request']

                    alarm_id, status = self.update_alarm(
                        endpoint, auth_token, alarm_details)

                    # Generate a response for an update request
                    try:
                        resp_message = self._response.generate_response(
                            'update_alarm_response', alarm_id=alarm_id,
                            cor_id=alarm_details['correlation_id'],
                            status=status)
                        self._producer.update_alarm_response(
                            'update_alarm_response', resp_message,
                            'alarm_response')
                    except Exception as exc:
                        log.warn("Failed to send an update response:%s", exc)

                else:
                    log.debug("Unknown key, no action will be performed")
            else:
                log.info("Message topic not relevant to this plugin: %s",
                         message.topic)

        return

    def configure_alarm(self, endpoint, auth_token, values):
        """Create requested alarm in Aodh."""
        url = "{}/v2/alarms/".format(endpoint)

        # Check if the desired alarm is supported
        alarm_name = values['alarm_name']
        if alarm_name not in ALARM_NAMES:
            log.warn("This alarm is not supported, by a valid metric.")
            return None, False

        try:
            metric_name = values['metric_name']
            resource_id = values['resource_uuid']
            # Check the payload for the desired alarm
            payload = self.check_payload(values, metric_name, resource_id,
                                         alarm_name)
            new_alarm = self._common._perform_request(
                url, auth_token, req_type="post", payload=payload)

            return json.loads(new_alarm.text)['alarm_id'], True
        except Exception as exc:
            log.warn("Alarm creation could not be performed: %s", exc)
        return None, False

    def delete_alarm(self, endpoint, auth_token, alarm_id):
        """Delete alarm function."""
        url = "{}/v2/alarms/%s".format(endpoint) % (alarm_id)

        try:
            result = self._common._perform_request(
                url, auth_token, req_type="delete")
            if str(result.status_code) == "404":
                # If status code is 404 alarm did not exist
                return False
            else:
                return True

        except Exception as exc:
            log.warn("Failed to delete alarm: %s because %s.", alarm_id, exc)
        return False

    def list_alarms(self, endpoint, auth_token,
                    alarm_name=None, resource_id=None, severity=None):
        """Generate the requested list of alarms."""
        url = "{}/v2/alarms/".format(endpoint)
        alarm_list = []

        result = self._common._perform_request(
            url, auth_token, req_type="get")
        if result is not None:
            # Check for a specified list based on:
            # alarm_name, severity, resource_id
            if alarm_name is not None:
                for alarm in json.loads(result.text):
                    if alarm_name in str(alarm):
                        alarm_list.append(str(alarm))
            elif resource_id is not None:
                for alarm in json.loads(result.text):
                    if resource_id in str(alarm):
                        alarm_list.append(str(alarm))
            elif severity is not None:
                for alarm in json.loads(result.text):
                    if severity in str(alarm):
                        alarm_list.append(str(alarm))
            else:
                alarm_list = result.text
        else:
            return None
        return alarm_list

    def update_alarm_state(self, endpoint, auth_token, alarm_id):
        """Set the state of an alarm to ok when ack message is received."""
        url = "{}/v2/alarms/%s/state".format(endpoint) % alarm_id
        payload = json.dumps("ok")

        try:
            self._common._perform_request(
                url, auth_token, req_type="put", payload=payload)
            return True
        except Exception as exc:
            log.warn("Unable to update alarm state: %s", exc)
        return False

    def update_alarm(self, endpoint, auth_token, values):
        """Get alarm name for an alarm configuration update."""
        # Get already existing alarm details
        url = "{}/v2/alarms/%s".format(endpoint) % values['alarm_uuid']

        # Gets current configurations about the alarm
        try:
            result = self._common._perform_request(
                url, auth_token, req_type="get")
            alarm_name = json.loads(result.text)['name']
            rule = json.loads(result.text)['gnocchi_resources_threshold_rule']
            alarm_state = json.loads(result.text)['state']
            resource_id = rule['resource_id']
            metric_name = rule['metric']
        except Exception as exc:
            log.warn("Failed to retreive existing alarm info: %s.\
                     Can only update OSM created alarms.", exc)
            return None, False

        # Generates and check payload configuration for alarm update
        payload = self.check_payload(values, metric_name, resource_id,
                                     alarm_name, alarm_state=alarm_state)

        # Updates the alarm configurations with the valid payload
        if payload is not None:
            try:
                update_alarm = self._common._perform_request(
                    url, auth_token, req_type="put", payload=payload)

                return json.loads(update_alarm.text)['alarm_id'], True
            except Exception as exc:
                log.warn("Alarm update could not be performed: %s", exc)
                return None, False
        return None, False

    def check_payload(self, values, metric_name, resource_id,
                      alarm_name, alarm_state=None):
        """Check that the payload is configuration for update/create alarm."""
        try:
            # Check state and severity
            severity = values['severity']
            if severity == "INDETERMINATE":
                alarm_state = "insufficient data"
            if alarm_state is None:
                alarm_state = "ok"

            # Try to configure the payload for the update/create request
            # Can only update: threshold, operation, statistic and
            # the severity of the alarm
            rule = {'threshold': values['threshold_value'],
                    'comparison_operator': values['operation'].lower(),
                    'metric': metric_name,
                    'resource_id': resource_id,
                    'resource_type': 'generic',
                    'aggregation_method': values['statistic'].lower()}
            payload = json.dumps({'state': alarm_state,
                                  'name': alarm_name,
                                  'severity': SEVERITIES[severity],
                                  'type': 'gnocchi_resources_threshold',
                                  'gnocchi_resources_threshold_rule': rule, })
            return payload
        except KeyError as exc:
            log.warn("Alarm is not configured correctly: %s", exc)
        return None

    def authenticate(self, values):
        """Generate an authentication token and endpoint for alarm request."""
        try:
            # Check for a tenant_id
            auth_token = self._common._authenticate(
                tenant_id=values['tenant_uuid'])
            endpoint = self._common.get_endpoint("alarming")
        except Exception as exc:
            log.warn("Tenant ID is not specified. Will use a generic\
                      authentication: %s", exc)
            auth_token = self._common._authenticate()
            endpoint = self._common.get_endpoint("alarming")

        return auth_token, endpoint

    def get_alarm_state(self, endpoint, auth_token, alarm_id):
        """Get the state of the alarm."""
        url = "{}/v2/alarms/%s/state".format(endpoint) % alarm_id

        try:
            alarm_state = self._common._perform_request(
                url, auth_token, req_type="get")
            return json.loads(alarm_state.text)
        except Exception as exc:
            log.warn("Failed to get the state of the alarm:%s", exc)
        return None
