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

''' Handling of alarms requests via BOTO 2.48 '''

__author__ = "Wajeeha Hamid"
__date__   = "18-September-2017"

import sys
import os
import re
import datetime
import random
import json
import logging
from random import randint
from operator import itemgetter
from connection import Connection

log = logging.getLogger(__name__)

try:
    import boto
    import boto.ec2
    import boto.vpc
    import boto.ec2.cloudwatch
    import boto.ec2.connection
except:
    exit("Boto not avialable. Try activating your virtualenv OR `pip install boto`")

STATISTICS = {
    "AVERAGE": "Average",
    "MINIMUM": "Minimum",
    "MAXIMUM": "Maximum",
    "COUNT"  : "SampleCount",
    "SUM"    : "Sum"}

OPERATIONS = {
    "GE"     : ">=",
    "LE"     : "<=",
    "GT"     : ">",
    "LT"     : "<",
    "EQ"     : "="}   

class MetricAlarm():
    """Alarms Functionality Handler -- Carries out alarming requests and responses via BOTO.Cloudwatch """
    def __init__(self):
        self.alarm_resp = dict()
        self.del_resp = dict()

    def config_alarm(self,cloudwatch_conn,create_info):
    	"""Configure or Create a new alarm"""
        inner_dict = dict()
        """ Alarm Name to ID Mapping """
        alarm_info = create_info['alarm_create_request']
        alarm_id = alarm_info['alarm_name'] + "_" + alarm_info['resource_uuid']
        if self.is_present(cloudwatch_conn,alarm_id)['status'] == True: 
            alarm_id = None
            log.debug ("Alarm already exists, Try updating the alarm using 'update_alarm_configuration()'")
            return alarm_id   
        else:              
            try:
                if alarm_info['statistic'] in STATISTICS:
                    if alarm_info['operation'] in OPERATIONS:
                        alarm = boto.ec2.cloudwatch.alarm.MetricAlarm(
                            connection = cloudwatch_conn,
                            name = alarm_info['alarm_name'] + "_" + alarm_info['resource_uuid'],
                            metric = alarm_info['metric_name'],
                            namespace = "AWS/EC2",
                            statistic = STATISTICS[alarm_info['statistic']],
                            comparison = OPERATIONS[alarm_info['operation']],
                            threshold = alarm_info['threshold_value'],
                            period = 60,
                            evaluation_periods = 1,
                            unit=alarm_info['unit'],
                            description = alarm_info['severity'] + ";" + alarm_id + ";" + alarm_info['description'],
                            dimensions = {'InstanceId':alarm_info['resource_uuid']},
                            alarm_actions = None,
                            ok_actions = None,
                            insufficient_data_actions = None)

                        """Setting Alarm Actions : 
                        alarm_actions = ['arn:aws:swf:us-west-2:465479087178:action/actions/AWS_EC2.InstanceId.Stop/1.0']"""

                        status=cloudwatch_conn.put_metric_alarm(alarm)

                        log.debug ("Alarm Configured Succesfully")
                        self.alarm_resp['schema_version'] = str(create_info['schema_version'])
                        self.alarm_resp['schema_type'] = 'create_alarm_response'

                        inner_dict['correlation_id'] = str(alarm_info['correlation_id'])
                        inner_dict['alarm_uuid'] = str(alarm_id) 
                        inner_dict['status'] = status

                        self.alarm_resp['alarm_create_response'] = inner_dict

                        if status == True:
                            return self.alarm_resp
                        else:
                            return None	
                    else: 
                        log.error("Operation not supported")
                        return None        
                else:
                    log.error("Statistic not supported")
                    return None
            except Exception as e:
                log.error("Alarm Configuration Failed: " + str(e))
            
#-----------------------------------------------------------------------------------------------------------------------------
    def update_alarm(self,cloudwatch_conn,update_info):

    	"""Update or reconfigure an alarm"""
        inner_dict = dict()
        alarm_info = update_info['alarm_update_request']

        """Alarm Name to ID Mapping"""
        alarm_id = alarm_info['alarm_uuid']
        status = self.is_present(cloudwatch_conn,alarm_id)

        """Verifying : Alarm exists already"""
        if status['status'] == False: 
            alarm_id = None
            log.debug("Alarm not found, Try creating the alarm using 'configure_alarm()'")
            return alarm_id   
        else:            
            try:
                if alarm_info['statistic'] in STATISTICS:
                    if alarm_info['operation'] in OPERATIONS:
                        alarm = boto.ec2.cloudwatch.alarm.MetricAlarm(
                            connection = cloudwatch_conn,
                            name = status['info'].name ,
                            metric = alarm_info['metric_name'],
                            namespace = "AWS/EC2",
                            statistic = STATISTICS[alarm_info['statistic']],
                            comparison = OPERATIONS[alarm_info['operation']],
                            threshold = alarm_info['threshold_value'],
                            period = 60,
                            evaluation_periods = 1,
                            unit=alarm_info['unit'],
                            description = alarm_info['severity'] + ";" + alarm_id + ";" + alarm_info['description'],
                            dimensions = {'InstanceId':str(status['info'].dimensions['InstanceId']).split("'")[1]},
                            alarm_actions = None,
                            ok_actions = None,
                            insufficient_data_actions = None)

                        """Setting Alarm Actions : 
                        alarm_actions = ['arn:aws:swf:us-west-2:465479087178:action/actions/AWS_EC2.InstanceId.Stop/1.0']"""

                        status=cloudwatch_conn.put_metric_alarm(alarm)
                        log.debug("Alarm %s Updated ",alarm.name)
                        self.alarm_resp['schema_version'] = str(update_info['schema_version'])
                        self.alarm_resp['schema_type'] = 'update_alarm_response'

                        inner_dict['correlation_id'] = str(alarm_info['correlation_id'])
                        inner_dict['alarm_uuid'] = str(alarm_id) 
                        inner_dict['status'] = status

                        self.alarm_resp['alarm_update_response'] = inner_dict
                        return self.alarm_resp
                    else: 
                        log.error("Operation not supported")
                        return None        
                else:
                    log.error("Statistic not supported")
                    return None        
            except Exception as e:
                log.error ("Error in Updating Alarm " + str(e))
        
#-----------------------------------------------------------------------------------------------------------------------------
    def delete_Alarm(self,cloudwatch_conn,del_info_all):

    	"""Deletes an Alarm with specified alarm_id"""
        inner_dict = dict()
        del_info = del_info_all['alarm_delete_request']
        status = self.is_present(cloudwatch_conn,del_info['alarm_uuid'])
        try:
            if status['status'] == True:                
                del_status=cloudwatch_conn.delete_alarms(status['info'].name)
                self.del_resp['schema_version'] = str(del_info_all['schema_version'])
                self.del_resp['schema_type'] = 'delete_alarm_response'
                inner_dict['correlation_id'] = str(del_info['correlation_id'])
                inner_dict['alarm_id'] = str(del_info['alarm_uuid'])
                inner_dict['status'] = del_status
                self.del_resp['alarm_deletion_response'] = inner_dict
                return self.del_resp
            return None 
        except Exception as e:
                log.error("Alarm Not Deleted: " + str(e))      
#-----------------------------------------------------------------------------------------------------------------------------
    def alarms_list(self,cloudwatch_conn,list_info):

        """Get a list of alarms that are present on a particular VIM type"""
        alarm_list = []
        alarm_info = dict()
        inner_dict = list_info['alarm_list_request']
        try: #id vim 
            alarms = cloudwatch_conn.describe_alarms()
            itr = 0
            for alarm in alarms:
                list_info['alarm_list_request']['alarm_uuid'] = str(alarm.description).split(';')[1]

                #Severity = alarm_name = resource_uuid = ""
                if inner_dict['severity'] == "" and inner_dict['alarm_name'] == "" and inner_dict['resource_uuid'] == "":
                    alarm_list.insert(itr,self.alarm_details(cloudwatch_conn,list_info))
                    itr += 1
                #alarm_name = resource_uuid = ""
                if inner_dict['severity'] == str(alarm.description).split(';')[0] and inner_dict['alarm_name'] == "" and inner_dict['resource_uuid'] == "":
                    alarm_list.insert(itr,self.alarm_details(cloudwatch_conn,list_info))
                    itr += 1
                #severity = resource_uuid = ""
                if inner_dict['severity'] == "" and inner_dict['alarm_name'] in alarm.name and inner_dict['resource_uuid'] == "":
                    alarm_list.insert(itr,self.alarm_details(cloudwatch_conn,list_info))
                    itr += 1
                #severity = alarm_name = ""    
                if inner_dict['severity'] == "" and inner_dict['alarm_name'] == "" and inner_dict['resource_uuid'] == str(alarm.dimensions['InstanceId']).split("'")[1]:
                    alarm_list.insert(itr,self.alarm_details(cloudwatch_conn,list_info))
                    itr += 1
                #resource_uuid = ""    
                if inner_dict['severity'] == str(alarm.description).split(';')[0] and inner_dict['alarm_name'] in alarm.name and inner_dict['resource_uuid'] == "":
                    alarm_list.insert(itr,self.alarm_details(cloudwatch_conn,list_info))
                    itr += 1
                #alarm_name = ""    
                if inner_dict['severity'] == str(alarm.description).split(';')[0] and inner_dict['alarm_name'] == "" and inner_dict['resource_uuid'] == str(alarm.dimensions['InstanceId']).split("'")[1]:
                    alarm_list.insert(itr,self.alarm_details(cloudwatch_conn,list_info))
                    itr += 1
                #severity = ""    
                if inner_dict['severity'] == "" and inner_dict['alarm_name'] in alarm.name and inner_dict['resource_uuid'] == str(alarm.dimensions['InstanceId']).split("'")[1]:
                    alarm_list.insert(itr,self.alarm_details(cloudwatch_conn,list_info))
                    itr += 1                    
                #Everything provided    
                if inner_dict['severity'] == str(alarm.description).split(';')[0] and inner_dict['alarm_name'] in alarm.name and inner_dict['resource_uuid'] == str(alarm.dimensions['InstanceId']).split("'")[1]:
                    alarm_list.insert(itr,self.alarm_details(cloudwatch_conn,list_info))
                    itr += 1

            alarm_info['schema_version'] = str(list_info['schema_version'])
            alarm_info['schema_type'] = 'list_alarm_response'    
            alarm_info['list_alarm_resp'] = alarm_list

            return alarm_info                  
        except Exception as e:
                log.error("Error in Getting List : %s",str(e))    
#-----------------------------------------------------------------------------------------------------------------------------
    def alarm_details(self,cloudwatch_conn,ack_info):

	"""Get an individual alarm details specified by alarm_name"""
        try:
            alarms_details=cloudwatch_conn.describe_alarm_history()  
            alarm_details_all = dict()     
            alarm_details_dict = dict()
            ack_info_all = ack_info


            if 'ack_details' in ack_info:
                ack_info = ack_info['ack_details']
            elif 'alarm_list_request' in ack_info:
                ack_info = ack_info['alarm_list_request']    
            
            is_present = self.is_present(cloudwatch_conn,ack_info['alarm_uuid'])

            for itr in range (len(alarms_details)):
                if alarms_details[itr].name == is_present['info'].name :#name, timestamp, summary
                    if 'created' in alarms_details[itr].summary:
                        alarm_details_dict['status'] = "New"
                    elif 'updated' in alarms_details[itr].summary:
                        alarm_details_dict['status'] = "Update"
                    elif 'deleted' in alarms_details[itr].summary:   
                        alarm_details_dict['status'] = "Canceled"

                    status = alarms_details[itr].summary.split()                  
                    alarms = cloudwatch_conn.describe_alarms()
                    for alarm in alarms:
                        if str(alarm.description).split(';')[1] == ack_info['alarm_uuid']:
                            alarm_details_dict['alarm_uuid'] = str(ack_info['alarm_uuid'])
                            alarm_details_dict['resource_uuid'] = str(alarm.dimensions['InstanceId']).split("'")[1]
                            alarm_details_dict['description'] = str(alarm.description).split(';')[1]
                            alarm_details_dict['severity'] = str(alarm.description).split(';')[0]
                            alarm_details_dict['start_date_time'] = str(alarms_details[itr].timestamp) 
                            alarm_details_dict['vim_type'] = str(ack_info_all['vim_type'])
                            #TODO : tenant id
                            if 'ack_details' in ack_info_all:
                                alarm_details_all['schema_version'] = str(ack_info_all['schema_version'])
                                alarm_details_all['schema_type'] = 'notify_alarm'
                                alarm_details_all['notify_details'] = alarm_details_dict
                                return alarm_details_all

                            elif 'alarm_list_request' in ack_info_all:
                                return alarm_details_dict                     
                  
        except Exception as e:
        	log.error("Error getting alarm details: %s",str(e))           
#-----------------------------------------------------------------------------------------------------------------------------
    def is_present(self,cloudwatch_conn,alarm_id):
    	"""Finding alarm from already configured alarms"""
        alarm_info = dict()
        try:
            alarms = cloudwatch_conn.describe_alarms()
            for alarm in alarms:
                if str(alarm.description).split(';')[1] == alarm_id:
                    alarm_info['status'] = True
                    alarm_info['info'] = alarm
                    return alarm_info
            alarm_info['status'] = False        
            return alarm_info
        except Exception as e:
                log.error("Error Finding Alarm",str(e))             
#-----------------------------------------------------------------------------------------------------------------------------
    