
# import asyncio
from http import HTTPStatus

__author__ = "Alfonso Tierno <alfonso.tiernosepulveda@telefonica.com>"


class MsgException(Exception):
    """
    Base Exception class for all msgXXXX exceptions
    """

    def __init__(self, message, http_code=HTTPStatus.INTERNAL_SERVER_ERROR):
        """
        General exception
        :param message:  descriptive text
        :param http_code: <http.HTTPStatus> type. It contains ".value" (http error code) and ".name" (http error name
        """
        self.http_code = http_code
        Exception.__init__(self, "messaging exception " + message)


class MsgBase(object):
    """
    Base class for all msgXXXX classes
    """

    def __init__(self):
        pass

    def connect(self, config):
        pass

    def disconnect(self):
        pass

    def write(self, topic, key, msg):
        raise MsgException("Method 'write' not implemented")

    def read(self, topic):
        raise MsgException("Method 'read' not implemented")

    async def aiowrite(self, topic, key, msg, loop):
        raise MsgException("Method 'aiowrite' not implemented")

    async def aioread(self, topic, loop):
        raise MsgException("Method 'aioread' not implemented")
