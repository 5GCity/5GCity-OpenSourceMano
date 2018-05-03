
from http import HTTPStatus

__author__ = "Alfonso Tierno <alfonso.tiernosepulveda@telefonica.com>"


class FsException(Exception):
    def __init__(self, message, http_code=HTTPStatus.INTERNAL_SERVER_ERROR):
        self.http_code = http_code
        Exception.__init__(self, "storage exception " + message)


class FsBase(object):
    def __init__(self):
        pass

    def get_params(self):
        return {}

    def fs_connect(self, config):
        pass

    def fs_disconnect(self):
        pass

    def mkdir(self, folder):
        raise FsException("Method 'mkdir' not implemented")

    def file_exists(self, storage):
        raise FsException("Method 'file_exists' not implemented")

    def file_size(self, storage):
        raise FsException("Method 'file_size' not implemented")

    def file_extract(self, tar_object, path):
        raise FsException("Method 'file_extract' not implemented")

    def file_open(self, storage, mode):
        raise FsException("Method 'file_open' not implemented")

    def file_delete(self, storage, ignore_non_exist=False):
        raise FsException("Method 'file_delete' not implemented")
