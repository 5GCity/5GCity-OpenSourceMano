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

"""In the case any error happens when trying to initiate the WIM Connector,
we need a replacement for it, that will throw an error every time we try to
execute any action
"""
import json
from .wimconn import WimConnectorError


class FailingConnector(object):
    """Placeholder for a connector whose incitation failed,
    This place holder will just raise an error every time an action is needed
    from the connector.

    This way we can make sure that all the other parts of the program will work
    but the user will have all the information available to fix the problem.
    """
    def __init__(self, error_msg):
        self.error_msg = error_msg

    def check_credentials(self):
        raise WimConnectorError('Impossible to use WIM:\n' + self.error_msg)

    def get_connectivity_service_status(self, service_uuid, _conn_info=None):
        raise WimConnectorError('Impossible to retrieve status for {}\n\n{}'
                                .format(service_uuid, self.error_msg))

    def create_connectivity_service(self, service_uuid, *args, **kwargs):
        raise WimConnectorError('Impossible to connect {}.\n{}\n{}\n{}'
                                .format(service_uuid, self.error_msg,
                                        json.dumps(args, indent=4),
                                        json.dumps(kwargs, indent=4)))

    def delete_connectivity_service(self, service_uuid, _conn_info=None):
        raise WimConnectorError('Impossible to disconnect {}\n\n{}'
                                .format(service_uuid, self.error_msg))

    def edit_connectivity_service(self, service_uuid, *args, **kwargs):
        raise WimConnectorError('Impossible to change connection {}.\n{}\n'
                                '{}\n{}'
                                .format(service_uuid, self.error_msg,
                                        json.dumps(args, indent=4),
                                        json.dumps(kwargs, indent=4)))

    def clear_all_connectivity_services(self):
        raise WimConnectorError('Impossible to use WIM:\n' + self.error_msg)

    def get_all_active_connectivity_services(self):
        raise WimConnectorError('Impossible to use WIM:\n' + self.error_msg)
