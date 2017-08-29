"""Configurations for the Aodh plugin."""

from __future__ import unicode_literals

import logging as log
import os

from collections import namedtuple

from plugins.Openstack.singleton import Singleton

import six


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
        CfgParam('OS_USERNAME', "aodh", six.text_type),
        CfgParam('OS_PASSWORD', "password", six.text_type),
        CfgParam('OS_TENANT_NAME', "service", six.text_type),
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
            if (key == "OS_IDENTITY_API_VERSION" or key == "OS_PASSWORD"):
                val = str(os.environ[key])
                setattr(self, key, val)
            elif (key == "OS_AUTH_URL"):
                val = str(os.environ[key]) + "/v3"
                setattr(self, key, val)
            else:
                # TODO(mcgoughh): Log errors and no config updates required
                log.warn("Configuration doesn't require updating")
                return
