#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

#__author__ = "Prithiv Mohan"
#__date__   = "25/Sep/2017"

import sys
import threading
import pytest
from kafka import KafkaConsumer, KafkaProducer

def test_end_to_end():
    producer = KafkaProducer(bootstrap_servers='localhost:9092',
                             retries=5,
                             max_block_ms=10000,
                             value_serializer=str.encode)
    consumer = KafkaConsumer(bootstrap_servers='localhost:9092',
                             group_id=None,
                             consumer_timeout_ms=10000,
                             auto_offset_reset='earliest',
                             value_deserializer=bytes.decode)

    topic = 'TutorialTopic'

    messages = 100
    futures = []
    for i in range(messages):
        futures.append(producer.send(topic, 'msg %d' % i))
    ret = [f.get(timeout=30) for f in futures]
    assert len(ret) == messages

    producer.close()

    consumer.subscribe([topic])
    msgs = set()
    for i in range(messages):
        try:
            msgs.add(next(consumer).value)
        except StopIteration:
            break

    assert msgs == set(['msg %d' % i for i in range(messages)])
