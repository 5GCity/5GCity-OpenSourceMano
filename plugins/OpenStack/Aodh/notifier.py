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

from core.message_bus.producer import KafkaProducer

from plugins.OpenStack.response import OpenStack_Response
from plugins.OpenStack.singleton import Singleton

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


@Singleton
class Notifier(object):
    """Alarm Notification class."""

    def __init__(self):
        """Initialize alarm notifier."""
        self._response = OpenStack_Response()

        self._producer = KafkaProducer("alarm_response")

    def notify(self, alarming):
        """Send alarm notifications responses to the SO."""
        auth_token, endpoint = alarming.authenticate(None)

        while(1):
            alarm_list = json.loads(alarming.list_alarms(endpoint, auth_token))
            for alarm in alarm_list:
                alarm_id = alarm['alarm_id']
                alarm_name = alarm['name']
                # Send a notification response to the SO on alarm trigger
                if alarm_name in ALARM_NAMES:
                    alarm_state = alarming.get_alarm_state(
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
