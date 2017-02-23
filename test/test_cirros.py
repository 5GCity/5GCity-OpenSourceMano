#!/usr/bin/env python3
#   Copyright 2016 RIFT.IO Inc
#   Copyright 2016 Telefónica Investigación y Desarrollo S.A.U.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import json
import logging
import pytest
import requests
import subprocess
import time

import certs

logger = logging.getLogger(__name__)


def chomp_json(string):
    return ''.join([line.strip() for line in string.splitlines()])


@pytest.fixture(scope='session')
def session(request, so_user, so_pass):
    client_session = requests.session()
    client_session.auth = (so_user, so_pass)
    client_session.headers = {
        "Accept": "application/vnd.yang.data+json",
        "Content-Type": "application/vnd.yang.data+json",
    }
    client_session.verify = False
    _, cert, key = certs.get_bootstrap_cert_and_key()
    client_session.cert = (cert, key)
    return client_session


@pytest.fixture(scope='session')
def fetch_packages():
    """ Fetch NSD/VNFD packages"""
    wget_command = 'wget --no-parent -r https://osm-download.etsi.org/ftp/osm-1.0-one/vnf-packages'
    subprocess.check_call(wget_command, shell=True)


@pytest.fixture(scope='session')
def rest_endpoint(so_host, so_port):
    return 'https://{host}:{port}'.format(host=so_host, port=so_port)


def test_so_started(session, rest_endpoint):
    ''' Get contents of /vcs/info/components and verify all components have started successfully
    '''
    uri = "{endpoint}/api/operational/vcs/info/components".format(endpoint=rest_endpoint)
    response = session.request("GET", uri)
    vcs_info = json.loads(response.text)
    for component in vcs_info['rw-base:components']['component_info']:
        assert component['state'] == 'RUNNING'


@pytest.fixture(scope='session')
def cirros_vnfd_pkg(package_location):
    '''cirros vnfd package location'''
    return "%s/cirros_vnf.tar.gz" % (package_location)


@pytest.fixture(scope='session')
def cirros_nsd_pkg(package_location):
    '''cirros  nsd package location'''
    return "%s/cirros_2vnf_ns.tar.gz" % (package_location)


def test_onboard_cirros_descriptors(session, so_host, cirros_vnfd_pkg,
                                    cirros_nsd_pkg, rest_endpoint):
    ''' Onboard Cirros NSD/VNFD descriptors
    '''
    onboard_command = 'onboard_pkg -s {host} -u {cirros_vnfd_pkg}'.format(
        host=so_host,
        cirros_vnfd_pkg=cirros_vnfd_pkg,
    )
    subprocess.check_call(onboard_command, shell=True)

    onboard_command = 'onboard_pkg -s {host} -u {cirros_nsd_pkg}'.format(
        host=so_host,
        cirros_nsd_pkg=cirros_nsd_pkg,
    )
    subprocess.check_call(onboard_command, shell=True)


def test_instantiate_cirros(session, so_host, data_center_id, rest_endpoint):
    ''' Instantiate an instance of cirros from descriptors
    '''
    uri = "{endpoint}/api/operational/nsd-catalog".format(endpoint=rest_endpoint)
    response = session.request("GET", uri)
    catalog = json.loads(response.text)
    cirros_nsd = None
    for nsd in catalog['nsd:nsd-catalog']['nsd']:
        if nsd['name'] == 'cirros_2vnf_nsd':
            cirros_nsd = nsd
            break
    assert cirros_nsd is not None

    instantiate_command = 'onboard_pkg -s {host} -i instance-0 -d {nsd_id} -D {data_center_id}'.format(
        host=so_host,
        nsd_id=cirros_nsd['id'],
        data_center_id=data_center_id
    )
    subprocess.check_call(instantiate_command, shell=True)

    def wait_for_cirros_ns(instance_name, timeout=600, retry_interval=5):
        start_time = time.time()
        while True:
            uri = "{endpoint}/api/operational/ns-instance-opdata".format(endpoint=rest_endpoint)
            response = session.request("GET", uri)
            print(response, response.text)
            opdata = json.loads(response.text)

            nsr = None
            for instance in opdata['nsr:ns-instance-opdata']['nsr']:
                if instance['name-ref'] == instance_name:
                    nsr = instance

            assert nsr is not None, response.text
            assert nsr['operational-status'] not in ['failed']
            assert nsr['config-status'] not in ['failed']

            if nsr['operational-status'] in ['running'] and nsr['config-status'] in ['configured']:
                break

            time_elapsed = time.time() - start_time
            time_remaining = timeout - time_elapsed
            assert time_remaining > 0
            time.sleep(min(time_remaining, retry_interval))

    wait_for_cirros_ns('instance-0')
