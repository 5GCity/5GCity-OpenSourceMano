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
"""Tests for settings for OpenStack plugins configurations."""

import logging

import os

import unittest

import mock

from osm_mon.plugins.OpenStack.settings import Config

log = logging.getLogger(__name__)


class TestSettings(unittest.TestCase):
    """Test the settings class for OpenStack plugin configuration."""

    def setUp(self):
        """Test Setup."""
        super(TestSettings, self).setUp()
        self.cfg = Config.instance()

    def test_set_os_username(self):
        """Test reading the environment for OpenStack plugin configuration."""
        os.environ["OS_USERNAME"] = "test"
        self.cfg.read_environ("my_service")

        self.assertEqual(self.cfg.OS_USERNAME, "test")

    @mock.patch.object(os, "environ")
    def test_read_environ(self, environ):
        """Test reading environment variables for configuration."""
        self.cfg.read_environ("my_service")

        # Called for each key in the configuration dictionary
        environ.assert_called_once
