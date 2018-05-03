from http import HTTPStatus

__author__ = "Alfonso Tierno <alfonso.tiernosepulveda@telefonica.com>"


class DbException(Exception):

    def __init__(self, message, http_code=HTTPStatus.NOT_FOUND):
        # TODO change to http.HTTPStatus instead of int that allows .value and .name
        self.http_code = http_code
        Exception.__init__(self, "database exception " + message)


class DbBase(object):

    def __init__(self):
        pass

    def db_connect(self, config):
        pass

    def db_disconnect(self):
        pass

    def get_list(self, table, filter={}):
        raise DbException("Method 'get_list' not implemented")

    def get_one(self, table, filter={}, fail_on_empty=True, fail_on_more=True):
        raise DbException("Method 'get_one' not implemented")

    def create(self, table, indata):
        raise DbException("Method 'create' not implemented")

    def del_list(self, table, filter={}):
        raise DbException("Method 'del_list' not implemented")

    def del_one(self, table, filter={}, fail_on_empty=True):
        raise DbException("Method 'del_one' not implemented")
