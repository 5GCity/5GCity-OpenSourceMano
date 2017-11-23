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

from plugins.OpenStack.common import Common
from plugins.OpenStack.settings import Config

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

    @mock.patch.object(client, "Client")
    def test_authenticate_exists(self, key_client):
        """Testing if an authentication token already exists."""
        # If the auth_token is already generated a new one will not be creates
        self.common._auth_token = "my_auth_token"
        token = self.common._authenticate()

        self.assertEqual(token, "my_auth_token")

    @mock.patch.object(Config, "instance")
    @mock.patch.object(client, "Client")
    def test_authenticate_none(self, key_client, cfg):
        """Test generating a new authentication token."""
        # If auth_token doesn't exist one will try to be created with keystone
        # With the configuration values from the environment
        self.common._auth_token = None
        config = cfg.return_value
        url = config.OS_AUTH_URL
        user = config.OS_USERNAME
        pword = config.OS_PASSWORD
        tenant = config.OS_TENANT_NAME

        self.common._authenticate()

        key_client.assert_called_with(auth_url=url,
                                      username=user,
                                      password=pword,
                                      tenant_name=tenant)
        key_client.reset_mock()

    @mock.patch.object(client, "Client")
    def test_authenticate_access_cred(self, key_client):
        """Test generating an auth_token using access_credentials from SO."""
        # Mock valid message from SO
        self.common._auth_token = None
        message = Message()

        self.common._authenticate(message=message)

        # The class variables are set for each consifugration
        self.assertEqual(self.common.openstack_url, "my_site")
        self.assertEqual(self.common.user, "my_user")
        self.assertEqual(self.common.password, "my_password")
        self.assertEqual(self.common.tenant, "my_tenant")
        key_client.assert_called

    @mock.patch.object(requests, 'post')
    def test_post_req(self, post):
        """Testing a post request."""
        self.common._perform_request("url", "auth_token", req_type="post",
                                     payload="payload")

        post.assert_called_with("url", data="payload", headers=mock.ANY,
                                timeout=mock.ANY)

    @mock.patch.object(requests, 'get')
    def test_get_req(self, get):
        """Testing a get request."""
        # Run the defualt get request without any parameters
        self.common._perform_request("url", "auth_token", req_type="get")

        get.assert_called_with("url", params=None, headers=mock.ANY,
                               timeout=mock.ANY)

        # Test with some parameters specified
        get.reset_mock()
        self.common._perform_request("url", "auth_token", req_type="get",
                                     params="some parameters")

        get.assert_called_with("url", params="some parameters",
                               headers=mock.ANY, timeout=mock.ANY)

    @mock.patch.object(requests, 'put')
    def test_put_req(self, put):
        """Testing a put request."""
        self.common._perform_request("url", "auth_token", req_type="put",
                                     payload="payload")
        put.assert_called_with("url", data="payload", headers=mock.ANY,
                               timeout=mock.ANY)

    @mock.patch.object(requests, 'delete')
    def test_delete_req(self, delete):
        """Testing a delete request."""
        self.common._perform_request("url", "auth_token", req_type="delete")

        delete.assert_called_with("url", headers=mock.ANY, timeout=mock.ANY)
