"""Send alarm info from Aodh to SO via MON."""

import json
import logging as log

from collections import OrderedDict

from kafka import KafkaConsumer

from plugins.OpenStack.common import Common


SEVERITIES = {
    "WARNING": "low",
    "MINOR": "low",
    "MAJOR": "moderate",
    "CRITICAL": "critical",
    "INDETERMINATE": "critical"}


class Alarming(object):
    """Receives alarm info from Aodh."""

    def __init__(self):
        """Create the aodh_receiver instance."""
        self._common = Common()
        self.auth_token = None
        self.endpoint = None
        self.resp_status = None

        # TODO(mcgoughh): Remove hardcoded kafkaconsumer
        # Initialize a generic consumer object to consume message from the SO
        server = {'server': 'localhost:9092', 'topic': 'alarm_request'}
        self._consumer = KafkaConsumer(server['topic'],
                                       group_id='osm_mon',
                                       bootstrap_servers=server['server'])

        # TODO(mcgoughh): Initialize a producer to send messages bask to the SO

    def alarming(self):
        """Consume info from the message bus to manage alarms."""
        # Check the alarming functionlity that needs to be performed
        for message in self._consumer:

            values = json.loads(message.value)
            vim_type = values['vim_type'].lower()

            if vim_type == "openstack":
                log.info("Alarm action required: %s" % (message.topic))

                if message.key == "create_alarm_request":
                    # Configure/Update an alarm
                    alarm_details = values['alarm_create_request']

                    # Generate an auth_token and endpoint
                    auth_token = self._common._authenticate(
                        tenant_id=alarm_details['tenant_uuid'])
                    endpoint = self._common.get_endpoint("alarming")

                    alarm_id = self.configure_alarm(
                        endpoint, auth_token, alarm_details)

                    # TODO(mcgoughh): will send an acknowledge message back on
                    # the bus via the producer
                    if alarm_id is not None:
                        self.resp_status = True
                        log.debug("A valid alarm was found/created: %s",
                                  self.resp_status)
                    else:
                        self.resp_status = False
                        log.debug("Failed to create desired alarm: %s",
                                  self.resp_status)

                elif message.key == "list_alarm_request":
                    auth_token = self._common._authenticate()
                    endpoint = self._common.get_endpoint("alarming")

                    # List all of the alarms
                    alarm_list = self.list_alarms(endpoint, auth_token)

                    # TODO(mcgoughh): send a repsonse back to SO
                    if alarm_list is not None:
                        self.resp_status = True
                        log.info("A list of alarms was generated: %s",
                                 alarm_list)
                    else:
                        self.resp_status = False
                        log.warn("Failed to generae an alarm list")

                elif message.key == "delete_alarm_request":
                    # Delete the specified alarm
                    auth_token = self._common._authenticate()
                    endpoint = self._common.get_endpoint("alarming")

                    alarm_id = values['alarm_delete_request']['alarm_uuid']

                    response = self.delete_alarm(
                        endpoint, auth_token, alarm_id)

                    # TODO(mcgoughh): send a response back on the bus
                    if response is True:
                        log.info("Requested alarm has been deleted: %s",
                                 alarm_id)
                    else:
                        log.warn("Failed to delete requested alarm.")

                elif message.key == "acknowledge_alarm":
                    # Acknowledge that an alarm has been dealt with by the SO
                    # Set its state to ok
                    auth_token = self._common._authenticate()
                    endpoint = self._common.get_endpoint("alarming")

                    alarm_id = values['ack_details']['alarm_uuid']

                    response = self.update_alarm_state(
                        endpoint, auth_token, alarm_id)

                    if response is True:
                        log.info("Status has been updated for alarm, %s.",
                                 alarm_id)
                    else:
                        log.warn("Failed update the state of requested alarm.")

                elif message.key == "update_alarm_request":
                    # Update alarm configurations
                    auth_token = self._common._authenticate()
                    endpoint = self._common.get_endpoint("alarming")

                    alarm_details = values['alarm_update_request']

                    alarm_id = self.update_alarm(
                        endpoint, auth_token, alarm_details)

                    # TODO(mcgoughh): send a response message to the SO
                    if alarm_id is not None:
                        log.info("Alarm configuration was update correctly.")
                    else:
                        log.warn("Unable to update the specified alarm")

                else:
                    log.debug("Unknown key, no action will be performed")
            else:
                log.info("Message topic not relevant to this plugin: %s",
                         message.topic)

        return

    def get_alarm_id(self, endpoint, auth_token, alarm_name):
        """Get a list of alarms that exist in Aodh."""
        alarm_id = None
        url = "{}/v2/alarms/".format(endpoint)

        # TODO(mcgoughh): will query on resource_id once it has been
        # implemented need to create the query field when creating
        # the alarm
        query = OrderedDict([("q.field", 'name'), ("q.op", "eq"),
                            ("q.value", alarm_name)])

        result = self._common._perform_request(
            url, auth_token, req_type="get", params=query)

        try:
            alarm_id = json.loads(result.text)[0]['alarm_id']
            log.info("An existing alarm was found: %s", alarm_id)
            return alarm_id
        except Exception:
            log.debug("Alarm doesn't exist, needs to be created.")
        return alarm_id

    def configure_alarm(self, endpoint, auth_token, values):
        """Create requested alarm in Aodh."""
        url = "{}/v2/alarms/".format(endpoint)

        alarm_name = values['alarm_name']

        # Confirm alarm doesn't exist
        alarm_id = self.get_alarm_id(endpoint, auth_token, alarm_name)
        if alarm_id is None:
            # Try to create the alarm
            try:
                metric_name = values['metric_name']
                resource_id = values['resource_uuid']
                payload = self.check_payload(values, metric_name, resource_id,
                                             alarm_name)
                new_alarm = self._common._perform_request(
                    url, auth_token, req_type="post", payload=payload)

                return json.loads(new_alarm.text)['alarm_id']
            except Exception as exc:
                log.warn("Alarm creation could not be performed: %s", exc)
                return alarm_id
        else:
            log.warn("This alarm already exists. Try an update instead.")
        return None

    def delete_alarm(self, endpoint, auth_token, alarm_id):
        """Delete alarm function."""
        url = "{}/v2/alarms/%s".format(endpoint) % (alarm_id)

        result = False
        try:
            self._common._perform_request(url, auth_token, req_type="delete")
            return True
        except Exception as exc:
            log.warn("Failed to delete alarm: %s because %s.", alarm_id, exc)
        return result

    def list_alarms(self, endpoint, auth_token,
                    alarm_name=None, resource_id=None, severity=None):
        """Generate the requested list of alarms."""
        result = None
        if (alarm_name and resource_id and severity) is None:
            # List all alarms
            url = "{}/v2/alarms/".format(endpoint)

            try:
                result = self._common._perform_request(
                    url, auth_token, req_type="get")
                return json.loads(result.text)
            except Exception as exc:
                log.warn("Unable to generate alarm list: %s", exc)

            return result
        else:
            # TODO(mcgoughh): support more specific lists
            log.debug("Requested list is unavailable")

        return result

    def update_alarm_state(self, endpoint, auth_token, alarm_id):
        """Set the state of an alarm to ok when ack message is received."""
        result = False

        url = "{}/v2/alarms/%s/state".format(endpoint) % alarm_id
        payload = json.dumps("ok")

        try:
            result = self._common._perform_request(
                url, auth_token, req_type="put", payload=payload)
            return True
        except Exception as exc:
            log.warn("Unable to update alarm state: %s", exc)
        return result

    def update_alarm(self, endpoint, auth_token, values):
        """Get alarm name for an alarm configuration update."""
        # Get already existing alarm details
        url = "{}/v2/alarms/%s".format(endpoint) % values['alarm_uuid']

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
            return None

        # Genate and check payload configuration for alarm update
        payload = self.check_payload(values, metric_name, resource_id,
                                     alarm_name, alarm_state=alarm_state)

        if payload is not None:
            try:
                update_alarm = self._common._perform_request(
                    url, auth_token, req_type="put", payload=payload)

                return json.loads(update_alarm.text)['alarm_id']
            except Exception as exc:
                log.warn("Alarm update could not be performed: %s", exc)
                return None
        return None

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
