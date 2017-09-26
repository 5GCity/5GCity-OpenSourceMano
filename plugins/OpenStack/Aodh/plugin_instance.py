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
"""Aodh plugin for the OSM monitoring module."""

import logging

logging.basicConfig(filename='aodh_MON.log', format='%(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p', filemode='a',
                    level=logging.INFO)
log = logging.getLogger(__name__)


try:
    import aodhclient
except ImportError:
    log.warn("Failed to import the aodhclient")

from plugins.OpenStack.Aodh.alarming import Alarming
from plugins.OpenStack.settings import Config

__author__ = "Helena McGough"


def register_plugin():
    """Register the plugin."""
    # Initialize configuration and notifications
    config = Config.instance()

    # Intialize plugin
    instance = Plugin(config=config)
    instance.config()
    instance.alarm()


class Plugin(object):
    """Aodh plugin for OSM MON."""

    def __init__(self, config):
        """Plugin instance."""
        log.info("Initialze the plugin instance.")
        self._config = config
        self._alarming = Alarming()

    def config(self):
        """Configure plugin."""
        log.info("Configure the plugin instance.")
        self._config.read_environ("aodh")

    def alarm(self):
        """Allow alarm info to be received from Aodh."""
        log.info("Begin alarm functionality.")
        self._alarming.alarming()

if aodhclient:
    register_plugin()
