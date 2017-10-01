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

import unittest

import mock

from plugins.OpenStack.common import Common

import requests


class TestCommon(unittest.TestCase):
    """Test the common class for OpenStack plugins."""

    def setUp(self):
        """Test Setup."""
        super(TestCommon, self).setUp()
        self.common = Common()

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
