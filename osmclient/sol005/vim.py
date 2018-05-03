# Copyright 2018 Telefonica
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
OSM vim API handling
"""

from osmclient.common import utils
from osmclient.common.exceptions import ClientException
from osmclient.common.exceptions import NotFound
import yaml


class Vim(object):
    def __init__(self, http=None, client=None):
        self._http = http
        self._client = client
        self._apiName = '/admin'
        self._apiVersion = '/v1'
        self._apiResource = '/vims'
        self._apiBase = '{}{}{}'.format(self._apiName,
                                        self._apiVersion, self._apiResource)
    def create(self, name, vim_access):
        if 'vim-type' not in vim_access:
            #'openstack' not in vim_access['vim-type']):
            raise Exception("vim type not provided")

        vim_account = {}
        vim_config = {'hello': 'hello'}
        vim_account['name'] = name
        vim_account = self.update_vim_account_dict(vim_account, vim_access)

        vim_config = {}
        if 'config' in vim_access and vim_access['config'] is not None:
           vim_config = yaml.load(vim_access['config'])

        vim_account['config'] = vim_config

        resp = self._http.post_cmd(endpoint=self._apiBase,
                                       postfields_dict=vim_account)
        if not resp or 'id' not in resp:
            raise ClientException('failed to create vim {}: {}'.format(
                                  name, resp))
        else:
            print resp['id']

    def update(self, vim_name, vim_account):
        vim = self.get(vim_name)
        resp = self._http.put_cmd(endpoint='{}/{}'.format(self._apiBase,vim['_id']),
                                       postfields_dict=vim_account)
        if not resp or '_id' not in resp:
            raise ClientException('failed to update vim: '.format(
                                  resp))
        else:
            print resp['_id']

    def update_vim_account_dict(self, vim_account, vim_access):
        vim_account['vim_type'] = vim_access['vim-type']
        vim_account['description'] = vim_access['description']
        vim_account['vim_url'] = vim_access['vim-url']
        vim_account['vim_user'] = vim_access['vim-username']
        vim_account['vim_password'] = vim_access['vim-password']
        vim_account['vim_tenant_name'] = vim_access['vim-tenant-name']
        return vim_account

    def get_id(self, name):
        """Returns a VIM id from a VIM name
        """
        for vim in self.list():
            if name == vim['name']:
                return vim['uuid']
        raise NotFound("vim {} not found".format(name))

    def delete(self, vim_name):
        vim_id = vim_name
        if not utils.validate_uuid4(vim_name):
            vim_id = self.get_id(vim_name)
        http_code, resp = self._http.delete_cmd('{}/{}'.format(self._apiBase,vim_id))
        #print 'RESP: {}'.format(resp)
        if http_code == 202:
            print 'Deletion in progress'
        elif http_code == 204:
            print 'Deleted'
        else:
            raise ClientException("failed to delete vim {} - {}".format(vim_name, resp))

    def list(self, filter=None):
        """Returns a list of VIM accounts
        """
        filter_string = ''
        if filter:
            filter_string = '?{}'.format(filter)
        resp = self._http.get_cmd('{}{}'.format(self._apiBase,filter_string))
        if not resp:
            return list()
        vim_accounts = []
        for datacenter in resp:
            vim_accounts.append({"name": datacenter['name'], "uuid": datacenter['_id']
                        if '_id' in datacenter else None})
        return vim_accounts

    def get(self, name):
        """Returns a VIM account based on name or id
        """
        vim_id = name
        if not utils.validate_uuid4(name):
            vim_id = self.get_id(name)
        resp = self._http.get_cmd('{}/{}'.format(self._apiBase,vim_id))
        if not resp or '_id' not in resp:
            raise ClientException('failed to get vim info: '.format(
                                  resp))
        else:
            return resp
        raise NotFound("vim {} not found".format(name))

