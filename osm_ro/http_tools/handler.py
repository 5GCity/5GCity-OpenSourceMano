# -*- coding: utf-8 -*-
##
# Copyright 2018 University of Bristol - High Performance Networks Research
# Group
# All Rights Reserved.
#
# Contributors: Anderson Bravalheri, Dimitrios Gkounis, Abubakar Siddique
# Muqaddas, Navdeep Uniyal, Reza Nejabati and Dimitra Simeonidou
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact with: <highperformance-networks@bristol.ac.uk>
#
# Neither the name of the University of Bristol nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# This work has been performed in the context of DCMS UK 5G Testbeds
# & Trials Programme and in the framework of the Metro-Haul project -
# funded by the European Commission under Grant number 761727 through the
# Horizon 2020 and 5G-PPP programmes.
##

from types import MethodType

from bottle import Bottle


class route(object):
    """Decorator that stores route information, so creating the routes can be
    postponed.

    This allows methods (OOP) with bottle.

    Arguments:
        method: HTTP verb (e.g. ``'get'``, ``'post'``, ``'put'``, ...)
        path: URL path that will be handled by the callback
    """
    def __init__(self, method, path, **kwargs):
        kwargs['method'] = method.upper()
        self.route_info = (path, kwargs)

    def __call__(self, function):
        function.route_info = self.route_info
        return function


class BaseHandler(object):
    """Base class that allows isolated webapp implementation using Bottle,
    when used in conjunction with the ``route`` decorator.

    In this context, a ``Handler`` is meant to be a collection of Bottle
    routes/callbacks related to a specific topic.

    A ``Handler`` instance can produce a WSGI app that can be mounted or merged
    inside another more general bottle app.

    Example:

        from http_tools.handler import Handler, route
        from http_tools.errors import ErrorHandler

        class MyHandler(Handler):
            plugins = [ErrorHandler()]
            url_base = '/my/url/base'

            @route('GET', '/some/path/<var>')
            def get_var(self, var):
                return var

        app = MyHandler.wsgi_app
        # ^  Webapp with a `GET /my/url/base/some/path/<var>` route
    """
    _wsgi_app = None

    url_base = ''
    """String representing a path fragment to be prepended to the routes"""

    plugins = []
    """Bottle plugins to be installed when creating the WSGI app"""

    @property
    def wsgi_app(self):
        """Create a WSGI app based on the implemented callbacks"""

        if self._wsgi_app:
            # Return if cached
            return self._wsgi_app

        app = Bottle()

        members = (getattr(self, m) for m in dir(self) if m != 'wsgi_app')
        callbacks = (m for m in members
                     if isinstance(m, MethodType) and hasattr(m, 'route_info'))

        for callback in callbacks:
            path, kwargs = callback.route_info
            kwargs.update(callback=callback, apply=self.plugins)
            app.route(self.url_base + path, **kwargs)

        self._wsgi_app = app

        return app
