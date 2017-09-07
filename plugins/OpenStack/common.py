"""Common methods for the Aodh Sender/Receiver."""

import logging as log

from keystoneclient.v3 import client

from plugins.OpenStack.settings import Config

import requests

# from keystoneauth1.identity.v3 import AuthMethod
# from keystoneclient.service_catalog import ServiceCatalog


class Common(object):
    """Common calls for Gnocchi/Aodh plugins."""

    def __init__(self):
        """Create the common instance."""
        self._auth_token = None
        self._endpoint = None
        self._ks = None

    def _authenticate(self, tenant_id=None):
        """Authenticate and/or renew the authentication token."""
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

            log.warn("Authentication failed with the following exception: %s",
                     exc)
            self._auth_token = None

        return self._auth_token

    def get_endpoint(self, service_type):
        """Get the endpoint for Gnocchi/Aodh."""
        try:
            return self._ks.service_catalog.url_for(
                service_type=service_type,
                endpoint_type='internalURL',
                region_name='RegionOne')
        except Exception as exc:
            log.warning("Failed to retreive endpoint for Aodh due to: %s",
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
        response = None
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
                    url, params=params, headers=headers, timeout=1)
            elif req_type == "delete":
                response = requests.delete(
                    url, headers=headers, timeout=1)
            else:
                log.warn("Invalid request type")

        except Exception as e:
            log.warn("Exception thrown on request", e)

        return response
