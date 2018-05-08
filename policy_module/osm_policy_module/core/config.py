# -*- coding: utf-8 -*-

# Copyright 2018 Whitestack, LLC
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Whitestack, LLC

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
# contact: bdiaz@whitestack.com or glavado@whitestack.com
##"""Global Configuration."""

import logging

from osm_policy_module.core.singleton import Singleton

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

log = logging.getLogger(__name__)


@Singleton
class Config(object):
    """Global configuration."""

    def __init__(self):
        # Default config values
        self.config = {
            'policy_module': {
                'kafka_server_host': '127.0.0.1',
                'kafka_server_port': '9092',
                'log_dir': 'stdout',
                'log_level': 'INFO',
                'enable_logstash_handler': 'false',
                'logstash_host': 'logstash',
                'logstash_port': '5000'
            },
        }

    def load_file(self, config_file_path):
        if config_file_path:
            config_parser = ConfigParser()
            config_parser.read(config_file_path)
            for section in config_parser.sections():
                for key, value in config_parser.items(section):
                    if section not in self.config:
                        self.config[section] = {}
                    self.config[section][key] = value

    def get(self, group, name=None, default=None):
        if group in self.config:
            if name is None:
                return self.config[group]
            return self.config[group].get(name, default)
        return default

    def __str__(self):
        return str(self.config)
