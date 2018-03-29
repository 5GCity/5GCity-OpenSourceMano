import json
import logging
import os
import unittest

from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError

log = logging.getLogger(__name__)


class ScalingConfigTest(unittest.TestCase):
    def setUp(self):
        try:
            kafka_server = '{}:{}'.format(os.getenv("KAFKA_SERVER_HOST", "localhost"),
                                          os.getenv("KAFKA_SERVER_PORT", "9092"))
            self.producer = KafkaProducer(bootstrap_servers=kafka_server,
                                          key_serializer=str.encode,
                                          value_serializer=str.encode)
            self.consumer = KafkaConsumer(bootstrap_servers='localhost:9092',
                                          group_id='osm_mon')
            self.consumer.subscribe(['lcm_pm'])
        except KafkaError:
            self.skipTest('Kafka server not present.')

    def test_send_scaling_config_msg(self):
        try:
            with open(
                    os.path.join(os.path.dirname(__file__), '../examples/configure_scaling_full_example.json')) as file:
                payload = json.load(file)
                future = self.producer.send('lcm_pm', json.dumps(payload), key="configure_scaling")
                result = future.get(timeout=60)
                log.info('Result: %s', result)

                self.producer.flush()
                # TODO: Improve assertions
                self.assertIsNotNone(result)
        except Exception as e:
            self.fail(e)


if __name__ == '__main__':
    unittest.main()
