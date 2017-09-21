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
"""Notifier class for alarm notification response."""

import json
import logging as log

try:
    import aodhclient
except ImportError:
    log.warn("Failed to import the aodhclient")


from core.message_bus.producer import KafkaProducer

from plugins.OpenStack.Aodh.alarming import Alarming
from plugins.OpenStack.response import OpenStack_Response
from plugins.OpenStack.settings import Config

__author__ = "Helena McGough"

ALARM_NAMES = [
    "average_memory_usage_above_threshold",
    "disk_read_ops",
    "disk_write_ops",
    "disk_read_bytes",
    "disk_write_bytes",
    "net_packets_dropped",
    "packets_in_above_threshold",
    "packets_out_above_threshold",
    "cpu_utilization_above_threshold"]


def register_notifier():
    """Run the notifier instance."""
    config = Config.instance()
    instance = Notifier(config=config)
    instance.config()
    instance.notify()


class Notifier(object):
    """Alarm Notification class."""

    def __init__(self, config):
        """Initialize alarm notifier."""
        log.info("Initialize the notifier for the SO.")
        self._config = config
        self._response = OpenStack_Response()
        self._producer = KafkaProducer("alarm_response")
        self._alarming = Alarming()

    def config(self):
        """Configure the alarm notifier."""
        log.info("Configure the notifier instance.")
        self._config.read_environ("aodh")

    def notify(self):
        """Send alarm notifications responses to the SO."""
        log.info("Checking for alarm notifications")
        auth_token, endpoint = self._alarming.authenticate()

        while(1):
            alarm_list = self._alarming.list_alarms(endpoint, auth_token)
            for alarm in json.loads(alarm_list):
                alarm_id = alarm['alarm_id']
                alarm_name = alarm['name']
                # Send a notification response to the SO on alarm trigger
                if alarm_name in ALARM_NAMES:
                    alarm_state = self._alarming.get_alarm_state(
                        endpoint, auth_token, alarm_id)
                    if alarm_state == "alarm":
                        # Generate and send an alarm notification response
                        try:
                            a_date = alarm['state_timestamp'].replace("T", " ")
                            rule = alarm['gnocchi_resources_threshold_rule']
                            resp_message = self._response.generate_response(
                                'notify_alarm', a_id=alarm_id,
                                r_id=rule['resource_id'],
                                sev=alarm['severity'], date=a_date,
                                state=alarm_state, vim_type="OpenStack")
                            self._producer.notify_alarm(
                                'notify_alarm', resp_message, 'alarm_response')
                        except Exception as exc:
                            log.warn("Failed to send notify response:%s", exc)

if aodhclient:
    register_notifier()
