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
