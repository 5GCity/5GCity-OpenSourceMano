import sys
import os
import re
import datetime
import random
import logging as log
from random import randint
from operator import itemgetter
from connection import Connection

try:
    import boto
    import boto.ec2
    import boto.vpc
    import boto.ec2.cloudwatch
    import boto.ec2.connection
except:
    exit("Boto not avialable. Try activating your virtualenv OR `pip install boto`")


class MetricAlarm():
    """Alarms Functionality Handler -- Cloudwatch """
 
    def config_alarm(self,cloudwatch_conn,alarm_info):
    	"""Configure or Create a new alarm"""

        """ Alarm Name to ID Mapping """
        alarm_id = alarm_info['alarm_name'] + "_" + alarm_info['resource_id']
        if self.is_present(cloudwatch_conn,alarm_id) == True: 
            alarm_id = None
            log.debug ("Alarm already exists, Try updating the alarm using 'update_alarm_configuration()'")   
        else:              
            try:
                alarm = boto.ec2.cloudwatch.alarm.MetricAlarm(
                    connection = cloudwatch_conn,
                    name = alarm_info['alarm_name'] + "_" + alarm_info['resource_id'],
                    metric = alarm_info['alarm_metric'],
                    namespace = alarm_info['instance_type'],
                    statistic = alarm_info['alarm_statistics'],
                    comparison = alarm_info['alarm_comparison'],
                    threshold = alarm_info['alarm_threshold'],
                    period = alarm_info['alarm_period'],
                    evaluation_periods = alarm_info['alarm_evaluation_period'],
                    unit=alarm_info['alarm_unit'],
                    description = alarm_info['alarm_severity'] + ";" + alarm_info['alarm_description'],
                    dimensions = {'InstanceId':alarm_info['resource_id']},
                    alarm_actions = None,
                    ok_actions = None,
                    insufficient_data_actions = None)

                """Setting Alarm Actions : 
                alarm_actions = ['arn:aws:swf:us-west-2:465479087178:action/actions/AWS_EC2.InstanceId.Stop/1.0']"""

                cloudwatch_conn.put_metric_alarm(alarm)
                log.debug ("Alarm Configured Succesfully")
                print "created"
                print "\n"    
            except Exception as e:
                log.error("Alarm Configuration Failed: " + str(e))
        return alarm_id    
#-----------------------------------------------------------------------------------------------------------------------------
    def update_alarm(self,cloudwatch_conn,alarm_info):

    	"""Update or reconfigure an alarm"""
        
        """Alarm Name to ID Mapping"""
        alarm_id = alarm_info['alarm_name'] + "_" + alarm_info['resource_id']

        """Verifying : Alarm exists already"""
        if self.is_present(cloudwatch_conn,alarm_id) == False: 
            alarm_id = None
            log.debug("Alarm not found, Try creating the alarm using 'configure_alarm()'")   
        else:            
            try:
                alarm = boto.ec2.cloudwatch.alarm.MetricAlarm(
                        connection = cloudwatch_conn,
                        name = alarm_info['alarm_name'] + "_" + alarm_info['resource_id'],
                        metric = alarm_info['alarm_metric'],
                        namespace = alarm_info['instance_type'],
                        statistic = alarm_info['alarm_statistics'],
                        comparison = alarm_info['alarm_comparison'],
                        threshold = alarm_info['alarm_threshold'],
                        period = alarm_info['alarm_period'],
                        evaluation_periods = alarm_info['alarm_evaluation_period'],
                        unit=alarm_info['alarm_unit'],
                        description = alarm_info['alarm_severity'] + ";" + alarm_info['alarm_description'],
                        dimensions = {'InstanceId':alarm_info['resource_id']},
                        alarm_actions = None,
                        ok_actions = None,
                        insufficient_data_actions = None)
                cloudwatch_conn.put_metric_alarm(alarm)
                log.debug("Alarm %s Updated ",alarm.name)
                print "updated"
            except Exception as e:
                log.error ("Error in Updating Alarm " + str(e))
        return alarm_id
#-----------------------------------------------------------------------------------------------------------------------------
    def delete_Alarm(self,cloudwatch_conn,alarm_id):
    	"""Deletes an Alarm with specified alarm_id"""
        try:
            if self.is_present(cloudwatch_conn,alarm_id) == True:
                deleted_alarm=cloudwatch_conn.delete_alarms(alarm_id)
                return alarm_id
            return None 
        except Exception as e:
                log.error("Alarm Not Deleted: " + str(e))      
#-----------------------------------------------------------------------------------------------------------------------------
    def alarms_list(self,cloudwatch_conn,instance_id):

    	"""Get a list of alarms that are present on a particular VM instance"""
        try:
            log.debug("Getting Alarm list for %s",instance_id)
            alarm_dict = dict()
            alarm_list = []
            alarms = cloudwatch_conn.describe_alarms()
            itr = 0
            for alarm in alarms:
                if str(alarm.dimensions['InstanceId']).split("'")[1] == instance_id:
                    alarm_list.insert(itr,str(alarm.name))
                    itr += 1
            alarm_dict['alarm_names'] = alarm_list
            alarm_dict['resource_id'] = instance_id   
            return alarm_dict
        except Exception as e:
                log.error("Error in Getting List : %s",str(e))    
#-----------------------------------------------------------------------------------------------------------------------------
    def alarm_details(self,cloudwatch_conn,alarm_name):

	"""Get an individual alarm details specified by alarm_name"""
        try:
            alarms_details=cloudwatch_conn.describe_alarm_history()       
            alarm_details_dict = dict()
            
            for itr in range (len(alarms_details)):
                if alarms_details[itr].name == alarm_name and 'created' in alarms_details[itr].summary :#name, timestamp, summary
                    status = alarms_details[itr].summary.split()                   
                    alarms = cloudwatch_conn.describe_alarms()
                    for alarm in alarms:
                        if alarm.name == alarm_name:
                            alarm_details_dict['alarm_id'] = alarm_name
                            alarm_details_dict['resource_id'] = str(alarm.dimensions['InstanceId']).split("'")[1]
                            alarm_details_dict['severity'] = str(alarm.description)
                            alarm_details_dict['start_date_time'] = str(alarms_details[x].timestamp) 

                            return alarm_details_dict             
                  
        except Exception as e:
        	log.error("Error getting alarm details: %s",str(e))           
#-----------------------------------------------------------------------------------------------------------------------------
    def metrics_data(self,cloudwatch_conn,metric_name,instance_id,period,metric_unit):

    	"""Getting Metrics Stats for an Hour. Time interval can be modified using Timedelta value"""
        metric_data= dict()
        metric_stats=cloudwatch_conn.get_metric_statistics(period, datetime.datetime.utcnow() - datetime.timedelta(seconds=3600),
                            datetime.datetime.utcnow(),metric_name,'AWS/EC2', 'Maximum',
                            dimensions={'InstanceId':instance_id}, unit=metric_unit)

        for itr in range (len(metric_stats)):
            metric_data['metric_name'] = metric_name
            metric_data['Resource_id'] = instance_id
            metric_data['Unit']		   = metric_stats[itr]['Unit']
            metric_data['Timestamp']   = metric_stats[itr]['Timestamp']  
        return metric_data

#-----------------------------------------------------------------------------------------------------------------------------
    def is_present(self,cloudwatch_conn,alarm_name):
    	"""Finding Alarm exists or not"""
        try:
            alarms = cloudwatch_conn.describe_alarms()
            for alarm in alarms:
                if alarm.name == alarm_name:
                    return True
            return False
        except Exception as e:
                log.error("Error Finding Alarm",str(e))             
#-----------------------------------------------------------------------------------------------------------------------------
