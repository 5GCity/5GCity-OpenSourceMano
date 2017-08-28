from kafka import KafkaProducer
from kafka.errors import KafkaError
import logging
import json


class KafkaProducer(object):

    def __init__(self):
        if not cfg.CONF.kafka.uri:
            raise Exception("Kafka URI Not Found. Check the config file for Kafka URI")
        else:
            broker = cfg.CONF.kafka.uri
        producer = KafkaProducer(key_serializer=str.encode, value_serializer=lambda v: json.dumps(v).encode('ascii'), bootstrap_servers='localhost:9092', api_version=(0,10))

    def publish(self, topic, messages):

        """Takes messages and puts them on the supplied kafka topic
        Memory Usage is used as a test value for alarm creation for
        topic 'alarms'. 'Configure_alarm' is the key, resource UUID
        and type of alarm are the list of values.

        """

        payload = {'configure_alarm': ['memory_usage']}
        try:
            future = producer.send('alarms', payload)
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

