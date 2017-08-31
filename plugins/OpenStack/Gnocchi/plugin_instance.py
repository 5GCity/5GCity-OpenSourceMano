"""Gnocchi plugin for the OSM monitoring module."""

import logging as log

from plugins.OpenStack.Gnocchi.metrics import Metrics
from plugins.OpenStack.settings import Config


def register_plugin():
    """Register the plugin."""
    config = Config.instance()
    instance = Plugin(config=config)
    instance.config()
    instance.metrics()


class Plugin(object):
    """Gnocchi plugin for OSM MON."""

    def __init__(self, config):
        """Plugin instance."""
        log.info("Initialze the plugin instance.")
        self._config = config
        self._metrics = Metrics()

    def config(self):
        """Configure plugin."""
        log.info("Configure the plugin instance.")
        self._config.read_environ("gnocchi")

    def metrics(self):
        """Initialize metric functionality."""
        log.info("Initialize metric functionality.")
        self._metrics.metric_calls()

register_plugin()
