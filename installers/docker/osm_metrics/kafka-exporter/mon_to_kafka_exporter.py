from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
import logging
import yaml
import json
import sys
import re
import datetime
import time

logging.basicConfig(stream=sys.stdout,
                    format='%(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.INFO)
log = logging.getLogger(__name__)


def main():
    if len(sys.argv) <= 1:
        print ("Usage: metric-transformer.py kafka_server")
        exit()
    kafka_server = sys.argv.pop(1)
    kafka_host = kafka_server.split(':')[0]
    kafka_port = kafka_server.split(':')[1]
    transform_messages(kafka_host=kafka_host,
                       kafka_port=kafka_port)


def transform_messages(kafka_host, kafka_port):
    bootstrap_servers = '{}:{}'.format(kafka_host, kafka_port)
    producer = KafkaProducer(bootstrap_servers=bootstrap_servers,
                             key_serializer=str.encode,
                             value_serializer=str.encode)
    consumer = KafkaConsumer(bootstrap_servers=bootstrap_servers,
                             key_deserializer=str.encode,
                             value_deserializer=str.encode)
    consumer.subscribe(["metric_response"])
    for message in consumer:
        try:
            if message.topic == "metric_response":
                if message.key == "read_metric_data_response":
                    values = json.loads(message.value)
                    new_msg = {
                        'name': values['metric_name'],
                        'value': values['metrics_data']['metrics_series'][-1],
                        'labels': {
                            'resource_uuid': values['resource_uuid']
                        }
                    }
                    log.info("Message to kafka exporter: %s", new_msg)
                    future = producer.send(topic='kafka_exporter_topic', key='kafka-exporter-key',
                                           value=json.dumps(new_msg))
                    response = future.get()
                    log.info("Response from Kafka: %s", response)
        except Exception as e:
            log.exception("Error processing message: ")


if __name__ == '__main__':
    main()

