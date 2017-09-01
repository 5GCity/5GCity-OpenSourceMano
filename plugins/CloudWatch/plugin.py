##
# Copyright 2017 xFlow Research Pvt. Ltd
# This file is part of MON module
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
# contact with: wajeeha.hamid@xflowresearch.com
##

'''
AWS-Plugin implements all the methods of MON to interact with AWS using the BOTO client
'''

__author__ = "Wajeeha Hamid"
__date__   = "31-August-2017"

import sys
from connection import Connection
from metric_alarms import MetricAlarm
try:
    from kafka import KafkaConsumer
    from kafka.errors import KafkaError
except:
    exit("Kafka Error. Try activating your Kafka Services")

class Plugin():
    """Receives Alarm info from MetricAlarm and connects with the consumer/producer """
    def __init__ (self): 
        self.conn = Connection()
        self.metricAlarm = MetricAlarm()

        server = {'server': 'localhost:9092', 'topic': 'alarms'}
    #Initialize a Consumer object to consume message from the SO    
        self._consumer = KafkaConsumer(server['topic'],
                                       group_id='my-group',
                                       bootstrap_servers=server['server'])
#---------------------------------------------------------------------------------------------------------------------------      
    def connection(self):
        """Connecting instances with CloudWatch"""
        self.conn.setEnvironment()
        self.cloudwatch_conn = self.conn.connection_instance()
#---------------------------------------------------------------------------------------------------------------------------   
    def configure_alarm(self,alarm_info):

        alarm_id = self.metricAlarm.config_alarm(self.cloudwatch_conn,alarm_info)
        return alarm_id
#---------------------------------------------------------------------------------------------------------------------------          
    def update_alarm_configuration(self,test):
        alarm_id = self.metricAlarm.update_alarm(self.cloudwatch_conn,test)
        return alarm_id
#---------------------------------------------------------------------------------------------------------------------------            
    def delete_alarm(self,alarm_id):
        return self.metricAlarm.delete_Alarm(self.cloudwatch_conn,alarm_id)
#---------------------------------------------------------------------------------------------------------------------------  
    def get_alarms_list(self,instance_id):
        return self.metricAlarm.alarms_list(self.cloudwatch_conn,instance_id) 
#---------------------------------------------------------------------------------------------------------------------------            
    def get_alarm_details(self,alarm_id):
        return self.metricAlarm.alarm_details(self.cloudwatch_conn,alarm_id)
#---------------------------------------------------------------------------------------------------------------------------            
    def get_metrics_data(self,metric_name,instance_id,period,metric_unit):
        return self.metricAlarm.metrics_data(self.cloudwatch_conn,metric_name,instance_id,period,metric_unit)
#---------------------------------------------------------------------------------------------------------------------------   
    def consumer(self,alarm_info):
        try:
            for message in self._consumer:

                # Check the Functionlity that needs to be performed: topic = 'alarms'/'metrics'/'Access_Credentials'
                if message.topic == "alarms":
                    log.info("Action required against: %s" % (message.topic))

                    if message.key == "Configure_Alarm":
                        #alarm_info = json.loads(message.value)
                        alarm_id = self.configure_alarm(alarm_info) #alarm_info = message.value
                        log.info("New alarm created with alarmID: %s", alarm_id)
                #Keys other than Configure_Alarm and Notify_Alarm are already handled here which are not yet finalized
                    elif message.key == "Notify_Alarm":
                        alarm_details = self.get_alarm_details(alarm_info['alarm_name'])#['alarm_id']

                    elif message.key == "Update_Alarm":
                        alarm_id = self.update_alarm_configuration(alarm_info)
                        log.info("Alarm Updated with alarmID: %s", alarm_id)
                    
                    elif message.key == "Delete_Alarm":    
                        alarm_id = self.delete_alarm(alarm_info['alarm_name'])
                        log.info("Alarm Deleted with alarmID: %s", alarm_id)
                   
                    elif message.key == "Alarms_List":    
                        self.get_alarms_list(alarm_info['resource_id'])#['alarm_names']
                    else:
                        log.debug("Unknown key, no action will be performed")
                else:
                    log.info("Message topic not relevant to this plugin: %s",
                         message.topic)    
        except Exception as e:
                log.error("Consumer exception: %s", str(e))             
#---------------------------------------------------------------------------------------------------------------------------   
"""For Testing Purpose: Required calls to Trigger defined functions """
'''obj = Plugin()
obj.connection() 
obj.consumer()

alarm_info = dict()
alarm_info['resource_id'] = 'i-098da78cbd8304e17'
alarm_info['alarm_name'] = 'alarm-6'
alarm_info['alarm_metric'] = 'CPUUtilization'
alarm_info['alarm_severity'] = 'Critical'
alarm_info['instance_type'] = 'AWS/EC2'
alarm_info['alarm_statistics'] = 'Maximum'
alarm_info['alarm_comparison'] = '>='
alarm_info['alarm_threshold'] = 1.5
alarm_info['alarm_period'] = 60
alarm_info['alarm_evaluation_period'] = 1
alarm_info['alarm_unit'] = None
alarm_info['alarm_description'] = ''

#obj.configure_alarm(alarm_info)
#obj.update_alarm_configuration(alarm_info)
#obj.delete_alarm('alarm-5|i-098da78cbd8304e17')
#obj.get_alarms_list('i-098da78cbd8304e17')#['alarm_names']
#obj.get_alarm_details('alarm-5|i-098da78cbd8304e17')#['alarm_id']
#print obj.get_metrics_data('CPUUtilization','i-09462760703837b26','60',None)      '''