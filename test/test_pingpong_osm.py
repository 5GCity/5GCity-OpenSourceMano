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

#!/usr/bin/env python3

import json
import logging
import os
import pytest
import requests
import requests_toolbelt
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
        "Accept" : "application/vnd.yang.data+json",
        "Content-Type" : "application/vnd.yang.data+json",
    }
    client_session.verify = False
    _, cert, key = certs.get_bootstrap_cert_and_key()
    client_session.cert = (cert, key)
    return client_session

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

def test_configure_vim_account(session, rest_endpoint, vim_type, vim_host, vim_user, vim_tenant, vim_pass):
    ''' Configure an openstack vim account
    '''
    uri = "{endpoint}/api/config/cloud/account".format(
        endpoint=rest_endpoint,
    )
    account = '''
    {
        "account":{
            "name":"vim-0",
            "account-type":"openstack",
            "openstack":{
                "admin":"True",
                "key": "%s",
                "secret": "%s",
                "auth_url": "http://%s:5000/v3/",
                "tenant": "%s",
                "mgmt-network": "private"
            }
        }
    }
    ''' % (vim_user, vim_pass, vim_host, vim_tenant)
    response = session.request("POST", uri, data=chomp_json(account))

    uri = "{endpoint}/api/operational/cloud/account".format(endpoint=rest_endpoint)
    response = session.request("GET", uri)
    assert 'error' not in response.text
    vim_accounts = json.loads(response.text)
    assert vim_accounts

    found_account = False
    for account in vim_accounts['rw-cloud:account']:
        if account['name'] == 'vim-0':
            found_account = True
            break
    assert found_account == True


@pytest.fixture(scope='session')
def ping_pkg(package_location):
    '''ping vnfd package location'''
    return "%s/ping_vnfd.tar.gz" % (package_location)


@pytest.fixture(scope='session')
def pong_pkg(package_location):
    '''pong vnfd package location'''
    return "%s/pong_vnfd.tar.gz" % (package_location)


@pytest.fixture(scope='session')
def ping_pong_pkg(package_location):
    '''ping pong nsd package location'''
    return "%s/ping_pong_nsd.tar.gz" % (package_location)


def test_onboard_pingpong_descriptors(session, so_host, ping_pkg, pong_pkg, ping_pong_pkg, rest_endpoint):
    ''' Onboard ping_pong descriptors
    '''
    onboard_command = 'onboard_pkg -s {host} -u {ping_pkg}'.format(
        host=so_host,
        ping_pkg=ping_pkg,
    )
    subprocess.check_call(onboard_command, shell=True)

    onboard_command = 'onboard_pkg -s {host} -u {pong_pkg}'.format(
        host=so_host,
        pong_pkg=pong_pkg,
    )
    subprocess.check_call(onboard_command, shell=True)

    onboard_command = 'onboard_pkg -s {host} -u {ping_pong_pkg}'.format(
        host=so_host,
        ping_pong_pkg=ping_pong_pkg,
    )
    subprocess.check_call(onboard_command, shell=True)


def test_instantiate_ping_pong(session, so_host, rest_endpoint):
    ''' Instantiate an instance of ping pong from descriptors
    '''
    uri = "{endpoint}/api/operational/nsd-catalog".format(endpoint=rest_endpoint)
    response = session.request("GET", uri)
    catalog = json.loads(response.text)
    ping_pong_nsd = None
    for nsd in catalog['nsd:nsd-catalog']['nsd']:
        if nsd['name'] == 'ping_pong_nsd':
            ping_pong_nsd = nsd
            break
    assert ping_pong_nsd is not None

    instantiate_command = 'onboard_pkg -s {host} -i instance-0 -d {nsd_id} -c vim-0'.format(
        host=so_host,
        nsd_id=ping_pong_nsd['id']
    )
    subprocess.check_call(instantiate_command, shell=True)

    def wait_for_ping_pong(instance_name, timeout=600, retry_interval=5):
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

    wait_for_ping_pong('instance-0')
