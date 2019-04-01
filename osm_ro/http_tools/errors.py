# -*- coding: utf-8 -*-
import logging
from functools import wraps

import bottle
import yaml

Bad_Request = 400
Unauthorized = 401
Not_Found = 404
Forbidden = 403
Method_Not_Allowed = 405
Not_Acceptable = 406
Request_Timeout = 408
Conflict = 409
Service_Unavailable = 503
Internal_Server_Error = 500


class HttpMappedError(Exception):
    """Base class for a new hierarchy that translate HTTP error codes
    to python exceptions

    This class accepts an extra argument ``http_code`` (integer
    representing HTTP error codes).
    """

    def __init__(self, message, http_code=Internal_Server_Error):
        Exception.__init__(self, message)
        self.http_code = http_code


class ErrorHandler(object):
    """Defines a default strategy for handling HttpMappedError.

    This class implements a wrapper (can also be used as decorator), that
    watches out for different exceptions and log them accordingly.

    Arguments:
        logger(logging.Logger): logger object to be used to report errors
    """
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger('openmano.http')

    def __call__(self, function):
        @wraps(function)
        def _wraped(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except bottle.HTTPError:
                raise
            except HttpMappedError as ex:
                self.logger.error(
                    "%s error %s",
                    function.__name__, ex.http_code, exc_info=True)
                bottle.abort(ex.http_code, str(ex))
            except yaml.YAMLError as ex:
                self.logger.error(
                    "YAML error while trying to serialize/unserialize fields",
                    exc_info=True)
                bottle.abort(Bad_Request, type(ex).__name__ + ": " + str(ex))
            except Exception as ex:
                self.logger.error("Unexpected exception: ", exc_info=True)
                bottle.abort(Internal_Server_Error,
                             type(ex).__name__ + ": " + str(ex))

        return _wraped
