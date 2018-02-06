import logging
import asyncio
import yaml
from aiokafka import AIOKafkaConsumer
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError
from msgbase import MsgBase, MsgException
#import json


class MsgKafka(MsgBase):
    def __init__(self, logger_name='msg'):
        self.logger = logging.getLogger(logger_name)
        self.host = None
        self.port = None
        self.consumer = None
        self.producer = None
        # create a different file for each topic
        #self.files = {}

    def connect(self, config):
        try:
            if "logger_name" in config:
                self.logger = logging.getLogger(config["logger_name"])
            self.host = config["host"]
            self.port = config["port"]
            self.topic_lst = []
            self.loop = asyncio.get_event_loop()
            self.broker = str(self.host) + ":" + str(self.port)

        except Exception as e:  # TODO refine
            raise MsgException(str(e))

    def write(self, topic, key, msg):
        try:
            self.loop.run_until_complete(self.aiowrite(topic=topic, key=key, msg=yaml.safe_dump(msg, default_flow_style=True)))

        except Exception as e:
            raise MsgException("Error writing {} topic: {}".format(topic, str(e)))

    def read(self, topic):
        #self.topic_lst.append(topic)
        try:
            return self.loop.run_until_complete(self.aioread(topic))
        except Exception as e:
            raise MsgException("Error reading {} topic: {}".format(topic, str(e)))

    async def aiowrite(self, topic, key, msg, loop=None):
        try:
            if not loop:
                loop = self.loop
            self.producer = AIOKafkaProducer(loop=loop, key_serializer=str.encode, value_serializer=str.encode,
                                             bootstrap_servers=self.broker)
            await self.producer.start()
            await self.producer.send(topic=topic, key=key, value=msg)
        except Exception as e:
            raise MsgException("Error publishing to {} topic: {}".format(topic, str(e)))
        finally:
            await self.producer.stop()

    async def aioread(self, topic, loop=None):
        if not loop:
            loop = self.loop
        self.consumer = AIOKafkaConsumer(loop=loop, bootstrap_servers=self.broker)
        await self.consumer.start()
        self.consumer.subscribe([topic])
        try:
            async for message in self.consumer:
                return yaml.load(message.key), yaml.load(message.value)
        except KafkaError as e:
            raise MsgException(str(e))
        finally:
            await self.consumer.stop()


