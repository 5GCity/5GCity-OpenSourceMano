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
                                      value_serializer=lambda v: json.dumps(v).encode('utf-8'))

    def create_alarm(self, metric_name, resource_uuid, vim_uuid, threshold, statistic, operation):
        cor_id = random.randint(1, 1000000)
        msg = self._create_alarm_payload(cor_id, metric_name, resource_uuid, vim_uuid, threshold, statistic, operation)
        self.producer.send(topic='alarm_request', key='create_alarm_request', value=msg)
        self.producer.flush()
        consumer = KafkaConsumer(bootstrap_servers=self.kafka_server, consumer_timeout_ms=10000)
        consumer.subscribe(['alarm_response'])
        alarm_uuid = None
        for message in consumer:
            if message.key == 'create_alarm_response':
                content = json.load(message.value)
                if self._is_alarm_response_correlation_id_eq(cor_id, content):
                    alarm_uuid = content['alarm_create_response']['alarm_uuid']
                    # TODO Handle error response
                    break
        consumer.close()
        if not alarm_uuid:
            raise ValueError(
                'Timeout: No alarm creation response from MON. Are it\'s IP and port correctly configured?')
        return alarm_uuid

    def _create_alarm_payload(self, cor_id, metric_name, resource_uuid, vim_uuid, threshold, statistic, operation):
        create_alarm_request = {
            'correlation_id': cor_id,
            'alarm_name': str(uuid.uuid4()),
            'metric_name': metric_name,
            'resource_uuid': resource_uuid,
            'operation': operation,
            'severity': 'critical',
            'threshold_value': threshold,
            'statistic': statistic
        }
        msg = {
            'create_alarm_request': create_alarm_request,
            'vim_uuid': vim_uuid
        }
        return msg

    def _is_alarm_response_correlation_id_eq(self, cor_id, message_content):
        return message_content['alarm_create_response']['correlation_id'] == cor_id
