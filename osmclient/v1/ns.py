# Copyright 2017 Sandvine
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
OSM ns API handling
"""

from osmclient.common import utils
from osmclient.common.exceptions import ClientException
from osmclient.common.exceptions import NotFound
import uuid


class Ns(object):

    def __init__(self, http=None, client=None):
        self._http = http
        self._client = client

    def list(self):
        """Returns a list of ns's
        """
        resp = self._http.get_cmd('api/running/ns-instance-config')

        if not resp or 'nsr:ns-instance-config' not in resp:
            return list()

        if 'nsr' not in resp['nsr:ns-instance-config']:
            return list()

        return resp['nsr:ns-instance-config']['nsr']

    def get(self, name):
        """Returns an ns based on name
        """
        for ns in self.list():
            if name == ns['name']:
                return ns
        raise NotFound("ns {} not found".format(name))

    def scale(self, ns_name, ns_scale_group, instance_index):
        postdata = {}
        postdata['instance'] = list()
        instance = {}
        instance['id'] = instance_index
        postdata['instance'].append(instance)

        ns = self.get(ns_name)
        resp = self._http.post_cmd(
            'v1/api/config/ns-instance-config/nsr/{}/scaling-group/{}/instance'
            .format(ns['id'], ns_scale_group), postdata)
        if 'success' not in resp:
            raise ClientException(
                "failed to scale ns: {} result: {}".format(
                    ns_name,
                    resp))

    def create(self, nsd_name, nsr_name, account, vim_network_prefix=None,
               ssh_keys=None, description='default description',
               admin_status='ENABLED'):
        postdata = {}
        postdata['nsr'] = list()
        nsr = {}
        nsr['id'] = str(uuid.uuid1())

        nsd = self._client.nsd.get(nsd_name)

        datacenter = self._client.vim.get_datacenter(account)
        if datacenter is None:
            raise NotFound("cannot find datacenter account {}".format(account))

        nsr['nsd'] = nsd
        nsr['name'] = nsr_name
        nsr['short-name'] = nsr_name
        nsr['description'] = description
        nsr['admin-status'] = admin_status
        nsr['om-datacenter'] = datacenter['uuid']

        if ssh_keys is not None:
            # ssh_keys is comma separate list
            ssh_keys_format = []
            for key in ssh_keys.split(','):
                ssh_keys_format.append({'key-pair-ref': key})

            nsr['ssh-authorized-key'] = ssh_keys_format

        if vim_network_prefix is not None:
            for index, vld in enumerate(nsr['nsd']['vld']):
                network_name = vld['name']
                nsr['nsd']['vld'][index]['vim-network-name'] = '{}-{}'.format(
                    vim_network_prefix, network_name)

        postdata['nsr'].append(nsr)

        resp = self._http.post_cmd(
            'api/config/ns-instance-config/nsr',
            postdata)

        if 'success' not in resp:
            raise ClientException(
                "failed to create ns: {} nsd: {} result: {}".format(
                    nsr_name,
                    nsd_name,
                    resp))

    def get_opdata(self, id):
        return self._http.get_cmd(
              'api/operational/ns-instance-opdata/nsr/{}?deep'.format(id))

    def get_field(self, ns_name, field):
        nsr = self.get(ns_name)
        if nsr is None:
            raise NotFound("failed to retrieve ns {}".format(ns_name))

        if field in nsr:
            return nsr[field]

        nsopdata = self.get_opdata(nsr['id'])

        if field in nsopdata['nsr:nsr']:
            return nsopdata['nsr:nsr'][field]

        raise NotFound("failed to find {} in ns {}".format(field, ns_name))

    def _terminate(self, ns_name):
        ns = self.get(ns_name)
        if ns is None:
            raise NotFound("cannot find ns {}".format(ns_name))

        return self._http.delete_cmd('api/config/ns-instance-config/nsr/' +
                                     ns['id'])

    def delete(self, ns_name, wait=True):
        vnfs = self.get_field(ns_name, 'constituent-vnfr-ref')

        resp = self._terminate(ns_name)
        if 'success' not in resp:
            raise ClientException("failed to delete ns {}".format(ns_name))

        # helper method to check if pkg exists
        def check_not_exists(func):
            try:
                func()
                return False
            except NotFound:
                return True

        for vnf in vnfs:
            if (not utils.wait_for_value(
                lambda:
                check_not_exists(lambda:
                                 self._client.vnf.get(vnf['vnfr-id'])))):
                raise ClientException(
                    "vnf {} failed to delete".format(vnf['vnfr-id']))
        if not utils.wait_for_value(lambda:
                                    check_not_exists(lambda:
                                                     self.get(ns_name))):
            raise ClientException("ns {} failed to delete".format(ns_name))

    def get_monitoring(self, ns_name):
        ns = self.get(ns_name)
        mon_list = {}
        if ns is None:
            return mon_list

        vnfs = self._client.vnf.list()
        for vnf in vnfs:
            if ns['id'] == vnf['nsr-id-ref']:
                if 'monitoring-param' in vnf:
                    mon_list[vnf['name']] = vnf['monitoring-param']

        return mon_list
