# Copyright 2017 Intel Research and Development Ireland Limited
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Intel Corporation

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at

#         http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# For those usages not covered by the Apache License, Version 2.0 please
# contact: prithiv.mohan@intel.com or adrian.hoban@intel.com
##

'''
This is a kafka producer app that interacts with the SO and the plugins of the
datacenters like OpenStack, VMWare, AWS.
'''

__author__ = "Prithiv Mohan"
__date__   = "06/Sep/2017"


from kafka import KafkaProducer as kaf
from kafka.errors import KafkaError
import logging
import json
import jsmin
import os
from os import listdir
from jsmin import jsmin

json_path = os.path.join(os.pardir+"/models/")


class KafkaProducer(object):

    def __init__(self, topic):

        self._topic= topic

        if "BROKER_URI" in os.environ:
            broker = os.getenv("BROKER_URI")
        else:
            broker = "localhost:9092"

        '''
        If the broker URI is not set in the env, by default,
        localhost container is taken as the host because an instance of
        is already running.
        '''

        self.producer = kaf(key_serializer=str.encode,
                   value_serializer=lambda v: json.dumps(v).encode('ascii'),
                   bootstrap_servers=broker, api_version=(0,10))


    def publish(self, key, value, topic=None):
        try:
            future = self.producer.send(key, value, topic)
            self.producer.flush()
        except Exception:
            logging.exception("Error publishing to {} topic." .format(topic))
            raise
        try:
            record_metadata = future.get(timeout=10)
            logging.debug("TOPIC:", record_metadata.topic)
            logging.debug("PARTITION:", record_metadata.partition)
            logging.debug("OFFSET:", record_metadata.offset)
        except KafkaError:
            pass

    def create_alarm_request(self, key, message, topic):

       #External to MON

        payload_create_alarm = jsmin(open(os.path.join(json_path,
                                         'create_alarm.json')).read())
        self.publish(key,
                value=json.dumps(payload_create_alarm),
                topic='alarm_request')

    def create_alarm_response(self, key, message, topic):

       #Internal to MON

        payload_create_alarm_resp = jsmin(open(os.path.join(json_path,
                                         'create_alarm_resp.json')).read())

        self.publish(key,
                value = message,
                topic = 'alarm_response')

    def acknowledge_alarm(self, key, message, topic):

       #Internal to MON

        payload_acknowledge_alarm = jsmin(open(os.path.join(json_path,
                                         'acknowledge_alarm.json')).read())

        self.publish(key,
                value = json.dumps(payload_acknowledge_alarm),
                topic = 'alarm_request')

    def list_alarm_request(self, key, message, topic):

        #External to MON

        payload_alarm_list_req = jsmin(open(os.path.join(json_path,
                                      'list_alarm_req.json')).read())

        self.publish(key,
                value=json.dumps(payload_alarm_list_req),
                topic='alarm_request')

    def notify_alarm(self, key, message, topic):

        payload_notify_alarm = jsmin(open(os.path.join(json_path,
                                          'notify_alarm.json')).read())

        self.publish(key,
                value=message,
                topic='alarm_response')

    def list_alarm_response(self, key, message, topic):

        payload_list_alarm_resp = jsmin(open(os.path.join(json_path,
                                             'list_alarm_resp.json')).read())

        self.publish(key,
                value=message,
                topic='alarm_response')


    def update_alarm_request(self, key, message, topic):

      # External to Mon

        payload_update_alarm_req = jsmin(open(os.path.join(json_path,
                                        'update_alarm_req.json')).read())

        self.publish(key,
                value=json.dumps(payload_update_alarm_req),
                topic='alarm_request')


    def update_alarm_response(self, key, message, topic):

        # Internal to Mon 

        payload_update_alarm_resp = jsmin(open(os.path.join(json_path,
                                        'update_alarm_resp.json')).read())

        self.publish(key,
                value=message,
                topic='alarm_response')


    def delete_alarm_request(self, key, message, topic):

      # External to Mon

        payload_delete_alarm_req = jsmin(open(os.path.join(json_path,
                                        'delete_alarm_req.json')).read())

        self.publish(key,
                value=json.dumps(payload_delete_alarm_req),
                topic='alarm_request')

    def delete_alarm_response(self, key, message, topic):

      # Internal to Mon

        payload_delete_alarm_resp = jsmin(open(os.path.join(json_path,
                                               'delete_alarm_resp.json')).read())

        self.publish(key,
                value=message,
                topic='alarm_response')



    def create_metrics_request(self, key, message, topic):

        # External to Mon

        payload_create_metrics_req = jsmin(open(os.path.join(json_path,
                                                'create_metric_req.json')).read())

        self.publish(key,
                value=json.dumps(payload_create_metrics_req),
                topic='metric_request')


    def create_metrics_resp(self, key, message, topic):

        # Internal to Mon

        payload_create_metrics_resp = jsmin(open(os.path.join(json_path,
                                                 'create_metric_resp.json')).read())

        self.publish(key,
                value=message,
                topic='metric_response')


    def read_metric_data_request(self, key, message, topic):

        # External to Mon

        payload_read_metric_data_request = jsmin(open(os.path.join(json_path,
                                                      'read_metric_data_req.json')).read())

        self.publish(key,
                value=json.dumps(payload_read_metric_data_request),
                topic='metric_request')


    def read_metric_data_response(self, key, message, topic):

        # Internal to Mon

        payload_metric_data_response = jsmin(open(os.path.join(json_path,
                                                  'read_metric_data_resp.json')).read())

        self.publish(key,
                value=message,
                topic='metric_response')


    def list_metric_request(self, key, message, topic):

        #External to MON

        payload_metric_list_req = jsmin(open(os.path.join(json_path,
                                             'list_metric_req.json')).read())

        self.publish(key,
                value=json.dumps(payload_metric_list_req),
                topic='metric_request')

    def list_metric_response(self, key, message, topic):

      #Internal to MON

        payload_metric_list_resp = jsmin(open(os.path.join(json_path,
                                              'list_metrics_resp.json')).read())

        self.publish(key,
                value=message,
                topic='metric_response')


    def delete_metric_request(self, key, message, topic):

      # External to Mon

        payload_delete_metric_req = jsmin(open(os.path.join(json_path,
                                               'delete_metric_req.json')).read())

        self.publish(key,
                value=json.dumps(payload_delete_metric_req),
                topic='metric_request')


    def delete_metric_response(self, key, message, topic):

      # Internal to Mon

        payload_delete_metric_resp = jsmin(open(os.path.join(json_path,
                                                'delete_metric_resp.json')).read())

        self.publish(key,
                value=message,
                topic='metric_response')


    def update_metric_request(self, key, message, topic):

        # External to Mon

        payload_update_metric_req = jsmin(open(os.path.join(json_path,
                                               'update_metric_req.json')).read())

        self.publish(key,
                value=json.dumps(payload_update_metric_req),
                topic='metric_request')


    def update_metric_response(self, key, message, topic):

        # Internal to Mon

        payload_update_metric_resp = jsmin(open(os.path.join(json_path,
                                                'update_metric_resp.json')).read())

        self.publish(key,
                value=message,
                topic='metric_response')

    def access_credentials(self, key, message, topic):

        payload_access_credentials = jsmin(open(os.path.join(json_path,
                                                'access_credentials.json')).read())

        self.publish(key,
                value=json.dumps(payload_access_credentials),
                topic='access_credentials')
