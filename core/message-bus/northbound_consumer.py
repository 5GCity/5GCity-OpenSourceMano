from kafka import KafkaConsumer
from kafka.errors import KafkaError
import logging

class KafkaConsumer(object):
    """Adds messages to a kafka topic. Topic is hardcoded as 'alarms' and group as
    'my_group' for now.

    """

    def __init__(self, uri):
        """Init

             uri - kafka connection details
        """
        if not cfg.CONF.kafka.uri:
            raise Exception("Kafka URI Not Found. Check the config file for Kafka URI")
        else:
            broker = cfg.CONF.kafka.uri
        consumer = KafkaConsumer('alarms',
            group_id='my_group',
            bootstrap_servers=broker, api_version=(0,10))
        #KafkaConsumer(value_deserializer=lambda m: json.loads(m.decode('ascii')))

    def consume(self, topic, messages):
        for message in self._consumer:
            print ("%s:%d:%d: key=%s value=%s" % (message.topic, message.partition, message.offset, message.key, message.value))
