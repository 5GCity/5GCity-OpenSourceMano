
from http import HTTPStatus


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
        Exception.__init__(self, message)


class MsgBase(object):
    """
    Base class for all msgXXXX classes
    """

    def __init__(self):
        pass

    def connect(self, config):
        pass

    def write(self, msg):
        pass

    def read(self):
        pass

    def disconnect(self):
        pass

