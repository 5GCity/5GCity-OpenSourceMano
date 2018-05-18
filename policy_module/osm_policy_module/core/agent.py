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
from typing import Dict, List

import peewee
import yaml

from kafka import KafkaConsumer
from osm_policy_module.core.config import Config
from osm_policy_module.common.lcm_client import LcmClient

from osm_policy_module.common.alarm_config import AlarmConfig
from osm_policy_module.common.mon_client import MonClient
from osm_policy_module.core.database import ScalingRecord, ScalingAlarm

log = logging.getLogger(__name__)


class PolicyModuleAgent:
    def run(self):
        cfg = Config.instance()
        # Initialize servers
        kafka_server = '{}:{}'.format(cfg.get('policy_module', 'kafka_server_host'),
                                      cfg.get('policy_module', 'kafka_server_port'))

        # Initialize Kafka consumer
        log.info("Connecting to Kafka server at %s", kafka_server)
        # TODO: Add logic to handle deduplication of messages when using group_id.
        # See: https://stackoverflow.com/a/29836412
        consumer = KafkaConsumer(bootstrap_servers=kafka_server,
                                 key_deserializer=bytes.decode,
                                 value_deserializer=bytes.decode)
        consumer.subscribe(['lcm_pm', 'alarm_response'])

        for message in consumer:
            log.info("Message arrived: %s", message)
            try:
                if message.key == 'configure_scaling':
                    try:
                        content = json.loads(message.value)
                    except:
                        content = yaml.safe_load(message.value)
                    log.info("Creating scaling record in DB")
                    # TODO: Use transactions: http://docs.peewee-orm.com/en/latest/peewee/transactions.html
                    scaling_record = ScalingRecord.create(
                        nsr_id=content['ns_id'],
                        name=content['scaling_group_descriptor']['name'],
                        content=json.dumps(content)
                    )
                    log.info("Created scaling record in DB : nsr_id=%s, name=%s, content=%s",
                             scaling_record.nsr_id,
                             scaling_record.name,
                             scaling_record.content)
                    alarm_configs = self._get_alarm_configs(content)
                    for config in alarm_configs:
                        mon_client = MonClient()
                        log.info("Creating alarm record in DB")
                        alarm_uuid = mon_client.create_alarm(
                            metric_name=config.metric_name,
                            ns_id=scaling_record.nsr_id,
                            vdu_name=config.vdu_name,
                            vnf_member_index=config.vnf_member_index,
                            threshold=config.threshold,
                            operation=config.operation,
                            statistic=config.statistic
                        )
                        ScalingAlarm.create(
                            alarm_id=alarm_uuid,
                            action=config.action,
                            scaling_record=scaling_record
                        )
                if message.key == 'notify_alarm':
                    content = json.loads(message.value)
                    alarm_id = content['notify_details']['alarm_uuid']
                    metric_name = content['notify_details']['metric_name']
                    operation = content['notify_details']['operation']
                    threshold = content['notify_details']['threshold_value']
                    vdu_name = content['notify_details']['vdu_name']
                    vnf_member_index = content['notify_details']['vnf_member_index']
                    ns_id = content['notify_details']['ns_id']
                    log.info(
                        "Received alarm notification for alarm %s, \
                        metric %s, \
                        operation %s, \
                        threshold %s, \
                        vdu_name %s, \
                        vnf_member_index %s, \
                        ns_id %s ",
                        alarm_id, metric_name, operation, threshold, vdu_name, vnf_member_index, ns_id)
                    try:
                        alarm = ScalingAlarm.select().where(ScalingAlarm.alarm_id == alarm_id).get()
                        lcm_client = LcmClient()
                        log.info("Sending scaling action message for ns: %s", alarm_id)
                        lcm_client.scale(alarm.scaling_record.nsr_id, alarm.scaling_record.name, alarm.action)
                    except ScalingAlarm.DoesNotExist:
                        log.info("There is no action configured for alarm %.", alarm_id)
            except Exception:
                log.exception("Error consuming message: ")

    def _get_alarm_configs(self, message_content: Dict) -> List[AlarmConfig]:
        scaling_criterias = message_content['scaling_group_descriptor']['scaling_policy']['scaling_criteria']
        alarm_configs = []
        for criteria in scaling_criterias:
            metric_name = ''
            scale_out_threshold = criteria['scale_out_threshold']
            scale_in_threshold = criteria['scale_in_threshold']
            scale_out_operation = criteria['scale_out_relational_operation']
            scale_in_operation = criteria['scale_in_relational_operation']
            statistic = criteria['monitoring_param']['aggregation_type']
            vdu_name = ''
            vnf_member_index = ''
            if 'vdu_monitoring_param' in criteria['monitoring_param']:
                vdu_name = criteria['monitoring_param']['vdu_monitoring_param']['vdu_name']
                vnf_member_index = criteria['monitoring_param']['vdu_monitoring_param']['vnf_member_index']
                metric_name = criteria['monitoring_param']['vdu_monitoring_param']['name']
            if 'vnf_metric' in criteria['monitoring_param']:
                # TODO vnf_metric
                continue
            if 'vdu_metric' in criteria['monitoring_param']:
                # TODO vdu_metric
                continue
            scale_out_alarm_config = AlarmConfig(metric_name,
                                                 vdu_name,
                                                 vnf_member_index,
                                                 scale_out_threshold,
                                                 scale_out_operation,
                                                 statistic,
                                                 'scale_out')
            scale_in_alarm_config = AlarmConfig(metric_name,
                                                vdu_name,
                                                vnf_member_index,
                                                scale_in_threshold,
                                                scale_in_operation,
                                                statistic,
                                                'scale_in')
            alarm_configs.append(scale_in_alarm_config)
            alarm_configs.append(scale_out_alarm_config)
        return alarm_configs
