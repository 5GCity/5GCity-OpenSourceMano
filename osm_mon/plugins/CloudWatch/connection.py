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
Connecting with AWS services --CloudWatch/EC2 using Required keys  
'''

__author__ = "Wajeeha Hamid"
__date__   = "18-September-2017"

import sys
import os

try:
    import boto
    import boto.ec2
    import boto.vpc
    import boto.ec2.cloudwatch
    import boto.ec2.connection
    import logging as log
    from boto.ec2.cloudwatch.alarm import MetricAlarm
    from boto.ec2.cloudwatch.dimension import Dimension
    from boto.sns import connect_to_region
    from boto.utils import get_instance_metadata

except:
    exit("Boto not avialable. Try activating your virtualenv OR `pip install boto`")


class Connection():
    """Connection Establishement with AWS -- VPC/EC2/CloudWatch"""
#-----------------------------------------------------------------------------------------------------------------------------
    def setEnvironment(self):  
    	try:
            """Credentials for connecting to AWS-CloudWatch""" 
            #Reads from the environment variables
            self.AWS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
            self.AWS_SECRET = os.environ.get("AWS_SECRET_ACCESS_KEY")
            self.AWS_REGION = os.environ.get("AWS_EC2_REGION","us-west-2")

            #TODO Read from the cloudwatch_credentials.txt file
            
            return self.connection_instance()
        except Exception as e:
            log.error("AWS Credentials not configured, Try setting the access credentials first %s: ",str(e)) 
#-----------------------------------------------------------------------------------------------------------------------------
    def connection_instance(self):
            try:
                #VPC Connection
                self.vpc_conn = boto.vpc.connect_to_region(self.AWS_REGION,
                    aws_access_key_id=self.AWS_KEY,
                    aws_secret_access_key=self.AWS_SECRET)
               
                
                #EC2 Connection
                self.ec2_conn = boto.ec2.connect_to_region(self.AWS_REGION,
                    aws_access_key_id=self.AWS_KEY,
                    aws_secret_access_key=self.AWS_SECRET)               
                
                """ TODO : Required to add actions against alarms when needed """
                #self.sns = connect_to_region(self.AWS_REGION)
                #self.topics = self.sns.get_all_topics()
                #self.topic = self.topics[u'ListTopicsResponse']['ListTopicsResult']['Topics'][0]['TopicArn']

                #Cloudwatch Connection
                self.cloudwatch_conn = boto.ec2.cloudwatch.connect_to_region(
                    self.AWS_REGION,
                    aws_access_key_id=self.AWS_KEY,
                    aws_secret_access_key=self.AWS_SECRET) 
                connection_dict = dict()
                connection_dict['ec2_connection'] = self.ec2_conn
                connection_dict['cloudwatch_connection'] = self.cloudwatch_conn
                return connection_dict
                
            except Exception as e:
                log.error("Failed to Connect with AWS %s: ",str(e)) 

