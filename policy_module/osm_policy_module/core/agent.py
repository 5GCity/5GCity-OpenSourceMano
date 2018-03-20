import json
import logging

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
        consumer = KafkaConsumer(bootstrap_servers=kafka_server,
                                 key_deserializer=bytes.decode,
                                 value_deserializer=bytes.decode,
                                 group_id="policy-module-agent")
        consumer.subscribe(['lcm_pm', 'alarm_response'])

        for message in consumer:
            log.info("Message arrived: %s", message)
            log.info("Message key: %s", message.key)
            try:
                if message.key == 'configure_scaling':
                    content = json.loads(message.value)
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
                            resource_uuid=config.resource_uuid,
                            vim_uuid=config.vim_uuid,
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
                    alarm = ScalingAlarm.select().where(ScalingAlarm.alarm_id == alarm_id).get()
                    if alarm:
                        lcm_client = LcmClient()
                        log.info("Sending scaling action message: %s", json.dumps(alarm))
                        lcm_client.scale(alarm.scaling_record.nsr_id, alarm.scaling_record.name, alarm.action)
            except Exception:
                log.exception("Error consuming message: ")

    def _get_alarm_configs(self, message_content):
        scaling_criterias = message_content['scaling_group_descriptor']['scaling_policy']['scaling_criteria']
        alarm_configs = []
        for criteria in scaling_criterias:
            metric_name = ''
            scale_out_threshold = criteria['scale_out_threshold']
            scale_in_threshold = criteria['scale_in_threshold']
            scale_out_operation = criteria['scale_out_relational_operation']
            scale_in_operation = criteria['scale_in_relational_operation']
            statistic = criteria['monitoring_param']['aggregation_type']
            vim_uuid = ''
            resource_uuid = ''
            if 'vdu_monitoring_param' in criteria['monitoring_param']:
                vim_uuid = criteria['monitoring_param']['vdu_monitoring_param']['vim_uuid']
                resource_uuid = criteria['monitoring_param']['vdu_monitoring_param']['resource_id']
                metric_name = criteria['monitoring_param']['vdu_monitoring_param']['name']
            if 'vnf_metric' in criteria['monitoring_param']:
                # TODO vnf_metric
                continue
            if 'vdu_metric' in criteria['monitoring_param']:
                # TODO vdu_metric
                continue
            scale_out_alarm_config = AlarmConfig(metric_name,
                                                 resource_uuid,
                                                 vim_uuid,
                                                 scale_out_threshold,
                                                 scale_out_operation,
                                                 statistic,
                                                 'scale_out')
            scale_in_alarm_config = AlarmConfig(metric_name,
                                                resource_uuid,
                                                vim_uuid,
                                                scale_in_threshold,
                                                scale_in_operation,
                                                statistic,
                                                'scale_in')
            alarm_configs.append(scale_in_alarm_config)
            alarm_configs.append(scale_out_alarm_config)
        return alarm_configs
