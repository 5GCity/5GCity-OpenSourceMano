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
__date__   = "18-September-2017"

import sys
import json
import logging
from jsmin import jsmin
from connection import Connection
from metric_alarms import MetricAlarm
from metrics import Metrics
sys.path.append("../../core/message_bus")
from producer import KafkaProducer

log = logging.getLogger(__name__)

class plugin_alarms():
    """Receives Alarm info from MetricAlarm and connects with the consumer/producer"""
    def __init__ (self): 
        self.metricAlarm = MetricAlarm()
        self.metric = Metrics()
        self.producer = KafkaProducer('')     
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
    def get_ack_details(self,ack_info):
        return self.metricAlarm.alarm_details(self.cloudwatch_conn,ack_info)
#---------------------------------------------------------------------------------------------------------------------------            
    def get_metrics_data(self,metric_name,period,instance_id):
        return self.metric.metricsData(self.cloudwatch_conn,metric_name,period,instance_id)
#--------------------------------------------------------------------------------------------------------------------------- 

    def alarm_calls(self,message,aws_conn):
        """Gets the message from the common consumer"""
        try:
            self.cloudwatch_conn = aws_conn['cloudwatch_connection']
            self.ec2_conn = aws_conn['ec2_connection'] 

            log.info("Action required against: %s" % (message.topic))
            alarm_info = json.loads(message.value)

            if message.key == "create_alarm_request":  
                alarm_inner_dict = alarm_info['alarm_create_request']
                metric_status = self.check_metric(alarm_inner_dict['metric_name'])                            
             
                if self.check_resource(alarm_inner_dict['resource_uuid']) == True and metric_status['status'] == True:
                    log.debug ("Resource and Metrics exists")
                
                    alarm_info['alarm_create_request']['metric_name'] = metric_status['metric_name']
                    #Generate a valid response message, send via producer
                    config_resp = self.configure_alarm(alarm_info) #alarm_info = message.value
             
                    if config_resp == None:
                        log.debug("Alarm Already exists")
                        payload = json.dumps(config_resp)                                   
                        file = open('../../core/models/create_alarm_resp.json','wb').write((payload))
                        self.producer.create_alarm_response(key='create_alarm_response',message=payload,topic = 'alarm_response')
             
                    else: 
                        payload = json.dumps(config_resp)                                
                        file = open('../../core/models/create_alarm_resp.json','wb').write((payload))                           
                        self.producer.create_alarm_response(key='create_alarm_response',message=payload,topic = 'alarm_response')
                        log.info("New alarm created with alarm info: %s", config_resp)                           
             
                else:
                    log.error("Resource ID doesn't exists")                
                
            elif message.key == "acknowledge_alarm":
                alarm_inner_dict = alarm_info['ack_details']
                
                if self.check_resource(alarm_inner_dict['resource_uuid']) == True: 
                    alarm_info = json.loads(message.value)
                    #Generate a valid response message, send via producer
                    ack_details = self.get_ack_details(alarm_info)
                    payload = json.dumps(ack_details)                                  
                    file = open('../../core/models/notify_alarm.json','wb').write((payload))
                    self.producer.notify_alarm(key='notify_alarm',message=payload,topic = 'alarm_response')
                    log.info("Acknowledge sent: %s", ack_details)

                else:
                    log.error("Resource ID is Incorrect")                        


            elif message.key == "update_alarm_request":                         
                alarm_inner_dict = alarm_info['alarm_update_request']
                metric_status = self.check_metric(alarm_inner_dict['metric_name'])
                
                if metric_status['status'] == True:
                    log.debug ("Resource and Metrics exists")
                    alarm_info['alarm_update_request']['metric_name'] = metric_status['metric_name']
                    #Generate a valid response message, send via producer
                    update_resp = self.update_alarm_configuration(alarm_info)

                    if update_resp == None:                                    
                        payload = json.dumps(update_resp)                                   
                        file = open('../../core/models/update_alarm_resp.json','wb').write((payload))
                        self.producer.update_alarm_response(key='update_alarm_response',message=payload,topic = 'alarm_response')
                        log.debug("Alarm Already exists")

                    else: 
                        payload = json.dumps(update_resp)                                   
                        file = open('../../core/models/update_alarm_resp.json','wb').write((payload))
                        self.producer.update_alarm_response(key='update_alarm_response',message=payload,topic = 'alarm_response')
                        log.info("Alarm Updated with alarm info: %s", update_resp)                           

                else:
                    log.info ("Metric Not Supported")
         
            
            elif message.key == "delete_alarm_request":  
                del_info = json.loads(message.value)
                #Generate a valid response message, send via producer
                del_resp = self.delete_alarm(del_info)
                payload = json.dumps(del_resp)                                   
                file = open('../../core/models/delete_alarm_resp.json','wb').write((payload))
                self.producer.delete_alarm_response(key='delete_alarm_response',message=payload,topic = 'alarm_response')
                log.info("Alarm Deleted with alarm info: %s", del_resp)

       
            elif message.key == "alarm_list_request":
                alarm_inner_dict = alarm_info['alarm_list_request']
                
                if self.check_resource(alarm_inner_dict['resource_uuid']) == True or alarm_inner_dict['resource_uuid'] == "": 
                    #Generate a valid response message, send via producer
                    list_resp = self.get_alarms_list(alarm_info)#['alarm_names']
                    payload = json.dumps(list_resp)                                                                 
                    file = open('../../core/models/list_alarm_resp.json','wb').write((payload))
                    self.producer.list_alarm_response(key='list_alarm_response',message=payload,topic = 'alarm_response')

                else:
                    log.error("Resource ID is Incorrect")             

            else:
                log.debug("Unknown key, no action will be performed")    

        except Exception as e:
                log.error("Message retrieval exception: %s", str(e))             
#--------------------------------------------------------------------------------------------------------------------------- 
    def check_resource(self,resource_uuid):
        '''Finding Resource with the resource_uuid'''
        try:
            check_resp = dict()
            instances = self.ec2_conn.get_all_instance_status()

            #resource_id
            for instance_id in instances:
                instance_id = str(instance_id).split(':')[1]

                if instance_id == resource_uuid:
                    check_resp['resource_uuid'] = resource_uuid
                    return True 
            return False

        except Exception as e: 
            log.error("Error in Plugin Inputs %s",str(e)) 
#--------------------------------------------------------------------------------------------------------------------------- 
    def check_metric(self,metric_name):
        ''' Checking whether the metric is supported by AWS '''
        try:
            check_resp = dict()
            
            #metric_name
            if metric_name == 'CPU_UTILIZATION':
                metric_name = 'CPUUtilization'
                metric_status = True

            elif metric_name == 'DISK_READ_OPS':
                metric_name = 'DiskReadOps'
                metric_status = True

            elif metric_name == 'DISK_WRITE_OPS':
                metric_name = 'DiskWriteOps'
                metric_status = True

            elif metric_name == 'DISK_READ_BYTES':
                metric_name = 'DiskReadBytes'
                metric_status = True

            elif metric_name == 'DISK_WRITE_BYTES':
                metric_name = 'DiskWriteBytes'
                metric_status = True

            elif metric_name == 'PACKETS_RECEIVED':
                metric_name = 'NetworkPacketsIn'
                metric_status = True

            elif metric_name == 'PACKETS_SENT':
                metric_name = 'NetworkPacketsOut'
                metric_status = True

            else:
                metric_name = None
                metric_status = False
            check_resp['metric_name'] = metric_name
            #status

            if metric_status == True:
                check_resp['status'] = True
                return check_resp   

        except Exception as e: 
            log.error("Error in Plugin Inputs %s",str(e)) 
#--------------------------------------------------------------------------------------------------------------------------- 
