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
"""Configurations for the OpenStack plugins."""

import logging
import os

from collections import namedtuple

from osm_mon.plugins.OpenStack.singleton import Singleton

import six

__author__ = "Helena McGough"

log = logging.getLogger(__name__)


class BadConfigError(Exception):
    """Configuration exception."""

    pass


class CfgParam(namedtuple('CfgParam', ['key', 'default', 'data_type'])):
    """Configuration parameter definition."""

    def value(self, data):
        """Convert a string to the parameter type."""
        try:
            return self.data_type(data)
        except (ValueError, TypeError):
            raise BadConfigError(
                'Invalid value "%s" for configuration parameter "%s"' % (
                    data, self.key))


@Singleton
class Config(object):
    """Plugin confguration."""

    _configuration = [
        CfgParam('OS_AUTH_URL', None, six.text_type),
        CfgParam('OS_IDENTITY_API_VERSION', "3", six.text_type),
        CfgParam('OS_USERNAME', None, six.text_type),
        CfgParam('OS_PASSWORD', "password", six.text_type),
        CfgParam('OS_TENANT_NAME', "service", six.text_type),
    ]

    _config_dict = {cfg.key: cfg for cfg in _configuration}
    _config_keys = _config_dict.keys()

    def __init__(self):
        """Set the default values."""
        for cfg in self._configuration:
            setattr(self, cfg.key, cfg.default)

    def read_environ(self, service):
        """Check the appropriate environment variables and update defaults."""
        for key in self._config_keys:
            try:
                if (key == "OS_IDENTITY_API_VERSION" or key == "OS_PASSWORD"):
                    val = str(os.environ[key])
                    setattr(self, key, val)
                elif (key == "OS_AUTH_URL"):
                    val = str(os.environ[key]) + "/v3"
                    setattr(self, key, val)
                else:
                    # Default username for a service is it's name
                    setattr(self, 'OS_USERNAME', service)
                    log.info("Configuration complete!")
                    return
            except KeyError as exc:
                log.warn("Falied to configure plugin: %s", exc)
                log.warn("Try re-authenticating your OpenStack deployment.")
        return
