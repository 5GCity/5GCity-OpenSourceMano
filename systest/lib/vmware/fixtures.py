# -*- coding: utf-8 -*-

##
# Copyright 2016-2017 VMware Inc.
# This file is part of ETSI OSM
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact:  osslegalrouting@vmware.com
##

import pytest
import json


def vmware_add_options(parser):
    parser.addoption("--vcd-url", default="", help="VMware vCloud identity url")
    parser.addoption("--vcd-username", default="", help="VMware vCloud username")
    parser.addoption("--vcd-password", default="", help="VMware vCloud password")
    parser.addoption("--vcd-tenant-name", default="", help="VMware vCloud tenant name")
    parser.addoption("--vcd-org", default="", help="VMware vCloud Organization name")

@pytest.fixture
def vmware(request):
    from lib.vmware import vmware
    access = {}
    access['vim-url'] = request.config.getoption("--vcd-url")
    access['vim-username'] = request.config.getoption("--vcd-username")
    access['vim-password'] = request.config.getoption("--vcd-password")
    access['vim-tenant-name'] = request.config.getoption("--vcd-tenant-name")
    access['vcd-org'] = request.config.getoption("--vcd-org")
    access['config'] = request.config.getoption("--vim-config")
    access['vim-type'] = 'vmware'
    access['description'] = 'pytest system test'

    return vmware.Vmware(access)
