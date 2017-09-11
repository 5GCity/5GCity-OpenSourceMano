
# Copyright© 2017 Intel Research and Development Ireland Limited
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

'''
This is a kafka consumer app that reads the messages from the message bus for
alarms and metrics responses.

#TODO: (Prithiv Mohan)
 - Modify topics based on new schema definitions
 - Include consumer logging
'''

__author__ = "Prithiv Mohan"
__date__   = "06/Sep/2017"

from kafka import KafkaConsumer
from kafka.errors import KafkaError
import logging

class KafkaConsumer(object):
    """Adds messages to a kafka topic. Topic is hardcoded as 'alarms' and group as
    'my_group' for now.

    """

    def __init__(self, uri):
        """Init

             uri - kafka connection details
        """
        if not cfg.CONF.kafka.uri:
            raise Exception("Kafka URI Not Found. Check the config file for Kafka URI")
        else:
            broker = cfg.CONF.kafka.uri
        consumer = KafkaConsumer('alarms',
            group_id='my_group',
            bootstrap_servers=broker, api_version=(0,10))
        #KafkaConsumer(value_deserializer=lambda m: json.loads(m.decode('ascii')))

    def consume(self, topic, messages):
        for message in self._consumer:
            print ("%s:%d:%d: key=%s value=%s" % (message.topic, message.partition, message.offset, message.key, message.value))
