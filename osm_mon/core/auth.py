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

    def store_auth_credentials(self, creds_dict):
        credentials = VimCredentials()
        credentials.uuid = creds_dict['_id']
        credentials.name = creds_dict['name']
        credentials.type = creds_dict['vim_type']
        credentials.url = creds_dict['vim_url']
        credentials.user = creds_dict['vim_user']
        credentials.password = creds_dict['vim_password']
        credentials.tenant_name = creds_dict['vim_tenant_name']
        credentials.config = json.dumps(creds_dict['config'])
        if creds_dict.get('OS_REGION_NAME'):
            credentials.region_name = creds_dict['OS_REGION_NAME']
        else:
            credentials.region_name = "RegionOne"
        if creds_dict.get('OS_ENDPOINT_TYPE'):
            credentials.endpoint_type = creds_dict['OS_ENDPOINT_TYPE']
        else:
            credentials.endpoint_type = "publicURL"
        self.database_manager.save_credentials(credentials)

    def get_credentials(self, vim_uuid):
        return self.database_manager.get_credentials(vim_uuid)

    def delete_auth_credentials(self, creds_dict):
        credentials = self.get_credentials(creds_dict['_id'])
        if credentials:
            credentials.delete_instance()

