from kafka import KafkaProducer
from kafka.errors import KafkaError
import logging


class KafkaProducer(object):

    def __init__(self):
        if not cfg.CONF.kafka.uri:
            raise Exception("Kafka URI Not Found. Check the config file for Kafka URI")
        else:
            broker = cfg.CONF.kafka.uri
        producer = KafkaProducer(bootstrap_servers=broker, api_version=(0,10))

    def publish(self, topic, messages):

        """Takes messages and puts them on the supplied kafka topic. The topic is
        hardcoded as 'alarms' and the message is harcoded as 'memory_usage' for now.

        """
        try:
            future = producer.send('alarms', b'memory_usage')
            producer.flush()
        except Exception:
            log.exception('Error publishing to {} topic.'.format(topic))
            raise
        try:
            record_metadata = future.get(timeout=10)
            self._log.debug("TOPIC:", record_metadata.topic)
            self._log.debug("PARTITION:", record_metadata.partition)
            self._log.debug("OFFSET:", record_metadata.offset)
        except KafkaError:
            pass
    #producer = KafkaProducer(retries=5)

