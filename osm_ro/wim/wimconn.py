# -*- coding: utf-8 -*-
##
# Copyright 2018 University of Bristol - High Performance Networks Research
# Group
# All Rights Reserved.
#
# Contributors: Anderson Bravalheri, Dimitrios Gkounis, Abubakar Siddique
# Muqaddas, Navdeep Uniyal, Reza Nejabati and Dimitra Simeonidou
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
# contact with: <highperformance-networks@bristol.ac.uk>
#
# Neither the name of the University of Bristol nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# This work has been performed in the context of DCMS UK 5G Testbeds
# & Trials Programme and in the framework of the Metro-Haul project -
# funded by the European Commission under Grant number 761727 through the
# Horizon 2020 and 5G-PPP programmes.
##
"""The WIM connector is responsible for establishing wide area network
connectivity.

It receives information from the WimThread/WAN Actions about the endpoints of
a link that spans across multiple datacenters and stablish a path between them.
"""
import logging

from ..http_tools.errors import HttpMappedError


class WimConnectorError(HttpMappedError):
    """Base Exception for all connector related errors"""


class WimConnector(object):
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
        self.logger = logger or logging.getLogger('openmano.wim.wimconn')

        self.wim = wim
        self.wim_account = wim_account
        self.config = config or {}
        self.service_endpoint_mapping = (
            config.get('service_endpoint_mapping', []))

    def check_credentials(self):
        """Check if the connector itself can access the WIM.

        Raises:
            WimConnectorError: Issues regarding authorization, access to
                external URLs, etc are detected.
        """
        raise NotImplementedError

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

                    {'wim_status': 'ACTIVE'}
                        # The service is up and running.

                    {'wim_status': 'INACTIVE'}
                        # The service was created, but the connector
                        # cannot determine yet if connectivity exists
                        # (ideally, the caller needs to wait and check again).

                    {'wim_status': 'DOWN'}
                        # Connection was previously established,
                        # but an error/failure was detected.

                    {'wim_status': 'ERROR'}
                        # An error occurred when trying to create the service/
                        # establish the connectivity.

                    {'wim_status': 'BUILD'}
                        # Still trying to create the service, the caller
                        # needs to wait and check again.

                Additionally ``error_msg``(**str**) and ``wim_info``(**dict**)
                keys can be used to provide additional status explanation or
                new information available for the connectivity service.
        """
        raise NotImplementedError

    def create_connectivity_service(self, service_type, connection_points,
                                    **kwargs):
        """Stablish WAN connectivity between the endpoints

        Arguments:
            service_type (str): ``ELINE`` (L2), ``ELAN`` (L2), ``ETREE`` (L2),
                ``L3``.
            connection_points (list): each point corresponds to
                an entry point from the DC to the transport network. One
                connection point serves to identify the specific access and
                some other service parameters, such as encapsulation type.
                Represented by a dict as follows::

                    {
                      "service_endpoint_id": ..., (str[uuid])
                      "service_endpoint_encapsulation_type": ...,
                           (enum: none, dot1q, ...)
                      "service_endpoint_encapsulation_info": {
                        ... (dict)
                        "vlan": ..., (int, present if encapsulation is dot1q)
                        "vni": ... (int, present if encapsulation is vxlan),
                        "peers": [(ipv4_1), (ipv4_2)]
                            (present if encapsulation is vxlan)
                      }
                    }

              The service endpoint ID should be previously informed to the WIM
              engine in the RO when the WIM port mapping is registered.

        Keyword Arguments:
            bandwidth (int): value in kilobytes
            latency (int): value in milliseconds

        Other QoS might be passed as keyword arguments.

        Returns:
            tuple: ``(service_id, conn_info)`` containing:
               - *service_uuid* (str): UUID of the established connectivity
                  service
               - *conn_info* (dict or None): Information to be stored at the
                 database (or ``None``). This information will be provided to
                 the :meth:`~.edit_connectivity_service` and :obj:`~.delete`.
                 **MUST** be JSON/YAML-serializable (plain data structures).

        Raises:
            WimConnectorException: In case of error.
        """
        raise NotImplementedError

    def delete_connectivity_service(self, service_uuid, conn_info=None):
        """Disconnect multi-site endpoints previously connected

        This method should receive as arguments both the UUID and the
        connection info dict (respectively), as returned by
        :meth:`~.create_connectivity_service` and
        :meth:`~.edit_connectivity_service`.

        Arguments:
            service_uuid (str): UUID of the connectivity service
            conn_info (dict or None): Information returned by the connector
                during the service creation and subsequently stored in the
                database.

        Raises:
            WimConnectorException: In case of error.
        """
        raise NotImplementedError

    def edit_connectivity_service(self, service_uuid, conn_info=None,
                                  connection_points=None, **kwargs):
        """Change an existing connectivity service.

        This method's arguments and return value follow the same convention as
        :meth:`~.create_connectivity_service`.

        Arguments:
            service_uuid (str): UUID of the connectivity service.
            conn_info (dict or None): Information previously stored in the
                database.
            connection_points (list): If provided, the old list of connection
                points will be replaced.

        Returns:
            dict or None: Information to be updated and stored at the
                database.
                When ``None`` is returned, no information should be changed.
                When an empty dict is returned, the database record will be
                deleted.
                **MUST** be JSON/YAML-serializable (plain data structures).

        Raises:
            WimConnectorException: In case of error.
        """
        raise NotImplementedError

    def clear_all_connectivity_services(self):
        """Delete all WAN Links in a WIM.

        This method is intended for debugging only, and should delete all the
        connections controlled by the WIM, not only the WIM connections that
        a specific RO is aware of.

        Raises:
            WimConnectorException: In case of error.
        """
        raise NotImplementedError

    def get_all_active_connectivity_services(self):
        """Provide information about all active connections provisioned by a
        WIM.

        Raises:
            WimConnectorException: In case of error.
        """
        raise NotImplementedError
