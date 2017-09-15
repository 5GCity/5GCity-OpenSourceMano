# -*- coding: utf-8 -*-

##
# Copyright 2016-2017 VMware Inc.
# This file is part of ETSI OSM
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact:  osslegalrouting@vmware.com
##

"""
Montoring plugin receiver that consumes the request messages &
responds using producer for vROPs
"""

from mon_plugin_vrops import MonPlugin
from kafka_consumer_vrops import vROP_KafkaConsumer
#Core producer
from core.message_bus.producer import KafkaProducer
import json
import logging as log
import traceback

class PluginReceiver():
    """MON Plugin receiver receiving request messages & responding using producer for vROPs
    telemetry plugin
    """
    def __init__(self):
        """Constructor of PluginReceiver
        """

        topics = ['alarm_request', 'metric_request', 'Access_Credentials', 'alarm_response']
        #To Do - Add broker uri
        broker_uri = None
        self.mon_plugin = MonPlugin()
        self.consumer = vROP_KafkaConsumer(topics, broker_uri)
        #Core producer
        self.producer = KafkaProducer()

    def consume(self):
        """Consume the message, act on it & respond
        """
        try:
            for message in self.consumer.vrops_consumer:
                message_values = json.loads(message.value)
                if message_values.has_key('vim_type'):
                    vim_type = message_values['vim_type'].lower()
                if vim_type == 'vmware':
                    log.info("Action required for: {}".format(message.topic))
                    if message.topic == 'alarm_request':
                        if message.key == "create_alarm_request":
                            config_alarm_info = json.loads(message.value)
                            alarm_uuid = self.create_alarm(config_alarm_info['alarm_creation_request'])
                            log.info("Alarm created with alarm uuid: {}".format(alarm_uuid))
                            #Publish message using producer
                            self.publish_create_alarm_status(alarm_uuid, config_alarm_info)
                        elif message.key == "update_alarm_request":
                            update_alarm_info = json.loads(message.value)
                            alarm_uuid = self.update_alarm(update_alarm_info['alarm_update_request'])
                            log.info("In plugin_receiver: Alarm defination updated : alarm uuid: {}".format(alarm_uuid))
                            #Publish message using producer
                            self.publish_update_alarm_status(alarm_uuid, update_alarm_info)
                        elif message.key == "delete_alarm_request":
                            delete_alarm_info = json.loads(message.value)
                            alarm_uuid = self.delete_alarm(delete_alarm_info['alarm_deletion_request'])
                            log.info("In plugin_receiver: Alarm defination deleted : alarm uuid: {}".format(alarm_uuid))
                            #Publish message using producer
                            self.publish_delete_alarm_status(alarm_uuid, delete_alarm_info)
                        elif message.key == "list_alarm_request":
                            request_input = json.loads(message.value)
                            triggered_alarm_list = self.list_alarms(request_input['alarm_list_request'])
                            #Publish message using producer
                            self.publish_list_alarm_response(triggered_alarm_list, request_input)
                    elif message.topic == 'metric_request':
                        if message.key == "read_metric_data_request":
                            metric_request_info = json.loads(message.value)
                            metrics_data = self.mon_plugin.get_metrics_data(metric_request_info)
                            log.info("Collected Metrics Data: {}".format(metrics_data))
                            #Publish message using producer
                            self.publish_metrics_data_status(metrics_data)
                        elif message.key == "create_metric_request":
                            metric_info = json.loads(message.value)
                            metric_status = self.verify_metric(metric_info['metric_create'])
                            #Publish message using producer
                            self.publish_create_metric_response(metric_info, metric_status)
                        elif message.key == "update_metric_request":
                            metric_info = json.loads(message.value)
                            metric_status = self.verify_metric(metric_info['metric_create'])
                            #Publish message using producer
                            self.publish_update_metric_response(metric_info, metric_status)
                        elif message.key == "delete_metric_request":
                            metric_info = json.loads(message.value)
                            #Deleting Metric Data is not allowed. Publish status as False
                            log.warn("Deleting Metric is not allowed: {}".format(metric_info['metric_name']))
                            #Publish message using producer
                            self.publish_delete_metric_response(metric_info)

        except Exception as exp:
            log.error("Exception in receiver: {} {}".format(exp, traceback.format_exc()))

    def create_alarm(self, config_alarm_info):
        """Create alarm using vROPs plugin
        """
        plugin_uuid = self.mon_plugin.configure_rest_plugin()
        alarm_uuid = self.mon_plugin.configure_alarm(config_alarm_info)
        return alarm_uuid

    def publish_create_alarm_status(self, alarm_uuid, config_alarm_info):
        """Publish create alarm status using producer
        """
        topic = 'alarm_response'
        msg_key = 'create_alarm_response'
        response_msg = {"schema_version":1.0,
                         "schema_type":"create_alarm_response",
                         "alarm_creation_response":
                            {"correlation_id":config_alarm_info["alarm_creation_request"]["correlation_id"],
                             "alarm_uuid":alarm_uuid,
                             "status": True if alarm_uuid else False
                            }
                       }
        #Core producer
        self.producer.publish(key=msg_key, value=json.dumps(response_msg), topic=topic)

    def update_alarm(self, update_alarm_info):
        """Updare already created alarm
        """
        alarm_uuid = self.mon_plugin.update_alarm_configuration(update_alarm_info)
        return alarm_uuid

    def publish_update_alarm_status(self, alarm_uuid, update_alarm_info):
        """Publish update alarm status requests using producer
        """
        topic = 'alarm_response'
        msg_key = 'update_alarm_response'
        response_msg = {"schema_version":1.0,
                         "schema_type":"update_alarm_response",
                         "alarm_update_response":
                            {"correlation_id":update_alarm_info["alarm_update_request"]["correlation_id"],
                             "alarm_uuid":alarm_uuid,
                             "status": True if alarm_uuid else False
                            }
                       }
        #Core producer
        self.producer.publish(key=msg_key, value=json.dumps(response_msg), topic=topic)

    def delete_alarm(self, delete_alarm_info):
        """Delete alarm configuration
        """
        alarm_uuid = self.mon_plugin.delete_alarm_configuration(delete_alarm_info)
        return alarm_uuid

    def publish_delete_alarm_status(self, alarm_uuid, delete_alarm_info):
        """Publish update alarm status requests using producer
        """
        topic = 'alarm_response'
        msg_key = 'delete_alarm_response'
        response_msg = {"schema_version":1.0,
                         "schema_type":"delete_alarm_response",
                         "alarm_deletion_response":
                            {"correlation_id":delete_alarm_info["alarm_deletion_request"]["correlation_id"],
                             "alarm_uuid":alarm_uuid,
                             "status": True if alarm_uuid else False
                            }
                       }
        #Core producer
        self.producer.publish(key=msg_key, value=json.dumps(response_msg), topic=topic)


    def publish_metrics_data_status(self, metrics_data):
        """Publish the requested metric data using producer
        """
        topic = 'metric_response'
        msg_key = 'read_metric_data_response'
        #Core producer
        self.producer.publish(key=msg_key, value=json.dumps(metrics_data), topic=topic)


    def verify_metric(self, metric_info):
        """Verify if metric is supported or not
        """
        metric_key_status = self.mon_plugin.verify_metric_support(metric_info)
        return metric_key_status

    def publish_create_metric_response(self, metric_info, metric_status):
        """Publish create metric response
        """
        topic = 'metric_response'
        msg_key = 'create_metric_response'
        response_msg = {"schema_version":1.0,
                         "schema_type":"create_metric_response",
                         "correlation_id":metric_info['correlation_id'],
                         "metric_create_response":
                            {
                             "metric_uuid":0,
                             "resource_uuid":metric_info['metric_create']['resource_uuid'],
                             "status":metric_status
                            }
                       }
        #Core producer
        self.producer.publish(key=msg_key, value=json.dumps(response_msg), topic=topic)

    def publish_update_metric_response(self, metric_info, metric_status):
        """Publish update metric response
        """
        topic = 'metric_response'
        msg_key = 'update_metric_response'
        response_msg = {"schema_version":1.0,
                        "schema_type":"metric_update_response",
                        "correlation_id":metric_info['correlation_id'],
                        "metric_update_response":
                            {
                             "metric_uuid":0,
                             "resource_uuid":metric_info['metric_create']['resource_uuid'],
                             "status":metric_status
                            }
                       }
        #Core producer
        self.producer.publish(key=msg_key, value=json.dumps(response_msg), topic=topic)

    def publish_delete_metric_response(self, metric_info):
        """
        """
        topic = 'metric_response'
        msg_key = 'delete_metric_response'
        response_msg = {"schema_version":1.0,
                        "schema_type":"delete_metric_response",
                        "correlation_id":metric_info['correlation_id'],
                        "metric_name":metric_info['metric_name'],
                        "metric_uuid":0,
                        "resource_uuid":metric_info['resource_uuid'],
                        "tenant_uuid":metric_info['tenant_uuid'],
                        "status":False
                       }
        #Core producer
        self.producer.publish(key=msg_key, value=json.dumps(response_msg), topic=topic)

    def list_alarms(self, list_alarm_input):
        """
        """
        triggered_alarms = self.mon_plugin.get_triggered_alarms_list(list_alarm_input)
        return triggered_alarms


    def publish_list_alarm_response(self, triggered_alarm_list, list_alarm_input):
        """
        """
        topic = 'alarm_response'
        msg_key = 'list_alarm_response'
        response_msg = {"schema_version":1.0,
                        "schema_type":"list_alarm_response",
                        "correlation_id":list_alarm_input['alarm_list_request']['correlation_id'],
                        "resource_uuid":list_alarm_input['alarm_list_request']['resource_uuid'],
                        "list_alarm_resp":triggered_alarm_list
                       }
        #Core producer
        self.producer.publish(key=msg_key, value=json.dumps(response_msg), topic=topic)


def main():
    log.basicConfig(filename='mon_vrops_log.log',level=log.DEBUG)
    plugin_rcvr = PluginReceiver()
    plugin_rcvr.consume()

if __name__ == "__main__":
    main()

