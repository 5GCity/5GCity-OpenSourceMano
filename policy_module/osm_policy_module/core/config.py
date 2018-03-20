"""Global Configuration."""

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
                'log_level': 'INFO'
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
