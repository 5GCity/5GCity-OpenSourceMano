# -*- coding: utf-8 -*-

##
# Copyright 2017-2018 VMware Inc.
# This file is part of ETSI OSM
# All Rights Reserved.
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
# contact:  osslegalrouting@vmware.com
##

""" Mock tests for VMware vROPs Mon plugin """

import sys

import json

import logging

import unittest

import mock

import requests

import os

log = logging.getLogger(__name__)

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..",".."))

from osm_mon.plugins.vRealiseOps import mon_plugin_vrops as monPlugin


class TestMonPlugin(unittest.TestCase):
    """Test class for vROPs Mon Plugin class methods"""

    def setUp(self):
        """Setup the tests for plugin_receiver class methods"""
        super(TestMonPlugin, self).setUp()
        self.mon_plugin = monPlugin.MonPlugin()


    def test_get_default_Params_valid_metric_alarm_name(self):
        """Test get default params method"""

        # Mock valid metric_alarm_name and response
        metric_alarm_name = "Average_Memory_Usage_Above_Threshold"
        exepcted_return = {'impact': 'risk', 'cancel_cycles': 2, 'adapter_kind': 'VMWARE', 'repeat': False,
                           'cancel_period': 300, 'alarm_type': 16, 'vrops_alarm': 'Avg_Mem_Usage_Above_Thr',
                           'enabled': True, 'period': 300, 'resource_kind': 'VirtualMachine', 'alarm_subType': 19,
                           'action': 'acknowledge', 'evaluation': 2, 'unit': '%'}

        # call get default param function under test
        actual_return = self.mon_plugin.get_default_Params(metric_alarm_name)

        # verify return value with expected value
        self.assertEqual(exepcted_return, actual_return)


    def test_get_default_Params_invalid_metric_alarm_name(self):
        """Test get default params method-invalid metric alarm"""

        # Mock valid metric_alarm_name and response
        metric_alarm_name = "Invalid_Alarm"
        exepcted_return = {}

        # call get default param function under test
        actual_return = self.mon_plugin.get_default_Params(metric_alarm_name)

        # verify return value with expected value
        self.assertEqual(exepcted_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'post')
    def test_create_symptom_valid_req_response(self, m_post):
        """Test create symptom method-valid request"""

        # Mock valid symptom params and mock responses
        symptom_param = {'threshold_value': 0, 'cancel_cycles': 1, 'adapter_kind_key': 'VMWARE',
                         'resource_kind_key': 'VirtualMachine', 'severity': 'CRITICAL',
                         'symptom_name': u'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                         'operation': 'GT', 'wait_cycles': 1, 'metric_key': 'cpu|usage_average'}

        m_post.return_value.status_code = 201
        m_post.return_value.content = '{"id":"SymptomDefinition-351c23b4-bc3c-4c7b-b4af-1ad90a673c5d",\
                                       "name":"CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4",\
                                       "adapterKindKey":"VMWARE","resourceKindKey":"VirtualMachine","waitCycles":1,\
                                       "cancelCycles":1,"state":{"severity":"CRITICAL","condition":{"type":"CONDITION_HT",\
                                       "key":"cpu|usage_average","operator":"GT","value":"0.0","valueType":"NUMERIC",\
                                       "instanced":false,"thresholdType":"STATIC"}}}'

        exepcted_return = "SymptomDefinition-351c23b4-bc3c-4c7b-b4af-1ad90a673c5d"

        # call create symptom method under test
        actual_return = self.mon_plugin.create_symptom(symptom_param)

        # verify that mocked method is called
        m_post.assert_called()

        # verify return value with expected value
        self.assertEqual(exepcted_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'post')
    def test_create_symptom_invalid_req_response(self, m_post):
        """Test create symptom method-invalid response"""

        # Mock valid symptom params and invalid  mock responses
        symptom_param = {'threshold_value': 0, 'cancel_cycles': 1, 'adapter_kind_key': 'VMWARE',
                         'resource_kind_key': 'VirtualMachine', 'severity': 'CRITICAL',
                         'symptom_name': u'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                         'operation': 'GT', 'wait_cycles': 1, 'metric_key': 'cpu|usage_average'}

        m_post.return_value.status_code = 404
        m_post.return_value.content = '404 Not Found'

        exepcted_return = None

        # call create symptom method under test
        actual_return = self.mon_plugin.create_symptom(symptom_param)

        # verify that mocked method is called
        m_post.assert_called()

        # verify return value with expected value
        self.assertEqual(exepcted_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'post')
    def test_create_symptom_incorrect_data(self, m_post):
        """Test create symptom method-incorrect data"""

        # Mock valid symptom params and invalid  mock responses
        symptom_param = {'threshold_value': 0, 'cancel_cycles': 1, 'adapter_kind_key': 'VMWARE',
                         'resource_kind_key': 'VirtualMachine', 'severity': 'CRITICAL',
                         'symptom_name': u'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                         'operation': 'GT', 'metric_key': 'cpu|usage_average'}

        exepcted_return = None

        # call create symptom method under test
        actual_return = self.mon_plugin.create_symptom(symptom_param)

        # verify that mocked method is not called
        m_post.assert_not_called()

        # verify return value with expected value
        self.assertEqual(exepcted_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'post')
    def test_create_alarm_definition_valid_req_response(self, m_post):
        """Test create alarm definition method-valid response"""

        # Mock valid alarm params and mock responses
        alarm_param = {'description': 'CPU_Utilization_Above_Threshold', 'cancelCycles': 1, 'subType': 19,
                       'waitCycles': 1, 'severity': 'CRITICAL', 'impact': 'risk', 'adapterKindKey': 'VMWARE',
                       'name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4', 'resourceKindKey': 'VirtualMachine',
                       'symptomDefinitionId': u'SymptomDefinition-25278b06-bff8-4409-a141-9b4e064235df', 'type': 16}

        m_post.return_value.status_code = 201
        m_post.return_value.content = '{"id":"AlertDefinition-d4f21e4b-770a-45d6-b298-022eaf489115",\
                                        "name":"CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4",\
                                        "description":"CPU_Utilization_Above_Threshold","adapterKindKey":"VMWARE",\
                                        "resourceKindKey":"VirtualMachine","waitCycles":1,"cancelCycles":1,"type":16,\
                                        "subType":19,"states":[{"severity":"CRITICAL","base-symptom-set":{"type":"SYMPTOM_SET",\
                                        "relation":"SELF","aggregation":"ALL","symptomSetOperator":"AND",\
                                        "symptomDefinitionIds":["SymptomDefinition-25278b06-bff8-4409-a141-9b4e064235df"]},\
                                        "impact":{"impactType":"BADGE","detail":"risk"}}]}'

        exepcted_return = "AlertDefinition-d4f21e4b-770a-45d6-b298-022eaf489115"

        # call create alarm definition method under test
        actual_return = self.mon_plugin.create_alarm_definition(alarm_param)

        # verify that mocked method is called
        m_post.assert_called()

        # verify return value with expected value
        self.assertEqual(exepcted_return, actual_return)


# For testing purpose
#if __name__ == '__main__':
#    unittest.main()

