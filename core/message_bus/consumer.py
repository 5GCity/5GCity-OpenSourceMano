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

'''
This is a kafka consumer app that reads the messages from the message bus for
alarms and metrics responses.

'''

__author__ = "Prithiv Mohan"
__date__ = "06/Sep/2017"


from kafka import KafkaConsumer
from kafka.errors import KafkaError
import json
import logging
import logging.config
import os


def logging_handler(filename, mode='a+', encoding=None):
    if not os.path.exists(filename):
        open(filename, 'a').close()
    return logging.FileHandler(filename, mode)

log_config = {
    'version': 1,
    'formatters': {
        'default': {
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s'
        },
    },
    'handlers': {
        'file': {
            '()': logging_handler,
            'level': 'DEBUG',
            'formatter': 'default',
            'filename': '/var/log/osm_mon.log',
            'mode': 'a+',
            'encoding': 'utf-8',
        },
    },
    'kafka': {
        'handlers': ['file'],
        'level': 'DEBUG',
    },
    'root': {
        'handlers': ['file'],
        'level': 'DEBUG',
    },
}


logging.config.dictConfig(log_config)
logger = logging.getLogger('kafka')

if "BROKER_URI" in os.environ:
    broker = os.getenv("BROKER_URI")
else:
    broker = "localhost:9092"

alarm_consumer = KafkaConsumer(
    'alarm_response', 'osm_mon', bootstrap_servers=broker)
metric_consumer = KafkaConsumer(
    'metric_response', 'osm_mon', bootstrap_servers=broker)
try:
    for message in alarm_consumer:
        logger.debug(message)
    for message in metric_consumer:
        logger.debug(message)
except KafkaError:
    log.exception()

alarm_consumer.subscribe('alarm_response')
metric_consumer.subscribe('metric_response')
