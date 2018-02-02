from aiokafka import AIOKafkaConsumer
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError
from msgbase import MsgBase, MsgException
import asyncio
import yaml
#import json

class msgKafka(MsgBase):
    def __init__(self):
        self.host = None
        self.port = None
        self.consumer = None
        self.producer = None
        # create a different file for each topic
        #self.files = {}

    def connect(self, config):
        try:
            self.host = config["host"]
            self.port = config["port"]
            self.topic_lst = []
            self.loop = asyncio.get_event_loop()
            self.broker = str(self.host) + ":" + str(self.port)

        except Exception as e:  # TODO refine
            raise MsgException(str(e))

    def write(self, topic, msg, key):

        try:
            self.loop.run_until_complete(self.aiowrite(key, msg=yaml.safe_dump(msg, default_flow_style=True), topic=topic))

        except Exception as e:
            raise MsgException("Error writing {} topic: {}".format(topic, str(e)))

    def read(self, topic):
        self.topic_lst.append(topic)
        try:
            return self.loop.run_until_complete(self.aioread(self.topic_lst))
        except Exception as e:
            raise MsgException("Error reading {} topic: {}".format(topic, str(e)))

    async def aiowrite(self, key, msg, topic):
        try:
            self.producer = AIOKafkaProducer(loop=self.loop, key_serializer=str.encode, value_serializer=str.encode,
                                             bootstrap_servers=self.broker)
            await self.producer.start()
            await self.producer.send(topic=topic, key=key, value=msg)
        except Exception as e:
            raise MsgException("Error publishing to {} topic: {}".format(topic, str(e)))
        finally:
            await self.producer.stop()

    async def aioread(self, topic):
        self.consumer = AIOKafkaConsumer(loop=self.loop, bootstrap_servers=self.broker)
        await self.consumer.start()
        self.consumer.subscribe(topic)
        try:
            async for message in self.consumer:
                return yaml.load(message.key), yaml.load(message.value)
        except KafkaError as e:
            raise MsgException(str(e))
        finally:
            await self.consumer.stop()


