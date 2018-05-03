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
"""Global configuration managed by environment variables."""

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
    """Configuration object."""

    _configuration = [
        CfgParam('BROKER_URI', "localhost:9092", six.text_type),
        CfgParam('DATABASE', "sqlite:///mon_sqlite.db", six.text_type),
        CfgParam('OS_NOTIFIER_URI', "http://localhost:8662", six.text_type),
        CfgParam('OS_DEFAULT_GRANULARITY', "300", six.text_type),
    ]

    _config_dict = {cfg.key: cfg for cfg in _configuration}
    _config_keys = _config_dict.keys()

    def __init__(self):
        """Set the default values."""
        for cfg in self._configuration:
            setattr(self, cfg.key, cfg.default)

    def read_environ(self):
        """Check the appropriate environment variables and update defaults."""
        for key in self._config_keys:
            try:
                val = str(os.environ[key])
                setattr(self, key, val)
            except KeyError as exc:
                log.warning("Environment variable not present: %s", exc)
        return
