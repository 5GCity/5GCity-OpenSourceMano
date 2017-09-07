"""Aodh plugin for the OSM monitoring module."""

import logging as log
#import sys

#path = "/home/stack/MON"
#if path not in sys.path:
#    sys.path.append(path)

from plugins.OpenStack.Aodh.alarming import Alarming
from plugins.OpenStack.settings import Config


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
        log.info("Initialze the plugin instance.")
        self._config = config
        self._alarm = Alarming()

    def config(self):
        """Configure plugin."""
        log.info("Configure the plugin instance.")
        self._config.read_environ("aodh")

    def alarm(self):
        """Allow alarm info to be received from Aodh."""
        log.info("Begin alarm functionality.")
        self._alarm.alarming()

register_plugin()
