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

from keystoneclient.v3 import client

from osm_mon.plugins.OpenStack.settings import Config

import requests

__author__ = "Helena McGough"

log = logging.getLogger(__name__)


class Common(object):
    """Common calls for Gnocchi/Aodh plugins."""

    def __init__(self):
        """Create the common instance."""
        self._auth_token = None
        self._ks = None
        self.openstack_url = None
        self.user = None
        self.password = None
        self.tenant = None

    def _authenticate(self, message=None):
        """Authenticate and/or renew the authentication token."""
        if self._auth_token is not None:
            return self._auth_token

        if message is not None:
            values = json.loads(message.value)['access_config']
            self.openstack_url = values['openstack_site']
            self.user = values['user']
            self.password = values['password']
            self.tenant = values['vim_tenant_name']

            try:
                # try to authenticate with supplied access_credentials
                self._ks = client.Client(auth_url=self.openstack_url,
                                         username=self.user,
                                         password=self.password,
                                         tenant_name=self.tenant)
                self._auth_token = self._ks.auth_token
                log.info("Authenticating with access_credentials from SO.")
                return self._auth_token
            except Exception as exc:
                log.warn("Authentication failed with access_credentials: %s",
                         exc)

        else:
            log.info("Access_credentials were not sent from SO.")

        # If there are no access_credentials or they fail use env variables
        try:
            cfg = Config.instance()
            self._ks = client.Client(auth_url=cfg.OS_AUTH_URL,
                                     username=cfg.OS_USERNAME,
                                     password=cfg.OS_PASSWORD,
                                     tenant_name=cfg.OS_TENANT_NAME)
            log.info("Authenticating with environment varialbles.")
            self._auth_token = self._ks.auth_token
        except Exception as exc:

            log.warn("Authentication failed: %s", exc)

            self._auth_token = None

        return self._auth_token

    def get_endpoint(self, service_type):
        """Get the endpoint for Gnocchi/Aodh."""
        try:
            return self._ks.service_catalog.url_for(
                service_type=service_type,
                endpoint_type='publicURL',
                region_name='regionOne')
        except Exception as exc:
            log.warning("Failed to retreive endpoint for service due to: %s",
                        exc)
        return None

    @classmethod
    def _perform_request(cls, url, auth_token,
                         req_type=None, payload=None, params=None):
        """Perform the POST/PUT/GET/DELETE request."""
        # request headers
        headers = {'X-Auth-Token': auth_token,
                   'Content-type': 'application/json'}
        # perform request and return its result
        if req_type == "put":
            response = requests.put(
                url, data=payload, headers=headers,
                timeout=1)
        elif req_type == "get":
            response = requests.get(
                url, params=params, headers=headers, timeout=1)
        elif req_type == "delete":
            response = requests.delete(
                url, headers=headers, timeout=1)
        else:
            response = requests.post(
                url, data=payload, headers=headers,
                timeout=1)

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
