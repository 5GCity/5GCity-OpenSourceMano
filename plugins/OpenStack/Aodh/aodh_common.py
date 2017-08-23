"""Common methods for the Aodh Sender/Receiver."""

import threading
import os
import requests

from keystoneauth1.identity import v3
from keystoneauth1.identity.v3 import AuthMethod
from keystoneauth1 import session
from keystoneclient.v3 import client
from keystoneclient.service_catalog import ServiceCatalog

from plugins.Openstack.settings import Config


class Aodh_Common(object):
    """Common calls for Aodh Sender/Receiver."""

    def __init__(self):
        """Create the common instance."""
        self._auth_token = None
        self._endpoint = None
        self._ks = None

    def _authenticate(self):
        """Authenticate and/or renew the authentication token"""

        if self._auth_token is not None:
            return self._auth_token

        try:
            cfg = Config.instance()
            self._ks = client.Client(auth_url=cfg.OS_AUTH_URL,
                                     username=cfg.OS_USERNAME,
                                     password=cfg.OS_PASSWORD,
                                     tenant_name=cfg.OS_TENANT_NAME)
            self._auth_token = self._ks.auth_token
        except Exception as exc:

            # TODO: Log errors
            self._auth_token = None

        return self._auth_token

    def get_endpoint(self):
        endpoint = self._ks.service_catalog.url_for(
            service_type='alarming',
            endpoint_type='internalURL',
            region_name='RegionOne')
        return endpoint

    @classmethod
    def _perform_request(cls, url, auth_token, req_type="get", payload=None):
        """Perform the POST/PUT/GET/DELETE request."""

        # request headers
        headers = {'X-Auth-Token': auth_token,
                   'Content-type': 'application/json'}
        # perform request and return its result
        try:
            if req_type == "put":
                response = requests.put(
                    url, data=payload, headers=headers,
                    timeout=1)
            elif req_type == "post":
                response = requests.post(
                    url, data=payload, headers=headers,
                    timeout=1)
            elif req_type == "get":
                response = requests.get(
                    url, headers=headers, timeout=1)
            elif req_type == "delete":
                response = requests.delete(
                    url, headers=headers, timeout=1)
            else:
                print("Invalid request type")

        except Exception as e:
            # Log info later
            print("Exception thrown on request", e)

        return response
