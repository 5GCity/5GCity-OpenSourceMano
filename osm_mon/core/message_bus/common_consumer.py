# Copyright 2017 Intel Research and Development Ireland Limited
# *************************************************************
# This file is part of OSM Monitoring module
# All Rights Reserved to Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License. You may
# obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact: helena.mcgough@intel.com or adrian.hoban@intel.com
"""A common KafkaConsumer for all MON plugins."""

import json
import logging
import os
import sys

import yaml

from osm_mon.core.settings import Config

logging.basicConfig(stream=sys.stdout,
                    format='%(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.INFO)
log = logging.getLogger(__name__)

sys.path.append(os.path.abspath(os.path.join(os.path.realpath(__file__), '..', '..', '..', '..')))

from kafka import KafkaConsumer

from osm_mon.plugins.OpenStack.Aodh import alarming
from osm_mon.plugins.OpenStack.Gnocchi import metrics

from osm_mon.plugins.CloudWatch.plugin_alarm import plugin_alarms
from osm_mon.plugins.CloudWatch.plugin_metric import plugin_metrics
from osm_mon.plugins.CloudWatch.connection import Connection
from osm_mon.plugins.CloudWatch.access_credentials import AccessCredentials

from osm_mon.plugins.vRealiseOps import plugin_receiver

from osm_mon.core.auth import AuthManager
from osm_mon.core.database import DatabaseManager

cfg = Config.instance()
cfg.read_environ()

# Initialize consumers for alarms and metrics
common_consumer = KafkaConsumer(bootstrap_servers=cfg.BROKER_URI,
                                key_deserializer=bytes.decode,
                                value_deserializer=bytes.decode,
                                group_id="mon-consumer")

auth_manager = AuthManager()
database_manager = DatabaseManager()
database_manager.create_tables()

# Create OpenStack alarming and metric instances
openstack_metrics = metrics.Metrics()
openstack_alarms = alarming.Alarming()

# Create CloudWatch alarm and metric instances
cloudwatch_alarms = plugin_alarms()
cloudwatch_metrics = plugin_metrics()
aws_connection = Connection()
aws_access_credentials = AccessCredentials()

# Create vROps plugin_receiver class instance
vrops_rcvr = plugin_receiver.PluginReceiver()


def get_vim_type(vim_uuid):
    """Get the vim type that is required by the message."""
    try:
        credentials = database_manager.get_credentials(vim_uuid)
        return credentials.type
    except Exception:
        log.exception("Error getting vim_type: ")
    return None


# Define subscribe the consumer for the plugins
topics = ['metric_request', 'alarm_request', 'access_credentials', 'vim_account']
# TODO: Remove access_credentials
common_consumer.subscribe(topics)

log.info("Listening for alarm_request and metric_request messages")
for message in common_consumer:
    log.info("Message arrived: %s", message)
    try:
        try:
            values = json.loads(message.value)
        except ValueError:
            values = yaml.safe_load(message.value)

        if message.topic == "vim_account":
            if message.key == "create" or message.key == "edit":
                auth_manager.store_auth_credentials(values)
            if message.key == "delete":
                auth_manager.delete_auth_credentials(values)

        else:
            # Check the vim desired by the message
            vim_type = get_vim_type(values['vim_uuid'])
            if vim_type == "openstack":
                log.info("This message is for the OpenStack plugin.")
                if message.topic == "metric_request":
                    openstack_metrics.metric_calls(message)
                if message.topic == "alarm_request":
                    openstack_alarms.alarming(message)

            elif vim_type == "aws":
                log.info("This message is for the CloudWatch plugin.")
                aws_conn = aws_connection.setEnvironment()
                if message.topic == "metric_request":
                    cloudwatch_metrics.metric_calls(message, aws_conn)
                if message.topic == "alarm_request":
                    cloudwatch_alarms.alarm_calls(message, aws_conn)
                if message.topic == "access_credentials":
                    aws_access_credentials.access_credential_calls(message)

            elif vim_type == "vmware":
                log.info("This metric_request message is for the vROPs plugin.")
                vrops_rcvr.consume(message)

            else:
                log.debug("vim_type is misconfigured or unsupported; %s",
                          vim_type)

    except Exception:
        log.exception("Exception processing message: ")
