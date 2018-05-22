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

import six
import yaml

from osm_mon.core.auth import AuthManager
from osm_mon.core.database import DatabaseManager
from osm_mon.core.message_bus.producer import KafkaProducer
from osm_mon.core.settings import Config
from osm_mon.plugins.OpenStack.Gnocchi.metrics import METRIC_MAPPINGS
from osm_mon.plugins.OpenStack.common import Common
from osm_mon.plugins.OpenStack.response import OpenStack_Response

log = logging.getLogger(__name__)

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
        config.read_environ()

        self._database_manager = DatabaseManager()
        self._auth_manager = AuthManager()

        # Use the Response class to generate valid json response messages
        self._response = OpenStack_Response()

        # Initializer a producer to send responses back to SO
        self._producer = KafkaProducer("alarm_response")

    def configure_alarm(self, alarm_endpoint, metric_endpoint, auth_token, values, vim_config):
        """Create requested alarm in Aodh."""
        url = "{}/v2/alarms/".format(alarm_endpoint)

        # Check if the desired alarm is supported
        alarm_name = values['alarm_name'].lower()
        metric_name = values['metric_name'].lower()
        resource_id = values['resource_uuid']

        if metric_name not in METRIC_MAPPINGS.keys():
            log.warning("This metric is not supported.")
            return None, False

        # Check for the required metric
        metric_id = self.check_for_metric(auth_token, metric_endpoint, metric_name, resource_id)

        try:
            if metric_id is not None:
                # Create the alarm if metric is available
                if 'granularity' in vim_config and 'granularity' not in values:
                    values['granularity'] = vim_config['granularity']
                payload = self.check_payload(values, metric_name, resource_id,
                                             alarm_name)
                new_alarm = Common.perform_request(
                    url, auth_token, req_type="post", payload=payload)
                return json.loads(new_alarm.text)['alarm_id'], True
            else:
                log.warning("The required Gnocchi metric does not exist.")
                return None, False

        except Exception as exc:
            log.warning("Failed to create the alarm: %s", exc)
        return None, False

    def alarming(self, message, vim_uuid):
        """Consume info from the message bus to manage alarms."""
        try:
            values = json.loads(message.value)
        except ValueError:
            values = yaml.safe_load(message.value)

        log.info("OpenStack alarm action required.")

        auth_token = Common.get_auth_token(vim_uuid)

        alarm_endpoint = Common.get_endpoint("alarming", vim_uuid)
        metric_endpoint = Common.get_endpoint("metric", vim_uuid)

        vim_account = self._auth_manager.get_credentials(vim_uuid)
        vim_config = json.loads(vim_account.config)

        if message.key == "create_alarm_request":
            # Configure/Update an alarm
            alarm_details = values['alarm_create_request']

            alarm_id, alarm_status = self.configure_alarm(
                alarm_endpoint, metric_endpoint, auth_token, alarm_details, vim_config)

            # Generate a valid response message, send via producer
            if alarm_status is True:
                log.info("Alarm successfully created")
                self._database_manager.save_alarm(alarm_id,
                                                  vim_uuid,
                                                  alarm_details['threshold_value'],
                                                  alarm_details['operation'].lower(),
                                                  alarm_details['metric_name'].lower(),
                                                  alarm_details['vdu_name'].lower(),
                                                  alarm_details['vnf_member_index'].lower(),
                                                  alarm_details['ns_id'].lower()
                                                  )
            try:
                resp_message = self._response.generate_response(
                    'create_alarm_response', status=alarm_status,
                    alarm_id=alarm_id,
                    cor_id=alarm_details['correlation_id'])
                log.info("Response Message: %s", resp_message)
                self._producer.create_alarm_response(
                    'create_alarm_response', resp_message)
            except Exception:
                log.exception("Response creation failed:")

        elif message.key == "list_alarm_request":
            # Check for a specified: alarm_name, resource_uuid, severity
            # and generate the appropriate list
            list_details = values['alarm_list_request']

            alarm_list = self.list_alarms(
                alarm_endpoint, auth_token, list_details)

            try:
                # Generate and send a list response back
                resp_message = self._response.generate_response(
                    'list_alarm_response', alarm_list=alarm_list,
                    cor_id=list_details['correlation_id'])
                log.info("Response Message: %s", resp_message)
                self._producer.list_alarm_response(
                    'list_alarm_response', resp_message)
            except Exception:
                log.exception("Failed to send a valid response back.")

        elif message.key == "delete_alarm_request":
            request_details = values['alarm_delete_request']
            alarm_id = request_details['alarm_uuid']

            resp_status = self.delete_alarm(
                alarm_endpoint, auth_token, alarm_id)

            # Generate and send a response message
            try:
                resp_message = self._response.generate_response(
                    'delete_alarm_response', alarm_id=alarm_id,
                    status=resp_status,
                    cor_id=request_details['correlation_id'])
                log.info("Response message: %s", resp_message)
                self._producer.delete_alarm_response(
                    'delete_alarm_response', resp_message)
            except Exception:
                log.exception("Failed to create delete response: ")

        elif message.key == "acknowledge_alarm":
            # Acknowledge that an alarm has been dealt with by the SO
            alarm_id = values['ack_details']['alarm_uuid']

            response = self.update_alarm_state(
                alarm_endpoint, auth_token, alarm_id)

            # Log if an alarm was reset
            if response is True:
                log.info("Acknowledged the alarm and cleared it.")
            else:
                log.warning("Failed to acknowledge/clear the alarm.")

        elif message.key == "update_alarm_request":
            # Update alarm configurations
            alarm_details = values['alarm_update_request']

            alarm_id, status = self.update_alarm(
                alarm_endpoint, auth_token, alarm_details, vim_config)

            # Generate a response for an update request
            try:
                resp_message = self._response.generate_response(
                    'update_alarm_response', alarm_id=alarm_id,
                    cor_id=alarm_details['correlation_id'],
                    status=status)
                log.info("Response message: %s", resp_message)
                self._producer.update_alarm_response(
                    'update_alarm_response', resp_message)
            except Exception:
                log.exception("Failed to send an update response: ")

        else:
            log.debug("Unknown key, no action will be performed")

        return

    def delete_alarm(self, endpoint, auth_token, alarm_id):
        """Delete alarm function."""
        url = "{}/v2/alarms/%s".format(endpoint) % alarm_id

        try:
            result = Common.perform_request(
                url, auth_token, req_type="delete")
            if str(result.status_code) == "404":
                log.info("Alarm doesn't exist: %s", result.status_code)
                # If status code is 404 alarm did not exist
                return False
            else:
                return True

        except Exception:
            log.exception("Failed to delete alarm %s :", alarm_id)
        return False

    def list_alarms(self, endpoint, auth_token, list_details):
        """Generate the requested list of alarms."""
        url = "{}/v2/alarms/".format(endpoint)
        a_list, name_list, sev_list, res_list = [], [], [], []

        # TODO(mcgoughh): for now resource_id is a mandatory field
        # Check for a resource id
        try:
            resource = list_details['resource_uuid']
        except KeyError as exc:
            log.warning("Resource id not specified for list request: %s", exc)
            return None

        # Checking what fields are specified for a list request
        try:
            name = list_details['alarm_name'].lower()
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
            result = Common.perform_request(
                url, auth_token, req_type="get")

            if result is not None:
                # Get list based on resource id
                for alarm in json.loads(result.text):
                    rule = alarm['gnocchi_resources_threshold_rule']
                    if resource == rule['resource_id']:
                        res_list.append(alarm)
                    if not res_list:
                        log.info("No alarms for this resource")
                        return a_list

                # Generate specified listed if requested
                if name is not None and sev is not None:
                    log.info("Return a list of %s alarms with %s severity.",
                             name, sev)
                    for alarm in json.loads(result.text):
                        if name == alarm['name']:
                            name_list.append(alarm)
                    for alarm in json.loads(result.text):
                        if sev == alarm['severity']:
                            sev_list.append(alarm)
                    name_sev_list = list(set(name_list).intersection(sev_list))
                    a_list = list(set(name_sev_list).intersection(res_list))
                elif name is not None:
                    log.info("Returning a %s list of alarms.", name)
                    for alarm in json.loads(result.text):
                        if name == alarm['name']:
                            name_list.append(alarm)
                    a_list = list(set(name_list).intersection(res_list))
                elif sev is not None:
                    log.info("Returning %s severity alarm list.", sev)
                    for alarm in json.loads(result.text):
                        if sev == alarm['severity']:
                            sev_list.append(alarm)
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
            Common.perform_request(
                url, auth_token, req_type="put", payload=payload)
            return True
        except Exception:
            log.exception("Unable to update alarm state: ")
        return False

    def update_alarm(self, endpoint, auth_token, values, vim_config):
        """Get alarm name for an alarm configuration update."""
        # Get already existing alarm details
        url = "{}/v2/alarms/%s".format(endpoint) % values['alarm_uuid']

        # Gets current configurations about the alarm
        try:
            result = Common.perform_request(
                url, auth_token, req_type="get")
            alarm_name = json.loads(result.text)['name']
            rule = json.loads(result.text)['gnocchi_resources_threshold_rule']
            alarm_state = json.loads(result.text)['state']
            resource_id = rule['resource_id']
            metric_name = [key for key, value in six.iteritems(METRIC_MAPPINGS) if value == rule['metric']][0]
        except Exception as exc:
            log.exception("Failed to retrieve existing alarm info. Can only update OSM alarms.")
            return None, False

        # Generates and check payload configuration for alarm update
        if 'granularity' in vim_config and 'granularity' not in values:
            values['granularity'] = vim_config['granularity']
        payload = self.check_payload(values, metric_name, resource_id,
                                     alarm_name, alarm_state=alarm_state)

        # Updates the alarm configurations with the valid payload
        if payload is not None:
            try:
                update_alarm = Common.perform_request(
                    url, auth_token, req_type="put", payload=payload)

                return json.loads(update_alarm.text)['alarm_id'], True
            except Exception as exc:
                log.exception("Alarm update could not be performed: ")
        return None, False

    def check_payload(self, values, metric_name, resource_id,
                      alarm_name, alarm_state=None):
        """Check that the payload is configuration for update/create alarm."""
        try:
            cfg = Config.instance()
            # Check state and severity

            severity = 'critical'
            if 'severity' in values:
                severity = values['severity'].lower()

            if severity == "indeterminate":
                alarm_state = "insufficient data"
            if alarm_state is None:
                alarm_state = "ok"

            statistic = values['statistic'].lower()

            granularity = cfg.OS_DEFAULT_GRANULARITY
            if 'granularity' in values:
                granularity = values['granularity']

            resource_type = 'generic'
            if 'resource_type' in values:
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
            log.warning("Alarm is not configured correctly: %s", exc)
        return None

    def get_alarm_state(self, endpoint, auth_token, alarm_id):
        """Get the state of the alarm."""
        url = "{}/v2/alarms/%s/state".format(endpoint) % alarm_id

        try:
            alarm_state = Common.perform_request(
                url, auth_token, req_type="get")
            return json.loads(alarm_state.text)
        except Exception as exc:
            log.warning("Failed to get the state of the alarm:%s", exc)
        return None

    def check_for_metric(self, auth_token, metric_endpoint, m_name, r_id):
        """Check for the alarm metric."""
        try:
            url = "{}/v1/resource/generic/{}".format(metric_endpoint, r_id)
            result = Common.perform_request(
                url, auth_token, req_type="get")
            resource = json.loads(result.text)
            metric_list = resource['metrics']
            if metric_list.get(METRIC_MAPPINGS[m_name]):
                metric_id = metric_list[METRIC_MAPPINGS[m_name]]
            else:
                metric_id = None
                log.info("Desired Gnocchi metric not found")
            return metric_id
        except Exception as exc:
            log.info("Desired Gnocchi metric not found:%s", exc)
        return None