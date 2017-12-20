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
# contact with: usman.javaid@xflowresearch.com
##

'''
Access credentials class implements all the methods to store the access credentials for AWS
'''

__author__ = "Usman Javaid"
__date__   = "20-December-2017"

import os
import sys
import json
import logging

logging.basicConfig(filename='MON_plugins.log',
                    format='%(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p', filemode='a',
                    level=logging.INFO)
log = logging.getLogger(__name__)

class AccessCredentials():

    def access_credential_calls(self,message):  
        try:   
            message = json.loads(message.value)['access_config']
            
            AWS_KEY = message['user']
            AWS_SECRET = message['password']
            AWS_REGION = message['vim_tenant_name']

            os.environ['AWS_ACCESS_KEY_ID'] = AWS_KEY
            os.environ['AWS_SECRET_ACCESS_KEY'] = AWS_SECRET
            os.environ['AWS_EC2_REGION'] = AWS_REGION


            #aws_credentials.txt file to save the access credentials 
            cloudwatch_credentials = open("../../plugins/CloudWatch/cloudwatch_credentials.txt","w+")
            cloudwatch_credentials.write("AWS_ACCESS_KEY_ID="+AWS_KEY+
                                         "\nAWS_SECRET_ACCESS_KEY="+AWS_SECRET+
                                         "\nAWS_EC2_REGION="+AWS_REGION)
            
            #Closing the file
            cloudwatch_credentials.close()
            log.info("Access credentials sourced for CloudWatch MON plugin")

        except Exception as e:
                log.error("Access credentials not provided correctly: %s", str(e))
