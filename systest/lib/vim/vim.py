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

from osmclient.common.exceptions import ClientException


class Vim():
    def __init__(self,osm,openstack):
        self.vim_name='pytest'
        try:
            osm.get_api().vim.get(self.vim_name)
        except ClientException:
            osm.get_api().vim.create(self.vim_name,openstack.get_access())
