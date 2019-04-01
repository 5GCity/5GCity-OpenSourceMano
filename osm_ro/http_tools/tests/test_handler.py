# -*- coding: utf-8 -*-
import unittest

from mock import MagicMock, patch
from webtest import TestApp

from .. import handler
from ..handler import BaseHandler, route


class TestIntegration(unittest.TestCase):
    def test_wsgi_app(self):
        # Given a Handler class that implements a route
        some_plugin = MagicMock()

        class MyHandler(BaseHandler):
            url_base = '/42'
            plugins = [some_plugin]

            @route('get', '/some/path')
            def callback(self):
                return 'some content'

        route_mock = MagicMock()
        with patch(handler.__name__+'.Bottle.route', route_mock):
            # When we try to access wsgi_app for the first time
            my_handler = MyHandler()
            assert my_handler.wsgi_app
            # then bottle.route should be called with the right arguments
            route_mock.assert_called_once_with('/42/some/path', method='GET',
                                               callback=my_handler.callback,
                                               apply=[some_plugin])

            # When we try to access wsgi_app for the second time
            assert my_handler.wsgi_app
            # then the result should be cached
            # and bottle.route should not be called again
            self.assertEqual(route_mock.call_count, 1)

    def test_route_created(self):
        # Given a Handler class, as in the example documentation
        class MyHandler(BaseHandler):
            def __init__(self):
                self.value = 42

            @route('GET', '/some/path/<param>')
            def callback(self, param):
                return '{} + {}'.format(self.value, param)

        # when this class is used to generate a webapp
        app = TestApp(MyHandler().wsgi_app)

        # then the defined URLs should be available
        response = app.get('/some/path/0')
        self.assertEqual(response.status_code, 200)
        # and the callbacks should have access to ``self``
        response.mustcontain('42 + 0')

    def test_url_base(self):
        # Given a Handler class that allows url_base customization
        class MyHandler(BaseHandler):
            def __init__(self, url_base):
                self.url_base = url_base

            @route('GET', '/some/path/<param>')
            def callback(self, param):
                return param

        # when this class is used to generate a webapp
        app = TestApp(MyHandler('/prefix').wsgi_app)

        # then the prefixed URLs should be available
        response = app.get('/prefix/some/path/content')
        self.assertEqual(response.status_code, 200)
        response.mustcontain('content')

    def test_starting_param(self):
        # Given a Handler class with a route beginning with a param
        class MyHandler(BaseHandler):
            @route('GET', '/<param>/some/path')
            def callback(self, param):
                return '**{}**'.format(param)

        # is used to generate a webapp
        app = TestApp(MyHandler().wsgi_app)

        # when the defined URLs is accessed
        response = app.get('/42/some/path')
        # Then no error should happen
        self.assertEqual(response.status_code, 200)
        response.mustcontain('**42**')


if __name__ == '__main__':
    unittest.main()
