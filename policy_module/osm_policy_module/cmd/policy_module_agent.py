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
##
import argparse
import logging
import sys
import logstash

from osm_policy_module.core.agent import PolicyModuleAgent
from osm_policy_module.core.config import Config
from osm_policy_module.core.database import DatabaseManager


def main():
    cfg = Config.instance()
    parser = argparse.ArgumentParser(prog='pm-scaling-config-agent')
    parser.add_argument('--config-file', nargs='?', help='Policy module agent configuration file')
    args = parser.parse_args()
    if args.config_file:
        cfg.load_file(args.config_file)
    # TODO: Handle different log levels in config
    if cfg.get('policy_module', 'log_dir') == 'stdout':
        logging.basicConfig(stream=sys.stdout,
                            format='%(asctime)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p',
                            level=logging.INFO)
    else:
        logging.basicConfig(filename=cfg.get('policy_module', 'log_dir') + 'pm_agent.log',
                            format='%(asctime)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p', filemode='a',
                            level=logging.INFO)
    if cfg.get('policy_module', 'enable_logstash_handler') == 'true':
        logstash_host = cfg.get('policy_module', 'logstash_host')
        logstash_port = int(cfg.get('policy_module', 'logstash_port'))
        root_logger = logging.getLogger()
        root_logger.addHandler(logstash.TCPLogstashHandler(logstash_host, logstash_port, version=1))
        root_logger.info("Logstash handler configured.")
    log = logging.getLogger(__name__)
    log.info("Config: %s", cfg)
    log.info("Syncing database...")
    db_manager = DatabaseManager()
    db_manager.create_tables()
    log.info("Database synced correctly.")
    log.info("Starting policy module agent...")
    agent = PolicyModuleAgent()
    agent.run()


if __name__ == '__main__':
    main()
