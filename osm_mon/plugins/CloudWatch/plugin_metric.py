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
from connection import Connection
from metric_alarms import MetricAlarm
from metrics import Metrics
sys.path.append("../../core/message_bus")
from producer import KafkaProducer
import logging

log = logging.getLogger(__name__)

class plugin_metrics():
    """Receives Alarm info from MetricAlarm and connects with the consumer/producer """
    def __init__ (self): 
        self.metric = Metrics()
        self.producer = KafkaProducer('')
#---------------------------------------------------------------------------------------------------------------------------   
    def create_metric_request(self,metric_info):
        '''Comaptible API using normalized parameters'''
        metric_resp = self.metric.createMetrics(self.cloudwatch_conn,metric_info)
        return metric_resp
#---------------------------------------------------------------------------------------------------------------------------          
    def update_metric_request(self,updated_info):
        '''Comaptible API using normalized parameters'''
        update_resp = self.metric.updateMetrics(self.cloudwatch_conn,updated_info)
        return update_resp
#---------------------------------------------------------------------------------------------------------------------------            
    def delete_metric_request(self,delete_info):
        '''Comaptible API using normalized parameters'''
        del_resp = self.metric.deleteMetrics(self.cloudwatch_conn,delete_info)
        return del_resp
#---------------------------------------------------------------------------------------------------------------------------  
    def list_metrics_request(self,list_info):
        '''Comaptible API using normalized parameters'''
        list_resp = self.metric.listMetrics(self.cloudwatch_conn,list_info)
        return list_resp
#---------------------------------------------------------------------------------------------------------------------------                        
    def read_metrics_data(self,list_info):
        '''Comaptible API using normalized parameters
        Read all metric data related to a specified metric'''
        data_resp=self.metric.metricsData(self.cloudwatch_conn,list_info)
        return data_resp
#--------------------------------------------------------------------------------------------------------------------------- 

    def metric_calls(self,message,aws_conn):
        """Gets the message from the common consumer"""
        
        try:
            self.cloudwatch_conn = aws_conn['cloudwatch_connection']
            self.ec2_conn = aws_conn['ec2_connection']

            metric_info = json.loads(message.value)
            metric_response = dict()

            if metric_info['vim_type'] == 'AWS':
                log.debug ("VIM support : AWS")

            # Check the Functionlity that needs to be performed: topic = 'alarms'/'metrics'/'Access_Credentials'
                if message.topic == "metric_request":
                    log.info("Action required against: %s" % (message.topic))

                    if message.key == "create_metric_request":                            
                        if self.check_resource(metric_info['metric_create']['resource_uuid']) == True:
                            metric_resp = self.create_metric_request(metric_info['metric_create']) #alarm_info = message.value
                            metric_response['schema_version'] = metric_info['schema_version']
                            metric_response['schema_type']    = "create_metric_response"
                            metric_response['metric_create_response'] = metric_resp
                            payload = json.dumps(metric_response)                                                                  
                            file = open('../../core/models/create_metric_resp.json','wb').write((payload))
                            self.producer.create_metrics_resp(key='create_metric_response',message=payload,topic = 'metric_response')
                            
                            log.info("Metric configured: %s", metric_resp)
                            return metric_response
                            
                    elif message.key == "update_metric_request":
                        if self.check_resource(metric_info['metric_create']['resource_uuid']) == True:
                            update_resp = self.update_metric_request(metric_info['metric_create'])
                            metric_response['schema_version'] = metric_info['schema_version']
                            metric_response['schema_type'] = "update_metric_response"
                            metric_response['metric_update_response'] = update_resp
                            payload = json.dumps(metric_response)                                                                                               
                            file = open('../../core/models/update_metric_resp.json','wb').write((payload))
                            self.producer.update_metric_response(key='update_metric_response',message=payload,topic = 'metric_response')

                            log.info("Metric Updates: %s",metric_response)
                            return metric_response
                            
                    elif message.key == "delete_metric_request":
                        if self.check_resource(metric_info['resource_uuid']) == True:
                            del_resp=self.delete_metric_request(metric_info)
                            payload = json.dumps(del_resp)                                                                                               
                            file = open('../../core/models/delete_metric_resp.json','wb').write((payload))
                            self.producer.delete_metric_response(key='delete_metric_response',message=payload,topic = 'metric_response')

                            log.info("Metric Deletion Not supported in AWS : %s",del_resp)
                            return del_resp

                    elif message.key == "list_metric_request": 
                        if self.check_resource(metric_info['metrics_list_request']['resource_uuid']) == True:
                            list_resp = self.list_metrics_request(metric_info['metrics_list_request'])
                            metric_response['schema_version'] = metric_info['schema_version']
                            metric_response['schema_type'] = "list_metric_response"
                            metric_response['correlation_id'] = metric_info['metrics_list_request']['correlation_id']
                            metric_response['vim_type'] = metric_info['vim_type']
                            metric_response['metrics_list'] = list_resp
                            payload = json.dumps(metric_response)                                                                                                
                            file = open('../../core/models/list_metric_resp.json','wb').write((payload))
                            self.producer.list_metric_response(key='list_metrics_response',message=payload,topic = 'metric_response')

                            log.info("Metric List: %s",metric_response)
                            return metric_response

                    elif message.key == "read_metric_data_request":
                        if self.check_resource(metric_info['resource_uuid']) == True:
                            data_resp = self.read_metrics_data(metric_info)
                            metric_response['schema_version'] = metric_info['schema_version']
                            metric_response['schema_type'] = "read_metric_data_response"
                            metric_response['metric_name'] = metric_info['metric_name']
                            metric_response['metric_uuid'] = metric_info['metric_uuid']
                            metric_response['correlation_id'] = metric_info['correlation_uuid']
                            metric_response['resource_uuid'] = metric_info['resource_uuid']
                            metric_response['tenant_uuid'] = metric_info['tenant_uuid']
                            metric_response['metrics_data'] = data_resp
                            payload = json.dumps(metric_response)                                                                
                            file = open('../../core/models/read_metric_data_resp.json','wb').write((payload))
                            self.producer.read_metric_data_response(key='read_metric_data_response',message=payload,topic = 'metric_response')
                            
                            log.info("Metric Data Response: %s",metric_response)
                            return metric_response 

                    else:
                        log.debug("Unknown key, no action will be performed")
                else:
                    log.info("Message topic not relevant to this plugin: %s",
                         message.topic)
            
        except Exception as e:
            log.error("Consumer exception: %s", str(e))

#---------------------------------------------------------------------------------------------------------------------------
    def check_resource(self,resource_uuid):

        '''Checking the resource_uuid is present in EC2 instances'''
        try:
            check_resp = dict()
            instances = self.ec2_conn.get_all_instance_status()
            status_resource = False

            #resource_id
            for instance_id in instances:
                instance_id = str(instance_id).split(':')[1]
                if instance_id == resource_uuid:
                    check_resp['resource_uuid'] = resource_uuid
                    status_resource = True
                else:
                    status_resource = False

            #status
            return status_resource

        except Exception as e: 
            log.error("Error in Plugin Inputs %s",str(e))          
#---------------------------------------------------------------------------------------------------------------------------   

