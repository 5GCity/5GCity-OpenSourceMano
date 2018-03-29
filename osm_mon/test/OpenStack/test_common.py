# Copyright 2017 Intel Research and Development Ireland Limited
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Intel Corporation

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at

#         http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# For those usages not covered by the Apache License, Version 2.0 please
# contact: helena.mcgough@intel.com or adrian.hoban@intel.com
##
"""Tests for all common OpenStack methods."""

import json

import logging

import unittest

from keystoneclient.v3 import client

import mock

from osm_mon.core.auth import AuthManager
from osm_mon.core.database import VimCredentials
from osm_mon.plugins.OpenStack.common import Common
from osm_mon.plugins.OpenStack.settings import Config

import requests

__author__ = "Helena McGough"

log = logging.getLogger(__name__)


class Message(object):
    """Mock a message for an access credentials request."""

    def __init__(self):
        """Initialise the topic and value of access_cred message."""
        self.topic = "access_credentials"
        self.value = json.dumps({"mock_value": "mock_details",
                                 "vim_type": "OPENSTACK",
                                 "access_config":
                                     {"openstack_site": "my_site",
                                      "user": "my_user",
                                      "password": "my_password",
                                      "vim_tenant_name": "my_tenant"}})


class TestCommon(unittest.TestCase):
    """Test the common class for OpenStack plugins."""

    def setUp(self):
        """Test Setup."""
        super(TestCommon, self).setUp()
        self.common = Common()
        self.creds = VimCredentials()
        self.creds.id = 'test_id'
        self.creds.user = 'user'
        self.creds.url = 'url'
        self.creds.password = 'password'
        self.creds.tenant_name = 'tenant_name'

    @mock.patch.object(AuthManager, "get_credentials")
    @mock.patch.object(Config, "instance")
    @mock.patch.object(client, "Client")
    def test_get_auth_token(self, key_client, cfg, get_creds):
        """Test generating a new authentication token."""
        get_creds.return_value = self.creds
        Common.get_auth_token('test_id')
        get_creds.assert_called_with('test_id')
        key_client.assert_called_with(auth_url='url', password='password', tenant_name='tenant_name', username='user')

    @mock.patch.object(requests, 'post')
    def test_post_req(self, post):
        """Testing a post request."""
        Common.perform_request("url", "auth_token", req_type="post",
                                    payload="payload")

        post.assert_called_with("url", data="payload", headers=mock.ANY,
                                timeout=mock.ANY)

    @mock.patch.object(requests, 'get')
    def test_get_req(self, get):
        """Testing a get request."""
        # Run the defualt get request without any parameters
        Common.perform_request("url", "auth_token", req_type="get")

        get.assert_called_with("url", params=None, headers=mock.ANY,
                               timeout=mock.ANY)

        # Test with some parameters specified
        get.reset_mock()
        Common.perform_request("url", "auth_token", req_type="get",
                                    params="some parameters")

        get.assert_called_with("url", params="some parameters",
                               headers=mock.ANY, timeout=mock.ANY)

    @mock.patch.object(requests, 'put')
    def test_put_req(self, put):
        """Testing a put request."""
        Common.perform_request("url", "auth_token", req_type="put",
                                    payload="payload")
        put.assert_called_with("url", data="payload", headers=mock.ANY,
                               timeout=mock.ANY)

    @mock.patch.object(requests, 'delete')
    def test_delete_req(self, delete):
        """Testing a delete request."""
        Common.perform_request("url", "auth_token", req_type="delete")

        delete.assert_called_with("url", headers=mock.ANY, timeout=mock.ANY)
