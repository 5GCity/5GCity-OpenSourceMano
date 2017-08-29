"""Send alarm info from Aodh to SO via MON."""

import json
import logging as log

from collections import OrderedDict

from kafka import KafkaConsumer

from plugins.OpenStack.Aodh.aodh_common import Aodh_Common


class Alarming(object):
    """Receives alarm info from Aodh."""

    def __init__(self):
        """Create the aodh_receiver instance."""
        self._aodh_common = Aodh_Common()

        # Initialize a generic consumer object to consume message from the SO
        server = {'server': 'localhost:9092', 'topic': 'alarms'}
        self._consumer = KafkaConsumer(server['topic'],
                                       group_id='my-group',
                                       bootstrap_servers=server['server'])

        # TODO(mcgoughh): Initialize a producer to send messages bask to the SO

    def alarming(self):
        """Consume info from the message bus to manage alarms."""
        # Generate authentication credentials to access keystone;
        # auth_token, endpoint
        auth_token = self._aodh_common._authenticate()
        endpoint = self._aodh_common.get_endpoint()

        # Check the alarming functionlity that needs to be performed
        for message in self._consumer:
            if message.topic == "alarms":
                log.info("Alarm action required: %s" % (message.topic))

                if message.key == "configure_alarm":
                    # Configure/Update an alarm
                    alarm_details = json.loads(message.value)
                    alarm_id = self.configure_alarm(endpoint,
                                                    auth_token, alarm_details)
                    log.info("New alarm created with alarmID: %s", alarm_id)

                    # TODO(mcgoughh): will send an acknowledge message back on
                    # the bus via the producer

                else:
                    # TODO(mcoughh): Key alternatives are "notify_alarm" and
                    # "acknowledge_alarm" will be accomodated later
                    log.debug("Unknown key, no action will be performed")
            else:
                log.info("Message topic not relevant to this plugin: %s",
                         message.topic)

        return

    def alarm_check(self, endpoint, auth_token, alarm_name):
        """Get a list of alarms that exist in Aodh."""
        url = "{}/v2/alarms/".format(endpoint)

        # TODO(mcgoughh): will query on resource_id once it has been
        # implemented need to create the query field when creating
        # the alarm
        query = OrderedDict([("q.field", 'name'), ("q.op", "eq"),
                            ("q.value", str(alarm_name))])

        result = self._aodh_common._perform_request(
            url, auth_token, req_type="get", params=query)

        try:
            alarm_id = json.loads(result.text)[0]['alarm_id']
            log.info("An existing alarm was found: %s", alarm_id)
            return alarm_id
        except Exception:
            log.debug("Alarm doesn't exist, needs to be created.")
            return None

    def configure_alarm(self, endpoint, auth_token, values):
        """Get a list of alarms that exist in Aodh."""
        alarm_id = None

        # TODO(mcgoughh): error check the values sent in the messag
        alarm_name = values['name']

        # Check that this alarm doesn't exist already
        alarm_id = self.alarm_check(endpoint, auth_token, alarm_name)

        if alarm_id is None:
            url = "{}/v2/alarms/".format(endpoint)
            severity = values['severity']

            # Create a new threshold alarm with a resourceID
            # specified as a query
            rule = {'threshold': values['threshold'],
                    'comparison_operator': 'gt',
                    'metric': values['metric'],
                    'resource_id': values['resource_id'],
                    'resource_type': 'generic',
                    'aggregation_method': 'last', }
            payload = json.dumps({'state': 'alarm',
                                  'name': alarm_name,
                                  'severity': self.get_severity(severity),
                                  'type': 'gnocchi_resources_threshold',
                                  'gnocchi_resources_threshold_rule': rule, })

            # Request performed to create alarm
            new_alarm = self._aodh_common._perform_request(
                url, auth_token, req_type="post", payload=payload)

            return json.loads(new_alarm.text)['alarm_id']
        else:
            return alarm_id

    def delete_alarm(self, endpoint, auth_token, alarmID):
        """Delete alarm function."""
        url = "{}/v2/alarms/%s".format(endpoint) % (alarmID)

        self._aodh_common._perform_request(url, auth_token, req_type="delete")
        return None

    def get_severity(self, alarm_severity):
        """Get a normalized severity for Aodh."""
        # This logic can be changed, the other alternative was to have
        # MINOR and MAJOR = "moderate" instead.
        if alarm_severity == "WARNIING":
            aodh_severity = "low"
        elif alarm_severity == "MINOR":
            aodh_severity = "moderate"
        elif (alarm_severity == "MAJOR" or alarm_severity == "CRITICAL"):
            aodh_severity = "critical"
        else:
            aodh_severity = None
            log.warn("Invalid alarm severity configuration")

        log.info("Severity has been normalized for Aodh to: %s", aodh_severity)
        return aodh_severity
