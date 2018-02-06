import logging
import os
import yaml
import asyncio
from msgbase import MsgBase, MsgException

__author__ = "Alfonso Tierno <alfonso.tiernosepulveda@telefonica.com>"


class MsgLocal(MsgBase):

    def __init__(self, logger_name='msg'):
        self.logger = logging.getLogger(logger_name)
        self.path = None
        # create a different file for each topic
        self.files = {}

    def connect(self, config):
        try:
            if "logger_name" in config:
                self.logger = logging.getLogger(config["logger_name"])
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
            msg = ""
            if topic not in self.files:
                self.files[topic] = open(self.path + topic, "a+")
                # ignore previous content
                for line in self.files[topic]:
                    if not line.endswith("\n"):
                        msg = line
            msg += self.files[topic].readline()
            if not msg.endswith("\n"):
                return None
            msg_dict = yaml.load(msg)
            assert len(msg_dict) == 1
            for k, v in msg_dict.items():
                return k, v
        except Exception as e:  # TODO refine
            raise MsgException(str(e))

    async def aioread(self, topic, loop=None):
        try:
            msg = ""
            if not loop:
                loop = asyncio.get_event_loop()
            if topic not in self.files:
                self.files[topic] = open(self.path + topic, "a+")
                # ignore previous content
                for line in self.files[topic]:
                    if not line.endswith("\n"):
                        msg = line
            while True:
                msg += self.files[topic].readline()
                if msg.endswith("\n"):
                    break
                await asyncio.sleep(2, loop=loop)
            msg_dict = yaml.load(msg)
            assert len(msg_dict) == 1
            for k, v in msg_dict.items():
                return k, v
        except Exception as e:  # TODO refine
            raise MsgException(str(e))
