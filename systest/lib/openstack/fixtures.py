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
import json


def openstack_add_options(parser):
    parser.addoption("--os-url", default="", help="openstack identity url")
    parser.addoption("--os-username", default="", help="openstack username")
    parser.addoption("--os-password", default="", help="openstack password")
    parser.addoption("--os-project-name", default="", help="openstack project name")

@pytest.fixture
def openstack(request):
    from lib.openstack import openstack
    access = {}
    access['vim-url'] = request.config.getoption("--os-url")
    access['vim-username'] = request.config.getoption("--os-username")
    access['vim-password'] = request.config.getoption("--os-password")
    access['vim-tenant-name'] = request.config.getoption("--os-project-name")
    access['vim-type'] = 'openstack'
    access['description'] = 'pytest system test'

    return openstack.Openstack(access)
