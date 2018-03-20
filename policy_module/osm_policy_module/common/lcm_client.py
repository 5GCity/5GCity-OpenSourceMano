import json

from kafka import KafkaProducer

from osm_policy_module.core.config import Config


class LcmClient:
    def __init__(self):
        cfg = Config.instance()
        self.kafka_server = {
            'server': '{}:{}'.format(cfg.get('policy_module', 'kafka_server_host'),
                                     cfg.get('policy_module', 'kafka_server_port'))}
        self.producer = KafkaProducer(bootstrap_servers=self.kafka_server,
                                      key_serializer=str.encode,
                                      value_serializer=lambda v: json.dumps(v).encode('utf-8'))

    def scale(self, nsr_id, name, action):
        msg = self._create_scale_action_payload(nsr_id, name, action)
        self.producer.send(topic='alarm_request', key='create_alarm_request', value=msg)
        self.producer.flush()
        pass

    def _create_scale_action_payload(self, nsr_id, name, action):
        msg = {
            "ns_id": nsr_id,
            "scaling_group_descriptor": {
                "name": name,
                "action": action
            }
        }
        return msg
