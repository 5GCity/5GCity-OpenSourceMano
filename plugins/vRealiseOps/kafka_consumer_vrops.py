# -*- coding: utf-8 -*-

##
# Copyright 2016-2017 VMware Inc.
# This file is part of ETSI OSM
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
# contact:  osslegalrouting@vmware.com
##

"""
vROPs Kafka Consumer that consumes the request messages
"""


from kafka import KafkaConsumer
from kafka.errors import KafkaError
import logging as log

class vROP_KafkaConsumer(object):
    """
        Kafka Consumer for vROPs
    """

    def __init__(self, topics=[], broker_uri=None):
        """
            Method to initize KafkaConsumer
            Args:
                broker_uri - hostname:port uri of Kafka broker
                topics - list of topics to subscribe
            Returns:
               None
        """

        if broker_uri is None:
            self.broker = '0.0.0.0:9092'
        else:
            self.broker = broker_uri

        self.topic = topics
        print ("vROPs Consumer started, Broker URI: {}".format(self.broker))
        print ("Subscribed Topics {}".format(self.topic))
        try:
            self.vrops_consumer = KafkaConsumer(bootstrap_servers=self.broker)
            self.vrops_consumer.subscribe(self.topic)
        except Exception as exp:
            msg = "fail to create consumer for topic {} with broker {} Error : {}"\
                    .format(self.topic, self.broker, exp)
            log.error(msg)
            raise Exception(msg)

