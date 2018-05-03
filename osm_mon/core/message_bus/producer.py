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
# contact: prithiv.mohan@intel.com or adrian.hoban@intel.com
##
"""This is a common kafka producer app.

It interacts with the SO and the plugins of the datacenters: OpenStack, VMWare
and AWS.
"""

import logging
import os

from kafka import KafkaProducer as kaf
from kafka.errors import KafkaError

__author__ = "Prithiv Mohan"
__date__ = "06/Sep/2017"

current_path = os.path.realpath(__file__)
json_path = os.path.abspath(os.path.join(current_path, '..', '..', 'models'))

# TODO(): validate all of the request and response messages against the
# json_schemas


class KafkaProducer(object):
    """A common KafkaProducer for requests and responses."""

    def __init__(self, topic):
        """Initialize the common kafka producer."""
        self._topic = topic

        if "BROKER_URI" in os.environ:
            broker = os.getenv("BROKER_URI")
        else:
            broker = "localhost:9092"

        '''
        If the broker URI is not set in the env by default,
        localhost container is taken as the host because an instance of
        is already running.
        '''

        self.producer = kaf(
            key_serializer=str.encode,
            value_serializer=str.encode,
            bootstrap_servers=broker, api_version=(0, 10))

    def publish(self, key, value, topic=None):
        """Send the required message on the Kafka message bus."""
        try:
            future = self.producer.send(topic=topic, key=key, value=value)
            self.producer.flush()
        except Exception:
            logging.exception("Error publishing to {} topic." .format(topic))
            raise
        try:
            record_metadata = future.get(timeout=10)
            logging.debug("TOPIC:", record_metadata.topic)
            logging.debug("PARTITION:", record_metadata.partition)
            logging.debug("OFFSET:", record_metadata.offset)
        except KafkaError:
            pass

    def create_alarm_request(self, key, message):
        """Create alarm request from SO to MON."""
        # External to MON

        self.publish(key,
                     value=message,
                     topic='alarm_request')

    def create_alarm_response(self, key, message):
        """Response to a create alarm request from MON to SO."""
        # Internal to MON

        self.publish(key,
                     value=message,
                     topic='alarm_response')

    def acknowledge_alarm(self, key, message):
        """Alarm acknowledgement request from SO to MON."""
        # Internal to MON

        self.publish(key,
                     value=message,
                     topic='alarm_request')

    def list_alarm_request(self, key, message):
        """List alarms request from SO to MON."""
        # External to MON

        self.publish(key,
                     value=message,
                     topic='alarm_request')

    def notify_alarm(self, key, message):
        """Notify of triggered alarm from MON to SO."""

        self.publish(key,
                     value=message,
                     topic='alarm_response')

    def list_alarm_response(self, key, message):
        """Response for list alarms request from MON to SO."""

        self.publish(key,
                     value=message,
                     topic='alarm_response')

    def update_alarm_request(self, key, message):
        """Update alarm request from SO to MON."""
        # External to Mon

        self.publish(key,
                     value=message,
                     topic='alarm_request')

    def update_alarm_response(self, key, message):
        """Response from update alarm request from MON to SO."""
        # Internal to Mon

        self.publish(key,
                     value=message,
                     topic='alarm_response')

    def delete_alarm_request(self, key, message):
        """Delete alarm request from SO to MON."""
        # External to Mon

        self.publish(key,
                     value=message,
                     topic='alarm_request')

    def delete_alarm_response(self, key, message):
        """Response for a delete alarm request from MON to SO."""
        # Internal to Mon

        self.publish(key,
                     value=message,
                     topic='alarm_response')

    def create_metrics_request(self, key, message):
        """Create metrics request from SO to MON."""
        # External to Mon

        self.publish(key,
                     value=message,
                     topic='metric_request')

    def create_metrics_resp(self, key, message):
        """Response for a create metric request from MON to SO."""
        # Internal to Mon

        self.publish(key,
                     value=message,
                     topic='metric_response')

    def read_metric_data_request(self, key, message):
        """Read metric data request from SO to MON."""
        # External to Mon

        self.publish(key,
                     value=message,
                     topic='metric_request')

    def read_metric_data_response(self, key, message):
        """Response from MON to SO for read metric data request."""
        # Internal to Mon

        self.publish(key,
                     value=message,
                     topic='metric_response')

    def list_metric_request(self, key, message):
        """List metric request from SO to MON."""
        # External to MON

        self.publish(key,
                     value=message,
                     topic='metric_request')

    def list_metric_response(self, key, message):
        """Response from SO to MON for list metrics request."""
        # Internal to MON

        self.publish(key,
                     value=message,
                     topic='metric_response')

    def delete_metric_request(self, key, message):
        """Delete metric request from SO to MON."""
        # External to Mon

        self.publish(key,
                     value=message,
                     topic='metric_request')

    def delete_metric_response(self, key, message):
        """Response from MON to SO for delete metric request."""
        # Internal to Mon

        self.publish(key,
                     value=message,
                     topic='metric_response')

    def update_metric_request(self, key, message):
        """Metric update request from SO to MON."""
        # External to Mon

        self.publish(key,
                     value=message,
                     topic='metric_request')

    def update_metric_response(self, key, message):
        """Reponse from MON to SO for metric update."""
        # Internal to Mon

        self.publish(key,
                     value=message,
                     topic='metric_response')

    def access_credentials(self, key, message):
        """Send access credentials to MON from SO."""

        self.publish(key,
                     value=message,
                     topic='access_credentials')
