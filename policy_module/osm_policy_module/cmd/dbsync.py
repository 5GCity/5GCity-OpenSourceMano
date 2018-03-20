import argparse
import logging
import sys

from osm_policy_module.core.config import Config

from osm_policy_module.core.database import DatabaseManager


def main():
    cfg = Config.instance()
    parser = argparse.ArgumentParser(prog='pm-dbsync')
    parser.add_argument('--config-file', nargs='?', help='Policy module database sync configuration file')
    args = parser.parse_args()
    if args.config_file:
        cfg.load_file(args.config_file)
    if cfg.get('policy_module', 'log_dir') == 'stdout':
        logging.basicConfig(stream=sys.stdout,
                            format='%(asctime)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p', filemode='a',
                            level=logging.INFO)
    else:
        logging.basicConfig(filename=cfg.get('policy_module', 'log_dir') + 'pm_dbsync.log',
                            format='%(asctime)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p', filemode='a',
                            level=logging.INFO)
    log = logging.getLogger(__name__)
    log.info("Starting database sync...")
    db_manager = DatabaseManager()
    db_manager.create_tables()
