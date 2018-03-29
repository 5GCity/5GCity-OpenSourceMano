# Copyright 2017 Intel Research and Development Ireland Limited
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Intel Corporation

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
# contact: helena.mcgough@intel.com or adrian.hoban@intel.com
##
"""Common methods for the OpenStack plugins."""

import logging

import requests
from keystoneclient.v3 import client

from osm_mon.core.auth import AuthManager

__author__ = "Helena McGough"

log = logging.getLogger(__name__)


class Common(object):
    """Common calls for Gnocchi/Aodh plugins."""

    def __init__(self):
        """Create the common instance."""
        self.auth_manager = AuthManager()

    @staticmethod
    def get_auth_token(vim_uuid):
        """Authenticate and/or renew the authentication token."""
        auth_manager = AuthManager()
        creds = auth_manager.get_credentials(vim_uuid)
        ks = client.Client(auth_url=creds.url,
                           username=creds.user,
                           password=creds.password,
                           tenant_name=creds.tenant_name)
        return ks.auth_token

    @staticmethod
    def get_endpoint(service_type, vim_uuid):
        """Get the endpoint for Gnocchi/Aodh."""
        auth_manager = AuthManager()
        creds = auth_manager.get_credentials(vim_uuid)
        ks = client.Client(auth_url=creds.url,
                           username=creds.user,
                           password=creds.password,
                           tenant_name=creds.tenant_name)
        return ks.service_catalog.url_for(
            service_type=service_type,
            endpoint_type='publicURL',
            region_name='RegionOne')

    @staticmethod
    def perform_request(url, auth_token,
                        req_type=None, payload=None, params=None):
        """Perform the POST/PUT/GET/DELETE request."""
        # request headers
        headers = {'X-Auth-Token': auth_token,
                   'Content-type': 'application/json'}
        # perform request and return its result
        if req_type == "put":
            response = requests.put(
                url, data=payload, headers=headers,
                timeout=10)
        elif req_type == "get":
            response = requests.get(
                url, params=params, headers=headers, timeout=10)
        elif req_type == "delete":
            response = requests.delete(
                url, headers=headers, timeout=10)
        else:
            response = requests.post(
                url, data=payload, headers=headers,
                timeout=10)

        # Raises exception if there was an error
        try:
            response.raise_for_status()
        # pylint: disable=broad-except
        except Exception:
            # Log out the result of the request for debugging purpose
            log.debug(
                'Result: %s, %s',
                response.status_code, response.text)
        return response
