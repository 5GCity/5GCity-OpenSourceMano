# -*- coding: utf-8 -*-
##
# Copyright 2018 Telefonica
# All Rights Reserved.
#
# Contributors: Oscar Gonzalez de Dios, Manuel Lopez Bravo, Guillermo Pajares Martin
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
#
# This work has been performed in the context of the Metro-Haul project -
# funded by the European Commission under Grant number 761727 through the
# Horizon 2020 program.
##
"""The WIM connector is responsible for establishing wide area network
connectivity.

This WIM connector implements the standard IETF RFC 8466 "A YANG Data
 Model for Layer 2 Virtual Private Network (L2VPN) Service Delivery"

It receives the endpoints and the necessary details to request
the Layer 2 service.
"""
import requests
import uuid
import logging
from .wimconn import WimConnector, WimConnectorError
"""CHeck layer where we move it"""


class WimconnectorIETFL2VPN(WimConnector):

    def __init__(self, wim, wim_account, config=None, logger=None):
        """IETF L2VPM WIM connector

        Arguments: (To be completed)
            wim (dict): WIM record, as stored in the database
            wim_account (dict): WIM account record, as stored in the database
        """
        self.logger = logging.getLogger('openmano.wimconn.ietfl2vpn')
        super(WimconnectorIETFL2VPN, self).__init__(wim, wim_account, config, logger)
        self.headers = {'Content-Type': 'application/json'}
        self.mappings = {m['wan_service_endpoint_id']: m
                         for m in self.service_endpoint_mapping}
        self.user = wim_account.get("user")
        self.passwd = wim_account.get("passwd")
        if self.user and self.passwd is not None:
            self.auth = (self.user, self.passwd)
        else:
            self.auth = None
        self.logger.info("IETFL2VPN Connector Initialized.")

    def check_credentials(self):
        endpoint = "{}/restconf/data/ietf-l2vpn-svc:l2vpn-svc/vpn-services".format(self.wim["wim_url"])
        try:
            response = requests.get(endpoint, auth=self.auth)    
            http_code = response.status_code
        except requests.exceptions.RequestException as e:
            raise WimConnectorError(e.message, http_code=503)

        if http_code != 200:
            raise WimConnectorError("Failed while authenticating", http_code=http_code)
        self.logger.info("Credentials checked")

    def get_connectivity_service_status(self, service_uuid, conn_info=None):
        """Monitor the status of the connectivity service stablished

        Arguments:
            service_uuid: Connectivity service unique identifier

        Returns:
            Examples::
                {'wim_status': 'ACTIVE'}
                {'wim_status': 'INACTIVE'}
                {'wim_status': 'DOWN'}
                {'wim_status': 'ERROR'}
        """
        try:
            self.logger.info("Sending get connectivity service stuatus")
            servicepoint = "{}/restconf/data/ietf-l2vpn-svc:l2vpn-svc/vpn-services/vpn-service={}/".format(
                self.wim["wim_url"], service_uuid)
            response = requests.get(servicepoint, auth=self.auth)
            if response.status_code != requests.codes.ok:
                raise WimConnectorError("Unable to obtain connectivity servcice status", http_code=response.status_code)
            service_status = {'wim_status': 'ACTIVE'}
            return service_status
        except requests.exceptions.ConnectionError:
            raise WimConnectorError("Request Timeout", http_code=408)
               
    def search_mapp(self, connection_point):
        id = connection_point['service_endpoint_id']
        if id not in self.mappings:         
            raise WimConnectorError("Endpoint {} not located".format(str(id)))
        else:
            return self.mappings[id]

    def create_connectivity_service(self, service_type, connection_points, **kwargs):
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
        if service_type == "ELINE":
            if len(connection_points) > 2:
                raise WimConnectorError('Connections between more than 2 endpoints are not supported')
            if len(connection_points) < 2:
                raise WimConnectorError('Connections must be of at least 2 endpoints')
            """ First step, create the vpn service """    
            uuid_l2vpn = str(uuid.uuid4())
            vpn_service = {}
            vpn_service["vpn-id"] = uuid_l2vpn
            vpn_service["vpn-scv-type"] = "vpws"
            vpn_service["svc-topo"] = "any-to-any"
            vpn_service["customer-name"] = "osm"
            vpn_service_list = []
            vpn_service_list.append(vpn_service)
            vpn_service_l = {"vpn-service": vpn_service_list}
            response_service_creation = None
            conn_info = []
            self.logger.info("Sending vpn-service :{}".format(vpn_service_l))
            try:
                endpoint_service_creation = "{}/restconf/data/ietf-l2vpn-svc:l2vpn-svc/vpn-services".format(
                    self.wim["wim_url"])
                response_service_creation = requests.post(endpoint_service_creation, headers=self.headers,
                                                          json=vpn_service_l, auth=self.auth)
            except requests.exceptions.ConnectionError:
                raise WimConnectorError("Request to create service Timeout", http_code=408)
            if response_service_creation.status_code == 409:
                raise WimConnectorError("Service already exists", http_code=response_service_creation.status_code)
            elif response_service_creation.status_code != requests.codes.created:
                raise WimConnectorError("Request to create service not accepted",
                                        http_code=response_service_creation.status_code)
            """ Second step, create the connections and vpn attachments """   
            for connection_point in connection_points:
                connection_point_wan_info = self.search_mapp(connection_point)
                site_network_access = {}
                connection = {}
                if connection_point["service_endpoint_encapsulation_type"] != "none":
                    if connection_point["service_endpoint_encapsulation_type"] == "dot1q":
                        """ The connection is a VLAN """
                        connection["encapsulation-type"] = "dot1q-vlan-tagged"
                        tagged = {}
                        tagged_interf = {}
                        service_endpoint_encapsulation_info = connection_point["service_endpoint_encapsulation_info"]
                        if service_endpoint_encapsulation_info["vlan"] is None:
                            raise WimConnectorError("VLAN must be provided")
                        tagged_interf["cvlan-id"] = service_endpoint_encapsulation_info["vlan"]
                        tagged["dot1q-vlan-tagged"] = tagged_interf
                        connection["tagged-interface"] = tagged
                    else:
                        raise NotImplementedError("Encapsulation type not implemented")
                site_network_access["connection"] = connection
                self.logger.info("Sending connection:{}".format(connection))
                vpn_attach = {}
                vpn_attach["vpn-id"] = uuid_l2vpn
                vpn_attach["site-role"] = vpn_service["svc-topo"]+"-role"
                site_network_access["vpn-attachment"] = vpn_attach
                self.logger.info("Sending vpn-attachement :{}".format(vpn_attach))
                uuid_sna = str(uuid.uuid4())
                site_network_access["network-access-id"] = uuid_sna
                site_network_accesses = {}
                site_network_access_list = []
                site_network_access_list.append(site_network_access)
                site_network_accesses["site-network-access"] = site_network_access_list
                conn_info_d = {}
                conn_info_d["site"] = connection_point_wan_info["site-id"]
                conn_info_d["site-network-access-id"] = site_network_access["network-access-id"]
                conn_info_d["mapping"] = None
                conn_info.append(conn_info_d)
                try:
                    endpoint_site_network_access_creation = \
                        "{}/restconf/data/ietf-l2vpn-svc:l2vpn-svc/sites/site={}/site-network-accesses/".format(
                            self.wim["wim_url"], connection_point_wan_info["site-id"])
                    response_endpoint_site_network_access_creation = requests.post(
                        endpoint_site_network_access_creation,
                        headers=self.headers,
                        json=site_network_accesses,
                        auth=self.auth)
                    
                    if response_endpoint_site_network_access_creation.status_code == 409:
                        self.delete_connectivity_service(vpn_service["vpn-id"])
                        raise WimConnectorError("Site_Network_Access with ID '{}' already exists".format(
                            site_network_access["network-access-id"]),
                            http_code=response_endpoint_site_network_access_creation.status_code)
                    
                    elif response_endpoint_site_network_access_creation.status_code == 400:
                        self.delete_connectivity_service(vpn_service["vpn-id"])
                        raise WimConnectorError("Site {} does not exist".format(connection_point_wan_info["site-id"]),
                                                http_code=response_endpoint_site_network_access_creation.status_code)
                    
                    elif response_endpoint_site_network_access_creation.status_code != requests.codes.created and \
                            response_endpoint_site_network_access_creation.status_code != requests.codes.no_content:
                        self.delete_connectivity_service(vpn_service["vpn-id"])
                        raise WimConnectorError("Request no accepted",
                                                http_code=response_endpoint_site_network_access_creation.status_code)
                
                except requests.exceptions.ConnectionError:
                    self.delete_connectivity_service(vpn_service["vpn-id"])
                    raise WimConnectorError("Request Timeout", http_code=408)
            return uuid_l2vpn, conn_info
        
        else:
            raise NotImplementedError

    def delete_connectivity_service(self, service_uuid, conn_info=None):
        """Disconnect multi-site endpoints previously connected

        This method should receive as the first argument the UUID generated by
        the ``create_connectivity_service``
        """
        try:
            self.logger.info("Sending delete")
            servicepoint = "{}/restconf/data/ietf-l2vpn-svc:l2vpn-svc/vpn-services/vpn-service={}/".format(
                self.wim["wim_url"], service_uuid)
            response = requests.delete(servicepoint, auth=self.auth)
            if response.status_code != requests.codes.no_content:
                raise WimConnectorError("Error in the request", http_code=response.status_code)
        except requests.exceptions.ConnectionError:
            raise WimConnectorError("Request Timeout", http_code=408)

    def edit_connectivity_service(self, service_uuid, conn_info=None,
                                  connection_points=None, **kwargs):
        """Change an existing connectivity service, see
        ``create_connectivity_service``"""

        # sites = {"sites": {}}
        # site_list = []
        vpn_service = {}
        vpn_service["svc-topo"] = "any-to-any"
        counter = 0
        for connection_point in connection_points:
            site_network_access = {}
            connection_point_wan_info = self.search_mapp(connection_point)
            params_site = {}
            params_site["site-id"] = connection_point_wan_info["site-id"]
            params_site["site-vpn-flavor"] = "site-vpn-flavor-single"
            device_site = {}
            device_site["device-id"] = connection_point_wan_info["device-id"]
            params_site["devices"] = device_site
            # network_access = {}
            connection = {}
            if connection_point["service_endpoint_encapsulation_type"] != "none":
                if connection_point["service_endpoint_encapsulation_type"] == "dot1q":
                    """ The connection is a VLAN """
                    connection["encapsulation-type"] = "dot1q-vlan-tagged"
                    tagged = {}
                    tagged_interf = {}
                    service_endpoint_encapsulation_info = connection_point["service_endpoint_encapsulation_info"]
                    if service_endpoint_encapsulation_info["vlan"] is None:
                        raise WimConnectorError("VLAN must be provided")
                    tagged_interf["cvlan-id"] = service_endpoint_encapsulation_info["vlan"]
                    tagged["dot1q-vlan-tagged"] = tagged_interf
                    connection["tagged-interface"] = tagged
                else:
                    raise NotImplementedError("Encapsulation type not implemented")
            site_network_access["connection"] = connection
            vpn_attach = {}
            vpn_attach["vpn-id"] = service_uuid
            vpn_attach["site-role"] = vpn_service["svc-topo"]+"-role"
            site_network_access["vpn-attachment"] = vpn_attach
            uuid_sna = conn_info[counter]["site-network-access-id"]
            site_network_access["network-access-id"] = uuid_sna
            site_network_accesses = {}
            site_network_access_list = []
            site_network_access_list.append(site_network_access)
            site_network_accesses["site-network-access"] = site_network_access_list
            try:
                endpoint_site_network_access_edit = \
                    "{}/restconf/data/ietf-l2vpn-svc:l2vpn-svc/sites/site={}/site-network-accesses/".format(
                        self.wim["wim_url"], connection_point_wan_info["site-id"])  # MODIF
                response_endpoint_site_network_access_creation = requests.put(endpoint_site_network_access_edit,
                                                                              headers=self.headers,
                                                                              json=site_network_accesses,
                                                                              auth=self.auth)
                if response_endpoint_site_network_access_creation.status_code == 400:
                    raise WimConnectorError("Service does not exist",
                                            http_code=response_endpoint_site_network_access_creation.status_code)
                elif response_endpoint_site_network_access_creation.status_code != 201 and \
                        response_endpoint_site_network_access_creation.status_code != 204:
                    raise WimConnectorError("Request no accepted",
                                            http_code=response_endpoint_site_network_access_creation.status_code)
            except requests.exceptions.ConnectionError:
                raise WimConnectorError("Request Timeout", http_code=408)
            counter += 1
        return None

    def clear_all_connectivity_services(self):
        """Delete all WAN Links corresponding to a WIM"""
        try:
            self.logger.info("Sending clear all connectivity services")
            servicepoint = "{}/restconf/data/ietf-l2vpn-svc:l2vpn-svc/vpn-services".format(self.wim["wim_url"])
            response = requests.delete(servicepoint, auth=self.auth)
            if response.status_code != requests.codes.no_content:
                raise WimConnectorError("Unable to clear all connectivity services", http_code=response.status_code)
        except requests.exceptions.ConnectionError:
            raise WimConnectorError("Request Timeout", http_code=408)

    def get_all_active_connectivity_services(self):
        """Provide information about all active connections provisioned by a
        WIM
        """
        try:
            self.logger.info("Sending get all connectivity services")
            servicepoint = "{}/restconf/data/ietf-l2vpn-svc:l2vpn-svc/vpn-services".format(self.wim["wim_url"])
            response = requests.get(servicepoint, auth=self.auth)
            if response.status_code != requests.codes.ok:
                raise WimConnectorError("Unable to get all connectivity services", http_code=response.status_code)
            return response
        except requests.exceptions.ConnectionError:
            raise WimConnectorError("Request Timeout", http_code=408)
