
class FsException(Exception):

    def __init__(self, message, http_code=404):
        self.http_code = http_code
        Exception.__init__(self, message)


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
        pass

    def file_exists(self, storage):
        pass

    def file_size(self, storage):
        pass

    def file_extract(self, tar_object, path):
        pass

    def file_open(self, storage, mode):
        pass

    def file_delete(self, storage, ignore_non_exist=False):
        pass

