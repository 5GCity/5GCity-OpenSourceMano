# -*- coding: utf-8 -*-
##
# Copyright 2018 Telefonica
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This WIM does nothing and allows using it for testing and when no WIM is needed
"""

import logging
from uuid import uuid4
from .wimconn import WimConnector

__author__ = "Alfonso Tierno <alfonso.tiernosepulveda@telefonica.com>"


class FakeConnector(WimConnector):
    """Abstract base class for all the WIM connectors

    Arguments:
        wim (dict): WIM record, as stored in the database
        wim_account (dict): WIM account record, as stored in the database
        config (dict): optional persistent information related to an specific
            connector.  Inside this dict, a special key,
            ``service_endpoint_mapping`` provides the internal endpoint
            mapping.
        logger (logging.Logger): optional logger object. If none is passed
            ``openmano.wim.wimconn`` is used.

    The arguments of the constructor are converted to object attributes.
    An extra property, ``service_endpoint_mapping`` is created from ``config``.
    """
    def __init__(self, wim, wim_account, config=None, logger=None):
        self.logger = logging.getLogger('openmano.wimconn.fake')
        super(FakeConnector, self).__init__(wim, wim_account, config, logger)
        self.logger.debug("__init: wim='{}' wim_account='{}'".format(wim, wim_account))
        self.connections = {}
        self.counter = 0

    def check_credentials(self):
        """Check if the connector itself can access the WIM.

        Raises:
            WimConnectorError: Issues regarding authorization, access to
                external URLs, etc are detected.
        """
        self.logger.debug("check_credentials")
        return None

    def get_connectivity_service_status(self, service_uuid, conn_info=None):
        """Monitor the status of the connectivity service established

        Arguments:
            service_uuid (str): UUID of the connectivity service
            conn_info (dict or None): Information returned by the connector
                during the service creation/edition and subsequently stored in
                the database.

        Returns:
            dict: JSON/YAML-serializable dict that contains a mandatory key
                ``wim_status`` associated with one of the following values::

                Additionally ``error_msg``(**str**) and ``wim_info``(**dict**)
                keys can be used to provide additional status explanation or
                new information available for the connectivity service.
        """
        self.logger.debug("get_connectivity_service_status: service_uuid='{}' conn_info='{}'".format(service_uuid,
                                                                                                     conn_info))
        return {'wim_status': 'ACTIVE', 'wim_info': self.connectivity.get(service_uuid)}

    def create_connectivity_service(self, service_type, connection_points,
                                    **kwargs):
        """
        Stablish WAN connectivity between the endpoints

        """
        self.logger.debug("create_connectivity_service: service_type='{}' connection_points='{}', kwargs='{}'".
                          format(service_type, connection_points, kwargs))
        _id = str(uuid4())
        self.connectivity[_id] = {"nb": self.counter}
        self.counter += 1
        return _id, self.connectivity[_id]

    def delete_connectivity_service(self, service_uuid, conn_info=None):
        """Disconnect multi-site endpoints previously connected

        """
        self.logger.debug("delete_connectivity_service: service_uuid='{}' conn_info='{}'".format(service_uuid,
                                                                                                 conn_info))
        self.connectivity.pop(service_uuid, None)
        return None

    def edit_connectivity_service(self, service_uuid, conn_info=None,
                                  connection_points=None, **kwargs):
        """Change an existing connectivity service.

        This method's arguments and return value follow the same convention as
        :meth:`~.create_connectivity_service`.
        """
        self.logger.debug("edit_connectivity_service: service_uuid='{}' conn_info='{}', connection_points='{}'"
                          "kwargs='{}'".format(service_uuid, conn_info, connection_points, kwargs))
        return None

    def clear_all_connectivity_services(self):
        """Delete all WAN Links in a WIM.

        This method is intended for debugging only, and should delete all the
        connections controlled by the WIM, not only the WIM connections that
        a specific RO is aware of.

        """
        self.logger.debug("clear_all_connectivity_services")
        self.connectivity.clear()
        return None

    def get_all_active_connectivity_services(self):
        """Provide information about all active connections provisioned by a
        WIM.

        Raises:
            WimConnectorException: In case of error.
        """
        self.logger.debug("get_all_active_connectivity_services")
        return self.connectivity
