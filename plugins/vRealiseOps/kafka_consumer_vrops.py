# -*- coding: utf-8 -*-
"""
vROPs Kafka Consumer that consumes the request messages
"""


from kafka import KafkaConsumer
from kafka.errors import KafkaError
import logging as log

class vROP_KafkaConsumer(object):
    """
        Kafka Consumer for vROPs
    """

    def __init__(self, topics=[], broker_uri=None):
        """
            Method to initize KafkaConsumer
            Args:
                broker_uri - hostname:port uri of Kafka broker
                topics - list of topics to subscribe
            Returns:
               None
        """

        if broker_uri is None:
            self.broker = '0.0.0.0:9092'
        else:
            self.broker = broker_uri

        self.topic = topics
        print ("vROPs Consumer started, Broker URI: {}".format(self.broker))
        print ("Subscribed Topics {}".format(self.topic))
        try:
            self.vrops_consumer = KafkaConsumer(bootstrap_servers=self.broker)
            self.vrops_consumer.subscribe(self.topic)
        except Exception as exp:
            msg = "fail to create consumer for topic {} with broker {} Error : {}"\
                    .format(self.topic, self.broker, exp)
            log.error(msg)
            raise Exception(msg)

