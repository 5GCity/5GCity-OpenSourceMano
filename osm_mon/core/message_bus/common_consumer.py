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

logging.basicConfig(stream=sys.stdout,
                    format='%(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.INFO)
log = logging.getLogger(__name__)

sys.path.append(os.path.abspath(os.path.join(os.path.realpath(__file__), '..', '..', '..', '..')))

from kafka import KafkaConsumer

from osm_mon.plugins.OpenStack.Aodh import alarming
from osm_mon.plugins.OpenStack.common import Common
from osm_mon.plugins.OpenStack.Gnocchi import metrics

from osm_mon.plugins.CloudWatch.plugin_alarm import plugin_alarms
from osm_mon.plugins.CloudWatch.plugin_metric import plugin_metrics
from osm_mon.plugins.CloudWatch.connection import Connection
from osm_mon.plugins.CloudWatch.access_credentials import AccessCredentials

from osm_mon.plugins.vRealiseOps import plugin_receiver

from osm_mon.core.auth import AuthManager
from osm_mon.core.database import DatabaseManager

# Initialize servers
if "BROKER_URI" in os.environ:
    server = {'server': os.getenv("BROKER_URI")}
else:
    server = {'server': 'localhost:9092'}

# Initialize consumers for alarms and metrics
common_consumer = KafkaConsumer(bootstrap_servers=server['server'],
                                key_deserializer=bytes.decode,
                                value_deserializer=bytes.decode,
                                group_id="mon-consumer")

auth_manager = AuthManager()
database_manager = DatabaseManager()
database_manager.create_tables()

# Create OpenStack alarming and metric instances
auth_token = None
openstack_auth = Common()
openstack_metrics = metrics.Metrics()
openstack_alarms = alarming.Alarming()

# Create CloudWatch alarm and metric instances
cloudwatch_alarms = plugin_alarms()
cloudwatch_metrics = plugin_metrics()
aws_connection = Connection()
aws_access_credentials = AccessCredentials()

# Create vROps plugin_receiver class instance
vrops_rcvr = plugin_receiver.PluginReceiver()


def get_vim_type(message):
    """Get the vim type that is required by the message."""
    try:
        return json.loads(message.value)["vim_type"].lower()
    except Exception as exc:
        log.warn("vim_type is not configured correctly; %s", exc)
    return None


# Define subscribe the consumer for the plugins
topics = ['metric_request', 'alarm_request', 'access_credentials', 'vim_account']
# TODO: Remove access_credentials
common_consumer.subscribe(topics)

log.info("Listening for alarm_request and metric_request messages")
for message in common_consumer:
    log.info("Message arrived: %s", message)
    try:
        # Check the message topic
        if message.topic == "metric_request":
            # Check the vim desired by the message
            vim_type = get_vim_type(message)

            if vim_type == "openstack":
                log.info("This message is for the OpenStack plugin.")
                openstack_metrics.metric_calls(
                    message, openstack_auth, auth_token)

            elif vim_type == "aws":
                log.info("This message is for the CloudWatch plugin.")
                aws_conn = aws_connection.setEnvironment()
                cloudwatch_metrics.metric_calls(message, aws_conn)

            elif vim_type == "vmware":
                log.info("This metric_request message is for the vROPs plugin.")
                vrops_rcvr.consume(message)

            else:
                log.debug("vim_type is misconfigured or unsupported; %s",
                          vim_type)

        elif message.topic == "alarm_request":
            # Check the vim desired by the message
            vim_type = get_vim_type(message)
            if vim_type == "openstack":
                log.info("This message is for the OpenStack plugin.")
                openstack_alarms.alarming(message, openstack_auth, auth_token)

            elif vim_type == "aws":
                log.info("This message is for the CloudWatch plugin.")
                aws_conn = aws_connection.setEnvironment()
                cloudwatch_alarms.alarm_calls(message, aws_conn)

            elif vim_type == "vmware":
                log.info("This alarm_request message is for the vROPs plugin.")
                vrops_rcvr.consume(message)

            else:
                log.debug("vim_type is misconfigured or unsupported; %s",
                          vim_type)

        elif message.topic == "vim_account":
            if message.key == "create" or message.key == "edit":
                auth_manager.store_auth_credentials(message)
            if message.key == "delete":
                auth_manager.delete_auth_credentials(message)

        # TODO: Remove in the near future. Modify tests accordingly.
        elif message.topic == "access_credentials":
            # Check the vim desired by the message
            vim_type = get_vim_type(message)
            if vim_type == "openstack":
                log.info("This message is for the OpenStack plugin.")
                auth_token = openstack_auth._authenticate(message=message)

            elif vim_type == "aws":
                log.info("This message is for the CloudWatch plugin.")
                aws_access_credentials.access_credential_calls(message)

            elif vim_type == "vmware":
                log.info("This access_credentials message is for the vROPs plugin.")
                vrops_rcvr.consume(message)

            else:
                log.debug("vim_type is misconfigured or unsupported; %s",
                          vim_type)

        else:
            log.info("This topic is not relevant to any of the MON plugins.")


    except Exception as exc:
        log.exception("Exception: %s")
