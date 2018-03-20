import argparse
import logging
import sys

from osm_policy_module.core.config import Config

from osm_policy_module.core.agent import PolicyModuleAgent


def main():
    cfg = Config.instance()
    parser = argparse.ArgumentParser(prog='pm-scaling-config-agent')
    parser.add_argument('--config-file', nargs='?', help='Policy module agent configuration file')
    args = parser.parse_args()
    if args.config_file:
        cfg.load_file(args.config_file)
    if cfg.get('policy_module', 'log_dir') == 'stdout':
        logging.basicConfig(stream=sys.stdout,
                            format='%(asctime)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p',
                            level=logging._nameToLevel[cfg.get('policy_module', 'log_level')])
    else:
        logging.basicConfig(filename=cfg.get('policy_module', 'log_dir') + 'pm_agent.log',
                            format='%(asctime)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p', filemode='a',
                            level=logging._nameToLevel[cfg.get('policy_module', 'log_level')])
    log = logging.getLogger(__name__)
    log.info("Starting policy module agent...")
    agent = PolicyModuleAgent()
    agent.run()
