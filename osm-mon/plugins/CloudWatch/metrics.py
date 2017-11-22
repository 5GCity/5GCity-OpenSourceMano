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
__date__   = "18-Sept-2017"

import sys
import datetime
import json
import logging as log

try:
    import boto
    import boto.ec2
    import boto.vpc
    import boto.ec2.cloudwatch
    import boto.ec2.connection
except:
    exit("Boto not avialable. Try activating your virtualenv OR `pip install boto`")



class Metrics():

    def createMetrics(self,cloudwatch_conn,metric_info):
        try:
            
            '''createMetrics will be returning the metric_uuid=0 and
             status=True when the metric is supported by AWS'''

            supported=self.check_metric(metric_info['metric_name'])
            metric_resp = dict()
            metric_resp['resource_uuid'] = metric_info['resource_uuid']
            
            if supported['status'] == True:
                metric_resp['status'] = True
                metric_resp['metric_uuid'] = 0
                log.debug("Metrics Configured Succesfully : %s" , metric_resp)
            else:
                metric_resp['status'] = False
                metric_resp['metric_uuid'] = None
                log.error("Metric name is not supported") 
            
            return metric_resp         

        except Exception as e:
            log.error("Metric Configuration Failed: " + str(e))
#-----------------------------------------------------------------------------------------------------------------------------
    
    def metricsData(self,cloudwatch_conn,data_info):

    	"""Getting Metrics Stats for an Hour.The datapoints are
        received after every one minute.
        Time interval can be modified using Timedelta value"""

        try:
            metric_info = dict()
            metric_info_dict = dict()
            timestamp_arr = {}
            value_arr = {}

            supported=self.check_metric(data_info['metric_name'])

            if supported['status'] == True:
                if int(data_info['collection_period']) % 60 == 0:
                    metric_stats=cloudwatch_conn.get_metric_statistics(60, datetime.datetime.utcnow() - datetime.timedelta(seconds=int(data_info['collection_period'])),
                                        datetime.datetime.utcnow(),supported['metric_name'],'AWS/EC2', 'Maximum',
                                        dimensions={'InstanceId':data_info['resource_uuid']}, unit='Percent')  
                    index = 0
                    for itr in range (len(metric_stats)):
                        timestamp_arr[index] = str(metric_stats[itr]['Timestamp'])
                        value_arr[index] = metric_stats[itr]['Maximum']
                        index +=1
                    metric_info_dict['time_series'] = timestamp_arr
                    metric_info_dict['metrics_series'] = value_arr
                    log.debug("Metrics Data : %s", metric_info_dict)
                    return metric_info_dict
                else: 
                    log.error("Collection Period should be a multiple of 60")
                    return False

            else:
                log.error("Metric name is not supported")
                return False
        
        except Exception as e:
            log.error("Error returning Metrics Data" + str(e))

#-----------------------------------------------------------------------------------------------------------------------------
    def updateMetrics(self,cloudwatch_conn,metric_info):
        
        '''updateMetrics will be returning the metric_uuid=0 and
         status=True when the metric is supported by AWS'''
        try:
            supported=self.check_metric(metric_info['metric_name'])
            update_resp = dict()
            update_resp['resource_uuid'] = metric_info['resource_uuid']
            if supported['status'] == True:
                update_resp['status'] = True
                update_resp['metric_uuid'] = 0
                log.debug("Metric Updated : %s", update_resp)
            else:
                update_resp['status'] = False
                update_resp['metric_uuid'] = None
                log.error("Metric name is not supported")
             
            return update_resp  
        
        except Exception as e:
            log.error("Error in Update Metrics" + str(e))
#-----------------------------------------------------------------------------------------------------------------------------
    def deleteMetrics(self,cloudwatch_conn,del_info):
        
        ''' " Not supported in AWS"
        Returning the required parameters with status = False'''
        try:
            supported=self.check_metric(del_info['metric_name'])
            metric_resp = dict()
            del_resp = dict()
            if supported['status'] == True:      
                del_resp['schema_version'] = del_info['schema_version']
                del_resp['schema_type'] = "delete_metric_response"
                del_resp['metric_name'] = del_info['metric_name']
                del_resp['metric_uuid'] = del_info['metric_uuid']
                del_resp['resource_uuid'] = del_info['resource_uuid']
                # TODO : yet to finalize
                del_resp['tenant_uuid'] = del_info['tenant_uuid']
                del_resp['correlation_id'] = del_info['correlation_uuid']
                del_resp['status'] = False
                log.info("Metric Deletion Not supported in AWS : %s",del_resp)
                return del_resp
            else:
                log.error("Metric name is not supported")
                return False

        except Exception as e:
                log.error(" Metric Deletion Not supported in AWS : " + str(e))
#------------------------------------------------------------------------------------------------------------------------------------
    
    def listMetrics(self,cloudwatch_conn ,list_info):

        '''Returns the list of available AWS/EC2 metrics on which
        alarms have been configured and the metrics are being monitored'''
        try:
            supported = self.check_metric(list_info['metric_name'])
            if supported['status'] == True: 
                metrics_list = []
                metrics_data = dict()    

                #To get the list of associated metrics with the alarms
                alarms = cloudwatch_conn.describe_alarms()
                itr = 0
                if list_info['metric_name'] == "":
                    for alarm in alarms:
                        metrics_info = dict()
                        instance_id = str(alarm.dimensions['InstanceId']).split("'")[1] 
                        metrics_info['metric_name'] = str(alarm.metric) 
                        metrics_info['metric_uuid'] = 0     
                        metrics_info['metric_unit'] = str(alarm.unit)    
                        metrics_info['resource_uuid'] = instance_id 
                        metrics_list.insert(itr,metrics_info)
                        itr += 1
                    print metrics_list
                    return metrics_list
                else: 
                    for alarm in alarms:
                        metrics_info = dict()
                        if alarm.metric == supported['metric_name']:
                            instance_id = str(alarm.dimensions['InstanceId']).split("'")[1] 
                            metrics_info['metric_name'] = str(alarm.metric)
                            metrics_info['metric_uuid'] = 0     
                            metrics_info['metric_unit'] = str(alarm.unit)    
                            metrics_info['resource_uuid'] = instance_id
                            metrics_list.insert(itr,metrics_info)
                            itr += 1
                    return metrics_list               
                log.debug("Metrics List : %s",metrics_list)
            else:
                log.error("Metric name is not supported")
                return False

        except Exception as e:
            log.error("Error in Getting Metric List " + str(e))

#------------------------------------------------------------------------------------------------------------------------------------

    def check_metric(self,metric_name):
    
        ''' Checking whether the metric is supported by AWS '''
        try:
            check_resp = dict()
            # metric_name
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
            elif metric_name == "":
                metric_name = None
                metric_status = True
                log.info("Metric Not Supported by AWS plugin ")
            else:
                metric_name = None
                metric_status = False
                log.info("Metric Not Supported by AWS plugin ")
            check_resp['metric_name'] = metric_name
            #status
            if metric_status == True:
                check_resp['status'] = True
            else:
            	check_resp['status'] = False

            return check_resp

        except Exception as e: 
            log.error("Error in Plugin Inputs %s",str(e))     
#--------------------------------------------------------------------------------------------------------------------------------------

      






