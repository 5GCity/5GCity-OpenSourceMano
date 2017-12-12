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

import sys
from mon_plugin_vrops import MonPlugin
from kafka_consumer_vrops import vROP_KafkaConsumer
#Core producer
sys.path.append("../../core/message_bus")
from producer import KafkaProducer
#from core.message_bus.producer import KafkaProducer
import json
import logging
import traceback
import os
from xml.etree import ElementTree as XmlElementTree

schema_version = "1.0"
req_config_params = ('vrops_site', 'vrops_user', 'vrops_password',
                    'vcloud-site','admin_username','admin_password',
                    'vcenter_ip','vcenter_port','vcenter_user','vcenter_password',
                    'vim_tenant_name','orgname','tenant_id')
MODULE_DIR = os.path.dirname(__file__)
CONFIG_FILE_NAME = 'vrops_config.xml'
CONFIG_FILE_PATH = os.path.join(MODULE_DIR, CONFIG_FILE_NAME)

def set_logger():
    """Set Logger
    """
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    logger = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler = logging.FileHandler(os.path.join(BASE_DIR,"mon_vrops_log.log"))
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class PluginReceiver():
    """MON Plugin receiver receiving request messages & responding using producer for vROPs
    telemetry plugin
    """
    def __init__(self):
        """Constructor of PluginReceiver
        """


        self.logger = logging.getLogger('PluginReceiver')
        self.logger.setLevel(logging.DEBUG)
        set_logger()

        #Core producer
        self.producer_alarms = KafkaProducer('alarm_response')
        self.producer_metrics = KafkaProducer('metric_response')
        self.producer_access_credentials = KafkaProducer('vim_access_credentials_response')


    def consume(self, message):
        """Consume the message, act on it & respond
        """
        try:
            self.logger.info("Message received:\nTopic={}:{}:{}:\nKey={}\nValue={}"\
                .format(message.topic, message.partition, message.offset, message.key, message.value))
            message_values = json.loads(message.value)
            self.logger.info("Action required for: {}".format(message.topic))
            if message.topic == 'alarm_request':
                if message.key == "create_alarm_request":
                    config_alarm_info = json.loads(message.value)
                    alarm_uuid = self.create_alarm(config_alarm_info['alarm_create_request'])
                    self.logger.info("Alarm created with alarm uuid: {}".format(alarm_uuid))
                    #Publish message using producer
                    self.publish_create_alarm_status(alarm_uuid, config_alarm_info)
                elif message.key == "update_alarm_request":
                    update_alarm_info = json.loads(message.value)
                    alarm_uuid = self.update_alarm(update_alarm_info['alarm_update_request'])
                    self.logger.info("Alarm defination updated : alarm uuid: {}".format(alarm_uuid))
                    #Publish message using producer
                    self.publish_update_alarm_status(alarm_uuid, update_alarm_info)
                elif message.key == "delete_alarm_request":
                    delete_alarm_info = json.loads(message.value)
                    alarm_uuid = self.delete_alarm(delete_alarm_info['alarm_delete_request'])
                    self.logger.info("Alarm defination deleted : alarm uuid: {}".format(alarm_uuid))
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
                    mon_plugin_obj = MonPlugin()
                    metrics_data = mon_plugin_obj.get_metrics_data(metric_request_info)
                    self.logger.info("Collected Metrics Data: {}".format(metrics_data))
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
                    self.logger.warn("Deleting Metric is not allowed: {}".format(metric_info['metric_name']))
                    #Publish message using producer
                    self.publish_delete_metric_response(metric_info)
            elif message.topic == 'access_credentials':
                if message.key == "vim_access_credentials":
                    access_info = json.loads(message.value)
                    access_update_status = self.update_access_credentials(access_info['access_config'])
                    self.publish_access_update_response(access_update_status, access_info)

        except:
            self.logger.error("Exception in vROPs plugin receiver: {}".format(traceback.format_exc()))


    def create_alarm(self, config_alarm_info):
        """Create alarm using vROPs plugin
        """
        mon_plugin = MonPlugin()
        plugin_uuid = mon_plugin.configure_rest_plugin()
        alarm_uuid = mon_plugin.configure_alarm(config_alarm_info)
        return alarm_uuid

    def publish_create_alarm_status(self, alarm_uuid, config_alarm_info):
        """Publish create alarm status using producer
        """
        topic = 'alarm_response'
        msg_key = 'create_alarm_response'
        response_msg = {"schema_version":schema_version,
                         "schema_type":"create_alarm_response",
                         "alarm_create_response":
                            {"correlation_id":config_alarm_info["alarm_create_request"]["correlation_id"],
                             "alarm_uuid":alarm_uuid,
                             "status": True if alarm_uuid else False
                            }
                       }
        self.logger.info("Publishing response:\nTopic={}\nKey={}\nValue={}"\
                .format(topic, msg_key, response_msg))
        #Core producer
        self.producer_alarms.publish(key=msg_key, value=json.dumps(response_msg), topic=topic)

    def update_alarm(self, update_alarm_info):
        """Updare already created alarm
        """
        mon_plugin = MonPlugin()
        alarm_uuid = mon_plugin.update_alarm_configuration(update_alarm_info)
        return alarm_uuid

    def publish_update_alarm_status(self, alarm_uuid, update_alarm_info):
        """Publish update alarm status requests using producer
        """
        topic = 'alarm_response'
        msg_key = 'update_alarm_response'
        response_msg = {"schema_version":schema_version,
                         "schema_type":"update_alarm_response",
                         "alarm_update_response":
                            {"correlation_id":update_alarm_info["alarm_update_request"]["correlation_id"],
                             "alarm_uuid":update_alarm_info["alarm_update_request"]["alarm_uuid"] \
                             if update_alarm_info["alarm_update_request"].get('alarm_uuid') is not None else None,
                             "status": True if alarm_uuid else False
                            }
                       }
        self.logger.info("Publishing response:\nTopic={}\nKey={}\nValue={}"\
                .format(topic, msg_key, response_msg))
        #Core producer
        self.producer_alarms.publish(key=msg_key, value=json.dumps(response_msg), topic=topic)

    def delete_alarm(self, delete_alarm_info):
        """Delete alarm configuration
        """
        mon_plugin = MonPlugin()
        alarm_uuid = mon_plugin.delete_alarm_configuration(delete_alarm_info)
        return alarm_uuid

    def publish_delete_alarm_status(self, alarm_uuid, delete_alarm_info):
        """Publish update alarm status requests using producer
        """
        topic = 'alarm_response'
        msg_key = 'delete_alarm_response'
        response_msg = {"schema_version":schema_version,
                         "schema_type":"delete_alarm_response",
                         "alarm_deletion_response":
                            {"correlation_id":delete_alarm_info["alarm_delete_request"]["correlation_id"],
                             "alarm_uuid":delete_alarm_info["alarm_delete_request"]["alarm_uuid"],
                             "status": True if alarm_uuid else False
                            }
                       }
        self.logger.info("Publishing response:\nTopic={}\nKey={}\nValue={}"\
                .format(topic, msg_key, response_msg))
        #Core producer
        self.producer_alarms.publish(key=msg_key, value=json.dumps(response_msg), topic=topic)


    def publish_metrics_data_status(self, metrics_data):
        """Publish the requested metric data using producer
        """
        topic = 'metric_response'
        msg_key = 'read_metric_data_response'
        self.logger.info("Publishing response:\nTopic={}\nKey={}\nValue={}"\
                .format(topic, msg_key, metrics_data))
        #Core producer
        self.producer_metrics.publish(key=msg_key, value=json.dumps(metrics_data), topic=topic)


    def verify_metric(self, metric_info):
        """Verify if metric is supported or not
        """
        mon_plugin = MonPlugin()
        metric_key_status = mon_plugin.verify_metric_support(metric_info)
        return metric_key_status

    def publish_create_metric_response(self, metric_info, metric_status):
        """Publish create metric response
        """
        topic = 'metric_response'
        msg_key = 'create_metric_response'
        response_msg = {"schema_version":schema_version,
                         "schema_type":"create_metric_response",
                         "correlation_id":metric_info['correlation_id'],
                         "metric_create_response":
                            {
                             "metric_uuid":'0',
                             "resource_uuid":metric_info['metric_create']['resource_uuid'],
                             "status":metric_status
                            }
                       }
        self.logger.info("Publishing response:\nTopic={}\nKey={}\nValue={}"\
                .format(topic, msg_key, response_msg))
        #Core producer
        self.producer_metrics.publish(key=msg_key, value=json.dumps(response_msg), topic=topic)

    def publish_update_metric_response(self, metric_info, metric_status):
        """Publish update metric response
        """
        topic = 'metric_response'
        msg_key = 'update_metric_response'
        response_msg = {"schema_version":schema_version,
                        "schema_type":"metric_update_response",
                        "correlation_id":metric_info['correlation_id'],
                        "metric_update_response":
                            {
                             "metric_uuid":'0',
                             "resource_uuid":metric_info['metric_create']['resource_uuid'],
                             "status":metric_status
                            }
                       }
        self.logger.info("Publishing response:\nTopic={}\nKey={}\nValue={}"\
                .format(topic, msg_key, response_msg))
        #Core producer
        self.producer_metrics.publish(key=msg_key, value=json.dumps(response_msg), topic=topic)

    def publish_delete_metric_response(self, metric_info):
        """
        """
        topic = 'metric_response'
        msg_key = 'delete_metric_response'
        if metric_info.has_key('tenant_uuid') and metric_info['tenant_uuid'] is not None:
            tenant_uuid = metric_info['tenant_uuid']
        else:
            tenant_uuid = None

        response_msg = {"schema_version":schema_version,
                        "schema_type":"delete_metric_response",
                        "correlation_id":metric_info['correlation_id'],
                        "metric_name":metric_info['metric_name'],
                        "metric_uuid":'0',
                        "resource_uuid":metric_info['resource_uuid'],
                        "tenant_uuid":tenant_uuid,
                        "status":False
                       }
        self.logger.info("Publishing response:\nTopic={}\nKey={}\nValue={}"\
                .format(topic, msg_key, response_msg))
        #Core producer
        self.producer_metrics.publish(key=msg_key, value=json.dumps(response_msg), topic=topic)

    def list_alarms(self, list_alarm_input):
        """Collect list of triggered alarms based on input
        """
        mon_plugin = MonPlugin()
        triggered_alarms = mon_plugin.get_triggered_alarms_list(list_alarm_input)
        return triggered_alarms


    def publish_list_alarm_response(self, triggered_alarm_list, list_alarm_input):
        """Publish list of triggered alarms
        """
        topic = 'alarm_response'
        msg_key = 'list_alarm_response'
        response_msg = {"schema_version":schema_version,
                        "schema_type":"list_alarm_response",
                        "correlation_id":list_alarm_input['alarm_list_request']['correlation_id'],
                        "list_alarm_resp":triggered_alarm_list
                       }
        self.logger.info("Publishing response:\nTopic={}\nKey={}\nValue={}"\
                .format(topic, msg_key, response_msg))
        #Core producer
        self.producer_alarms.publish(key=msg_key, value=json.dumps(response_msg), topic=topic)


    def update_access_credentials(self, access_info):
        """Verify if all the required access config params are provided and
           updates access config in default vrops config file
        """
        update_status = False
        wr_status = False
        #Check if all the required config params are passed in request
        if not all (keys in access_info for keys in req_config_params):
            self.logger.debug("All required Access Config Parameters not provided")
            self.logger.debug("List of required Access Config Parameters: {}".format(req_config_params))
            self.logger.debug("List of given Access Config Parameters: {}".format(access_info))
            return update_status

        wr_status = self.write_access_config(access_info)
        return wr_status    #True/False

    def write_access_config(self, access_info):
        """Write access configuration to vROPs config file.
        """
        wr_status = False
        try:
            tree = XmlElementTree.parse(CONFIG_FILE_PATH)
            root = tree.getroot()
            alarmParams = {}
            for config in root:
                if config.tag == 'Access_Config':
                    for param in config:
                        for key,val in access_info.iteritems():
                            if param.tag == key:
                                #print param.tag, val
                                param.text = val

            tree.write(CONFIG_FILE_PATH)
            wr_status = True
        except Exception as exp:
            self.logger.warn("Failed to update Access Config Parameters: {}".format(exp))

        return wr_status


    def publish_access_update_response(self, access_update_status, access_info_req):
        """Publish access update response
        """
        topic = 'access_credentials'
        msg_key = 'vim_access_credentials_response'
        response_msg = {"schema_version":schema_version,
                        "schema_type":"vim_access_credentials_response",
                        "correlation_id":access_info_req['access_config']['correlation_id'],
                        "status":access_update_status
                       }
        self.logger.info("Publishing response:\nTopic={}\nKey={}\nValue={}"\
                .format(topic, msg_key, response_msg))
        #Core Add producer
        self.producer_access_credentials.publish(key=msg_key, value=json.dumps(response_msg), topic=topic)

"""
def main():
    #log.basicConfig(filename='mon_vrops_log.log',level=log.DEBUG)
    set_logger()
    plugin_rcvr = PluginReceiver()
    plugin_rcvr.consume()

if __name__ == "__main__":
    main()
"""
