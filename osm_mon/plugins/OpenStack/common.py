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
import json
import logging

import requests
import yaml
from keystoneauth1 import session
from keystoneauth1.identity import v3
from keystoneclient.v3 import client

from osm_mon.core.auth import AuthManager
from osm_mon.core.settings import Config

__author__ = "Helena McGough"

log = logging.getLogger(__name__)
cfg = Config.instance()


class Common(object):
    """Common calls for Gnocchi/Aodh plugins."""

    def __init__(self):
        """Create the common instance."""

    @staticmethod
    def get_auth_token(vim_uuid, verify_ssl=True):
        """Authenticate and/or renew the authentication token."""
        auth_manager = AuthManager()
        creds = auth_manager.get_credentials(vim_uuid)
        sess = session.Session(verify=verify_ssl)
        ks = client.Client(session=sess)
        token_dict = ks.get_raw_token_from_identity_service(auth_url=creds.url,
                                                            username=creds.user,
                                                            password=creds.password,
                                                            project_name=creds.tenant_name,
                                                            project_domain_id='default',
                                                            user_domain_id='default')
        return token_dict['auth_token']

    @staticmethod
    def get_endpoint(service_type, vim_uuid, verify_ssl=True):
        """Get the endpoint for Gnocchi/Aodh."""
        auth_manager = AuthManager()
        creds = auth_manager.get_credentials(vim_uuid)
        auth = v3.Password(auth_url=creds.url,
                           username=creds.user,
                           password=creds.password,
                           project_name=creds.tenant_name,
                           project_domain_id='default',
                           user_domain_id='default')
        sess = session.Session(auth=auth, verify=verify_ssl)
        ks = client.Client(session=sess, interface='public')
        service = ks.services.list(type=service_type)[0]
        endpoints = ks.endpoints.list(service)
        endpoint_type = 'publicURL'
        region_name = 'RegionOne'
        if creds.config is not None:
            try:
                config = json.loads(creds.config)
            except ValueError:
                config = yaml.safe_load(creds.config)
            if 'endpoint_type' in config:
                endpoint_type = config['endpoint_type']
            if 'region_name' in config:
                region_name = config['region_name']
        for endpoint in endpoints:
            if endpoint.interface in endpoint_type and endpoint.region == region_name:
                return endpoint.url

    @staticmethod
    def perform_request(url, auth_token,
                        req_type=None, payload=None, params=None, verify_ssl=True):
        """Perform the POST/PUT/GET/DELETE request."""

        timeout = cfg.REQUEST_TIMEOUT

        # request headers
        headers = {'X-Auth-Token': auth_token,
                   'Content-type': 'application/json'}
        # perform request and return its result
        if req_type == "put":
            response = requests.put(
                url, data=payload, headers=headers,
                timeout=timeout, verify=verify_ssl)
        elif req_type == "get":
            response = requests.get(
                url, params=params, headers=headers, timeout=timeout, verify=verify_ssl)
        elif req_type == "delete":
            response = requests.delete(
                url, headers=headers, timeout=timeout, verify=verify_ssl)
        else:
            response = requests.post(
                url, data=payload, headers=headers,
                timeout=timeout, verify=verify_ssl)

        # Raises exception if there was an error
        try:
            response.raise_for_status()
        # pylint: disable=broad-except
        except Exception:
            # Log out the result of the request
            log.warning(
                'Result: %s, %s',
                response.status_code, response.text)
        return response
