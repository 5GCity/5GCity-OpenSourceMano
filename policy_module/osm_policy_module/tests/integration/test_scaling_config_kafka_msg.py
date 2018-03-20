import json
import logging
import os
import unittest

from kafka import KafkaProducer

log = logging.getLogger(__name__)


# logging.basicConfig(stream=sys.stdout,
#                     format='%(asctime)s %(message)s',
#                     datefmt='%m/%d/%Y %I:%M:%S %p',
#                     level=logging.DEBUG)

class ScalingConfigTest(unittest.TestCase):
    def test_send_scaling_config_msg(self):
        try:
            with open(
                    os.path.join(os.path.dirname(__file__), '../examples/configure_scaling_full_example.json')) as file:
                payload = json.load(file)
                kafka_server = '{}:{}'.format(os.getenv("KAFKA_SERVER_HOST", "localhost"),
                                              os.getenv("KAFKA_SERVER_PORT", "9092"))
                producer = KafkaProducer(bootstrap_servers=kafka_server,
                                         key_serializer=str.encode,
                                         value_serializer=str.encode)
                future = producer.send('lcm_pm', json.dumps(payload), key="configure_scaling")
                result = future.get(timeout=60)
                log.info('Result: %s', result)

                producer.flush()
                self.assertIsNotNone(result)
        except Exception as e:
            self.fail(e)


if __name__ == '__main__':
    unittest.main()
