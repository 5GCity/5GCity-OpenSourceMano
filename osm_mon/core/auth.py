# -*- coding: utf-8 -*-

# Copyright 2018 Whitestack, LLC
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Whitestack, LLC

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at

#         http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# For those usages not covered by the Apache License, Version 2.0 please
# contact: bdiaz@whitestack.com or glavado@whitestack.com
##

import json

from osm_mon.core.database import VimCredentials, DatabaseManager


class AuthManager:

    def __init__(self):
        self.database_manager = DatabaseManager()

    def store_auth_credentials(self, message):
        values = json.loads(message.value)
        credentials = VimCredentials()
        credentials.uuid = values['_id']
        credentials.name = values['name']
        credentials.type = values['vim_type']
        credentials.url = values['vim_url']
        credentials.user = values['vim_user']
        credentials.password = values['vim_password']
        credentials.tenant_name = values['vim_tenant_name']
        credentials.config = json.dumps(values['config'])
        self.database_manager.save_credentials(credentials)

    def get_credentials(self, vim_uuid):
        return self.database_manager.get_credentials(vim_uuid)

    def delete_auth_credentials(self, message):
        # TODO
        pass

