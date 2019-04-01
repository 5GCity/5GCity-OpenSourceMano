# -*- coding: utf-8 -*-
import unittest

import bottle

from .. import errors as httperrors
from ...tests.helpers import TestCaseWithLogging


class TestHttpErrors(TestCaseWithLogging):
    def test_http_error_base(self):
        # When an error code is passed as argument
        ex = httperrors.HttpMappedError(http_code=1226324)
        # then it should be set in the exception object
        self.assertEqual(ex.http_code, 1226324)
        # When an error code is not passed as argument
        ex = httperrors.HttpMappedError()
        # then the default error code (internal server error) should be used
        self.assertEqual(ex.http_code, httperrors.Internal_Server_Error)

    def test_error_handler_should_log_unexpected_errors(self):
        # Given a error handler wraps a function
        error_handler = httperrors.ErrorHandler(self.logger)

        # and the function raises an unexpected error
        @error_handler
        def _throw():
            raise AttributeError('some error')

        # when the function is called
        with self.assertRaises(bottle.HTTPError):
            _throw()
        logs = self.caplog.getvalue()
        # then the exception should be contained by bottle
        # and a proper message should be logged
        assert "Unexpected exception:" in logs

    def test_error_handler_should_log_http_based_errors(self):
        # Given a error handler wraps a function
        error_handler = httperrors.ErrorHandler(self.logger)

        # and the function raises an error that is considered by the
        # application
        @error_handler
        def _throw():
            raise httperrors.HttpMappedError(http_code=404)

        # when the function is called
        with self.assertRaises(bottle.HTTPError):
            _throw()
        logs = self.caplog.getvalue()
        # then the exception should be contained by bottle
        # and a proper message should be logged
        assert "_throw error 404" in logs

    def test_error_handler_should_ignore_bottle_errors(self):
        # Given a error handler wraps a function
        error_handler = httperrors.ErrorHandler(self.logger)

        # and the function raises an error that is considered by the
        # application
        exception = bottle.HTTPError()

        @error_handler
        def _throw():
            raise exception

        # when the function is called
        with self.assertRaises(bottle.HTTPError) as context:
            _throw()
        # then the exception should bypass the error handler
        self.assertEqual(context.exception, exception)


if __name__ == '__main__':
    unittest.main()
