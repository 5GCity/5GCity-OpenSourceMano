# -*- coding: utf-8 -*-

# Copyright 2018 Whitestack, LLC
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Whitestack, LLC

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
# contact: bdiaz@whitestack.com or glavado@whitestack.com
##
import json
import logging

from kafka import KafkaProducer

from osm_policy_module.core.config import Config

log = logging.getLogger(__name__)


class LcmClient:
    def __init__(self):
        cfg = Config.instance()
        self.kafka_server = '{}:{}'.format(cfg.get('policy_module', 'kafka_server_host'),
                                           cfg.get('policy_module', 'kafka_server_port'))
        self.producer = KafkaProducer(bootstrap_servers=self.kafka_server,
                                      key_serializer=str.encode,
                                      value_serializer=str.encode)

    def scale(self, nsr_id, name, action):
        msg = self._create_scale_action_payload(nsr_id, name, action)
        log.info("Sending scale action message: %s", json.dumps(msg))
        self.producer.send(topic='lcm_pm', key='trigger_scaling', value=json.dumps(msg))
        self.producer.flush()

    def _create_scale_action_payload(self, nsr_id, name, action):
        msg = {
            "ns_id": nsr_id,
            "scaling_group_descriptor": {
                "name": name,
                "action": action
            }
        }
        return msg
