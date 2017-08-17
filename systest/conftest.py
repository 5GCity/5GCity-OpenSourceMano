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

from lib.osm.fixtures import osm_add_options
from lib.openstack.fixtures import openstack_add_options
from lib.vim.fixtures import vim_add_options
from lib.vmware.fixtures import vmware_add_options

def pytest_addoption(parser):
    osm_add_options(parser)
    openstack_add_options(parser)
    vmware_add_options(parser)
    vim_add_options(parser)
