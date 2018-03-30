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

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..",".."))

from osm_mon.plugins.vRealiseOps import mon_plugin_vrops as monPlugin

from pyvcloud.vcd.client import Client


class TestMonPlugin(unittest.TestCase):
    """Test class for vROPs Mon Plugin class methods"""

    def setUp(self):
        """Setup the tests for Mon Plugin class methods"""
        super(TestMonPlugin, self).setUp()
        self.mon_plugin = monPlugin.MonPlugin()
        # create client object
        self.vca = Client('test', verify_ssl_certs=False)
        # create session
        self.session = requests.Session()

    def test_get_default_Params_valid_metric_alarm_name(self):
        """Test get default params method"""

        # Mock valid metric_alarm_name and response
        metric_alarm_name = "Average_Memory_Usage_Above_Threshold"
        expected_return = {'impact': 'risk', 'cancel_cycles': 2, 'adapter_kind': 'VMWARE',
                           'repeat': False,'cancel_period': 300, 'alarm_type': 16,
                           'vrops_alarm': 'Avg_Mem_Usage_Above_Thr','enabled': True, 'period': 300,
                           'resource_kind': 'VirtualMachine', 'alarm_subType': 19,
                           'action': 'acknowledge', 'evaluation': 2, 'unit': '%'}

        # call get default param function under test
        actual_return = self.mon_plugin.get_default_Params(metric_alarm_name)

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    def test_get_default_Params_invalid_metric_alarm_name(self):
        """Test get default params method invalid metric alarm"""

        # Mock valid metric_alarm_name and response
        metric_alarm_name = "Invalid_Alarm"
        expected_return = {}

        # call get default param function under test
        actual_return = self.mon_plugin.get_default_Params(metric_alarm_name)

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'post')
    def test_create_symptom_valid_req_response(self, m_post):
        """Test create symptom method-valid request"""

        # Mock valid symptom params and mock responses
        symptom_param = {'threshold_value': 0, 'cancel_cycles': 1, 'adapter_kind_key': 'VMWARE',
                         'resource_kind_key': 'VirtualMachine', 'severity': 'CRITICAL',
                         'symptom_name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                         'operation': 'GT', 'wait_cycles': 1, 'metric_key': 'cpu|usage_average'}

        m_post.return_value.status_code = 201
        m_post.return_value.content = \
                         '{"id":"SymptomDefinition-351c23b4-bc3c-4c7b-b4af-1ad90a673c5d",\
                         "name":"CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4",\
                         "adapterKindKey":"VMWARE","resourceKindKey":"VirtualMachine","waitCycles":1,\
                         "cancelCycles":1,"state":{"severity":"CRITICAL","condition":{"type":"CONDITION_HT",\
                         "key":"cpu|usage_average","operator":"GT","value":"0.0","valueType":"NUMERIC",\
                         "instanced":false,"thresholdType":"STATIC"}}}'

        expected_return = "SymptomDefinition-351c23b4-bc3c-4c7b-b4af-1ad90a673c5d"

        # call create symptom method under test
        actual_return = self.mon_plugin.create_symptom(symptom_param)

        # verify that mocked method is called
        m_post.assert_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'post')
    def test_create_symptom_invalid_req_response(self, m_post):
        """Test create symptom method-invalid response"""

        # Mock valid symptom params and invalid  mock responses
        symptom_param = {'threshold_value': 0, 'cancel_cycles': 1, 'adapter_kind_key': 'VMWARE',
                         'resource_kind_key': 'VirtualMachine', 'severity': 'CRITICAL',
                         'symptom_name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                         'operation': 'GT', 'wait_cycles': 1, 'metric_key': 'cpu|usage_average'}

        m_post.return_value.status_code = 404
        m_post.return_value.content = '404 Not Found'

        expected_return = None

        # call create symptom method under test
        actual_return = self.mon_plugin.create_symptom(symptom_param)

        # verify that mocked method is called
        m_post.assert_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'post')
    def test_create_symptom_incorrect_data(self, m_post):
        """Test create symptom method-incorrect data"""

        # Mock valid symptom params and invalid  mock responses
        symptom_param = {'threshold_value': 0, 'cancel_cycles': 1, 'adapter_kind_key': 'VMWARE',
                         'resource_kind_key': 'VirtualMachine', 'severity': 'CRITICAL',
                         'symptom_name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                         'operation': 'GT', 'metric_key': 'cpu|usage_average'}

        expected_return = None

        # call create symptom method under test
        actual_return = self.mon_plugin.create_symptom(symptom_param)

        # verify that mocked method is not called
        m_post.assert_not_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'post')
    def test_create_alarm_definition_valid_req_response(self, m_post):
        """Test create alarm definition method-valid response"""

        # Mock valid alarm params and mock responses
        alarm_param = {'description': 'CPU_Utilization_Above_Threshold', 'cancelCycles': 1, 'subType': 19,
                       'waitCycles': 1, 'severity': 'CRITICAL', 'impact': 'risk', 'adapterKindKey': 'VMWARE',
                       'name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                       'resourceKindKey': 'VirtualMachine', 'type': 16,
                       'symptomDefinitionId': 'SymptomDefinition-25278b06-bff8-4409-a141-9b4e064235df'}

        m_post.return_value.status_code = 201
        m_post.return_value.content = \
                       '{"id":"AlertDefinition-d4f21e4b-770a-45d6-b298-022eaf489115",\
                       "name":"CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4",\
                       "description":"CPU_Utilization_Above_Threshold","adapterKindKey":"VMWARE",\
                       "resourceKindKey":"VirtualMachine","waitCycles":1,"cancelCycles":1,"type":16,\
                       "subType":19,"states":[{"severity":"CRITICAL","base-symptom-set":{"type":"SYMPTOM_SET",\
                       "relation":"SELF","aggregation":"ALL","symptomSetOperator":"AND",\
                       "symptomDefinitionIds":["SymptomDefinition-25278b06-bff8-4409-a141-9b4e064235df"]},\
                       "impact":{"impactType":"BADGE","detail":"risk"}}]}'

        expected_return = "AlertDefinition-d4f21e4b-770a-45d6-b298-022eaf489115"

        # call create alarm definition method under test
        actual_return = self.mon_plugin.create_alarm_definition(alarm_param)

        # verify that mocked method is called
        m_post.assert_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'post')
    def test_create_alarm_definition_invalid_req_response(self, m_post):
        """Test create alarm definition method-invalid response"""

        # Mock valid alarm params and mock responses
        alarm_param = {'description': 'CPU_Utilization_Above_Threshold', 'cancelCycles': 1, 'subType': 19,
                       'waitCycles': 1, 'severity': 'CRITICAL', 'impact': 'risk', 'adapterKindKey': 'VMWARE',
                       'name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                       'resourceKindKey': 'VirtualMachine', 'type': 16,
                       'symptomDefinitionId': 'SymptomDefinition-25278b06-bff8-4409-a141-9b4e064235df'}

        m_post.return_value.status_code = 404
        m_post.return_value.content = '404 Not Found'

        expected_return = None

        # call create alarm definition method under test
        actual_return = self.mon_plugin.create_alarm_definition(alarm_param)

        # verify that mocked method is called
        m_post.assert_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'post')
    def test_create_alarm_definition_incorrect_data(self, m_post):
        """Test create alarm definition method-incorrect data"""

        # Mock incorrect alarm param
        alarm_param = {'description': 'CPU_Utilization_Above_Threshold', 'cancelCycles': 1, 'subType': 19,
                       'waitCycles': 1, 'severity': 'CRITICAL', 'impact': 'risk', 'adapterKindKey': 'VMWARE',
                       'symptomDefinitionId': 'SymptomDefinition-25278b06-bff8-4409-a141-9b4e064235df', 'type': 16}
        expected_return = None

        # call create symptom method under test
        actual_return = self.mon_plugin.create_alarm_definition(alarm_param)

        # verify that mocked method is not called
        m_post.assert_not_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.MonPlugin, 'create_alarm_notification_rule')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_resource_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_moref_id')
    @mock.patch.object(monPlugin.MonPlugin, 'create_alarm_definition')
    @mock.patch.object(monPlugin.MonPlugin, 'create_symptom')
    @mock.patch.object(monPlugin.MonPlugin, 'get_alarm_defination_by_name')
    @mock.patch.object(monPlugin.MonPlugin, 'get_default_Params')
    def test_configure_alarm_valid_req(self, m_get_default_Params,\
                                       m_get_alarm_defination_by_name,\
                                       m_create_symptom,\
                                       m_create_alarm_definition,\
                                       m_get_vm_moref_id,\
                                       m_get_vm_resource_id,\
                                       m_create_alarm_notification_rule):
        """Test configure alarm valid request creating alarm"""

        #Mock input configuration dictionary
        config_dict = {'threshold_value': 0, 'severity': 'CRITICAL',
                       'alarm_name': 'CPU_Utilization_Above_Threshold',
                       'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                       'correlation_id': 'e14b203c-6bf2-4e2f-a91c-8c19d2abcdef',
                       'statistic': 'AVERAGE', 'metric_name': 'CPU_UTILIZATION',
                       'operation': 'GT', 'unit': '%',
                       'description': 'CPU_Utilization_Above_Threshold'}

        #symptom parameters to be passed for symptom creation
        symptom_params = {'threshold_value': 0,
                          'cancel_cycles': 1,
                          'adapter_kind_key': 'VMWARE',
                          'resource_kind_key': 'VirtualMachine',
                          'severity': 'CRITICAL',
                          'symptom_name':'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                          'operation': 'GT',
                          'wait_cycles': 1,
                          'metric_key': 'cpu|usage_average'}

        #alarm parameters to  be passed for alarm creation
        alarm_params = {'description': 'CPU_Utilization_Above_Threshold',
                        'cancelCycles': 1, 'subType': 19,
                        'waitCycles': 1, 'severity': 'CRITICAL',
                        'impact': 'risk', 'adapterKindKey': 'VMWARE',
                        'name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                        'resourceKindKey': 'VirtualMachine',
                        'symptomDefinitionId': 'SymptomDefinition-2e8f9ddc-9f7b-4cd6-b85d-7d7fe3a8a804',
                        'type': 16}

        vm_moref_id = 'vm-6626'
        vrops_alarm_name = 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
        alarm_def = 'AlertDefinition-0f3cdcb3-4e1b-4a0b-86d0-66d4b3f65220'
        resource_id = 'ac87622f-b761-40a0-b151-00872a2a456e'
        alarm_def_uuid = '0f3cdcb3-4e1b-4a0b-86d0-66d4b3f65220'

        #Mock default Parameters for alarm & metric configuration
        m_get_default_Params.side_effect = [{'impact': 'risk', 'cancel_cycles': 1,
                                             'adapter_kind': 'VMWARE', 'repeat': False,
                                             'cancel_period': 300, 'alarm_type': 16,
                                             'vrops_alarm': 'CPU_Utilization_Above_Thr',
                                             'enabled': True, 'period': 300,
                                             'resource_kind': 'VirtualMachine',
                                             'alarm_subType': 19, 'action': 'acknowledge',
                                             'evaluation': 1, 'unit': 'msec'},
                                            {'metric_key': 'cpu|usage_average', 'unit': '%'}
                                            ]

        #set mocked function return values
        m_get_alarm_defination_by_name.return_value = []
        m_create_symptom.return_value = 'SymptomDefinition-2e8f9ddc-9f7b-4cd6-b85d-7d7fe3a8a804'
        m_create_alarm_definition.return_value = 'AlertDefinition-0f3cdcb3-4e1b-4a0b-86d0-66d4b3f65220'
        m_get_vm_moref_id.return_value = vm_moref_id
        m_get_vm_resource_id.return_value = 'ac87622f-b761-40a0-b151-00872a2a456e'
        m_create_alarm_notification_rule.return_value = 'f37900e7-dd01-4383-b84c-08f519530d71'

        #Call configure_alarm method under test
        return_value = self.mon_plugin.configure_alarm(config_dict)

        #Verify that mocked methods are called with correct parameters
        self.assertEqual(m_get_default_Params.call_count, 2)
        m_get_alarm_defination_by_name.assert_called_with(vrops_alarm_name)
        m_create_symptom.assert_called_with(symptom_params)
        m_create_alarm_definition.assert_called_with(alarm_params)
        m_get_vm_moref_id.assert_called_with(config_dict['resource_uuid'])
        m_get_vm_resource_id.assert_called_with(vm_moref_id)
        m_create_alarm_notification_rule.assert_called_with(vrops_alarm_name, alarm_def, resource_id)

        #Verify return value with expected value of alarm_def_uuid
        self.assertEqual(return_value, alarm_def_uuid)


    @mock.patch.object(monPlugin.MonPlugin, 'create_alarm_notification_rule')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_resource_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_moref_id')
    @mock.patch.object(monPlugin.MonPlugin, 'create_alarm_definition')
    @mock.patch.object(monPlugin.MonPlugin, 'create_symptom')
    @mock.patch.object(monPlugin.MonPlugin, 'get_alarm_defination_by_name')
    @mock.patch.object(monPlugin.MonPlugin, 'get_default_Params')
    def test_configure_alarm_invalid_alarm_name_req(self, m_get_default_Params,\
                                       m_get_alarm_defination_by_name,\
                                       m_create_symptom,\
                                       m_create_alarm_definition,\
                                       m_get_vm_moref_id,\
                                       m_get_vm_resource_id,\
                                       m_create_alarm_notification_rule):
        """Test configure alarm invalid test: for invalid alarm name"""

        #Mock input configuration dictionary
        config_dict = {'threshold_value': 0, 'severity': 'CRITICAL',
                       'alarm_name': 'CPU_Utilization_Above_Threshold',
                       'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                       'correlation_id': 'e14b203c-6bf2-4e2f-a91c-8c19d2abcdef',
                       'statistic': 'AVERAGE', 'metric_name': 'CPU_UTILIZATION',
                       'operation': 'GT', 'unit': '%',
                       'description': 'CPU_Utilization_Above_Threshold'}

        alarm_def_uuid = None

        #Mock default Parameters return value to None
        m_get_default_Params.return_value = {}

        #Call configure_alarm method under test
        return_value = self.mon_plugin.configure_alarm(config_dict)

        #Verify that mocked methods are called with correct parameters
        m_get_default_Params.assert_called_once()
        m_get_alarm_defination_by_name.assert_not_called()
        m_create_symptom.assert_not_called()
        m_create_alarm_definition.assert_not_called()
        m_get_vm_moref_id.assert_not_called()
        m_get_vm_resource_id.assert_not_called()
        m_create_alarm_notification_rule.assert_not_called()

        #Verify return value with expected value i.e. None
        self.assertEqual(return_value, alarm_def_uuid)


    @mock.patch.object(monPlugin.MonPlugin, 'create_alarm_notification_rule')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_resource_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_moref_id')
    @mock.patch.object(monPlugin.MonPlugin, 'create_alarm_definition')
    @mock.patch.object(monPlugin.MonPlugin, 'create_symptom')
    @mock.patch.object(monPlugin.MonPlugin, 'get_alarm_defination_by_name')
    @mock.patch.object(monPlugin.MonPlugin, 'get_default_Params')
    def test_configure_alarm_invalid_metric_name_req(self, m_get_default_Params,\
                                       m_get_alarm_defination_by_name,\
                                       m_create_symptom,\
                                       m_create_alarm_definition,\
                                       m_get_vm_moref_id,\
                                       m_get_vm_resource_id,\
                                       m_create_alarm_notification_rule):
        """Test configure alarm invalid test: for invalid metric name"""

        #Mock input configuration dictionary
        config_dict = {'threshold_value': 0, 'severity': 'CRITICAL',
                       'alarm_name': 'CPU_Utilization_Above_Threshold',
                       'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                       'correlation_id': 'e14b203c-6bf2-4e2f-a91c-8c19d2abcdef',
                       'statistic': 'AVERAGE', 'metric_name': 'CPU_UTILIZATION',
                       'operation': 'GT', 'unit': '%',
                       'description': 'CPU_Utilization_Above_Threshold'}

        alarm_def_uuid = None

        #Mock default Parameters return values for metrics to None
        m_get_default_Params.side_effect = [{'impact': 'risk', 'cancel_cycles': 1,
                                             'adapter_kind': 'VMWARE', 'repeat': False,
                                             'cancel_period': 300, 'alarm_type': 16,
                                             'vrops_alarm': 'CPU_Utilization_Above_Thr',
                                             'enabled': True, 'period': 300,
                                             'resource_kind': 'VirtualMachine',
                                             'alarm_subType': 19, 'action': 'acknowledge',
                                             'evaluation': 1, 'unit': 'msec'},
                                            {}
                                            ]

        #Call configure_alarm method under test
        return_value = self.mon_plugin.configure_alarm(config_dict)

        #Verify that mocked methods are called with correct parameters
        self.assertEqual(m_get_default_Params.call_count, 2)
        m_get_alarm_defination_by_name.assert_not_called()
        m_create_symptom.assert_not_called()
        m_create_alarm_definition.assert_not_called()
        m_get_vm_moref_id.assert_not_called()
        m_get_vm_resource_id.assert_not_called()
        m_create_alarm_notification_rule.assert_not_called()

        #Verify return value with expected value i.e. None
        self.assertEqual(return_value, alarm_def_uuid)

    @mock.patch.object(monPlugin.MonPlugin, 'create_alarm_notification_rule')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_resource_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_moref_id')
    @mock.patch.object(monPlugin.MonPlugin, 'create_alarm_definition')
    @mock.patch.object(monPlugin.MonPlugin, 'create_symptom')
    @mock.patch.object(monPlugin.MonPlugin, 'get_alarm_defination_by_name')
    @mock.patch.object(monPlugin.MonPlugin, 'get_default_Params')
    def test_configure_alarm_invalid_already_exists(self, m_get_default_Params,\
                                       m_get_alarm_defination_by_name,\
                                       m_create_symptom,\
                                       m_create_alarm_definition,\
                                       m_get_vm_moref_id,\
                                       m_get_vm_resource_id,\
                                       m_create_alarm_notification_rule):
        """Test configure alarm invalid test: for alarm that already exists"""

        #Mock input configuration dictionary
        config_dict = {'threshold_value': 0, 'severity': 'CRITICAL',
                       'alarm_name': 'CPU_Utilization_Above_Threshold',
                       'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                       'correlation_id': 'e14b203c-6bf2-4e2f-a91c-8c19d2abcdef',
                       'statistic': 'AVERAGE', 'metric_name': 'CPU_UTILIZATION',
                       'operation': 'GT', 'unit': '%',
                       'description': 'CPU_Utilization_Above_Threshold'}

        vrops_alarm_name = 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
        alarm_def_uuid = None

        #Mock default Parameters for alarm & metric configuration
        m_get_default_Params.side_effect = [{'impact': 'risk', 'cancel_cycles': 1,
                                             'adapter_kind': 'VMWARE', 'repeat': False,
                                             'cancel_period': 300, 'alarm_type': 16,
                                             'vrops_alarm': 'CPU_Utilization_Above_Thr',
                                             'enabled': True, 'period': 300,
                                             'resource_kind': 'VirtualMachine',
                                             'alarm_subType': 19, 'action': 'acknowledge',
                                             'evaluation': 1, 'unit': 'msec'},
                                            {'metric_key': 'cpu|usage_average', 'unit': '%'}
                                            ]
        #set mocked function return value
        m_get_alarm_defination_by_name.return_value = ['mocked_alarm_CPU_Utilization_Above_Thr']


        #Call configure_alarm method under test
        return_value = self.mon_plugin.configure_alarm(config_dict)

        #Verify that mocked methods are called with correct parameters
        self.assertEqual(m_get_default_Params.call_count, 2)
        m_get_alarm_defination_by_name.assert_called_with(vrops_alarm_name)
        m_create_symptom.assert_not_called()
        m_create_alarm_definition.assert_not_called()
        m_get_vm_moref_id.assert_not_called()
        m_get_vm_resource_id.assert_not_called()
        m_create_alarm_notification_rule.assert_not_called()

        #Verify return value with expected value of alarm_def_uuid
        self.assertEqual(return_value, alarm_def_uuid)


    @mock.patch.object(monPlugin.MonPlugin, 'create_alarm_notification_rule')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_resource_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_moref_id')
    @mock.patch.object(monPlugin.MonPlugin, 'create_alarm_definition')
    @mock.patch.object(monPlugin.MonPlugin, 'create_symptom')
    @mock.patch.object(monPlugin.MonPlugin, 'get_alarm_defination_by_name')
    @mock.patch.object(monPlugin.MonPlugin, 'get_default_Params')
    def test_configure_alarm_failed_symptom_creation(self, m_get_default_Params,\
                                       m_get_alarm_defination_by_name,\
                                       m_create_symptom,\
                                       m_create_alarm_definition,\
                                       m_get_vm_moref_id,\
                                       m_get_vm_resource_id,\
                                       m_create_alarm_notification_rule):
        """Test configure alarm: failed to create symptom"""

        #Mock input configuration dictionary
        config_dict = {'threshold_value': 0, 'severity': 'CRITICAL',
                       'alarm_name': 'CPU_Utilization_Above_Threshold',
                       'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                       'correlation_id': 'e14b203c-6bf2-4e2f-a91c-8c19d2abcdef',
                       'statistic': 'AVERAGE', 'metric_name': 'CPU_UTILIZATION',
                       'operation': 'GT', 'unit': '%',
                       'description': 'CPU_Utilization_Above_Threshold'}

        #symptom parameters to be passed for symptom creation
        symptom_params = {'threshold_value': 0,
                          'cancel_cycles': 1,
                          'adapter_kind_key': 'VMWARE',
                          'resource_kind_key': 'VirtualMachine',
                          'severity': 'CRITICAL',
                          'symptom_name':'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                          'operation': 'GT',
                          'wait_cycles': 1,
                          'metric_key': 'cpu|usage_average'}
        vrops_alarm_name = 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
        alarm_def_uuid = None

        #Mock default Parameters for alarm & metric configuration
        m_get_default_Params.side_effect = [{'impact': 'risk', 'cancel_cycles': 1,
                                             'adapter_kind': 'VMWARE', 'repeat': False,
                                             'cancel_period': 300, 'alarm_type': 16,
                                             'vrops_alarm': 'CPU_Utilization_Above_Thr',
                                             'enabled': True, 'period': 300,
                                             'resource_kind': 'VirtualMachine',
                                             'alarm_subType': 19, 'action': 'acknowledge',
                                             'evaluation': 1, 'unit': 'msec'},
                                            {'metric_key': 'cpu|usage_average', 'unit': '%'}
                                            ]
        #set mocked function return values
        m_get_alarm_defination_by_name.return_value = []
        m_create_symptom.return_value = None

        #Call configure_alarm method under test
        return_value = self.mon_plugin.configure_alarm(config_dict)

        #Verify that mocked methods are called with correct parameters
        self.assertEqual(m_get_default_Params.call_count, 2)
        m_get_alarm_defination_by_name.assert_called_with(vrops_alarm_name)
        m_create_symptom.assert_called_with(symptom_params)
        m_create_alarm_definition.assert_not_called()
        m_get_vm_moref_id.assert_not_called()
        m_get_vm_resource_id.assert_not_called()
        m_create_alarm_notification_rule.assert_not_called()

        #Verify return value with expected value of alarm_def_uuid
        self.assertEqual(return_value, alarm_def_uuid)


    @mock.patch.object(monPlugin.MonPlugin, 'create_alarm_notification_rule')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_resource_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_moref_id')
    @mock.patch.object(monPlugin.MonPlugin, 'create_alarm_definition')
    @mock.patch.object(monPlugin.MonPlugin, 'create_symptom')
    @mock.patch.object(monPlugin.MonPlugin, 'get_alarm_defination_by_name')
    @mock.patch.object(monPlugin.MonPlugin, 'get_default_Params')
    def test_configure_alarm_failed_alert_creation(self, m_get_default_Params,\
                                       m_get_alarm_defination_by_name,\
                                       m_create_symptom,\
                                       m_create_alarm_definition,\
                                       m_get_vm_moref_id,\
                                       m_get_vm_resource_id,\
                                       m_create_alarm_notification_rule):
        """Test configure alarm: failed to create alert in vROPs"""

        #Mock input configuration dictionary
        config_dict = {'threshold_value': 0, 'severity': 'CRITICAL',
                       'alarm_name': 'CPU_Utilization_Above_Threshold',
                       'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                       'correlation_id': 'e14b203c-6bf2-4e2f-a91c-8c19d2abcdef',
                       'statistic': 'AVERAGE', 'metric_name': 'CPU_UTILIZATION',
                       'operation': 'GT', 'unit': '%',
                       'description': 'CPU_Utilization_Above_Threshold'}

        #symptom parameters to be passed for symptom creation
        symptom_params = {'threshold_value': 0,
                          'cancel_cycles': 1,
                          'adapter_kind_key': 'VMWARE',
                          'resource_kind_key': 'VirtualMachine',
                          'severity': 'CRITICAL',
                          'symptom_name':'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                          'operation': 'GT',
                          'wait_cycles': 1,
                          'metric_key': 'cpu|usage_average'}

        #alarm parameters to  be passed for alarm creation
        alarm_params = {'description': 'CPU_Utilization_Above_Threshold',
                        'cancelCycles': 1, 'subType': 19,
                        'waitCycles': 1, 'severity': 'CRITICAL',
                        'impact': 'risk', 'adapterKindKey': 'VMWARE',
                        'name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                        'resourceKindKey': 'VirtualMachine',
                        'symptomDefinitionId': 'SymptomDefinition-2e8f9ddc-9f7b-4cd6-b85d-7d7fe3a8a804',
                        'type': 16}

        vrops_alarm_name = 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
        alarm_def_uuid = None

        #Mock default Parameters for alarm & metric configuration
        m_get_default_Params.side_effect = [{'impact': 'risk', 'cancel_cycles': 1,
                                             'adapter_kind': 'VMWARE', 'repeat': False,
                                             'cancel_period': 300, 'alarm_type': 16,
                                             'vrops_alarm': 'CPU_Utilization_Above_Thr',
                                             'enabled': True, 'period': 300,
                                             'resource_kind': 'VirtualMachine',
                                             'alarm_subType': 19, 'action': 'acknowledge',
                                             'evaluation': 1, 'unit': 'msec'},
                                            {'metric_key': 'cpu|usage_average', 'unit': '%'}
                                            ]
        #set mocked function return values
        m_get_alarm_defination_by_name.return_value = []
        m_create_symptom.return_value = 'SymptomDefinition-2e8f9ddc-9f7b-4cd6-b85d-7d7fe3a8a804'
        m_create_alarm_definition.return_value = None

        #Call configure_alarm method under test
        return_value = self.mon_plugin.configure_alarm(config_dict)

        #Verify that mocked methods are called with correct parameters
        self.assertEqual(m_get_default_Params.call_count, 2)
        m_get_alarm_defination_by_name.assert_called_with(vrops_alarm_name)
        m_create_symptom.assert_called_with(symptom_params)
        m_create_alarm_definition.assert_called_with(alarm_params)
        m_get_vm_moref_id.assert_not_called()
        m_get_vm_resource_id.assert_not_called()
        m_create_alarm_notification_rule.assert_not_called()

        #Verify return value with expected value of alarm_def_uuid
        self.assertEqual(return_value, alarm_def_uuid)


    @mock.patch.object(monPlugin.MonPlugin, 'create_alarm_notification_rule')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_resource_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_moref_id')
    @mock.patch.object(monPlugin.MonPlugin, 'create_alarm_definition')
    @mock.patch.object(monPlugin.MonPlugin, 'create_symptom')
    @mock.patch.object(monPlugin.MonPlugin, 'get_alarm_defination_by_name')
    @mock.patch.object(monPlugin.MonPlugin, 'get_default_Params')
    def test_configure_alarm_failed_to_get_vm_moref_id(self, m_get_default_Params,\
                                       m_get_alarm_defination_by_name,\
                                       m_create_symptom,\
                                       m_create_alarm_definition,\
                                       m_get_vm_moref_id,\
                                       m_get_vm_resource_id,\
                                       m_create_alarm_notification_rule):
        """Test configure alarm: failed to get vm_moref_id"""

        #Mock input configuration dictionary
        config_dict = {'threshold_value': 0, 'severity': 'CRITICAL',
                       'alarm_name': 'CPU_Utilization_Above_Threshold',
                       'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                       'correlation_id': 'e14b203c-6bf2-4e2f-a91c-8c19d2abcdef',
                       'statistic': 'AVERAGE', 'metric_name': 'CPU_UTILIZATION',
                       'operation': 'GT', 'unit': '%',
                       'description': 'CPU_Utilization_Above_Threshold'}

        #symptom parameters to be passed for symptom creation
        symptom_params = {'threshold_value': 0,
                          'cancel_cycles': 1,
                          'adapter_kind_key': 'VMWARE',
                          'resource_kind_key': 'VirtualMachine',
                          'severity': 'CRITICAL',
                          'symptom_name':'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                          'operation': 'GT',
                          'wait_cycles': 1,
                          'metric_key': 'cpu|usage_average'}

        #alarm parameters to  be passed for alarm creation
        alarm_params = {'description': 'CPU_Utilization_Above_Threshold',
                        'cancelCycles': 1, 'subType': 19,
                        'waitCycles': 1, 'severity': 'CRITICAL',
                        'impact': 'risk', 'adapterKindKey': 'VMWARE',
                        'name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                        'resourceKindKey': 'VirtualMachine',
                        'symptomDefinitionId': 'SymptomDefinition-2e8f9ddc-9f7b-4cd6-b85d-7d7fe3a8a804',
                        'type': 16}

        vrops_alarm_name = 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
        alarm_def_uuid = None

        #Mock default Parameters for alarm & metric configuration
        m_get_default_Params.side_effect = [{'impact': 'risk', 'cancel_cycles': 1,
                                             'adapter_kind': 'VMWARE', 'repeat': False,
                                             'cancel_period': 300, 'alarm_type': 16,
                                             'vrops_alarm': 'CPU_Utilization_Above_Thr',
                                             'enabled': True, 'period': 300,
                                             'resource_kind': 'VirtualMachine',
                                             'alarm_subType': 19, 'action': 'acknowledge',
                                             'evaluation': 1, 'unit': 'msec'},
                                            {'metric_key': 'cpu|usage_average', 'unit': '%'}
                                            ]
        #set mocked function return values
        m_get_alarm_defination_by_name.return_value = []
        m_create_symptom.return_value = 'SymptomDefinition-2e8f9ddc-9f7b-4cd6-b85d-7d7fe3a8a804'
        m_create_alarm_definition.return_value = 'AlertDefinition-0f3cdcb3-4e1b-4a0b-86d0-66d4b3f65220'
        m_get_vm_moref_id.return_value = None

        #Call configure_alarm method under test
        return_value = self.mon_plugin.configure_alarm(config_dict)

        #Verify that mocked methods are called with correct parameters
        self.assertEqual(m_get_default_Params.call_count, 2)
        m_get_alarm_defination_by_name.assert_called_with(vrops_alarm_name)
        m_create_symptom.assert_called_with(symptom_params)
        m_create_alarm_definition.assert_called_with(alarm_params)
        m_get_vm_moref_id.assert_called_with(config_dict['resource_uuid'])
        m_get_vm_resource_id.assert_not_called()
        m_create_alarm_notification_rule.assert_not_called()

        #Verify return value with expected value of alarm_def_uuid
        self.assertEqual(return_value, alarm_def_uuid)


    @mock.patch.object(monPlugin.MonPlugin, 'create_alarm_notification_rule')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_resource_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_moref_id')
    @mock.patch.object(monPlugin.MonPlugin, 'create_alarm_definition')
    @mock.patch.object(monPlugin.MonPlugin, 'create_symptom')
    @mock.patch.object(monPlugin.MonPlugin, 'get_alarm_defination_by_name')
    @mock.patch.object(monPlugin.MonPlugin, 'get_default_Params')
    def test_configure_alarm_failed_to_get_vm_resource_id(self, m_get_default_Params,\
                                       m_get_alarm_defination_by_name,\
                                       m_create_symptom,\
                                       m_create_alarm_definition,\
                                       m_get_vm_moref_id,\
                                       m_get_vm_resource_id,\
                                       m_create_alarm_notification_rule):
        """Test configure alarm: failed to get vm resource_id"""

        #Mock input configuration dictionary
        config_dict = {'threshold_value': 0, 'severity': 'CRITICAL',
                       'alarm_name': 'CPU_Utilization_Above_Threshold',
                       'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                       'correlation_id': 'e14b203c-6bf2-4e2f-a91c-8c19d2abcdef',
                       'statistic': 'AVERAGE', 'metric_name': 'CPU_UTILIZATION',
                       'operation': 'GT', 'unit': '%',
                       'description': 'CPU_Utilization_Above_Threshold'}

        #symptom parameters to be passed for symptom creation
        symptom_params = {'threshold_value': 0,
                          'cancel_cycles': 1,
                          'adapter_kind_key': 'VMWARE',
                          'resource_kind_key': 'VirtualMachine',
                          'severity': 'CRITICAL',
                          'symptom_name':'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                          'operation': 'GT',
                          'wait_cycles': 1,
                          'metric_key': 'cpu|usage_average'}

        #alarm parameters to  be passed for alarm creation
        alarm_params = {'description': 'CPU_Utilization_Above_Threshold',
                        'cancelCycles': 1, 'subType': 19,
                        'waitCycles': 1, 'severity': 'CRITICAL',
                        'impact': 'risk', 'adapterKindKey': 'VMWARE',
                        'name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                        'resourceKindKey': 'VirtualMachine',
                        'symptomDefinitionId': 'SymptomDefinition-2e8f9ddc-9f7b-4cd6-b85d-7d7fe3a8a804',
                        'type': 16}

        vrops_alarm_name = 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
        vm_moref_id = 'vm-6626'
        alarm_def_uuid = None

        #Mock default Parameters for alarm & metric configuration
        m_get_default_Params.side_effect = [{'impact': 'risk', 'cancel_cycles': 1,
                                             'adapter_kind': 'VMWARE', 'repeat': False,
                                             'cancel_period': 300, 'alarm_type': 16,
                                             'vrops_alarm': 'CPU_Utilization_Above_Thr',
                                             'enabled': True, 'period': 300,
                                             'resource_kind': 'VirtualMachine',
                                             'alarm_subType': 19, 'action': 'acknowledge',
                                             'evaluation': 1, 'unit': 'msec'},
                                            {'metric_key': 'cpu|usage_average', 'unit': '%'}
                                            ]
        #set mocked function return values
        m_get_alarm_defination_by_name.return_value = []
        m_create_symptom.return_value = 'SymptomDefinition-2e8f9ddc-9f7b-4cd6-b85d-7d7fe3a8a804'
        m_create_alarm_definition.return_value = 'AlertDefinition-0f3cdcb3-4e1b-4a0b-86d0-66d4b3f65220'
        m_get_vm_moref_id.return_value = vm_moref_id
        m_get_vm_resource_id.return_value = None

        #Call configure_alarm method under test
        return_value = self.mon_plugin.configure_alarm(config_dict)

        #Verify that mocked methods are called with correct parameters
        self.assertEqual(m_get_default_Params.call_count, 2)
        m_get_alarm_defination_by_name.assert_called_with(vrops_alarm_name)
        m_create_symptom.assert_called_with(symptom_params)
        m_create_alarm_definition.assert_called_with(alarm_params)
        m_get_vm_moref_id.assert_called_with(config_dict['resource_uuid'])
        m_get_vm_resource_id.assert_called_with(vm_moref_id)
        m_create_alarm_notification_rule.assert_not_called()

        #Verify return value with expected value of alarm_def_uuid
        self.assertEqual(return_value, alarm_def_uuid)


    @mock.patch.object(monPlugin.MonPlugin, 'create_alarm_notification_rule')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_resource_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_moref_id')
    @mock.patch.object(monPlugin.MonPlugin, 'create_alarm_definition')
    @mock.patch.object(monPlugin.MonPlugin, 'create_symptom')
    @mock.patch.object(monPlugin.MonPlugin, 'get_alarm_defination_by_name')
    @mock.patch.object(monPlugin.MonPlugin, 'get_default_Params')
    def test_configure_alarm_failed_to_create_alarm_notification_rule(self, m_get_default_Params,\
                                       m_get_alarm_defination_by_name,\
                                       m_create_symptom,\
                                       m_create_alarm_definition,\
                                       m_get_vm_moref_id,\
                                       m_get_vm_resource_id,\
                                       m_create_alarm_notification_rule):
        """Test configure alarm: failed to create alarm notification rule"""

        #Mock input configuration dictionary
        config_dict = {'threshold_value': 0, 'severity': 'CRITICAL',
                       'alarm_name': 'CPU_Utilization_Above_Threshold',
                       'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                       'correlation_id': 'e14b203c-6bf2-4e2f-a91c-8c19d2abcdef',
                       'statistic': 'AVERAGE', 'metric_name': 'CPU_UTILIZATION',
                       'operation': 'GT', 'unit': '%',
                       'description': 'CPU_Utilization_Above_Threshold'}

        #symptom parameters to be passed for symptom creation
        symptom_params = {'threshold_value': 0,
                          'cancel_cycles': 1,
                          'adapter_kind_key': 'VMWARE',
                          'resource_kind_key': 'VirtualMachine',
                          'severity': 'CRITICAL',
                          'symptom_name':'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                          'operation': 'GT',
                          'wait_cycles': 1,
                          'metric_key': 'cpu|usage_average'}

        #alarm parameters to  be passed for alarm creation
        alarm_params = {'description': 'CPU_Utilization_Above_Threshold',
                        'cancelCycles': 1, 'subType': 19,
                        'waitCycles': 1, 'severity': 'CRITICAL',
                        'impact': 'risk', 'adapterKindKey': 'VMWARE',
                        'name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                        'resourceKindKey': 'VirtualMachine',
                        'symptomDefinitionId': 'SymptomDefinition-2e8f9ddc-9f7b-4cd6-b85d-7d7fe3a8a804',
                        'type': 16}

        vrops_alarm_name = 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
        vm_moref_id = 'vm-6626'
        alarm_def = 'AlertDefinition-0f3cdcb3-4e1b-4a0b-86d0-66d4b3f65220'
        resource_id = 'ac87622f-b761-40a0-b151-00872a2a456e'
        alarm_def_uuid = None

        #Mock default Parameters for alarm & metric configuration
        m_get_default_Params.side_effect = [{'impact': 'risk', 'cancel_cycles': 1,
                                             'adapter_kind': 'VMWARE', 'repeat': False,
                                             'cancel_period': 300, 'alarm_type': 16,
                                             'vrops_alarm': 'CPU_Utilization_Above_Thr',
                                             'enabled': True, 'period': 300,
                                             'resource_kind': 'VirtualMachine',
                                             'alarm_subType': 19, 'action': 'acknowledge',
                                             'evaluation': 1, 'unit': 'msec'},
                                            {'metric_key': 'cpu|usage_average', 'unit': '%'}
                                            ]
        #set mocked function return values
        m_get_alarm_defination_by_name.return_value = []
        m_create_symptom.return_value = 'SymptomDefinition-2e8f9ddc-9f7b-4cd6-b85d-7d7fe3a8a804'
        m_create_alarm_definition.return_value = 'AlertDefinition-0f3cdcb3-4e1b-4a0b-86d0-66d4b3f65220'
        m_get_vm_moref_id.return_value = vm_moref_id
        m_get_vm_resource_id.return_value = 'ac87622f-b761-40a0-b151-00872a2a456e'
        m_create_alarm_notification_rule.return_value = None

        #Call configure_alarm method under test
        return_value = self.mon_plugin.configure_alarm(config_dict)

        #Verify that mocked methods are called with correct parameters
        self.assertEqual(m_get_default_Params.call_count, 2)
        m_get_alarm_defination_by_name.assert_called_with(vrops_alarm_name)
        m_create_symptom.assert_called_with(symptom_params)
        m_create_alarm_definition.assert_called_with(alarm_params)
        m_get_vm_moref_id.assert_called_with(config_dict['resource_uuid'])
        m_get_vm_resource_id.assert_called_with(vm_moref_id)
        m_create_alarm_notification_rule.assert_called_with(vrops_alarm_name, alarm_def, resource_id)

        #Verify return value with expected value of alarm_def_uuid
        self.assertEqual(return_value, alarm_def_uuid)


    @mock.patch.object(monPlugin.requests, 'get')
    def test_get_alarm_defination_details_valid_rest_req_response(self, m_get):
        """Test get_alarm_defination_details: For a valid REST request response"""

        alarm_uuid = '9a6d8a14-9f25-4d81-bf91-4d773497444d'

        #Set mocked function's return values
        m_get.return_value.status_code = 200
        m_get.return_value.content = '{"id":"AlertDefinition-9a6d8a14-9f25-4d81-bf91-4d773497444d",\
                            "name":"CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4",\
                            "description":"CPU_Utilization_Above_Threshold",\
                            "adapterKindKey":"VMWARE","resourceKindKey":"VirtualMachine",\
                            "waitCycles":1,"cancelCycles":1,"type":16,"subType":19,\
                            "states":[{"severity":"CRITICAL","base-symptom-set":{"type":"SYMPTOM_SET",\
                            "relation":"SELF","aggregation":"ALL","symptomSetOperator":"AND",\
                            "symptomDefinitionIds":["SymptomDefinition-bcc2cb36-a67b-4deb-bcd3-9b5884973278"]},\
                            "impact":{"impactType":"BADGE","detail":"risk"}}]}'

        expected_alarm_details = {'adapter_kind': 'VMWARE',
                         'symptom_definition_id': 'SymptomDefinition-bcc2cb36-a67b-4deb-bcd3-9b5884973278',
                         'alarm_name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                         'alarm_id': 'AlertDefinition-9a6d8a14-9f25-4d81-bf91-4d773497444d',
                         'resource_kind': 'VirtualMachine', 'type': 16, 'sub_type': 19}

        expected_alarm_details_json = {'states':
                                       [{'impact':
                                         {'impactType':'BADGE', 'detail':'risk'},'severity':'CRITICAL',
                                         'base-symptom-set': {'symptomDefinitionIds':\
                                         ['SymptomDefinition-bcc2cb36-a67b-4deb-bcd3-9b5884973278'],
                                         'relation': 'SELF', 'type': 'SYMPTOM_SET',
                                         'aggregation':'ALL', 'symptomSetOperator': 'AND'}}],
                                       'adapterKindKey': 'VMWARE',
                                       'description': 'CPU_Utilization_Above_Threshold',
                                       'type': 16, 'cancelCycles': 1, 'resourceKindKey': 'VirtualMachine',
                                       'subType': 19, 'waitCycles': 1,
                                       'id': 'AlertDefinition-9a6d8a14-9f25-4d81-bf91-4d773497444d',
                                       'name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4'}

        #Call get_alarm_defination_details method under test
        alarm_details_json, alarm_details = self.mon_plugin.get_alarm_defination_details(alarm_uuid)

        #Verify that mocked method is called
        m_get.assert_called()

        #Verify return value with expected value
        self.assertEqual(expected_alarm_details, alarm_details)
        self.assertEqual(expected_alarm_details_json, alarm_details_json)


    @mock.patch.object(monPlugin.requests, 'get')
    def test_get_alarm_defination_details_invalid_rest_req_response(self, m_get):
        """Test get_alarm_defination_details: For an invalid REST request response"""

        alarm_uuid = '9a6d8a14-9f25-4d81-bf91-4d773497444d'

        #Set mocked function's return values
        m_get.return_value.status_code = 404
        m_get.return_value.content = '{"message": "No such AlertDefinition - \
                                        AlertDefinition-9a6d8a14-9f25-4d81-bf91-4d773497444.",\
                                        "httpStatusCode": 404,"apiErrorCode": 404}'

        expected_alarm_details = None
        expected_alarm_details_json = None

        #Call get_alarm_defination_details method under test
        alarm_details_json, alarm_details = self.mon_plugin.get_alarm_defination_details(alarm_uuid)

        #verify that mocked method is called
        m_get.assert_called()

        #Verify return value with expected value
        self.assertEqual(expected_alarm_details, alarm_details)
        self.assertEqual(expected_alarm_details_json, alarm_details_json)


    @mock.patch.object(monPlugin.requests, 'get')
    def test_get_alarm_defination_by_name_valid_rest_req_response(self, m_get):
        """Test get_alarm_defination_by_name: For a valid REST request response"""

        alarm_name = 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4'

        #Set mocked function's return values
        m_get.return_value.status_code = 200
        m_get.return_value.content = '{"pageInfo": {"totalCount": 1,"page": 0,"pageSize": 1000},\
                                    "links": [\
                                        {"href": "/suite-api/api/alertdefinitions?page=0&amp;pageSize=1000",\
                                        "rel": "SELF","name": "current"},\
                                        {"href": "/suite-api/api/alertdefinitions?page=0&amp;pageSize=1000",\
                                         "rel": "RELATED","name": "first"},\
                                        {"href": "/suite-api/api/alertdefinitions?page=0&amp;pageSize=1000",\
                                         "rel": "RELATED","name": "last"}],\
                                    "alertDefinitions": [{\
                                        "id": "AlertDefinition-9a6d8a14-9f25-4d81-bf91-4d773497444d",\
                                        "name": "CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4",\
                                        "description": "CPU_Utilization_Above_Threshold",\
                                        "adapterKindKey": "VMWARE","resourceKindKey": "VirtualMachine",\
                                        "waitCycles": 1,"cancelCycles": 1,"type": 16,"subType": 19,\
                                        "states": [{"impact": {"impactType": "BADGE","detail": "risk"},\
                                            "severity": "CRITICAL",\
                                            "base-symptom-set": {"type": "SYMPTOM_SET",\
                                            "relation": "SELF","aggregation": "ALL",\
                                            "symptomSetOperator": "AND",\
                                            "symptomDefinitionIds": [\
                                            "SymptomDefinition-bcc2cb36-a67b-4deb-bcd3-9b5884973278"]}}]\
                                        }]}'

        #Expected return match list
        Exp_alert_match_list = [{'states':
                                   [{'impact': {'impactType': 'BADGE', 'detail': 'risk'},
                                     'severity': 'CRITICAL',
                                     'base-symptom-set': {
                                         'symptomDefinitionIds': \
                                         ['SymptomDefinition-bcc2cb36-a67b-4deb-bcd3-9b5884973278'],
                                         'relation': 'SELF',
                                         'type': 'SYMPTOM_SET',
                                         'aggregation': 'ALL',
                                         'symptomSetOperator': 'AND'}
                                     }],
                                   'adapterKindKey': 'VMWARE',
                                   'description': 'CPU_Utilization_Above_Threshold',
                                   'type': 16,
                                   'cancelCycles': 1,
                                   'resourceKindKey': 'VirtualMachine',
                                   'subType': 19, 'waitCycles': 1,
                                   'id': 'AlertDefinition-9a6d8a14-9f25-4d81-bf91-4d773497444d',
                                   'name': \
                                   'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
                                   }]

        #Call get_alarm_defination_by_name method under test
        alert_match_list = self.mon_plugin.get_alarm_defination_by_name(alarm_name)

        #Verify that mocked method is called
        m_get.assert_called()

        #Verify return value with expected value
        self.assertEqual(Exp_alert_match_list, alert_match_list)


    @mock.patch.object(monPlugin.requests, 'get')
    def test_get_alarm_defination_by_name_no_valid_alarm_found(self, m_get):
        """Test get_alarm_defination_by_name: With no valid alarm found in returned list"""

        alarm_name = 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda5'

        #Set mocked function's return values
        m_get.return_value.status_code = 200
        m_get.return_value.content = '{"pageInfo": {"totalCount": 1,"page": 0,"pageSize": 1000},\
                                    "links": [\
                                        {"href": "/suite-api/api/alertdefinitions?page=0&amp;pageSize=1000",\
                                        "rel": "SELF","name": "current"},\
                                        {"href": "/suite-api/api/alertdefinitions?page=0&amp;pageSize=1000",\
                                         "rel": "RELATED","name": "first"},\
                                        {"href": "/suite-api/api/alertdefinitions?page=0&amp;pageSize=1000",\
                                         "rel": "RELATED","name": "last"}],\
                                    "alertDefinitions": [{\
                                        "id": "AlertDefinition-9a6d8a14-9f25-4d81-bf91-4d773497444d",\
                                        "name": "CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4",\
                                        "description": "CPU_Utilization_Above_Threshold",\
                                        "adapterKindKey": "VMWARE","resourceKindKey": "VirtualMachine",\
                                        "waitCycles": 1,"cancelCycles": 1,"type": 16,"subType": 19,\
                                        "states": [{"impact": {"impactType": "BADGE","detail": "risk"},\
                                            "severity": "CRITICAL",\
                                            "base-symptom-set": {"type": "SYMPTOM_SET",\
                                            "relation": "SELF","aggregation": "ALL",\
                                            "symptomSetOperator": "AND",\
                                            "symptomDefinitionIds": [\
                                            "SymptomDefinition-bcc2cb36-a67b-4deb-bcd3-9b5884973278"]}}]\
                                        }]}'

        #Expected return match list
        Exp_alert_match_list = []

        #Call get_alarm_defination_by_name method under test
        alert_match_list = self.mon_plugin.get_alarm_defination_by_name(alarm_name)

        #Verify that mocked method is called
        m_get.assert_called()

        #Verify return value with expected value
        self.assertEqual(Exp_alert_match_list, alert_match_list)


    @mock.patch.object(monPlugin.requests, 'put')
    @mock.patch.object(monPlugin.MonPlugin, 'get_symptom_defination_details')
    def test_update_symptom_defination_valid_symptom_req_response(self,\
                                                                  m_get_symptom_defination_details,\
                                                                  m_put):
        """Test update_symptom_defination: With valid REST response, update symptom"""

        #Expected symptom to be updated
        symptom_defination_id = 'SymptomDefinition-bcc2cb36-a67b-4deb-bcd3-9b5884973278'
        new_alarm_config = {'severity':"CRITICAL",
                            'operation': 'GT',
                            'threshold_value':5,
                            'alarm_uuid':'9a6d8a14-9f25-4d81-bf91-4d773497444d'
                            }

        #Set mocked function's return values
        m_get_symptom_defination_details.return_value = {
                            "id": "SymptomDefinition-bcc2cb36-a67b-4deb-bcd3-9b5884973278",
                            "name": "CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4",
                            "adapterKindKey": "VMWARE",
                            "resourceKindKey": "VirtualMachine",
                            "waitCycles": 1,
                            "cancelCycles": 1,
                            "state": {"severity": "CRITICAL",
                                      "condition": {
                                          "type": "CONDITION_HT",
                                          "key": "cpu|usage_average","operator": "GT","value": "0.0",
                                          "valueType": "NUMERIC","instanced": False,
                                          "thresholdType": "STATIC"}
                                      }
                           }

        m_put.return_value.status_code = 200
        m_put.return_value.content = '{\
            "id":"SymptomDefinition-bcc2cb36-a67b-4deb-bcd3-9b5884973278",\
            "name":"CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4",\
            "adapterKindKey":"VMWARE","resourceKindKey":"VirtualMachine","waitCycles":1,\
            "cancelCycles":1,\
            "state":{\
                "severity":"CRITICAL",\
                "condition":{\
                    "type":"CONDITION_HT","key":"cpu|usage_average","operator":"GT","value":"5.0",\
                    "valueType":"NUMERIC","instanced":False,"thresholdType":"STATIC"}}}'

        #Call update_symptom_defination method under test
        symptom_uuid = self.mon_plugin.update_symptom_defination(symptom_defination_id,\
                                                                 new_alarm_config)

        #Verify that mocked method is called with required parameters
        m_get_symptom_defination_details.assert_called_with(symptom_defination_id)
        m_put.assert_called()

        #Verify return value with expected value
        self.assertEqual(symptom_defination_id, symptom_uuid)


    @mock.patch.object(monPlugin.requests, 'put')
    @mock.patch.object(monPlugin.MonPlugin, 'get_symptom_defination_details')
    def test_update_symptom_defination_invalid_symptom_req_response(self,\
                                                                  m_get_symptom_defination_details,\
                                                                  m_put):
        """Test update_symptom_defination: If invalid REST response received, return None"""

        #Expected symptom to be updated
        symptom_defination_id = 'SymptomDefinition-bcc2cb36-a67b-4deb-bcd3-9b5884973278'
        new_alarm_config = {'severity':"CRITICAL",
                            'operation': 'GT',
                            'threshold_value':5,
                            'alarm_uuid':'9a6d8a14-9f25-4d81-bf91-4d773497444d'
                            }

        #Set mocked function's return values
        m_get_symptom_defination_details.return_value = {
                            "id": "SymptomDefinition-bcc2cb36-a67b-4deb-bcd3-9b5884973278",
                            "name": "CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4",
                            "adapterKindKey": "VMWARE",
                            "resourceKindKey": "VirtualMachine",
                            "waitCycles": 1,
                            "cancelCycles": 1,
                            "state": {"severity": "CRITICAL",
                                      "condition": {
                                          "type": "CONDITION_HT",
                                          "key": "cpu|usage_average","operator": "GT","value": "0.0",
                                          "valueType": "NUMERIC","instanced": False,
                                          "thresholdType": "STATIC"}
                                      }
                           }

        m_put.return_value.status_code = 500
        m_put.return_value.content = '{\
            "message": "Internal Server error, cause unknown.",\
            "moreInformation": [\
                {"name": "errorMessage",\
                 "value": "Symptom Definition CPU_Utilization_Above_Thr-e14b203c-\
                 6bf2-4e2f-a91c-8c19d240eda4 does not exist and hence cannot be updated."},\
                {"name": "localizedMessage",\
                 "value": "Symptom Definition CPU_Utilization_Above_Thr-e14b203c-\
                 6bf2-4e2f-a91c-8c19d240eda4 does not exist and hence cannot be updated.;"}],\
            "httpStatusCode": 500,"apiErrorCode": 500}'

        #Call update_symptom_defination method under test
        symptom_uuid = self.mon_plugin.update_symptom_defination(symptom_defination_id,\
                                                                 new_alarm_config)

        #Verify that mocked method is called with required parameters
        m_get_symptom_defination_details.assert_called_with(symptom_defination_id)
        m_put.assert_called()

        #Verify return value with expected value
        self.assertEqual(symptom_uuid, None)


    @mock.patch.object(monPlugin.requests, 'put')
    @mock.patch.object(monPlugin.MonPlugin, 'get_symptom_defination_details')
    def test_update_symptom_defination_failed_to_get_symptom_defination(self,\
                                                                  m_get_symptom_defination_details,\
                                                                  m_put):
        """Test update_symptom_defination: if fails to get symptom_defination returns None"""

        #Expected symptom to be updated
        symptom_defination_id = 'SymptomDefinition-bcc2cb36-a67b-4deb-bcd3-9b5884973278'
        new_alarm_config = {'severity':"CRITICAL",
                            'operation': 'GT',
                            'threshold_value':5,
                            'alarm_uuid':'9a6d8a14-9f25-4d81-bf91-4d773497444d'
                            }

        #Set mocked function's return values
        m_get_symptom_defination_details.return_value = None

        #Call update_symptom_defination method under test
        symptom_uuid = self.mon_plugin.update_symptom_defination(symptom_defination_id,\
                                                                 new_alarm_config)

        #Verify that mocked method is called with required parameters
        m_get_symptom_defination_details.assert_called_with(symptom_defination_id)
        m_put.assert_not_called()

        #Verify return value with expected value
        self.assertEqual(symptom_uuid, None)


    @mock.patch.object(monPlugin.requests, 'get')
    def test_get_symptom_defination_details_valid_req_response(self,m_get):
        """Test update_symptom_defination: With valid REST response symptom is created"""

        #Expected symptom to be updated
        symptom_uuid = 'SymptomDefinition-bcc2cb36-a67b-4deb-bcd3-9b5884973278'

        #Set mocked function's return values
        m_get.return_value.status_code = 200
        m_get.return_value.content = '{\
            "id": "SymptomDefinition-bcc2cb36-a67b-4deb-bcd3-9b5884973278",\
            "name": "CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4",\
            "adapterKindKey": "VMWARE","resourceKindKey": "VirtualMachine","waitCycles": 1,\
            "cancelCycles": 1,"state": {"severity": "CRITICAL","condition": {"type": "CONDITION_HT",\
            "key": "cpu|usage_average","operator": "GT","value": "6.0","valueType": "NUMERIC",\
            "instanced": false,"thresholdType": "STATIC"}}}'
        expected_symptom_details = {\
            "id": "SymptomDefinition-bcc2cb36-a67b-4deb-bcd3-9b5884973278",\
            "name": "CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4",\
            "adapterKindKey": "VMWARE","resourceKindKey": "VirtualMachine","waitCycles": 1,\
            "cancelCycles": 1,"state": {"severity": "CRITICAL","condition": {"type": "CONDITION_HT",\
            "key": "cpu|usage_average","operator": "GT","value": "6.0","valueType": "NUMERIC",\
            "instanced": False,"thresholdType": "STATIC"}}}

        #Call update_symptom_defination method under test
        symptom_details = self.mon_plugin.get_symptom_defination_details(symptom_uuid)

        #Verify that mocked method is called with required parameters
        m_get.assert_called()

        #Verify return value with expected value
        self.assertEqual(expected_symptom_details, symptom_details)


    @mock.patch.object(monPlugin.requests, 'get')
    def test_get_symptom_defination_details_invalid_req_response(self,m_get):
        """Test update_symptom_defination: if invalid REST response received return None"""

        #Expected symptom to be updated
        symptom_uuid = 'SymptomDefinition-bcc2cb36-a67b-4deb-bcd3-9b5884973278'

        #Set mocked function's return values
        m_get.return_value.status_code = 404
        m_get.return_value.content = '{"message": "No such SymptomDefinition\
        - SymptomDefinition-bcc2cb36-a67b-4deb-bcd3-9b5884973278.",\
        "httpStatusCode": 404,"apiErrorCode": 404}'

        expected_symptom_details = None

        #Call update_symptom_defination method under test
        symptom_details = self.mon_plugin.get_symptom_defination_details(symptom_uuid)

        #Verify that mocked method is called with required parameters
        m_get.assert_called()

        #Verify return value with expected value
        self.assertEqual(expected_symptom_details, symptom_details)


    @mock.patch.object(monPlugin.requests, 'get')
    def test_get_symptom_defination_details_symptom_uuid_not_provided(self,m_get):
        """Test update_symptom_defination: if required symptom uuid is not provided"""

        #Expected symptom to be updated
        symptom_uuid = None
        expected_symptom_details = None

        #Call update_symptom_defination method under test
        symptom_details = self.mon_plugin.get_symptom_defination_details(symptom_uuid)

        #Verify that mocked method is called with required parameters
        m_get.assert_not_called()

        #Verify return value with expected value
        self.assertEqual(expected_symptom_details, symptom_details)


    @mock.patch.object(monPlugin.requests, 'put')
    def test_reconfigure_alarm_valid_req_response(self, m_put):
        """Test reconfigure_alarm: for valid REST response"""

        #Set input parameters to reconfigure_alarm
        alarm_details_json = {
            'id': 'AlertDefinition-9a6d8a14-9f25-4d81-bf91-4d773497444d',
            'name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
            'description': 'CPU_Utilization_Above_Threshold', 'adapterKindKey': 'VMWARE',
            'states':[{'impact':{'impactType':'BADGE', 'detail':'risk'}, 'severity':'CRITICAL',
                       'base-symptom-set':{
                           'symptomDefinitionIds':['SymptomDefinition-bcc2cb36-a67b-4deb-bcd3-9b5884973278'],
                           'relation': 'SELF','type': 'SYMPTOM_SET', 'aggregation':'ALL',
                           'symptomSetOperator': 'AND'}}],
            'type': 16, 'cancelCycles': 1, 'resourceKindKey': 'VirtualMachine','subType': 19,
            'waitCycles': 1}

        new_alarm_config = {'severity':'WARNING',
                            'description': 'CPU_Utilization_Above_Threshold_Warning'}

        #Set mocked function's return values
        m_put.return_value.status_code = 200
        m_put.return_value.content = '{"id":"AlertDefinition-9a6d8a14-9f25-4d81-bf91-4d773497444d",\
            "name":"CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4",\
            "description":"CPU_Utilization_Above_Threshold_Warning","adapterKindKey":"VMWARE",\
            "resourceKindKey":"VirtualMachine","waitCycles":1,"cancelCycles":1,"type":16,\
            "subType":19,"states":[{"severity":"WARNING","base-symptom-set":{"type":"SYMPTOM_SET",\
            "relation":"SELF","aggregation":"ALL","symptomSetOperator":"AND",\
            "symptomDefinitionIds":["SymptomDefinition-bcc2cb36-a67b-4deb-bcd3-9b5884973278"]},\
            "impact":{"impactType":"BADGE","detail":"risk"}}]}'

        #Expected alarm_def_uuid to be returned
        expected_alarm_def_uuid = '9a6d8a14-9f25-4d81-bf91-4d773497444d'

        #Call reconfigure_alarm method under test
        alarm_def_uuid = self.mon_plugin.reconfigure_alarm(alarm_details_json, new_alarm_config)

        #Verify that mocked method is called with required parameters
        m_put.assert_called()

        #Verify return value with expected value
        self.assertEqual(expected_alarm_def_uuid, alarm_def_uuid)


    @mock.patch.object(monPlugin.requests, 'put')
    def test_reconfigure_alarm_invalid_req_response(self, m_put):
        """Test reconfigure_alarm: for invalid REST response, return None"""

        #Set input parameters to reconfigure_alarm
        alarm_details_json = {
            'id': 'AlertDefinition-9a6d8a14-9f25-4d81-bf91-4d773497444d',
            'name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
            'description': 'CPU_Utilization_Above_Threshold', 'adapterKindKey': 'VMWARE',
            'states':[{'impact':{'impactType':'BADGE', 'detail':'risk'}, 'severity':'CRITICAL',
                       'base-symptom-set':{
                           'symptomDefinitionIds':['SymptomDefinition-bcc2cb36-a67b-4deb-bcd3-9b5884973278'],
                           'relation': 'SELF','type': 'SYMPTOM_SET', 'aggregation':'ALL',
                           'symptomSetOperator': 'AND'}}],
            'type': 16, 'cancelCycles': 1, 'resourceKindKey': 'VirtualMachine','subType': 19,
            'waitCycles': 1}

        new_alarm_config = {'severity':'WARNING',
                            'description': 'CPU_Utilization_Above_Threshold_Warning'}

        #Set mocked function's return values
        m_put.return_value.status_code = 500
        m_put.return_value.content = '{"message": "Internal Server error, cause unknown.",\
            "moreInformation": [{"name": "errorMessage",\
            "value": "Cannot update Alert Definition CPU_Utilization_Above_Thr-\
            e14b203c-6bf2-4e2f-a91c-8c19d240eda4 since it does not exist"},\
            {"name": "localizedMessage",\
            "value": "Cannot update Alert Definition CPU_Utilization_Above_Thr-\
            e14b203c-6bf2-4e2f-a91c-8c19d240eda4 since it does not exist;"}],\
            "httpStatusCode": 500,"apiErrorCode": 500}'

        #Expected alarm_def_uuid to be returned
        expected_alarm_def_uuid = None

        #Call reconfigure_alarm method under test
        alarm_def_uuid = self.mon_plugin.reconfigure_alarm(alarm_details_json, new_alarm_config)

        #Verify that mocked method is called with required parameters
        m_put.assert_called()

        #Verify return value with expected value
        self.assertEqual(expected_alarm_def_uuid, alarm_def_uuid)


    @mock.patch.object(monPlugin.MonPlugin, 'delete_symptom_definition')
    @mock.patch.object(monPlugin.MonPlugin, 'delete_alarm_defination')
    @mock.patch.object(monPlugin.MonPlugin, 'delete_notification_rule')
    @mock.patch.object(monPlugin.MonPlugin, 'get_alarm_defination_details')
    def test_delete_alarm_configuration_successful_alarm_deletion(self,\
                                                                  m_get_alarm_defination_details,\
                                                                  m_delete_notification_rule,\
                                                                  m_delete_alarm_defination,\
                                                                  m_delete_symptom_definition):
        """Test delete_alarm_configuration: for successful alarm deletion, return alarm uuid"""

        #Set input parameters to delete_alarm_configuration
        delete_alarm_req_dict = {'alarm_uuid':'9a6d8a14-9f25-4d81-bf91-4d773497444d'}

        #Set mocked function's return values
        alarm_details_json = {
            'id': 'AlertDefinition-9a6d8a14-9f25-4d81-4d773497444d',
            'name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-8c19d240eda4',
            'symptomDefinitionIds':['SymptomDefinition-bcc2cb36-a67b-4deb-9b5884973278']}
        alarm_details = {
            'alarm_name':'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-8c19d240eda4',
            'alarm_id':'AlertDefinition-9a6d8a14-9f25-4d81-4d773497444d',
            'symptom_definition_id':'SymptomDefinition-bcc2cb36-a67b-4deb-9b5884973278'}

        m_get_alarm_defination_details.return_value = (alarm_details_json, alarm_details)
        m_delete_notification_rule.return_value = '989e7293-d78d-4405-92e30ec4f247'
        m_delete_alarm_defination.return_value = alarm_details['alarm_id']
        m_delete_symptom_definition.return_value = alarm_details['symptom_definition_id']

        #Call reconfigure_alarm method under test
        alarm_uuid = self.mon_plugin.delete_alarm_configuration(delete_alarm_req_dict)

        #Verify that mocked method is called with required parameters
        m_get_alarm_defination_details.assert_called_with(delete_alarm_req_dict['alarm_uuid'])
        m_delete_notification_rule.assert_called_with(alarm_details['alarm_name'])
        m_delete_alarm_defination.assert_called_with(alarm_details['alarm_id'])
        m_delete_symptom_definition.assert_called_with(alarm_details['symptom_definition_id'])

        #Verify return value with expected value
        self.assertEqual(alarm_uuid, delete_alarm_req_dict['alarm_uuid'])


    @mock.patch.object(monPlugin.MonPlugin, 'delete_symptom_definition')
    @mock.patch.object(monPlugin.MonPlugin, 'delete_alarm_defination')
    @mock.patch.object(monPlugin.MonPlugin, 'delete_notification_rule')
    @mock.patch.object(monPlugin.MonPlugin, 'get_alarm_defination_details')
    def test_delete_alarm_configuration_failed_to_get_alarm_defination(self,\
                                                                  m_get_alarm_defination_details,\
                                                                  m_delete_notification_rule,\
                                                                  m_delete_alarm_defination,\
                                                                  m_delete_symptom_definition):
        """Test delete_alarm_configuration: if failed to get alarm definition, return None"""

        #Set input parameters to delete_alarm_configuration
        delete_alarm_req_dict = {'alarm_uuid':'9a6d8a14-9f25-4d81-bf91-4d773497444d'}

        #Set mocked function's return values
        alarm_details_json = None
        alarm_details = None

        m_get_alarm_defination_details.return_value = (alarm_details_json, alarm_details)

        #Call reconfigure_alarm method under test
        alarm_uuid = self.mon_plugin.delete_alarm_configuration(delete_alarm_req_dict)

        #Verify that mocked method is called with required parameters
        m_get_alarm_defination_details.assert_called_with(delete_alarm_req_dict['alarm_uuid'])
        m_delete_notification_rule.assert_not_called()
        m_delete_alarm_defination.assert_not_called()
        m_delete_symptom_definition.assert_not_called()

        #Verify return value with expected value
        self.assertEqual(alarm_uuid, None)


    @mock.patch.object(monPlugin.MonPlugin, 'delete_symptom_definition')
    @mock.patch.object(monPlugin.MonPlugin, 'delete_alarm_defination')
    @mock.patch.object(monPlugin.MonPlugin, 'delete_notification_rule')
    @mock.patch.object(monPlugin.MonPlugin, 'get_alarm_defination_details')
    def test_delete_alarm_configuration_failed_to_delete_notification_rule(self,\
                                                                  m_get_alarm_defination_details,\
                                                                  m_delete_notification_rule,\
                                                                  m_delete_alarm_defination,\
                                                                  m_delete_symptom_definition):
        """Test delete_alarm_configuration: if failed to delete notification rule, return None"""

        #Set input parameters to delete_alarm_configuration
        delete_alarm_req_dict = {'alarm_uuid':'9a6d8a14-9f25-4d81-bf91-4d773497444d'}

        #Set mocked function's return values
        alarm_details_json = {
            'id': 'AlertDefinition-9a6d8a14-9f25-4d81-4d773497444d',
            'name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-8c19d240eda4',
            'symptomDefinitionIds':['SymptomDefinition-bcc2cb36-a67b-4deb-9b5884973278']}
        alarm_details = {
            'alarm_name':'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-8c19d240eda4',
            'alarm_id':'AlertDefinition-9a6d8a14-9f25-4d81-4d773497444d',
            'symptom_definition_id':'SymptomDefinition-bcc2cb36-a67b-4deb-9b5884973278'}

        m_get_alarm_defination_details.return_value = (alarm_details_json, alarm_details)
        m_delete_notification_rule.return_value = None

        #Call reconfigure_alarm method under test
        alarm_uuid = self.mon_plugin.delete_alarm_configuration(delete_alarm_req_dict)

        #Verify that mocked method is called with required parameters
        m_get_alarm_defination_details.assert_called_with(delete_alarm_req_dict['alarm_uuid'])
        m_delete_notification_rule.assert_called_with(alarm_details['alarm_name'])
        m_delete_alarm_defination.assert_not_called()
        m_delete_symptom_definition.assert_not_called()

        #Verify return value with expected value
        self.assertEqual(alarm_uuid, None)


    @mock.patch.object(monPlugin.MonPlugin, 'delete_symptom_definition')
    @mock.patch.object(monPlugin.MonPlugin, 'delete_alarm_defination')
    @mock.patch.object(monPlugin.MonPlugin, 'delete_notification_rule')
    @mock.patch.object(monPlugin.MonPlugin, 'get_alarm_defination_details')
    def test_delete_alarm_configuration_failed_to_delete_alarm_defination(self,\
                                                                  m_get_alarm_defination_details,\
                                                                  m_delete_notification_rule,\
                                                                  m_delete_alarm_defination,\
                                                                  m_delete_symptom_definition):
        """Test delete_alarm_configuration: if failed to delete alarm definition, return None"""

        #Set input parameters to delete_alarm_configuration
        delete_alarm_req_dict = {'alarm_uuid':'9a6d8a14-9f25-4d81-bf91-4d773497444d'}

        #Set mocked function's return values
        alarm_details_json = {
            'id': 'AlertDefinition-9a6d8a14-9f25-4d81-4d773497444d',
            'name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-8c19d240eda4',
            'symptomDefinitionIds':['SymptomDefinition-bcc2cb36-a67b-4deb-9b5884973278']}
        alarm_details = {
            'alarm_name':'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-8c19d240eda4',
            'alarm_id':'AlertDefinition-9a6d8a14-9f25-4d81-4d773497444d',
            'symptom_definition_id':'SymptomDefinition-bcc2cb36-a67b-4deb-9b5884973278'}

        m_get_alarm_defination_details.return_value = (alarm_details_json, alarm_details)
        m_delete_notification_rule.return_value = '989e7293-d78d-4405-92e30ec4f247'
        m_delete_alarm_defination.return_value = None

        #Call reconfigure_alarm method under test
        alarm_uuid = self.mon_plugin.delete_alarm_configuration(delete_alarm_req_dict)

        #Verify that mocked method is called with required parameters
        m_get_alarm_defination_details.assert_called_with(delete_alarm_req_dict['alarm_uuid'])
        m_delete_notification_rule.assert_called_with(alarm_details['alarm_name'])
        m_delete_alarm_defination.assert_called_with(alarm_details['alarm_id'])
        m_delete_symptom_definition.assert_not_called()

        #Verify return value with expected value
        self.assertEqual(alarm_uuid, None)


    @mock.patch.object(monPlugin.MonPlugin, 'delete_symptom_definition')
    @mock.patch.object(monPlugin.MonPlugin, 'delete_alarm_defination')
    @mock.patch.object(monPlugin.MonPlugin, 'delete_notification_rule')
    @mock.patch.object(monPlugin.MonPlugin, 'get_alarm_defination_details')
    def test_delete_alarm_configuration_failed_to_delete_symptom_definition(self,\
                                                                  m_get_alarm_defination_details,\
                                                                  m_delete_notification_rule,\
                                                                  m_delete_alarm_defination,\
                                                                  m_delete_symptom_definition):
        """Test delete_alarm_configuration: if failed to delete symptom definition, return None"""

        #Set input parameters to delete_alarm_configuration
        delete_alarm_req_dict = {'alarm_uuid':'9a6d8a14-9f25-4d81-bf91-4d773497444d'}

        #Set mocked function's return values
        alarm_details_json = {
            'id': 'AlertDefinition-9a6d8a14-9f25-4d81-4d773497444d',
            'name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-8c19d240eda4',
            'symptomDefinitionIds':['SymptomDefinition-bcc2cb36-a67b-4deb-9b5884973278']}
        alarm_details = {
            'alarm_name':'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-8c19d240eda4',
            'alarm_id':'AlertDefinition-9a6d8a14-9f25-4d81-4d773497444d',
            'symptom_definition_id':'SymptomDefinition-bcc2cb36-a67b-4deb-9b5884973278'}

        m_get_alarm_defination_details.return_value = (alarm_details_json, alarm_details)
        m_delete_notification_rule.return_value = '989e7293-d78d-4405-92e30ec4f247'
        m_delete_alarm_defination.return_value = alarm_details['alarm_id']
        m_delete_symptom_definition.return_value = None

        #Call reconfigure_alarm method under test
        alarm_uuid = self.mon_plugin.delete_alarm_configuration(delete_alarm_req_dict)

        #Verify that mocked method is called with required parameters
        m_get_alarm_defination_details.assert_called_with(delete_alarm_req_dict['alarm_uuid'])
        m_delete_notification_rule.assert_called_with(alarm_details['alarm_name'])
        m_delete_alarm_defination.assert_called_with(alarm_details['alarm_id'])
        m_delete_symptom_definition.assert_called_with(alarm_details['symptom_definition_id'])

        #Verify return value with expected value
        self.assertEqual(alarm_uuid, None)


    @mock.patch.object(monPlugin.requests, 'delete')
    @mock.patch.object(monPlugin.MonPlugin, 'get_notification_rule_id_by_alarm_name')
    def test_delete_notification_rule_successful_deletion_req_response(self,\
                                                            m_get_notification_rule_id_by_alarm_name,\
                                                            m_delete):
        """Test delete_notification_rule: Valid notification rule is deleted & returns rule_id"""

        #Set input parameters to delete_notification_rule
        alarm_name = 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-8c19d240eda4'

        #Set mocked function's return values
        m_get_notification_rule_id_by_alarm_name.return_value = '8db86441-71d8-4830-9e1a-a90be3776d12'
        m_delete.return_value.status_code = 204

        #Call delete_notification_rule method under test
        rule_id = self.mon_plugin.delete_notification_rule(alarm_name)

        #Verify that mocked method is called with required parameters
        m_get_notification_rule_id_by_alarm_name.assert_called_with(alarm_name)
        m_delete.assert_called()

        #Verify return value with expected value
        self.assertEqual(rule_id, '8db86441-71d8-4830-9e1a-a90be3776d12')


    @mock.patch.object(monPlugin.requests, 'delete')
    @mock.patch.object(monPlugin.MonPlugin, 'get_notification_rule_id_by_alarm_name')
    def test_delete_notification_rule_failed_to_get_notification_rule_id(self,\
                                                            m_get_notification_rule_id_by_alarm_name,\
                                                            m_delete):
        """Test delete_notification_rule: if notification rule is not found, returns None"""

        #Set input parameters to delete_notification_rule
        alarm_name = 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-8c19d240eda4'

        #Set mocked function's return values
        m_get_notification_rule_id_by_alarm_name.return_value = None

        #Call delete_notification_rule method under test
        rule_id = self.mon_plugin.delete_notification_rule(alarm_name)

        #Verify that mocked method is called with required parameters
        m_get_notification_rule_id_by_alarm_name.assert_called_with(alarm_name)
        m_delete.assert_not_called()

        # verify return value with expected value
        self.assertEqual(rule_id, None)


    @mock.patch.object(monPlugin.requests, 'delete')
    @mock.patch.object(monPlugin.MonPlugin, 'get_notification_rule_id_by_alarm_name')
    def test_delete_notification_rule_invalid_deletion_req_response(self,\
                                                            m_get_notification_rule_id_by_alarm_name,\
                                                            m_delete):
        """Test delete_notification_rule: If an invalid response is received, returns None"""

        #Set input parameters to delete_notification_rule
        alarm_name = 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-8c19d240eda4'

        #Set mocked function's return values
        m_get_notification_rule_id_by_alarm_name.return_value = '8db86441-71d8-4830-9e1a-a90be3776d12'
        m_delete.return_value.status_code = 404

        #Call delete_notification_rule method under test
        rule_id = self.mon_plugin.delete_notification_rule(alarm_name)

        #Verify that mocked method is called with required parameters
        m_get_notification_rule_id_by_alarm_name.assert_called_with(alarm_name)
        m_delete.assert_called()

        #Verify return value with expected value
        self.assertEqual(rule_id, None)


    @mock.patch.object(monPlugin.requests, 'get')
    def test_get_notification_rule_id_by_alarm_name_valid_req_response(self,m_get):
        """Test get_notification_rule_id_by_alarm_name: A valid request response received,
            returns notification_id
        """

        #Set input parameters to get_notification_rule_id_by_alarm_name
        alarm_name = 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4'

        #Set mocked function's return values
        m_get.return_value.status_code = 200
        m_get.return_value.content = '{\
        "pageInfo": {"totalCount": 0,"page": 0,"pageSize": 1000},\
        "links": [\
            {"href": "/suite-api/api/notifications/rules?page=0&amp;pageSize=1000",\
            "rel": "SELF","name": "current"},\
            {"href": "/suite-api/api/notifications/rules?page=0&amp;pageSize=1000",\
            "rel": "RELATED","name": "first"},\
            {"href": "/suite-api/api/notifications/rules?page=0&amp;pageSize=1000",\
            "rel": "RELATED","name": "last"}],\
        "notification-rule": [{\
        "id": "2b86fa23-0c15-445c-a2b1-7bd725c46f59",\
        "name": "notify_CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4",\
        "pluginId": "03053f51-f829-438d-993d-cc33a435d76a",\
        "links": [{"href": "/suite-api/api/notifications/rules/2b86fa23-0c15-445c-a2b1-7bd725c46f59",\
        "rel": "SELF","name": "linkToSelf"}]}]}'

        #Call get_notification_rule_id_by_alarm_name method under test
        notification_id = self.mon_plugin.get_notification_rule_id_by_alarm_name(alarm_name)

        #Verify that mocked method is called with required parameters
        m_get.assert_called()

        #Verify return value with expected value
        self.assertEqual(notification_id, '2b86fa23-0c15-445c-a2b1-7bd725c46f59')


    @mock.patch.object(monPlugin.requests, 'get')
    def test_get_notification_rule_id_by_alarm_name_invalid_req_response(self,m_get):
        """Test get_notification_rule_id_by_alarm_name: If an invalid response received,\
            returns None
        """

        #Set input parameters to delete_alarm_configuration
        alarm_name = 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4'

        #Set mocked function's return values
        m_get.return_value.status_code = 404

        #Call get_notification_rule_id_by_alarm_name method under test
        notification_id = self.mon_plugin.get_notification_rule_id_by_alarm_name(alarm_name)

        #Verify that mocked method is called with required parameters
        m_get.assert_called()

        #Verify return value with expected value
        self.assertEqual(notification_id, None)


    @mock.patch.object(monPlugin.requests, 'get')
    def test_get_notification_rule_id_by_alarm_name_rule_not_found(self,m_get):
        """Test get_notification_rule_id_by_alarm_name: If a notification rule is not found,
            returns None
        """

        #Set input parameters to delete_alarm_configuration
        alarm_name = 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda'

        #Set mocked function's return values
        m_get.return_value.status_code = 200
        m_get.return_value.content = '{\
        "pageInfo": {"totalCount": 0,"page": 0,"pageSize": 1000},\
        "links": [\
            {"href": "/suite-api/api/notifications/rules?page=0&amp;pageSize=1000",\
            "rel": "SELF","name": "current"},\
            {"href": "/suite-api/api/notifications/rules?page=0&amp;pageSize=1000",\
            "rel": "RELATED","name": "first"},\
            {"href": "/suite-api/api/notifications/rules?page=0&amp;pageSize=1000",\
            "rel": "RELATED","name": "last"}],\
        "notification-rule": [{\
        "id": "2b86fa23-0c15-445c-a2b1-7bd725c46f59",\
        "name": "notify_CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4",\
        "pluginId": "03053f51-f829-438d-993d-cc33a435d76a",\
        "links": [{"href": "/suite-api/api/notifications/rules/2b86fa23-0c15-445c-a2b1-7bd725c46f59",\
        "rel": "SELF","name": "linkToSelf"}]}]}'

        #Call get_notification_rule_id_by_alarm_name method under test
        notification_id = self.mon_plugin.get_notification_rule_id_by_alarm_name(alarm_name)

        #Verify that mocked method is called with required parameters
        m_get.assert_called()

        #Verify return value with expected value
        self.assertEqual(notification_id, None)


    @mock.patch.object(monPlugin.requests, 'delete')
    def test_delete_alarm_defination_valid_req_response(self,m_delete):
        """Test delete_alarm_defination: A valid request response received,
            returns symptom_id
        """

        #Set input parameters to delete_alarm_definition
        alarm_definition_id = 'AlertDefinition-9a6d8a14-9f25-4d81-4d773497444d'

        #Set mocked function's return values
        m_delete.return_value.status_code = 204

        #Call delete_alarm_defination method under test
        actual_alarm_id = self.mon_plugin.delete_alarm_defination(alarm_definition_id)

        #Verify that mocked method is called with required parameters
        m_delete.assert_called()

        #Verify return value with expected value
        self.assertEqual(actual_alarm_id, alarm_definition_id)


    @mock.patch.object(monPlugin.requests, 'delete')
    def test_delete_alarm_defination_invalid_req_response(self,m_delete):
        """Test delete_alarm_defination: If an invalid request response received,
            returns None
        """

        #Set input parameters to delete_alarm_definition
        alarm_definition_id = 'AlertDefinition-9a6d8a14-9f25-4d81-4d773497444d'

        #Set mocked function's return values
        m_delete.return_value.status_code = 404

        #Call delete_alarm_defination method under test
        actual_alarm_id = self.mon_plugin.delete_alarm_defination(alarm_definition_id)

        #Verify that mocked method is called with required parameters
        m_delete.assert_called()

        #Verify return value with expected value
        self.assertEqual(actual_alarm_id, None)


    @mock.patch.object(monPlugin.requests, 'delete')
    def test_delete_symptom_definition_valid_req_response(self,m_delete):
        """Test delete_symptom_definition: A valid request response received,
            returns symptom_id
        """

        #Set input parameters to delete_symptom_definition
        symptom_definition_id = 'SymptomDefinition-bcc2cb36-a67b-4deb-9b5884973278'

        #Set mocked function's return values
        m_delete.return_value.status_code = 204

        #Call delete_symptom_definition method under test
        actual_symptom_id = self.mon_plugin.delete_symptom_definition(symptom_definition_id)

        #Verify that mocked method is called with required parameters
        m_delete.assert_called()

        #Verify return value with expected value
        self.assertEqual(actual_symptom_id, symptom_definition_id)


    @mock.patch.object(monPlugin.requests, 'delete')
    def test_delete_symptom_definition_invalid_req_response(self,m_delete):
        """Test delete_symptom_definition: If an invalid request response received,
            returns None
        """

        #Set input parameters to delete_symptom_definition
        symptom_definition_id = 'SymptomDefinition-bcc2cb36-a67b-4deb-9b5884973278'

        #Set mocked function's return values
        m_delete.return_value.status_code = 404

        #Call delete_symptom_definition method under test
        actual_symptom_id = self.mon_plugin.delete_symptom_definition(symptom_definition_id)

        #Verify that mocked method is called with required parameters
        m_delete.assert_called()

        #Verify return value with expected value
        self.assertEqual(actual_symptom_id, None)


    @mock.patch.object(monPlugin.requests, 'post')
    @mock.patch.object(monPlugin.MonPlugin, 'check_if_plugin_configured')
    def test_configure_rest_plugin_valid_plugin_id(self, m_check_if_plugin_configured, m_post):
        """Test configure rest plugin method-valid plugin id"""

        # mock return values
        expected_return = m_check_if_plugin_configured.return_value = "mock_pluginid"

        # call configure rest plugin method under test
        actual_return = self.mon_plugin.configure_rest_plugin()

        # verify that mocked method is called
        m_check_if_plugin_configured.assert_called()
        m_post.assert_not_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.MonPlugin,'enable_rest_plugin')
    @mock.patch.object(monPlugin.requests, 'post')
    @mock.patch.object(monPlugin.MonPlugin, 'check_if_plugin_configured')
    def est_configure_rest_plugin_invalid_plugin_id(self, m_check_if_plugin_configured, m_post, m_enable_rest_plugin):
        """Test configure rest plugin method-invalid plugin id"""

        # mock return values
        m_check_if_plugin_configured.return_value = None # not configured
        m_post.return_value.status_code = 201 #success
        m_post.return_value.content = '{"pluginTypeId":"RestPlugin","pluginId":"1ef15663-9739-49fe-8c41-022bcc9f690c",\
                                        "name":"MON_module_REST_Plugin","version":1518693747871,"enabled":false,\
                                        "configValues":[{"name":"Url","value":"https://MON.lxd:8080/notify/"},\
                                        {"name":"Content-type","value":"application/json"},{"name":"Certificate",\
                                        "value":"AA:E7:3E:A5:34:E0:25:FB:28:84:3B:74:B2:18:74:C0:C3:E8:26:50"},\
                                        {"name":"ConnectionCount","value":"20"}]}'

        m_enable_rest_plugin.return_value = True #success
        expected_return = '1ef15663-9739-49fe-8c41-022bcc9f690c'

        # call configure rest plugin method under test
        actual_return = self.mon_plugin.configure_rest_plugin()

        # verify that mocked method is called
        m_check_if_plugin_configured.assert_called()
        m_post.assert_called()
        m_enable_rest_plugin.assert_called_with('1ef15663-9739-49fe-8c41-022bcc9f690c','MON_module_REST_Plugin')

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.MonPlugin,'enable_rest_plugin')
    @mock.patch.object(monPlugin.requests, 'post')
    @mock.patch.object(monPlugin.MonPlugin, 'check_if_plugin_configured')
    def est_configure_rest_plugin_failed_to_enable_plugin(self, m_check_if_plugin_configured, m_post, m_enable_rest_plugin):
        """Test configure rest plugin method-failed to enable plugin case"""

        # mock return values
        m_check_if_plugin_configured.return_value = None # not configured
        m_post.return_value.status_code = 201 #success
        m_post.return_value.content = '{"pluginTypeId":"RestPlugin","pluginId":"1ef15663-9739-49fe-8c41-022bcc9f690c",\
                                        "name":"MON_module_REST_Plugin","version":1518693747871,"enabled":false,\
                                        "configValues":[{"name":"Url","value":"https://MON.lxd:8080/notify/"},\
                                        {"name":"Content-type","value":"application/json"},{"name":"Certificate",\
                                        "value":"AA:E7:3E:A5:34:E0:25:FB:28:84:3B:74:B2:18:74:C0:C3:E8:26:50"},\
                                        {"name":"ConnectionCount","value":"20"}]}'

        m_enable_rest_plugin.return_value = False #return failure
        expected_return = None

        # call configure rest plugin method under test
        actual_return = self.mon_plugin.configure_rest_plugin()

        # verify that mocked method is called
        m_check_if_plugin_configured.assert_called()
        m_post.assert_called()
        m_enable_rest_plugin.assert_called_with('1ef15663-9739-49fe-8c41-022bcc9f690c','MON_module_REST_Plugin')

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'get')
    def test_check_if_plugin_configured_valid_req_response(self, m_get):
        """Test check if plugin configured method-valid request response"""

        plugin_name = 'MON_module_REST_Plugin'
        # mock return values
        m_get.return_value.status_code = 200
        expected_return = '1ef15663-9739-49fe-8c41-022bcc9f690c'
        m_get.return_value.content = '{"notificationPluginInstances":\
                                       [{"pluginTypeId":"RestPlugin",\
                                        "pluginId":"1ef15663-9739-49fe-8c41-022bcc9f690c",\
                                        "name":"MON_module_REST_Plugin","version":1518694966987,\
                                        "enabled":true,"configValues":[{"name":"Url",\
                                        "value":"https://MON.lxd:8080/notify/"},\
                                        {"name":"Content-type","value":"application/json"},\
                                        {"name":"Certificate",\
                                        "value":"AA:E7:3E:A5:34:E0:25:FB:28:84:3B:74:B2:18:74:C0"},\
                                        {"name":"ConnectionCount","value":"20"}]}]}'

        # call check if plugin configured method under test
        actual_return = self.mon_plugin.check_if_plugin_configured(plugin_name)

        # verify that mocked method is called
        m_get.assert_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'get')
    def test_check_if_plugin_configured_invalid_req_response(self, m_get):
        """Test check if plugin configured method-invalid request response"""

        plugin_name = 'MON_module_REST_Plugin'
        # mock return values
        m_get.return_value.status_code = 201
        expected_return = None
        m_get.return_value.content = '{"notificationPluginInstances":\
                                       [{"pluginTypeId":"RestPlugin",\
                                        "pluginId":"1ef15663-9739-49fe-8c41-022bcc9f690c",\
                                        "name":"MON_module_REST_Plugin","version":1518694966987,\
                                        "enabled":true,"configValues":[{"name":"Url",\
                                        "value":"https://MON.lxd:8080/notify/"},\
                                        {"name":"Content-type","value":"application/json"},\
                                        {"name":"Certificate",\
                                        "value":"AA:E7:3E:A5:34:E0:25:FB:28:84:3B:74:B2:18:74:C0"},\
                                        {"name":"ConnectionCount","value":"20"}]}]}'

        # call check if plugin configured method under test
        actual_return = self.mon_plugin.check_if_plugin_configured(plugin_name)

        # verify that mocked method is called
        m_get.assert_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'put')
    def test_enable_rest_plugin_valid_req_response(self, m_put):
        """Test enable rest plugin method-valid request response"""

        plugin_name = 'MON_module_REST_Plugin'
        plugin_id = '1ef15663-9739-49fe-8c41-022bcc9f690c'
        # mock return values
        m_put.return_value.status_code = 204
        expected_return = True
        m_put.return_value.content = ''

        # call enable rest plugin configured method under test
        actual_return = self.mon_plugin.enable_rest_plugin(plugin_id, plugin_name)

        # verify that mocked method is called
        m_put.assert_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'put')
    def test_enable_rest_plugin_invalid_req_response(self, m_put):
        """Test enable rest plugin method-invalid request response"""

        plugin_name = 'MON_module_REST_Plugin'
        plugin_id = '08018c0f-8879-4ca1-9b92-00e22d2ff81b' #invalid plugin id
        # mock return values
        m_put.return_value.status_code = 404 # api Error code
        expected_return = False
        m_put.return_value.content = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><ops:\
                                      error xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
                                      xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:ops=\
                                      "http://webservice.vmware.com/vRealizeOpsMgr/1.0/" \
                                      httpStatusCode="404" apiErrorCode="404"><ops:message>\
                                      No such Notification Plugin - 08018c0f-8879-4ca1-9b92-\
                                      00e22d2ff81b.</ops:message></ops:error>'

        # call enable rest plugin configured method under test
        actual_return = self.mon_plugin.enable_rest_plugin(plugin_id, plugin_name)

        # verify that mocked method is called
        m_put.assert_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'post')
    @mock.patch.object(monPlugin.MonPlugin, 'check_if_plugin_configured')
    def test_create_alarm_notification_rule_valid_req(self, m_check_if_plugin_configured, m_post):
        """Test create alarm notification rule method valid request response"""

        alarm_name = 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
        alarm_id = 'AlertDefinition-f1163767-6eac-438f-8e60-a7a867257e14'
        res_id = 'ac87622f-b761-40a0-b151-00872a2a456e'
        expected_return = "8db86441-71d8-4830-9e1a-a90be3776d12"

        # mock return values
        m_check_if_plugin_configured.return_value = '03053f51-f829-438d-993d-cc33a435d76a'
        m_post.return_value.status_code = 201
        m_post.return_value.content = '{"id":"8db86441-71d8-4830-9e1a-a90be3776d12",\
                                      "name":"notify_CPU_Utilization_Above_Thr-e14b203c",\
                                      "pluginId":"03053f51-f829-438d-993d-cc33a435d76a",\
                                      "alertControlStates":[],"alertStatuses":[],\
                                      "resourceFilter":{"matchResourceIdOnly":true,\
                                      "childrenResourceKindFilters":[],\
                                      "resourceId":"ac87622f-b761-40a0-b151-00872a2a456e"},\
                                      "alertTypeFilters":[],"alertDefinitionIdFilters":{"values":[\
                                      "AlertDefinition-f1163767-6eac-438f-8e60-a7a867257e14"]}}'

        # call enable rest plugin configured method under test
        actual_return = self.mon_plugin.create_alarm_notification_rule(alarm_name, alarm_id, res_id)

        # verify that mocked method is called
        m_check_if_plugin_configured.assert_called_with('MON_module_REST_Plugin')
        m_post.assert_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'post')
    @mock.patch.object(monPlugin.MonPlugin, 'check_if_plugin_configured')
    def test_create_alarm_notification_rule_invalid_req(self, m_check_if_plugin_configured, m_post):
        """Test create alarm notification rule method invalid request response"""

        alarm_name = 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
        alarm_id = 'AlertDefinition-f1163767-6eac-438f-8e60-a7a867257e14'
        res_id = 'ac87622f-b761-40a0-b151-00872a2a456e'
        expected_return = None # invalid req should retrun none

        # mock return values
        m_check_if_plugin_configured.return_value = '03053f51-f829-438d-993d-cc33a435d76a'
        m_post.return_value.status_code = 500
        m_post.return_value.content = '{"message":"Internal Server error, cause unknown.",\
                                        "moreInformation":[{"name":"errorMessage","value":\
                                        "there is already a rule with the same rule name"},\
                                       {"name":"localizedMessage","value":"there is already \
                                        a rule with the same rule name;"}],"httpStatusCode":500,\
                                        "apiErrorCode":500}'

        # call enable rest plugin configured method under test
        actual_return = self.mon_plugin.create_alarm_notification_rule(alarm_name, alarm_id, res_id)

        # verify that mocked method is called
        m_check_if_plugin_configured.assert_called_with('MON_module_REST_Plugin')
        m_post.assert_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'post')
    @mock.patch.object(monPlugin.MonPlugin, 'check_if_plugin_configured')
    def test_create_alarm_notification_rule_failed_to_get_plugin_id(self, \
                                    m_check_if_plugin_configured, m_post):
        """Test create alarm notification rule method invalid plugin id"""

        alarm_name = 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
        alarm_id = 'AlertDefinition-f1163767-6eac-438f-8e60-a7a867257e14'
        res_id = 'ac87622f-b761-40a0-b151-00872a2a456e'
        expected_return = None # invalid req should retrun none

        # mock return values
        m_check_if_plugin_configured.return_value = None

        # call enable rest plugin configured method under test
        actual_return = self.mon_plugin.create_alarm_notification_rule(alarm_name, alarm_id, res_id)

        # verify that mocked method is called
        m_check_if_plugin_configured.assert_called_with('MON_module_REST_Plugin')
        m_post.assert_not_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'get')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_resource_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_moref_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_default_Params')
    def test_get_metrics_data_valid_rest_req_response(self, m_get_default_Params, \
                                                      m_get_vm_moref_id, \
                                                      m_get_vm_resource_id, \
                                                      m_get):
        """Test get metrics data of resource method valid request response"""

        metrics = {'collection_period': 1, 'metric_name': 'CPU_UTILIZATION', 'metric_uuid': None, \
                   'schema_version': 1.0, 'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4',\
                   'correlation_id': 'e14b203c-6bf2-4e2f-a91c-8c19d2abcdef', \
                   'schema_type': 'read_metric_data_request', 'vim_type': 'VMware', \
                   'collection_unit': 'HR'}

        # mock return value
        m_get_default_Params.return_value = {'metric_key': 'cpu|usage_average', 'unit': '%'}
        vm_moref_id = m_get_vm_moref_id.return_value = 'vm-6626'
        m_get_vm_resource_id.return_value = 'ac87622f-b761-40a0-b151-00872a2a456e'
        m_get.return_value.status_code = 200
        m_get.return_value.content = '{"values":[{"resourceId":"ac87622f-b761-40a0-b151-\
                                       00872a2a456e","stat-list":{"stat":[{"timestamps":\
                                      [1519716874297,1519717174294,1519717474295,1519717774298,\
                                      1519718074300,1519718374299,1519718674314,1519718974325,\
                                      1519719274304,1519719574298,1519719874298,1519720174301],\
                                      "statKey":{"key":"cpu|usage_average"},"intervalUnit":\
                                      {"quantifier":1},"data":[0.1120000034570694,\
                                      0.11866666376590729,0.11599999666213989,0.11400000005960464,\
                                      0.12066666781902313,0.11533333361148834,0.11800000071525574,\
                                      0.11533333361148834,0.12200000137090683,0.11400000005960464,\
                                      0.1459999978542328,0.12133333086967468]}]}}]}'

        # call get matrics data method under test
        actual_return = self.mon_plugin.get_metrics_data(metrics)

        # verify that mocked method is called
        m_get_default_Params.assert_called_with(metrics['metric_name'])
        m_get_vm_moref_id.assert_called_with(metrics['resource_uuid'])
        m_get_vm_resource_id.assert_called_with(vm_moref_id)
        m_get.assert_called()

        # verify return value with expected value
        #self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'get')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_resource_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_moref_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_default_Params')
    def test_get_metrics_data_invalid_rest_req_response(self, m_get_default_Params, \
                                                      m_get_vm_moref_id, \
                                                      m_get_vm_resource_id, \
                                                      m_get):
        """Test get metrics data of resource method invalid request response"""

        metrics = {'collection_period': 1, 'metric_name': 'CPU_UTILIZATION', 'metric_uuid': None, \
                   'schema_version': 1.0, 'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4',\
                   'correlation_id': 'e14b203c-6bf2-4e2f-a91c-8c19d2abcdef', \
                   'schema_type': 'read_metric_data_request', 'vim_type': 'VMware', \
                   'collection_unit': 'HR'}

        # mock return value
        m_get_default_Params.return_value = {'metric_key': 'cpu|usage_average', 'unit': '%'}
        vm_moref_id = m_get_vm_moref_id.return_value = 'vm-6626'
        m_get_vm_resource_id.return_value = 'ac87622f-b761-40a0-b151-00872a2a456e'
        m_get.return_value.status_code = 400
        expected_return = {'metric_name': 'CPU_UTILIZATION', 'metric_uuid': '0',
                           'schema_version': '1.0',
                           'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                           'correlation_id': u'e14b203c-6bf2-4e2f-a91c-8c19d2abcdef',
                           'metrics_data': {'time_series': [], 'metrics_series': []},
                           'schema_type': 'read_metric_data_response', 'tenant_uuid': None,
                            'unit': '%'}

        # call get matrics data method under test
        actual_return = self.mon_plugin.get_metrics_data(metrics)

        # verify that mocked method is called
        m_get_default_Params.assert_called_with(metrics['metric_name'])
        m_get_vm_moref_id.assert_called_with(metrics['resource_uuid'])
        m_get_vm_resource_id.assert_called_with(vm_moref_id)
        m_get.assert_called()

        m_get.return_value.content = '{"message":"Invalid request... #1 violations found.",\
                                       "validationFailures":[{"failureMessage":"Invalid Parameter",\
                                       "violationPath":"end"}],"httpStatusCode":400,\
                                       "apiErrorCode":400}'

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'get')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_resource_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_moref_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_default_Params')
    def test_get_metrics_data_metric_not_supported(self, m_get_default_Params, \
                                                   m_get_vm_moref_id, \
                                                   m_get_vm_resource_id, \
                                                   m_get):
        """Test get metrics data of resource method invalid metric name"""

        metrics = {'collection_period': 1, 'metric_name': 'INVALID_METRIC', 'metric_uuid': None, \
                   'schema_version': 1.0, 'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4',\
                   'correlation_id': 'e14b203c-6bf2-4e2f-a91c-8c19d2abcdef', \
                   'schema_type': 'read_metric_data_request', 'vim_type': 'VMware', \
                   'collection_unit': 'HR'}

        # mock return value
        m_get_default_Params.return_value = {} # returns empty dict

        expected_return = {'metric_name': 'INVALID_METRIC', 'metric_uuid': '0',
                           'schema_version': '1.0',
                           'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                           'correlation_id': u'e14b203c-6bf2-4e2f-a91c-8c19d2abcdef',
                           'metrics_data': {'time_series': [], 'metrics_series': []},
                           'schema_type': 'read_metric_data_response', 'tenant_uuid': None,
                            'unit': None}

        # call get matrics data method under test
        actual_return = self.mon_plugin.get_metrics_data(metrics)

        # verify that mocked method is called/not called
        m_get_default_Params.assert_called_with(metrics['metric_name'])
        m_get_vm_moref_id.assert_not_called()
        m_get_vm_resource_id.assert_not_called()
        m_get.assert_not_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'get')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_resource_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_moref_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_default_Params')
    def test_get_metrics_data_failed_to_get_vm_moref_id(self, m_get_default_Params, \
                                                        m_get_vm_moref_id, \
                                                        m_get_vm_resource_id, \
                                                        m_get):
        """Test get metrics data method negative scenario- invalid resource id"""

        metrics = {'collection_period': 1, 'metric_name': 'CPU_UTILIZATION', 'metric_uuid': None, \
                   'schema_version': 1.0, 'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4',\
                   'correlation_id': 'e14b203c-6bf2-4e2f-a91c-8c19d2abcdef', \
                   'schema_type': 'read_metric_data_request', 'vim_type': 'VMware', \
                   'collection_unit': 'HR'}

        # mock return value
        m_get_default_Params.return_value = {'metric_key': 'cpu|usage_average', 'unit': '%'}
        m_get_vm_moref_id.return_value = None
        expected_return = {'metric_name': 'CPU_UTILIZATION', 'metric_uuid': '0',
                           'schema_version': '1.0',
                           'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                           'correlation_id': u'e14b203c-6bf2-4e2f-a91c-8c19d2abcdef',
                           'metrics_data': {'time_series': [], 'metrics_series': []},
                           'schema_type': 'read_metric_data_response', 'tenant_uuid': None,
                            'unit': '%'}

        # call get matrics data method under test
        actual_return = self.mon_plugin.get_metrics_data(metrics)

        # verify that mocked method is called/not called
        m_get_default_Params.assert_called_with(metrics['metric_name'])
        m_get_vm_moref_id.assert_called_with(metrics['resource_uuid'])
        m_get_vm_resource_id.assert_not_called()
        m_get.assert_not_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'get')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_resource_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_moref_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_default_Params')
    def test_get_metrics_data_failed_to_get_vm_resource_id(self, m_get_default_Params, \
                                                           m_get_vm_moref_id, \
                                                           m_get_vm_resource_id, \
                                                           m_get):
        """Test get metrics data method negative scenario- invalid moref id"""

        metrics = {'collection_period': 1, 'metric_name': 'CPU_UTILIZATION', 'metric_uuid': None, \
                   'schema_version': 1.0, 'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4',\
                   'correlation_id': 'e14b203c-6bf2-4e2f-a91c-8c19d2abcdef', \
                   'schema_type': 'read_metric_data_request', 'vim_type': 'VMware', \
                   'collection_unit': 'HR'}

        # mock return value
        m_get_default_Params.return_value = {'metric_key': 'cpu|usage_average', 'unit': '%'}
        m_get_vm_moref_id.return_value = 'Invalid-vm-6626'
        m_get_vm_resource_id.return_value = None
        expected_return = {'metric_name': 'CPU_UTILIZATION', 'metric_uuid': '0',
                           'schema_version': '1.0',
                           'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                           'correlation_id': u'e14b203c-6bf2-4e2f-a91c-8c19d2abcdef',
                           'metrics_data': {'time_series': [], 'metrics_series': []},
                           'schema_type': 'read_metric_data_response', 'tenant_uuid': None,
                            'unit': '%'}

        # call get matrics data method under test
        actual_return = self.mon_plugin.get_metrics_data(metrics)

        # verify that mocked method is called/not called
        m_get_default_Params.assert_called_with(metrics['metric_name'])
        m_get_vm_moref_id.assert_called_with(metrics['resource_uuid'])
        m_get_vm_resource_id.assert_called()
        m_get.assert_not_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.MonPlugin, 'reconfigure_alarm')
    @mock.patch.object(monPlugin.MonPlugin, 'update_symptom_defination')
    @mock.patch.object(monPlugin.MonPlugin, 'get_alarm_defination_details')
    def test_update_alarm_configuration_successful_updation(self, m_get_alarm_defination_details, \
                                                            m_update_symptom_defination, \
                                                            m_reconfigure_alarm ):
        """Test update alarm configuration method"""

        alarm_config = {'alarm_uuid': 'f1163767-6eac-438f-8e60-a7a867257e14',
                        'correlation_id': 14203,
                        'description': 'CPU_Utilization_Above_Threshold_L', 'operation': 'GT'}

        # mock return value
        alarm_details_json = {'states': [{'impact': {'impactType': 'BADGE', 'detail': 'risk'},
                              'severity': 'CRITICAL', 'base-symptom-set': {'symptomDefinitionIds':
                              ['SymptomDefinition-47c88675-bea8-436a-bb41-8d2231428f44'],
                              'relation': 'SELF', 'type': 'SYMPTOM_SET', 'aggregation': 'ALL'}}],
                              'description': 'CPU_Utilization_Above_Threshold', 'type': 16,
                              'id': 'AlertDefinition-f1163767-6eac-438f-8e60-a7a867257e14',
                              'name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d2'}
        alarm_details = {'symptom_definition_id': 'SymptomDefinition-47c88675-bea8-436a-bb41-\
                        8d2231428f44', 'alarm_name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-\
                        a91c-8c19d2', 'alarm_id': 'AlertDefinition-f1163767-6eac-438f-8e60-\
                        a7a867257e14', 'resource_kind': u'VirtualMachine', 'type': 16}
        m_get_alarm_defination_details.return_value = (alarm_details_json, alarm_details)
        m_update_symptom_defination.return_value = 'SymptomDefinition-47c88675-bea8-436a-bb41-\
                                                   8d2231428f44'
        expected_return = m_reconfigure_alarm.return_value = 'f1163767-6eac-438f-8e60-a7a867257e14'

        # call update alarm configuration method under test
        actual_return = self.mon_plugin.update_alarm_configuration(alarm_config)

        # verify that mocked method is called
        m_get_alarm_defination_details.assert_called_with(alarm_config['alarm_uuid'])
        m_update_symptom_defination.assert_called_with(alarm_details['symptom_definition_id'],\
                                                       alarm_config)
        m_reconfigure_alarm.assert_called_with(alarm_details_json, alarm_config)

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.MonPlugin, 'reconfigure_alarm')
    @mock.patch.object(monPlugin.MonPlugin, 'update_symptom_defination')
    @mock.patch.object(monPlugin.MonPlugin, 'get_alarm_defination_details')
    def test_update_alarm_configuration_failed_to_reconfigure_alarm(self, \
                                                        m_get_alarm_defination_details, \
                                                        m_update_symptom_defination, \
                                                        m_reconfigure_alarm ):
        """Test update alarm configuration method- failed to reconfigure alarm"""

        alarm_config = {'alarm_uuid': 'f1163767-6eac-438f-8e60-a7a867257e14',
                        'correlation_id': 14203,
                        'description': 'CPU_Utilization_Above_Threshold_L', 'operation': 'GT'}

        # mock return value
        alarm_details_json = {'states': [{'impact': {'impactType': 'BADGE', 'detail': 'risk'},
                              'severity': 'CRITICAL', 'base-symptom-set': {'symptomDefinitionIds':
                              ['SymptomDefinition-47c88675-bea8-436a-bb41-8d2231428f44'],
                              'relation': 'SELF', 'type': 'SYMPTOM_SET', 'aggregation': 'ALL'}}],
                              'description': 'CPU_Utilization_Above_Threshold', 'type': 16,
                              'id': 'AlertDefinition-f1163767-6eac-438f-8e60-a7a867257e14',
                              'name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d2'}
        alarm_details = {'symptom_definition_id': 'SymptomDefinition-47c88675-bea8-436a-bb41-\
                        8d2231428f44', 'alarm_name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-\
                        a91c-8c19d2', 'alarm_id': 'AlertDefinition-f1163767-6eac-438f-8e60-\
                        a7a867257e14', 'resource_kind': u'VirtualMachine', 'type': 16}
        m_get_alarm_defination_details.return_value = (alarm_details_json, alarm_details)
        m_update_symptom_defination.return_value = 'SymptomDefinition-47c88675-bea8-436a-bb41-\
                                                    8d2231428f44'
        expected_return = m_reconfigure_alarm.return_value = None # failed to reconfigure

        # call update alarm configuration method under test
        actual_return = self.mon_plugin.update_alarm_configuration(alarm_config)

        # verify that mocked method is called
        m_get_alarm_defination_details.assert_called_with(alarm_config['alarm_uuid'])
        m_update_symptom_defination.assert_called_with(alarm_details['symptom_definition_id'],\
                                                       alarm_config)
        m_reconfigure_alarm.assert_called_with(alarm_details_json, alarm_config)

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.MonPlugin, 'reconfigure_alarm')
    @mock.patch.object(monPlugin.MonPlugin, 'update_symptom_defination')
    @mock.patch.object(monPlugin.MonPlugin, 'get_alarm_defination_details')
    def test_update_alarm_configuration_failed_to_update_symptom(self, \
                                                        m_get_alarm_defination_details, \
                                                        m_update_symptom_defination, \
                                                        m_reconfigure_alarm ):
        """Test update alarm configuration method- failed to update alarm"""

        alarm_config = {'alarm_uuid': 'f1163767-6eac-438f-8e60-a7a867257e14',
                        'correlation_id': 14203,
                        'description': 'CPU_Utilization_Above_Threshold_L', 'operation': 'GT'}

        # mock return value
        alarm_details_json = {'states': [{'impact': {'impactType': 'BADGE', 'detail': 'risk'},
                              'severity': 'CRITICAL', 'base-symptom-set': {'symptomDefinitionIds':
                              ['SymptomDefinition-47c88675-bea8-436a-bb41-8d2231428f44'],
                              'relation': 'SELF', 'type': 'SYMPTOM_SET', 'aggregation': 'ALL'}}],
                              'description': 'CPU_Utilization_Above_Threshold', 'type': 16,
                              'id': 'AlertDefinition-f1163767-6eac-438f-8e60-a7a867257e14',
                              'name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d2'}
        alarm_details = {'symptom_definition_id': 'Invalid-47c88675-bea8-436a-bb41-\
                        8d2231428f44', 'alarm_name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-\
                        a91c-8c19d2', 'alarm_id': 'AlertDefinition-f1163767-6eac-438f-8e60-\
                        a7a867257e14', 'resource_kind': u'VirtualMachine', 'type': 16}
        m_get_alarm_defination_details.return_value = (alarm_details_json, alarm_details)
        expected_return = m_update_symptom_defination.return_value = None

        # call update alarm configuration method under test
        actual_return = self.mon_plugin.update_alarm_configuration(alarm_config)

        # verify that mocked method is called
        m_get_alarm_defination_details.assert_called_with(alarm_config['alarm_uuid'])
        m_update_symptom_defination.assert_called_with(alarm_details['symptom_definition_id'],\
                                                       alarm_config)
        m_reconfigure_alarm.assert_not_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.MonPlugin, 'get_default_Params')
    def test_verify_metric_support_metric_supported_with_unit(self,m_get_default_Params):
        """Test verify metric support method for supported metric"""

        # mock return value
        metric_info = {'metric_unit': '%', 'metric_name': 'CPU_UTILIZATION',
                       'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4'}
        m_get_default_Params.return_value = {'metric_key': 'cpu|usage_average', 'unit': '%'}
        expected_return = True #supported metric returns True

        # call verify metric support method under test
        actual_return = self.mon_plugin.verify_metric_support(metric_info)

        # verify that mocked method is called
        m_get_default_Params.assert_called_with(metric_info['metric_name'])

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.MonPlugin, 'get_default_Params')
    def test_verify_metric_support_metric_not_supported(self,m_get_default_Params):
        """Test verify metric support method for un-supported metric"""

        # mock return value
        metric_info = {'metric_unit': '%', 'metric_name': 'INVALID_METRIC',
                       'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4'}
        m_get_default_Params.return_value = {}
        expected_return = False #supported metric returns True

        # call verify metric support method under test
        actual_return = self.mon_plugin.verify_metric_support(metric_info)

        # verify that mocked method is called
        m_get_default_Params.assert_called_with(metric_info['metric_name'])

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.MonPlugin, 'get_default_Params')
    def test_verify_metric_support_metric_supported_with_mismatched_unit(self, \
                                                               m_get_default_Params):
        """Test verify metric support method for supported metric with mismatched unit"""

        # mock return value
        metric_info = {'metric_unit': '', 'metric_name': 'INVALID_METRIC',
                       'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4'}
        m_get_default_Params.return_value = {'metric_key': 'cpu|usage_average', 'unit': '%'}
        expected_return = True #supported metric returns True

        # call verify metric support method under test
        actual_return = self.mon_plugin.verify_metric_support(metric_info)

        # verify that mocked method is called
        m_get_default_Params.assert_called_with(metric_info['metric_name'])

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.MonPlugin, 'get_triggered_alarms_on_resource')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vrops_resourceid_from_ro_uuid')
    def test_get_triggered_alarms_list_returns_triggered_alarms(self, \
                                                        m_get_vrops_resourceid, \
                                                        m_triggered_alarms):
        """Test get triggered alarm list method valid input"""

        # Mock list alarm input
        list_alarm_input = {'severity': 'CRITICAL',
                            'correlation_id': 'e14b203c',
                            'alarm_name': 'CPU_Utilization_Above_Threshold',
                            'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4'}

        resource_id = m_get_vrops_resourceid.return_value = 'ac87622f-b761-40a0-b151-00872a2a456e'
        expected_return = m_triggered_alarms.return_value = [{'status': 'ACTIVE',
                                           'update_date': '2018-01-12T08:34:05',
                                           'severity': 'CRITICAL', 'resource_uuid': 'e14b203c',
                                           'cancel_date': '0000-00-00T00:00:00',
                                           'alarm_instance_uuid': 'd9e3bc84',
                                           'alarm_uuid': '5714977d', 'vim_type': 'VMware',
                                           'start_date': '2018-01-12T08:34:05'},
                                          {'status': 'CANCELED','update_date':'2017-12-20T09:37:57',
                                           'severity': 'CRITICAL', 'resource_uuid': 'e14b203c',
                                           'cancel_date': '2018-01-12T06:49:19',
                                           'alarm_instance_uuid': 'd3bbeef6',
                                           'alarm_uuid': '7ba1bf3e', 'vim_type': 'VMware',
                                           'start_date': '2017-12-20T09:37:57'}]

        # call get triggered alarms list method under test
        actual_return = self.mon_plugin.get_triggered_alarms_list(list_alarm_input)

        # verify that mocked method is called
        m_get_vrops_resourceid.assert_called_with(list_alarm_input['resource_uuid'])
        m_triggered_alarms.assert_called_with(list_alarm_input['resource_uuid'] , resource_id)

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.MonPlugin, 'get_triggered_alarms_on_resource')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vrops_resourceid_from_ro_uuid')
    def test_get_triggered_alarms_list_invalid_resource_uuid(self, \
                                                        m_get_vrops_resourceid, \
                                                        m_triggered_alarms):
        """Test get triggered alarm list method invalid resource uuid"""

        # Mock list alarm input
        list_alarm_input = {'severity': 'CRITICAL',
                            'correlation_id': 'e14b203c',
                            'alarm_name': 'CPU_Utilization_Above_Threshold',
                            'resource_uuid': '12345'} #invalid resource uuid

        expected_return = m_get_vrops_resourceid.return_value = None #returns empty list

        # call get triggered alarms list method under test
        actual_return = self.mon_plugin.get_triggered_alarms_list(list_alarm_input)

        # verify that mocked method is called
        m_get_vrops_resourceid.assert_called_with(list_alarm_input['resource_uuid'])
        m_triggered_alarms.assert_not_called()

        # verify return value with expected value
        self.assertEqual([], actual_return)


    @mock.patch.object(monPlugin.MonPlugin, 'get_triggered_alarms_on_resource')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vrops_resourceid_from_ro_uuid')
    def test_get_triggered_alarms_list_resource_uuid_not_present(self, \
                                                        m_get_vrops_resourceid, \
                                                        m_triggered_alarms):
        """Test get triggered alarm list method resource not present"""

        # Mock list alarm input
        list_alarm_input = {'severity': 'CRITICAL',
                            'correlation_id': 'e14b203c',
                            'alarm_name': 'CPU_Utilization_Above_Threshold'}

        # call get triggered alarms list method under test
        actual_return = self.mon_plugin.get_triggered_alarms_list(list_alarm_input)

        # verify that mocked method is called
        m_get_vrops_resourceid.assert_not_called()
        m_triggered_alarms.assert_not_called()

        # verify return value with expected value
        self.assertEqual([], actual_return)


    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_resource_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_moref_id')
    def test_get_vrops_resourceid_from_ro_uuid(self, m_get_vm_moref_id, m_get_vm_resource_id):
        """Test get vrops resourceid from ro uuid method"""

        # Mock the inputs
        ro_resource_uuid = 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
        vm_moref_id = m_get_vm_moref_id.return_value = 'vm-6626'
        expected_return = m_get_vm_resource_id.return_value ='ac87622f-b761-40a0-b151-00872a2a456e'

        # call get_vrops_resourceid_from_ro_uuid method under test
        actual_return = self.mon_plugin.get_vrops_resourceid_from_ro_uuid(ro_resource_uuid)

        # verify that mocked method is called
        m_get_vm_moref_id.assert_called_with(ro_resource_uuid)
        m_get_vm_resource_id.assert_called_with(vm_moref_id)

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_resource_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_moref_id')
    def test_get_vrops_resourceid_from_ro_uuid_failed_to_get_vm_resource_id(self, \
                                                                    m_get_vm_moref_id, \
                                                                    m_get_vm_resource_id):
        """Test get vrops resourceid from ro uuid method negative scenario"""

        # Mock the inputs
        ro_resource_uuid = 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
        vm_moref_id = m_get_vm_moref_id.return_value = 'vm-6626'
        expected_return = m_get_vm_resource_id.return_value = None

        # call get_vrops_resourceid_from_ro_uuid method under test
        actual_return = self.mon_plugin.get_vrops_resourceid_from_ro_uuid(ro_resource_uuid)

        # verify that mocked method is called
        m_get_vm_moref_id.assert_called_with(ro_resource_uuid)
        m_get_vm_resource_id.assert_called_with(vm_moref_id)

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_resource_id')
    @mock.patch.object(monPlugin.MonPlugin, 'get_vm_moref_id')
    def test_get_vrops_resourceid_from_ro_uuid_failed_to_get_vm_moref_id(self, \
                                                                    m_get_vm_moref_id, \
                                                                    m_get_vm_resource_id):
        """Test get vrops resourceid from ro uuid method negative scenario"""

        # Mock the inputs
        ro_resource_uuid = 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
        expected_return = vm_moref_id = m_get_vm_moref_id.return_value = None

        # call get_vrops_resourceid_from_ro_uuid method under test
        actual_return = self.mon_plugin.get_vrops_resourceid_from_ro_uuid(ro_resource_uuid)

        # verify that mocked method is called
        m_get_vm_moref_id.assert_called_with(ro_resource_uuid)
        m_get_vm_resource_id.assert_not_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'get')
    def test_get_triggered_alarms_on_resource_valid_req_response(self, m_get):
        """Test get triggered alarms on resource method for valid request"""

        # Mock the inputs
        ro_resource_uuid = 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
        vrops_resource_id = 'ac87622f-b761-40a0-b151-00872a2a456e'
        m_get.return_value.status_code = 200
        expected_return = [{'status': 'ACTIVE', 'update_date': '2018-01-12T08:34:05',
                            'severity': 'CRITICAL', 'start_date': '2018-01-12T08:34:05',
                            'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                            'cancel_date': '2018-02-12T08:24:48', 'vim_type': 'VMware',
                            'alarm_instance_uuid': 'd9e3bc84-dcb4-4905-b592-00a55f4cdaf1',
                            'alarm_uuid': '5714977d-56f6-4222-adc7-43fa6c6e7e39'}]

        m_get.return_value.content = '{"alerts": [\
        {\
            "alertId": "d9e3bc84-dcb4-4905-b592-00a55f4cdaf1",\
            "resourceId": "ac87622f-b761-40a0-b151-00872a2a456e",\
            "alertLevel": "CRITICAL",\
            "status": "ACTIVE",\
            "startTimeUTC": 1515746045278,\
            "cancelTimeUTC": 1518423888708,\
            "updateTimeUTC": 1515746045278,\
            "alertDefinitionId": "AlertDefinition-5714977d-56f6-4222-adc7-43fa6c6e7e39",\
            "alertDefinitionName": "CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4"\
        },\
        {\
            "alertId": "5fb5e940-e161-4253-a729-7255c6d6b1f5",\
            "resourceId": "ac87622f-b761-40a0-b151-00872a2a456e",\
            "alertLevel": "WARNING",\
            "status": "CANCELED",\
            "startTimeUTC": 1506684979154,\
            "cancelTimeUTC": 0,\
            "updateTimeUTC": 1520471975507,\
            "alertDefinitionId": "AlertDefinition-9ec5a921-1a54-411d-85ec-4c1c9b26dd02",\
            "alertDefinitionName": "VM_CPU_Usage_Alarm"\
        }]}'

        # call get_vrops_resourceid_from_ro_uuid method under test
        actual_return = self.mon_plugin.get_triggered_alarms_on_resource(ro_resource_uuid, \
                                                                        vrops_resource_id)

        # verify that mocked method is called
        m_get.assert_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'get')
    def test_get_triggered_alarms_on_resource_invalid_req_response(self, m_get):
        """Test get triggered alarms on resource method for invalid request"""

        # Mock the inputs
        ro_resource_uuid = 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
        vrops_resource_id = 'ac87622f-b761-40a0-b151-00872a2a456e'
        m_get.return_value.status_code = 204
        expected_return = None

        # call get_vrops_resourceid_from_ro_uuid method under test
        actual_return = self.mon_plugin.get_triggered_alarms_on_resource(ro_resource_uuid, \
                                                                        vrops_resource_id)

        # verify that mocked method is called
        m_get.assert_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'get')
    def test_get_triggered_alarms_on_resource_no_alarms_present(self, m_get):
        """Test get triggered alarms on resource method for no alarms present"""

        # Mock the inputs
        ro_resource_uuid = 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
        vrops_resource_id = 'ac87622f-b761-40a0-b151-00872a2a456e'
        m_get.return_value.status_code = 200
        expected_return = []
        m_get.return_value.content = '{"alerts": []}'

        # call get_vrops_resourceid_from_ro_uuid method under test
        actual_return = self.mon_plugin.get_triggered_alarms_on_resource(ro_resource_uuid, \
                                                                        vrops_resource_id)

        # verify that mocked method is called
        m_get.assert_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    def test_convert_date_time_valid_date_time(self):
        """Test convert date time method valid input"""

        # Mock the inputs
        date_time = 1515746045278
        expected_return = '2018-01-12T08:34:05'

        # call convert_date_time method under test
        actual_return = self.mon_plugin.convert_date_time(date_time)

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)

    def test_convert_date_time_invalid_date_time(self):
        """Test convert date time method invalid input"""

        # Mock the inputs
        date_time = 0
        expected_return = '0000-00-00T00:00:00'

        # call convert_date_time method under test
        actual_return = self.mon_plugin.convert_date_time(date_time)

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'get')
    def test_get_vm_resource_id_rest_valid_req_response(self, m_get):
        """Test get vms resource id valid request"""

        # Mock the inputs
        vm_moref_id = 'vm-6626'
        m_get.return_value.status_code = 200
        expected_return = "ac87622f-b761-40a0-b151-00872a2a456e"
        m_get.return_value.content = \
        '{ \
            "resourceList": [\
               {\
                   "creationTime": 1497770174130,\
                   "resourceKey": {\
                       "name": "OCInst2.ubuntu(4337d51f-1e65-4ab0-9c08-4897778d4fda)",\
                       "adapterKindKey": "VMWARE",\
                       "resourceKindKey": "VirtualMachine",\
                       "resourceIdentifiers": [\
                           {\
                               "identifierType": {\
                               "name": "VMEntityObjectID",\
                               "dataType": "STRING",\
                               "isPartOfUniqueness": true\
                               },\
                               "value": "vm-6626"\
                           }\
                       ]\
                   },\
                   "identifier": "ac87622f-b761-40a0-b151-00872a2a456e"\
                }\
            ]\
        }'

        # call get_vm_resource_id method under test
        actual_return = self.mon_plugin.get_vm_resource_id(vm_moref_id)

        # verify that mocked method is called
        m_get.assert_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'get')
    def test_get_vm_resource_id_rest_invalid_req_response(self, m_get):
        """Test get vms resource id invalid request"""

        # Mock the inputs
        vm_moref_id = 'vm-6626'
        m_get.return_value.status_code = 406
        expected_return = None
        m_get.return_value.content = '406 Not Acceptable'

        # call get_vm_resource_id method under test
        actual_return = self.mon_plugin.get_vm_resource_id(vm_moref_id)

        # verify that mocked method is called
        m_get.assert_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'get')
    def test_get_vm_resource_id_rest_invalid_response(self, m_get):
        """Test get vms resource id invalid response"""

        # Mock the inputs
        vm_moref_id = 'vm-6626'
        m_get.return_value.status_code = 200
        expected_return = None
        m_get.return_value.content = \
        '{ \
            "resourceList": \
               {\
                   "creationTime": 1497770174130,\
                   "resourceKey": {\
                       "name": "OCInst2.ubuntu(4337d51f-1e65-4ab0-9c08-4897778d4fda)",\
                       "adapterKindKey": "VMWARE",\
                       "resourceKindKey": "VirtualMachine",\
                       "resourceIdentifiers": [\
                           {\
                               "identifierType": {\
                               "name": "VMEntityObjectID",\
                               "dataType": "STRING",\
                               "isPartOfUniqueness": true\
                               },\
                               "value": "vm-6626"\
                           }\
                       ]\
                   },\
                   "identifier": "ac87622f-b761-40a0-b151-00872a2a456e"\
                }\
            ]\
        }'

        # call get_vm_resource_id method under test
        actual_return = self.mon_plugin.get_vm_resource_id(vm_moref_id)

        # verify that mocked method is called
        m_get.assert_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.MonPlugin, 'get_vapp_details_rest')
    def test_get_vm_moref_id_valid_id_found (self, m_get_vapp_details_rest):
        """Test get vm moref id valid scenario"""

        #mock the inputs
        vapp_uuid = 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
        m_get_vapp_details_rest.return_value = {'vm_vcenter_info': {'vm_moref_id': 'vm-6626'}}
        expected_return = 'vm-6626'

        # call get_vm_resource_id method under test
        actual_return = self.mon_plugin.get_vm_moref_id(vapp_uuid)

        # verify that mocked method is called
        m_get_vapp_details_rest.assert_called_with(vapp_uuid)

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.MonPlugin, 'get_vapp_details_rest')
    def test_get_vm_moref_id_valid_id_not_found(self, m_get_vapp_details_rest):
        """Test get vm moref id invalid scenario"""

        #mock the inputs
        vapp_uuid = 'e14b203c-6bf2-4e2f-a91c-8c19d240eda'#invalid uuid
        m_get_vapp_details_rest.return_value = {}
        expected_return = None

        # call get_vm_resource_id method under test
        actual_return = self.mon_plugin.get_vm_moref_id(vapp_uuid)

        # verify that mocked method is called
        m_get_vapp_details_rest.assert_called_with(vapp_uuid)

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'get')
    @mock.patch.object(monPlugin.MonPlugin, 'connect_as_admin')
    def test_get_vapp_details_rest_valid_req_response(self, m_connect_as_admin, m_get):
        """Test get vapp details rest method for valid request response"""

        #mock the inputs
        vapp_uuid = 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
        m_connect_as_admin.return_value = self.vca
        self.vca._session = self.session
        self.vca._session.headers['x-vcloud-authorization'] = '2ec69b2cc6264ad0a47aaf4e3e280d16'
        m_get.return_value.status_code = 200
        expected_return = {'vm_vcenter_info': {'vm_moref_id': 'vm-6626'}}
        m_get.return_value.content = '<?xml version="1.0" encoding="UTF-8"?>\
        <VApp xmlns="http://www.vmware.com/vcloud/v1.5"  xmlns:vmext="http://www.vmware.com/vcloud/extension/v1.5" >\
            <Children>\
                <Vm needsCustomization="false"  type="application/vnd.vmware.vcloud.vm+xml">\
                    <VCloudExtension required="false">\
                        <vmext:VmVimInfo>\
                            <vmext:VmVimObjectRef>\
                                <vmext:VimServerRef  type="application/vnd.vmware.admin.vmwvirtualcenter+xml"/>\
                                <vmext:MoRef>vm-6626</vmext:MoRef>\
                                <vmext:VimObjectType>VIRTUAL_MACHINE</vmext:VimObjectType>\
                            </vmext:VmVimObjectRef>\
                        </vmext:VmVimInfo>\
                    </VCloudExtension>\
                </Vm>\
            </Children>\
        </VApp>'

        # call get_vapp_details_rest method under test
        actual_return = self.mon_plugin.get_vapp_details_rest(vapp_uuid)

        # verify that mocked method is called
        m_connect_as_admin.assert_called_with()
        m_get.assert_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'get')
    @mock.patch.object(monPlugin.MonPlugin, 'connect_as_admin')
    def test_get_vapp_details_rest_invalid_req_response(self, m_connect_as_admin, m_get):
        """Test get vapp details rest method for invalid request response"""

        #mock the inputs
        vapp_uuid = 'Invalid-e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
        m_connect_as_admin.return_value = self.vca
        self.vca._session = self.session
        self.vca._session.headers['x-vcloud-authorization'] = '2ec69b2cc6264ad0a47aaf4e3e280d16'
        m_get.return_value.status_code = 400
        expected_return = {}
        m_get.return_value.content = 'Bad Request'

        # call get_vapp_details_rest method under test
        actual_return = self.mon_plugin.get_vapp_details_rest(vapp_uuid)

        # verify that mocked method is called
        m_connect_as_admin.assert_called_with()
        m_get.assert_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'get')
    @mock.patch.object(monPlugin.MonPlugin, 'connect_as_admin')
    def test_get_vapp_details_rest_failed_to_connect_vcd(self, m_connect_as_admin, m_get):
        """Test get vapp details rest method for failed to connect to vcd"""

        #mock the inputs
        vapp_uuid = 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
        m_connect_as_admin.return_value = None
        expected_return = {}

        # call get_vapp_details_rest method under test
        actual_return = self.mon_plugin.get_vapp_details_rest(vapp_uuid)

        # verify that mocked method is called
        m_connect_as_admin.assert_called_with()
        m_get.assert_not_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'get')
    @mock.patch.object(monPlugin.MonPlugin, 'connect_as_admin')
    def test_get_vapp_details_rest_invalid_response(self, m_connect_as_admin, m_get):
        """Test get vapp details rest method for invalid response"""

        #mock the inputs
        vapp_uuid = 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4'
        m_connect_as_admin.return_value = self.vca
        self.vca._session = self.session
        self.vca._session.headers['x-vcloud-authorization'] = '2ec69b2cc6264ad0a47aaf4e3e280d16'
        m_get.return_value.status_code = 200
        expected_return = {}
        m_get.return_value.content = '<?xml version="1.0" encoding="UTF-8"?>\
        <VApp xmlns="http://www.vmware.com/vcloud/v1.5"  xmlns:vmext="http://www.vmware.com/vcloud/extension/v1.5" >\
            <Children>\
                <Vm needsCustomization="false"  type="application/vnd.vmware.vcloud.vm+xml">\
                    <VCloudExtension required="false">\
                        <vmext:VmVimInfo>\
                            <vmext:VmVimObjectRef>\
                                <vmext:VimServerRef  type="application/vnd.vmware.admin.vmwvirtualcenter+xml"/>\
                                <vmext:MoRef>vm-!!6626</vmext:MoRef>\
                                <vmext:VimObjectType>VIRTUAL_MACHINE</vmext:VimObjectType>\
                            </vmext:\
                        </vmext:VmVimInfo>\
                    </VCloudExtension>\
                </Vm>\
            </Children>\
        </VApp>'

        # call get_vapp_details_rest method under test
        actual_return = self.mon_plugin.get_vapp_details_rest(vapp_uuid)

        # verify that mocked method is called
        m_connect_as_admin.assert_called_with()
        m_get.assert_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


    @mock.patch.object(monPlugin.Client, 'set_credentials')
    @mock.patch.object(monPlugin, 'Client')
    def test_connect_as_admin(self, m_client, m_set_credentials):
        """Test connect as admin to vCD method"""

        #mock the inputs and mocked returns
        expected_return = m_client.return_value = self.vca
        m_set_credentials.retrun_value = True

        # call connect_as_admin method under test
        actual_return = self.mon_plugin.connect_as_admin()

        # verify that mocked method is called
        m_client.assert_called()
        m_set_credentials.assert_called()

        # verify return value with expected value
        self.assertEqual(expected_return, actual_return)


# For testing purpose
#if __name__ == '__main__':
#   unittest.main()


