#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##
# Copyright 2018 David García, University of the Basque Country
# Copyright 2018 University of the Basque Country
# This file is part of openmano
# All Rights Reserved.
# Contact information at http://i2t.ehu.eus
#
# # Licensed under the Apache License, Version 2.0 (the "License");
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

import requests
import json
import logging
from enum import Enum

from wimconn import WimConnector, WimConnectorError


class WimError(Enum):
    UNREACHABLE = 'Unable to reach the WIM.',
    SERVICE_TYPE_ERROR = 'Unexpected service_type. Only "L2" is accepted.',
    CONNECTION_POINTS_SIZE = \
        'Unexpected number of connection points: 2 expected.',
    ENCAPSULATION_TYPE = \
        'Unexpected service_endpoint_encapsulation_type. \
         Only "dotq1" is accepted.',
    BANDWIDTH = 'Unable to get the bandwidth.',
    STATUS = 'Unable to get the status for the service.',
    DELETE = 'Unable to delete service.',
    CLEAR_ALL = 'Unable to clear all the services',
    UNKNOWN_ACTION = 'Unknown action invoked.',
    BACKUP = 'Unable to get the backup parameter.',
    UNSUPPORTED_FEATURE = "Unsupported feature",
    UNAUTHORIZED = "Failed while authenticating"


class WimAPIActions(Enum):
    CHECK_CONNECTIVITY = "CHECK_CONNECTIVITY",
    CREATE_SERVICE = "CREATE_SERVICE",
    DELETE_SERVICE = "DELETE_SERVICE",
    CLEAR_ALL = "CLEAR_ALL",
    SERVICE_STATUS = "SERVICE_STATUS",


class DynpacConnector(WimConnector):
    __supported_service_types = ["ELINE (L2)", "ELINE"]
    __supported_encapsulation_types = ["dot1q"]
    __WIM_LOGGER = 'openmano.wimconn.dynpac'
    __ENCAPSULATION_TYPE_PARAM = "service_endpoint_encapsulation_type"
    __ENCAPSULATION_INFO_PARAM = "service_endpoint_encapsulation_info"
    __BACKUP_PARAM = "backup"
    __BANDWIDTH_PARAM = "bandwidth"
    __SERVICE_ENDPOINT_PARAM = "service_endpoint_id"
    __WAN_SERVICE_ENDPOINT_PARAM = "wan_service_endpoint_id"
    __WAN_MAPPING_INFO_PARAM = "wan_service_mapping_info"
    __SW_ID_PARAM = "wan_switch_dpid"
    __SW_PORT_PARAM = "wan_switch_port"
    __VLAN_PARAM = "vlan"

    # Public functions exposed to the Resource Orchestrator
    def __init__(self, wim, wim_account, config):
        self.logger = logging.getLogger(self.__WIM_LOGGER)
        self.__wim = wim
        self.__wim_account = wim_account
        self.__config = config
        self.__wim_url = self.__wim.get("wim_url")
        self.__user = wim_account.get("user")
        self.__passwd = wim_account.get("passwd")
        self.logger.info("Initialized.")

    def create_connectivity_service(self,
                                    service_type,
                                    connection_points,
                                    **kwargs):
        self.__check_service(service_type, connection_points, kwargs)

        body = self.__get_body(service_type, connection_points, kwargs)

        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        endpoint = "{}/service/create".format(self.__wim_url)

        try:
            response = requests.post(endpoint, data=body, headers=headers)
        except requests.exceptions.RequestException as e:
            self.__exception(e.message, http_code=503)

        if response.status_code != 200:
            error = json.loads(response.content)
            reason = "Reason: {}. ".format(error.get("code"))
            description = "Description: {}.".format(error.get("description"))
            exception = reason + description
            self.__exception(exception, http_code=response.status_code)
        uuid = response.content
        self.logger.info("Service with uuid {} created.".format(uuid))
        return (uuid, None)

    def edit_connectivity_service(self, service_uuid,
                                  conn_info, connection_points,
                                  **kwargs):
        self.__exception(WimError.UNSUPPORTED_FEATURE, http_code=501)

    def get_connectivity_service_status(self, service_uuid):
        endpoint = "{}/service/status/{}".format(self.__wim_url, service_uuid)
        try:
            response = requests.get(endpoint)
        except requests.exceptions.RequestException as e:
            self.__exception(e.message, http_code=503)

        if response.status_code != 200:
            self.__exception(WimError.STATUS, http_code=response.status_code)
        self.logger.info("Status for service with uuid {}: {}"
                         .format(service_uuid, response.content))
        return response.content

    def delete_connectivity_service(self, service_uuid, conn_info):
        endpoint = "{}/service/delete/{}".format(self.__wim_url, service_uuid)
        try:
            response = requests.delete(endpoint)
        except requests.exceptions.RequestException as e:
            self.__exception(e.message, http_code=503)
        if response.status_code != 200:
            self.__exception(WimError.DELETE, http_code=response.status_code)

        self.logger.info("Service with uuid: {} deleted".format(service_uuid))

    def clear_all_connectivity_services(self):
        endpoint = "{}/service/clearAll".format(self.__wim_url)
        try:
            response = requests.delete(endpoint)
            http_code = response.status_code
        except requests.exceptions.RequestException as e:
            self.__exception(e.message, http_code=503)
        if http_code != 200:
            self.__exception(WimError.CLEAR_ALL, http_code=http_code)

        self.logger.info("{} services deleted".format(response.content))
        return "{} services deleted".format(response.content)

    def check_connectivity(self):
        endpoint = "{}/checkConnectivity".format(self.__wim_url)

        try:
            response = requests.get(endpoint)
            http_code = response.status_code
        except requests.exceptions.RequestException as e:
            self.__exception(e.message, http_code=503)

        if http_code != 200:
            self.__exception(WimError.UNREACHABLE, http_code=http_code)
        self.logger.info("Connectivity checked")

    def check_credentials(self):
        endpoint = "{}/checkCredentials".format(self.__wim_url)
        auth = (self.__user, self.__passwd)

        try:
            response = requests.get(endpoint, auth=auth)
            http_code = response.status_code
        except requests.exceptions.RequestException as e:
            self.__exception(e.message, http_code=503)

        if http_code != 200:
            self.__exception(WimError.UNAUTHORIZED, http_code=http_code)
        self.logger.info("Credentials checked")

    # Private functions
    def __exception(self, x, **kwargs):
        http_code = kwargs.get("http_code")
        if hasattr(x, "value"):
            error = x.value
        else:
            error = x
        self.logger.error(error)
        raise WimConnectorError(error, http_code=http_code)

    def __check_service(self, service_type, connection_points, kwargs):
        if service_type not in self.__supported_service_types:
            self.__exception(WimError.SERVICE_TYPE_ERROR, http_code=400)

        if len(connection_points) != 2:
            self.__exception(WimError.CONNECTION_POINTS_SIZE, http_code=400)

        for connection_point in connection_points:
            enc_type = connection_point.get(self.__ENCAPSULATION_TYPE_PARAM)
            if enc_type not in self.__supported_encapsulation_types:
                self.__exception(WimError.ENCAPSULATION_TYPE, http_code=400)

        # Commented out for as long as parameter isn't implemented
        # bandwidth = kwargs.get(self.__BANDWIDTH_PARAM)
        # if not isinstance(bandwidth, int):
            # self.__exception(WimError.BANDWIDTH, http_code=400)

        # Commented out for as long as parameter isn't implemented
        # backup = kwargs.get(self.__BACKUP_PARAM)
        # if not isinstance(backup, bool):
            # self.__exception(WimError.BACKUP, http_code=400)

    def __get_body(self, service_type, connection_points, kwargs):
        port_mapping = self.__config.get("service_endpoint_mapping")
        selected_ports = []
        for connection_point in connection_points:
            endpoint_id = connection_point.get(self.__SERVICE_ENDPOINT_PARAM)
            port = filter(lambda x: x.get(self.__WAN_SERVICE_ENDPOINT_PARAM) == endpoint_id, port_mapping)[0]
            port_info = port.get(self.__WAN_MAPPING_INFO_PARAM)
            selected_ports.append(port_info)
        if service_type == "ELINE (L2)" or service_type == "ELINE":
            service_type = "L2"
        body = {
            "connection_points": [{
                "wan_switch_dpid": selected_ports[0].get(self.__SW_ID_PARAM),
                "wan_switch_port": selected_ports[0].get(self.__SW_PORT_PARAM),
                "wan_vlan": connection_points[0].get(self.__ENCAPSULATION_INFO_PARAM).get(self.__VLAN_PARAM)
            }, {
                "wan_switch_dpid": selected_ports[1].get(self.__SW_ID_PARAM),
                "wan_switch_port": selected_ports[1].get(self.__SW_PORT_PARAM),
                "wan_vlan": connection_points[1].get(self.__ENCAPSULATION_INFO_PARAM).get(self.__VLAN_PARAM)
            }],
            "bandwidth": 100,  # Hardcoded for as long as parameter isn't implemented
            "service_type": service_type,
            "backup": False    # Hardcoded for as long as parameter isn't implemented
        }
        return "body={}".format(json.dumps(body))
