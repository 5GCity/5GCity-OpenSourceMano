#!/usr/bin/env python3

############################################################################
# Copyright 2016 RIFT.IO Inc                                               #
#                                                                          #
# Licensed under the Apache License, Version 2.0 (the "License");          #
# you may not use this file except in compliance with the License.         #
# You may obtain a copy of the License at                                  #
#                                                                          #
#     http://www.apache.org/licenses/LICENSE-2.0                           #
#                                                                          #
# Unless required by applicable law or agreed to in writing, software      #
# distributed under the License is distributed on an "AS IS" BASIS,        #
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. #
# See the License for the specific language governing permissions and      #
# limitations under the License.                                           #
############################################################################


import argparse
import logging
import os
import subprocess
import sys
import time

import yaml


def start_traffic(yaml_cfg, logger):
    '''Use curl and set admin status to enable on pong and ping vnfs'''

    curl_fmt = 'curl -D /dev/stdout -H "Accept: application/vnd.yang.data' \
                   '+xml" -H "Content-Type: application/vnd.yang.data+json" ' \
                   '-X POST -d "{{ {data} }}" http://{mgmt_ip}:' \
                   '{mgmt_port}/api/v1/{vnf_type}/{url}'

    def setup_service(mgmt_ip, port, vnf_type, service_ip, service_port):
        data = '\\"ip\\":\\"{}\\", \\"port\\":5555'.format(service_ip)
        curl_cmd = curl_fmt.format(
            mgmt_ip=mgmt_ip,
            mgmt_port=port,
            vnf_type=vnf_type,
            data=data,
            url='server'
        )

        logger.debug("Executing cmd: %s", curl_cmd)
        proc = subprocess.run(curl_cmd, shell=True,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)

        logger.debug("Process: {}".format(proc))

        return proc.returncode

    def enable_service(mgmt_ip, port, vnf_type):
        curl_cmd = curl_fmt.format(
            mgmt_ip=mgmt_ip,
            mgmt_port=port,
            vnf_type=vnf_type,
            data='\\"enable\\":true',
            url='adminstatus/state'
        )

        logger.debug("Executing cmd: %s", curl_cmd)
        proc = subprocess.run(curl_cmd, shell=True,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)

        logger.debug("Process: {}".format(proc))

        return proc.returncode

    # Get port from user parameter
    service_port = yaml_cfg['parameter']['port']

    service_ip = None
    # Enable pong service first
    for index, vnfr in yaml_cfg['vnfr'].items():
        logger.debug("VNFR {}: {}".format(index, vnfr))

        def get_cp_ip(cp_name):
            for cp in vnfr['connection_point']:
                if cp['name'].endswith(cp_name):
                    return cp['ip_address']

        # Check if it is pong vnf
        if 'pong_vnf' in vnfr['name']:
            vnf_type = 'pong'
            mgmt_ip = vnfr['mgmt_ip_address']
            port = vnfr['mgmt_port']
            service_ip = get_cp_ip('cp1')

            max_tries = 60
            tries = 0
            while tries < max_tries:
                rc = setup_service(mgmt_ip, port, vnf_type, service_ip, service_port)
                tries += 1
                if rc != 0:
                    logger.error("Setup service for pong failed ({}): {}".
                                 format(tries, rc))
                    if rc != 7:
                        return rc
                    else:
                        time.sleep(1) # Sleep for 1 seconds

            rc = enable_service(mgmt_ip, port, vnf_type)
            if rc != 0:
                logger.error("Enable service for pong failed: {}".
                             format(rc))
                return rc
            break

    # Add a delay to provide pong port to come up
    time.sleep(1)

    # Enable ping service next
    for index, vnfr in yaml_cfg['vnfr'].items():
        logger.debug("VNFR {}: {}".format(index, vnfr))

        # Check if it is pong vnf
        if 'ping_vnf' in vnfr['name']:
            vnf_type = 'ping'
            mgmt_ip = vnfr['mgmt_ip_address']
            port = vnfr['mgmt_port']
            if service_ip is None:
                logger.error("Did not find pong ip!!")
                return 1

            max_tries = 30
            tries = 0
            while tries < max_tries:
                rc = setup_service(mgmt_ip, port, vnf_type, service_ip, service_port)
                tries += 1
                if rc != 0:
                    logger.error("Setup service for ping failed ({}): {}".
                                 format(tries, rc))
                    if rc != 7:
                        return rc
                    else:
                        time.sleep(1) # Sleep for 1 seconds

            rc = enable_service(mgmt_ip, port, vnf_type)
            if rc != 0:
                logger.error("Enable service for ping failed: {}".
                             format(rc))
            break

    return rc


def main(argv=sys.argv[1:]):
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("yaml_cfg_file", type=argparse.FileType('r'))
        parser.add_argument("-q", "--quiet", dest="verbose", action="store_false")
        args = parser.parse_args()

        run_dir = os.path.join(os.environ['RIFT_INSTALL'], "var/run/rift")
        if not os.path.exists(run_dir):
            os.makedirs(run_dir)
        log_file = "{}/ping_pong_start_traffic-{}.log".format(run_dir, time.strftime("%Y%m%d%H%M%S"))

        # logging.basicConfig(filename=log_file, level=logging.DEBUG)
        logger = logging.getLogger('ping-pong-start-traffic')
        logger.setLevel(logging.DEBUG)

        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)

        ch = logging.StreamHandler()
        if args.verbose:
            ch.setLevel(logging.DEBUG)
        else:
            ch.setLevel(logging.INFO)

        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        logger.addHandler(fh)
        logger.addHandler(ch)

    except Exception as e:
        logger.exception("Exception in {}: {}".format(__file__, e))
        sys.exit(1)

    try:
        logger.debug("Input file: {}".format(args.yaml_cfg_file.name))
        yaml_str = args.yaml_cfg_file.read()
        yaml_cfg = yaml.load(yaml_str)
        logger.debug("Input YAML: {}".format(yaml_cfg))

        rc = start_traffic(yaml_cfg, logger)
        logger.info("Return code: {}".format(rc))
        sys.exit(rc)

    except Exception as e:
        logger.exception("Exception in {}: {}".format(__file__, e))
        sys.exit(1)

if __name__ == "__main__":
    main()
