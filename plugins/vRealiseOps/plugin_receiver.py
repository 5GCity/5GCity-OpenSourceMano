# -*- coding: utf-8 -*-
"""
Montoring plugin receiver that consumes the request messages &
responds using producer for vROPs
"""

from mon_plugin_vrops import MonPlugin
from kafka_consumer_vrops import vROP_KafkaConsumer
#To Do- Change producer
#from core.message_bus.producer import KafkaProducer
import json
import logging as log

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
        #To Do- Change producer
        #self.producer = KafkaProducer()

    def consume(self):
        """Consume the message, act on it & respond
        """
        try:
            for message in self.consumer.vrops_consumer:
                if message.topic == 'alarm_request':
                    if message.key == "create_alarm_request":
                        config_alarm_info = json.loads(message.value)
                        alarm_uuid = self.create_alarm(config_alarm_info['alarm_creation_request'])
                        log.info("Alarm created with alarm uuid: {}".format(alarm_uuid))
                        #To Do - Publish message using producer
                        #self.publish_create_alarm_status(alarm_uuid, config_alarm_info)
                    elif message.key == "update_alarm_request":
                        update_alarm_info = json.loads(message.value)
                        alarm_uuid = self.update_alarm(update_alarm_info['alarm_creation_request'])
                        log.info("Alarm defination updated : alarm uuid: {}".format(alarm_uuid))
                        #To Do - Publish message using producer
                        #self.publish_update_alarm_status(alarm_uuid, update_alarm_info)
                elif message.topic == 'metric_request':
                    if message.key == "read_metric_data_request":
                        metric_request_info = json.loads(message.value)
                        metrics_data = self.mon_plugin.get_metrics_data(metric_request_info)
                        log.info("Collected Metrics Data: {}".format(metrics_data))
                        #To Do - Publish message using producer
                        #self.publish_metrics_data_status(metrics_data)

        except Exception as exp:
            log.error("Exception in receiver: {}".format(exp))

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
        #To Do - Add producer
        #self.producer.publish(key=msg_key, value=json.dumps(response_msg), topic=topic)

    def update_alarm(self, update_alarm_info):
        """Updare already created alarm
        """
        alarm_uuid = self.mon_plugin.reconfigure_alarm(update_alarm_info)
        return alarm_uuid

    def publish_update_alarm_status(self, alarm_uuid, update_alarm_info):
        """Publish update alarm status requests using producer
        """
        topic = 'alarm_response'
        msg_key = 'update_alarm_response'
        response_msg = {"schema_version":1.0,
                         "schema_type":"update_alarm_response",
                         "alarm_update_response":
                            {"correlation_id":update_alarm_info["alarm_creation_request"]["correlation_id"],
                             "alarm_uuid":alarm_uuid,
                             "status": True if alarm_uuid else False
                            }
                       }
        #To Do - Add producer
        #self.producer.publish(key=msg_key, value=json.dumps(response_msg), topic=topic)

    def publish_metrics_data_status(self, metrics_data):
        """Publish the requested metric data using producer
        """
        topic = 'metric_response'
        msg_key = 'read_metric_data_response'
        #To Do - Add producer
        #self.producer.publish(key=msg_key, value=json.dumps(metrics_data), topic=topic)

#For testing
#log.basicConfig(filename='mon_vrops_log.log',level=log.DEBUG)
#plugin_rcvr = PluginReceiver()
#plugin_rcvr.consume()

