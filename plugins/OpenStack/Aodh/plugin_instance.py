"""Aodh plugin for the OSM monitoring module."""

import sys
import logging

path = "/home/stack/MON"
if path not in sys.path:
    sys.path.append(path)

from plugins.Openstack.Aodh.alarming import Alarming
from plugins.Openstack.settings import Config


def register_plugin():
    """Register the plugin."""
    config = Config.instance()
    instance = Plugin(config=config)
    instance.config()
    instance.alarm()


class Plugin(object):
    """Aodh plugin for OSM MON."""

    def __init__(self, config):
        """Plugin instance."""
        self._config = config
        self._alarm = Alarming()

    def config(self):
        """Configure plugin."""
        self._config.read_environ()

    def alarm(self):
        """Allow alarm info to be received from Aodh."""
        self._alarm.alarming()

register_plugin()
