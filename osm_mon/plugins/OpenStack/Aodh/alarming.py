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

import logging

from osm_mon.core.message_bus.producer import KafkaProducer

from osm_mon.plugins.OpenStack.response import OpenStack_Response
from osm_mon.plugins.OpenStack.settings import Config
from osm_mon.plugins.OpenStack.Gnocchi.metrics import Metrics

log = logging.getLogger(__name__)

ALARM_NAMES = {
    "average_memory_usage_above_threshold": "average_memory_utilization",
    "disk_read_ops": "disk_read_ops",
    "disk_write_ops": "disk_write_ops",
    "disk_read_bytes": "disk_read_bytes",
    "disk_write_bytes": "disk_write_bytes",
    "net_packets_dropped": "packets_dropped",
    "packets_in_above_threshold": "packets_received",
    "packets_out_above_threshold": "packets_sent",
    "cpu_utilization_above_threshold": "cpu_utilization"}

METRIC_MAPPINGS = {
    "average_memory_utilization": "memory.percent",
    "disk_read_ops": "disk.disk_ops",
    "disk_write_ops": "disk.disk_ops",
    "disk_read_bytes": "disk.read.bytes",
    "disk_write_bytes": "disk.write.bytes",
    "packets_dropped": "interface.if_dropped",
    "packets_received": "interface.if_packets",
    "packets_sent": "interface.if_packets",
    "cpu_utilization": "cpu_util",
}

SEVERITIES = {
    "warning": "low",
    "minor": "low",
    "major": "moderate",
    "critical": "critical",
    "indeterminate": "critical"}

STATISTICS = {
    "average": "mean",
    "minimum": "min",
    "maximum": "max",
    "count": "count",
    "sum": "sum"}


class Alarming(object):
    """Carries out alarming requests and responses via Aodh API."""

    def __init__(self):
        """Create the OpenStack alarming instance."""
        # Initialize configuration and notifications
        config = Config.instance()
        config.read_environ("aodh")

        # Initialise authentication for API requests
        self.auth_token = None
        self.endpoint = None
        self.common = None

        # Use the Response class to generate valid json response messages
        self._response = OpenStack_Response()

        # Initializer a producer to send responses back to SO
        self._producer = KafkaProducer("alarm_response")

    def alarming(self, message, common, auth_token):
        """Consume info from the message bus to manage alarms."""
        values = json.loads(message.value)
        self.common = common

        log.info("OpenStack alarm action required.")

        # Generate and auth_token and endpoint for request
        if auth_token is not None:
            if self.auth_token != auth_token:
                log.info("Auth_token for alarming set by access_credentials.")
                self.auth_token = auth_token
            else:
                log.info("Auth_token has not been updated.")
        else:
            log.info("Using environment variables to set auth_token for Aodh.")
            self.auth_token = self.common._authenticate()

        if self.endpoint is None:
            log.info("Generating a new endpoint for Aodh.")
            self.endpoint = self.common.get_endpoint("alarming")

        if message.key == "create_alarm_request":
            # Configure/Update an alarm
            alarm_details = values['alarm_create_request']

            alarm_id, alarm_status = self.configure_alarm(
                self.endpoint, self.auth_token, alarm_details)

            # Generate a valid response message, send via producer
            try:
                if alarm_status is True:
                    log.info("Alarm successfully created")

                resp_message = self._response.generate_response(
                    'create_alarm_response', status=alarm_status,
                    alarm_id=alarm_id,
                    cor_id=alarm_details['correlation_id'])
                log.info("Response Message: %s", resp_message)
                self._producer.create_alarm_response(
                    'create_alarm_response', resp_message,
                    'alarm_response')
            except Exception as exc:
                log.warn("Response creation failed: %s", exc)

        elif message.key == "list_alarm_request":
            # Check for a specifed: alarm_name, resource_uuid, severity
            # and generate the appropriate list
            list_details = values['alarm_list_request']

            alarm_list = self.list_alarms(
                self.endpoint, self.auth_token, list_details)

            try:
                # Generate and send a list response back
                resp_message = self._response.generate_response(
                    'list_alarm_response', alarm_list=alarm_list,
                    cor_id=list_details['correlation_id'])
                log.info("Response Message: %s", resp_message)
                self._producer.list_alarm_response(
                    'list_alarm_response', resp_message,
                    'alarm_response')
            except Exception as exc:
                log.warn("Failed to send a valid response back.")

        elif message.key == "delete_alarm_request":
            request_details = values['alarm_delete_request']
            alarm_id = request_details['alarm_uuid']

            resp_status = self.delete_alarm(
                self.endpoint, self.auth_token, alarm_id)

            # Generate and send a response message
            try:
                resp_message = self._response.generate_response(
                    'delete_alarm_response', alarm_id=alarm_id,
                    status=resp_status,
                    cor_id=request_details['correlation_id'])
                log.info("Response message: %s", resp_message)
                self._producer.delete_alarm_response(
                    'delete_alarm_response', resp_message,
                    'alarm_response')
            except Exception as exc:
                log.warn("Failed to create delete reponse:%s", exc)

        elif message.key == "acknowledge_alarm":
            # Acknowledge that an alarm has been dealt with by the SO
            alarm_id = values['ack_details']['alarm_uuid']

            response = self.update_alarm_state(
                self.endpoint, self.auth_token, alarm_id)

            # Log if an alarm was reset
            if response is True:
                log.info("Acknowledged the alarm and cleared it.")
            else:
                log.warn("Failed to acknowledge/clear the alarm.")

        elif message.key == "update_alarm_request":
            # Update alarm configurations
            alarm_details = values['alarm_update_request']

            alarm_id, status = self.update_alarm(
                self.endpoint, self.auth_token, alarm_details)

            # Generate a response for an update request
            try:
                resp_message = self._response.generate_response(
                    'update_alarm_response', alarm_id=alarm_id,
                    cor_id=alarm_details['correlation_id'],
                    status=status)
                log.info("Response message: %s", resp_message)
                self._producer.update_alarm_response(
                    'update_alarm_response', resp_message,
                    'alarm_response')
            except Exception as exc:
                log.warn("Failed to send an update response:%s", exc)

        else:
            log.debug("Unknown key, no action will be performed")

        return

    def configure_alarm(self, endpoint, auth_token, values):
        """Create requested alarm in Aodh."""
        url = "{}/v2/alarms/".format(endpoint)

        # Check if the desired alarm is supported
        alarm_name = values['alarm_name'].lower()
        metric_name = values['metric_name'].lower()
        resource_id = values['resource_uuid']

        if alarm_name not in ALARM_NAMES.keys():
            log.warn("This alarm is not supported, by a valid metric.")
            return None, False
        if ALARM_NAMES[alarm_name] != metric_name:
            log.warn("This is not the correct metric for this alarm.")
            return None, False

        # Check for the required metric
        metric_id = self.check_for_metric(auth_token, metric_name, resource_id)

        try:
            if metric_id is not None:
                # Create the alarm if metric is available
                payload = self.check_payload(values, metric_name, resource_id,
                                             alarm_name)
                new_alarm = self.common._perform_request(
                    url, auth_token, req_type="post", payload=payload)
                return json.loads(new_alarm.text)['alarm_id'], True
            else:
                log.warn("The required Gnocchi metric does not exist.")
                return None, False

        except Exception as exc:
            log.warn("Failed to create the alarm: %s", exc)
        return None, False

    def delete_alarm(self, endpoint, auth_token, alarm_id):
        """Delete alarm function."""
        url = "{}/v2/alarms/%s".format(endpoint) % (alarm_id)

        try:
            result = self.common._perform_request(
                url, auth_token, req_type="delete")
            if str(result.status_code) == "404":
                log.info("Alarm doesn't exist: %s", result.status_code)
                # If status code is 404 alarm did not exist
                return False
            else:
                return True

        except Exception as exc:
            log.warn("Failed to delete alarm: %s because %s.", alarm_id, exc)
        return False

    def list_alarms(self, endpoint, auth_token, list_details):
        """Generate the requested list of alarms."""
        url = "{}/v2/alarms/".format(endpoint)
        a_list, name_list, sev_list, res_list = [], [], [], []

        # TODO(mcgoughh): for now resource_id is a mandatory field
        # Check for a reqource is
        try:
            resource = list_details['resource_uuid']
        except KeyError as exc:
            log.warn("Resource id not specified for list request: %s", exc)
            return None

        # Checking what fields are specified for a list request
        try:
            name = list_details['alarm_name'].lower()
            if name not in ALARM_NAMES.keys():
                log.warn("This alarm is not supported, won't be used!")
                name = None
        except KeyError as exc:
            log.info("Alarm name isn't specified.")
            name = None

        try:
            severity = list_details['severity'].lower()
            sev = SEVERITIES[severity]
        except KeyError as exc:
            log.info("Severity is unspecified/incorrectly configured")
            sev = None

        # Perform the request to get the desired list
        try:
            result = self.common._perform_request(
                url, auth_token, req_type="get")

            if result is not None:
                # Get list based on resource id
                for alarm in json.loads(result.text):
                    rule = alarm['gnocchi_resources_threshold_rule']
                    if resource == rule['resource_id']:
                        res_list.append(str(alarm))
                    if not res_list:
                        log.info("No alarms for this resource")
                        return a_list

                # Generate specified listed if requested
                if name is not None and sev is not None:
                    log.info("Return a list of %s alarms with %s severity.",
                             name, sev)
                    for alarm in json.loads(result.text):
                        if name == alarm['name']:
                            name_list.append(str(alarm))
                    for alarm in json.loads(result.text):
                        if sev == alarm['severity']:
                            sev_list.append(str(alarm))
                    name_sev_list = list(set(name_list).intersection(sev_list))
                    a_list = list(set(name_sev_list).intersection(res_list))
                elif name is not None:
                    log.info("Returning a %s list of alarms.", name)
                    for alarm in json.loads(result.text):
                        if name == alarm['name']:
                            name_list.append(str(alarm))
                    a_list = list(set(name_list).intersection(res_list))
                elif sev is not None:
                    log.info("Returning %s severity alarm list.", sev)
                    for alarm in json.loads(result.text):
                        if sev == alarm['severity']:
                            sev_list.append(str(alarm))
                    a_list = list(set(sev_list).intersection(res_list))
                else:
                    log.info("Returning an entire list of alarms.")
                    a_list = res_list
            else:
                log.info("There are no alarms!")

        except Exception as exc:
            log.info("Failed to generate required list: %s", exc)
            return None

        return a_list

    def update_alarm_state(self, endpoint, auth_token, alarm_id):
        """Set the state of an alarm to ok when ack message is received."""
        url = "{}/v2/alarms/%s/state".format(endpoint) % alarm_id
        payload = json.dumps("ok")

        try:
            self.common._perform_request(
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
            result = self.common._perform_request(
                url, auth_token, req_type="get")
            alarm_name = json.loads(result.text)['name']
            rule = json.loads(result.text)['gnocchi_resources_threshold_rule']
            alarm_state = json.loads(result.text)['state']
            resource_id = rule['resource_id']
            metric_name = rule['metric']
        except Exception as exc:
            log.warn("Failed to retreive existing alarm info: %s.\
                     Can only update OSM alarms.", exc)
            return None, False

        # Generates and check payload configuration for alarm update
        payload = self.check_payload(values, metric_name, resource_id,
                                     alarm_name, alarm_state=alarm_state)

        # Updates the alarm configurations with the valid payload
        if payload is not None:
            try:
                update_alarm = self.common._perform_request(
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
            cfg = Config.instance()
            # Check state and severity
            severity = values['severity'].lower()
            if severity == "indeterminate":
                alarm_state = "insufficient data"
            if alarm_state is None:
                alarm_state = "ok"

            statistic = values['statistic'].lower()
            granularity = values['granularity']
            resource_type = values['resource_type'].lower()

            # Try to configure the payload for the update/create request
            # Can only update: threshold, operation, statistic and
            # the severity of the alarm
            rule = {'threshold': values['threshold_value'],
                    'comparison_operator': values['operation'].lower(),
                    'metric': METRIC_MAPPINGS[metric_name],
                    'resource_id': resource_id,
                    'resource_type': resource_type,
                    'aggregation_method': STATISTICS[statistic],
                    'granularity': granularity, }
            payload = json.dumps({'state': alarm_state,
                                  'name': alarm_name,
                                  'severity': SEVERITIES[severity],
                                  'type': 'gnocchi_resources_threshold',
                                  'gnocchi_resources_threshold_rule': rule,
                                  'alarm_actions': [cfg.OS_NOTIFIER_URI], })
            return payload
        except KeyError as exc:
            log.warn("Alarm is not configured correctly: %s", exc)
        return None

    def get_alarm_state(self, endpoint, auth_token, alarm_id):
        """Get the state of the alarm."""
        url = "{}/v2/alarms/%s/state".format(endpoint) % alarm_id

        try:
            alarm_state = self.common._perform_request(
                url, auth_token, req_type="get")
            return json.loads(alarm_state.text)
        except Exception as exc:
            log.warn("Failed to get the state of the alarm:%s", exc)
        return None

    def check_for_metric(self, auth_token, m_name, r_id):
        """Check for the alarm metric."""
        try:
            endpoint = self.common.get_endpoint("metric")
            url = "{}/v1/metric?sort=name:asc".format(endpoint)
            result = self.common._perform_request(
                url, auth_token, req_type="get")
            metric_list = []
            metrics_partial = json.loads(result.text)
            for metric in metrics_partial:
                metric_list.append(metric)

            while len(json.loads(result.text)) > 0:
                last_metric_id = metrics_partial[-1]['id']
                url = "{}/v1/metric?sort=name:asc&marker={}".format(endpoint, last_metric_id)
                result = self.common._perform_request(
                    url, auth_token, req_type="get")
                if len(json.loads(result.text)) > 0:
                    metrics_partial = json.loads(result.text)
                    for metric in metrics_partial:
                        metric_list.append(metric)

            for metric in metric_list:
                name = metric['name']
                resource = metric['resource_id']
                if (name == METRIC_MAPPINGS[m_name] and resource == r_id):
                    metric_id = metric['id']
            log.info("The required metric exists, an alarm will be created.")
            return metric_id
        except Exception as exc:
            log.info("Desired Gnocchi metric not found:%s", exc)
        return None
