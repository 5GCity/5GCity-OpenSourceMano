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

import pytest
import time


@pytest.mark.vim
@pytest.mark.openstack
@pytest.mark.vmware
class TestClass(object):

    def test_empty_vim(self,osm):
        assert not osm.get_api().vim.list()

    @pytest.fixture(scope='function')
    def cleanup_test_add_vim_account(self,osm,request):
        def teardown():
            try:
                for vim in osm.get_api().vim.list(False):
                    osm.get_api().vim.delete(vim['name'])
            except:
                pass
        request.addfinalizer(teardown)
 
    @pytest.mark.openstack
    @pytest.mark.smoke
    def test_add_vim_account(self,osm,openstack,cleanup_test_add_vim_account):
        os_access = {}
        vim_name = 'helloworld-os'
        os_access['vim-url'] = 'https://169.254.169.245/'
        os_access['vim-username'] = 'pytest2'
        os_access['vim-password'] = 'fred'
        os_access['vim-tenant-name'] = 'pytest3'
        os_access['vim-type'] = 'openstack'
        os_access['description'] = 'a test vim'
        assert not osm.get_api().vim.create(vim_name,os_access)

        resp=osm.get_api().vim.get(vim_name)
        assert resp['name'] == vim_name
        assert resp['type'] == 'openstack'
        assert resp['vim_url'] == os_access['vim-url']
        assert resp['vim_url_admin'] == os_access['vim-url']
        assert resp['vim_tenants'][0]['user'] == os_access['vim-username']
        assert resp['vim_tenants'][0]['vim_tenant_name'] == os_access['vim-tenant-name']
        assert not osm.get_api().vim.delete(vim_name)

    @pytest.mark.vmware
    #@pytest.mark.smoke
    def test_add_vim_account_vmware(self,osm,vmware,cleanup_test_add_vim_account):
        os_access = {}
        vim_name = 'helloworld-vmware'
        os_access['vim-url'] = 'https://169.254.169.245/'
        os_access['vim-username'] = 'pytest2'
        os_access['vim-password'] = 'fred'
        os_access['vim-tenant-name'] = 'pytest3'
        os_access['vim-type'] = 'vmware'
        os_access['description'] = 'a test vim'
        assert not osm.get_api().vim.create(vim_name,os_access)

        resp=osm.get_api().vim.get(vim_name)
        assert resp['name'] == vim_name
        assert resp['type'] == 'vmware'
        assert resp['vim_url'] == os_access['vim-url']
        assert resp['vim_url_admin'] == os_access['vim-url']
        assert resp['vim_tenants'][0]['user'] == os_access['vim-username']
        assert resp['vim_tenants'][0]['vim_tenant_name'] == os_access['vim-tenant-name']

        assert not osm.get_api().vim.delete(vim_name)

    #@pytest.mark.smoke
    def test_add_multiple_accounts(self,osm,cleanup_test_add_vim_account):
        os_access = {}
        vims = [ {'name': 'testvim1', 'vim-type': 'openstack'}, {'name': 'testvim2','vim-type': 'vmware'} ]
        os_access['vim-url'] = 'https://169.254.169.245/'
        os_access['vim-username'] = 'pytest2'
        os_access['vim-password'] = 'fred'
        os_access['vim-tenant-name'] = 'pytest3'
        os_access['description'] = 'a test vim'

        for vim in vims:
            os_access['vim-type'] = vim['vim-type']
            assert not osm.get_api().vim.create(vim['name'],os_access)
            resp=osm.get_api().vim.get(vim['name'])
            assert resp['name'] == vim['name'] 
            assert resp['type'] == vim['vim-type']
            assert resp['vim_url'] == os_access['vim-url']
            assert resp['vim_url_admin'] == os_access['vim-url']
            assert resp['vim_tenants'][0]['user'] == os_access['vim-username']
            assert resp['vim_tenants'][0]['vim_tenant_name'] == os_access['vim-tenant-name']

        for vim in osm.get_api().vim.list(False):
            osm.get_api().vim.delete(vim['name'])
