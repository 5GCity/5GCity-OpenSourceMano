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
import random
import uuid

from kafka import KafkaProducer, KafkaConsumer

from osm_policy_module.core.config import Config

log = logging.getLogger(__name__)


class MonClient:
    def __init__(self):
        cfg = Config.instance()
        self.kafka_server = '{}:{}'.format(cfg.get('policy_module', 'kafka_server_host'),
                                           cfg.get('policy_module', 'kafka_server_port'))
        self.producer = KafkaProducer(bootstrap_servers=self.kafka_server,
                                      key_serializer=str.encode,
                                      value_serializer=str.encode)

    def create_alarm(self, metric_name: str, ns_id: str, vdu_name: str, vnf_member_index: str, threshold: int,
                     statistic: str, operation: str):
        cor_id = random.randint(1, 1000000)
        msg = self._create_alarm_payload(cor_id, metric_name, ns_id, vdu_name, vnf_member_index, threshold, statistic,
                                         operation)
        log.info("Sending create_alarm_request %s", msg)
        future = self.producer.send(topic='alarm_request', key='create_alarm_request', value=json.dumps(msg))
        future.get(timeout=60)
        consumer = KafkaConsumer(bootstrap_servers=self.kafka_server,
                                 key_deserializer=bytes.decode,
                                 value_deserializer=bytes.decode,
                                 consumer_timeout_ms=10000)
        consumer.subscribe(['alarm_response'])
        for message in consumer:
            if message.key == 'create_alarm_response':
                content = json.loads(message.value)
                log.info("Received create_alarm_response %s", content)
                if self._is_alarm_response_correlation_id_eq(cor_id, content):
                    alarm_uuid = content['alarm_create_response']['alarm_uuid']
                    # TODO Handle error response
                    return alarm_uuid

        raise ValueError('Timeout: No alarm creation response from MON. Is MON up?')

    def _create_alarm_payload(self, cor_id: int, metric_name: str, ns_id: str, vdu_name: str, vnf_member_index: str,
                              threshold: int, statistic: str, operation: str):
        alarm_create_request = {
            'correlation_id': cor_id,
            'alarm_name': str(uuid.uuid4()),
            'metric_name': metric_name,
            'ns_id': ns_id,
            'vdu_name': vdu_name,
            'vnf_member_index': vnf_member_index,
            'operation': operation,
            'severity': 'critical',
            'threshold_value': threshold,
            'statistic': statistic
        }
        msg = {
            'alarm_create_request': alarm_create_request,
        }
        return msg

    def _is_alarm_response_correlation_id_eq(self, cor_id, message_content):
        return message_content['alarm_create_response']['correlation_id'] == cor_id
