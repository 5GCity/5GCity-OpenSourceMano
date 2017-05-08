# Copyright 2017 Sandvine
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
OSM v1 client API
"""

from osmclient.v1 import vnf
from osmclient.v1 import vnfd
from osmclient.v1 import ns
from osmclient.v1 import nsd
from osmclient.v1 import vim
from osmclient.v1 import package
from osmclient.v1 import vca
from osmclient.v1 import utils
from osmclient.common import http


class Client(object):

    def __init__(
        self,
        host=None,
        so_port=8008,
        ro_host=None,
        ro_port=9090,
        upload_port=8443,
            **kwargs):
        self._user = 'admin'
        self._password = 'admin'

        if len(host.split(':')) > 1:
            # backwards compatible, port provided as part of host
            self._host = host.split(':')[0]
            self._so_port = host.split(':')[1]
        else:
            self._host = host
            self._so_port = so_port

        http_client = http.Http(
            'https://{}:{}/'.format(
                self._host,
                self._so_port))
        http_client.set_http_header(
            ['Accept: application/vnd.yand.data+json',
             'Content-Type: application/json'])

        if ro_host is None:
            ro_host = host
        ro_http_client = http.Http('http://{}:{}/'.format(ro_host, ro_port))
        ro_http_client.set_http_header(
            ['Accept: application/vnd.yand.data+json',
             'Content-Type: application/json'])

        upload_client = http.Http(
            'https://{}:{}/composer/upload?api_server={}{}'.format(
                self._host,
                upload_port,
                'https://localhost&upload_server=https://',
                self._host))

        self.vnf = vnf.Vnf(http_client, **kwargs)
        self.vnfd = vnfd.Vnfd(http_client, **kwargs)
        self.ns = ns.Ns(http=http_client, client=self, **kwargs)
        self.nsd = nsd.Nsd(http_client, **kwargs)
        self.vim = vim.Vim(
            http=http_client,
            ro_http=ro_http_client,
            client=self,
            **kwargs)
        self.package = package.Package(
            http=http_client,
            upload_http=upload_client,
            client=self,
            **kwargs)
        self.vca = vca.Vca(http_client, **kwargs)
        self.utils = utils.Utils(http_client, **kwargs)
