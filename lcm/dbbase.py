

class DbException(Exception):

    def __init__(self, message, http_code=404):
        self.http_code = http_code
        Exception.__init__(self, message)

class dbbase(object):

    def __init__(self):
        pass

    def db_connect(self, config):
        pass

    def db_disconnect(self):
        pass

    def get_list(self, table, filter={}):
        pass

    def get_one(self, table, filter={}, fail_on_empty=True, fail_on_more=True):
        pass

    def create(self, table, indata):
        pass

    def del_list(self, table, filter={}):
        pass

    def del_one(self, table, filter={}, fail_on_empty=True):
        pass


