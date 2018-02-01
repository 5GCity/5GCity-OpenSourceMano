import os
import yaml
import asyncio
from msgbase import MsgBase, MsgException


class msgLocal(MsgBase):

    def __init__(self):
        self.path = None
        # create a different file for each topic
        self.files = {}

    def connect(self, config):
        try:
            self.path = config["path"]
            if not self.path.endswith("/"):
                self.path += "/"
            if not os.path.exists(self.path):
                os.mkdir(self.path)
        except MsgException:
            raise
        except Exception as e:  # TODO refine
            raise MsgException(str(e))

    def disconnect(self):
        for f in self.files.values():
            try:
                f.close()
            except Exception as e:  # TODO refine
                pass

    def write(self, topic, key, msg):
        """
        Insert a message into topic
        :param topic: topic
        :param key: key text to be inserted
        :param msg: value object to be inserted
        :return: None or raises and exception
        """
        try:
            if topic not in self.files:
                self.files[topic] = open(self.path + topic, "w+")
            yaml.safe_dump({key: msg}, self.files[topic], default_flow_style=True)
            self.files[topic].flush()
        except Exception as e:  # TODO refine
            raise MsgException(str(e))

    def read(self, topic):
        try:
            if topic not in self.files:
                self.files[topic] = open(self.path + topic, "r+")
            msg = self.files[topic].read()
            msg_dict = yaml.load(msg)
            assert len(msg_dict) == 1
            for k, v in msg_dict.items():
                return k, v
        except Exception as e:  # TODO refine
            raise MsgException(str(e))

    async def aioread(self, loop, topic):
        try:
            if topic not in self.files:
                self.files[topic] = open(self.path + topic, "r+")
                # ignore previous content
                while self.files[topic].read():
                    pass
            while True:
                msg = self.files[topic].read()
                if msg:
                    break
                await asyncio.sleep(2, loop=loop)
            msg_dict = yaml.load(msg)
            assert len(msg_dict) == 1
            for k, v in msg_dict.items():
                return k, v
        except Exception as e:  # TODO refine
            raise MsgException(str(e))
