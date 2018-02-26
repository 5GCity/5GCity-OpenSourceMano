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

        #Verify return value with expected value
        self.assertEqual(exepcted_return, actual_return)


    def test_get_default_Params_invalid_metric_alarm_name(self):
        """Test get default params method-invalid metric alarm"""

        # Mock valid metric_alarm_name and response
        metric_alarm_name = "Invalid_Alarm"
        exepcted_return = {}

        # call get default param function under test
        actual_return = self.mon_plugin.get_default_Params(metric_alarm_name)

        #Verify return value with expected value
        self.assertEqual(exepcted_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'post')
    def test_create_symptom_valid_req_response(self, m_post):
        """Test create symptom method-valid request"""

        # Mock valid symptom params and mock responses
        symptom_param = {'threshold_value': 0, 'cancel_cycles': 1, 'adapter_kind_key': 'VMWARE',
                         'resource_kind_key': 'VirtualMachine', 'severity': 'CRITICAL',
                         'symptom_name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
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

        #Verify that mocked method is called
        m_post.assert_called()

        #Verify return value with expected value
        self.assertEqual(exepcted_return, actual_return)


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

        exepcted_return = None

        # call create symptom method under test
        actual_return = self.mon_plugin.create_symptom(symptom_param)

        #Verify that mocked method is called
        m_post.assert_called()

        #Verify return value with expected value
        self.assertEqual(exepcted_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'post')
    def test_create_symptom_incorrect_data(self, m_post):
        """Test create symptom method-incorrect data"""

        # Mock valid symptom params and invalid  mock responses
        symptom_param = {'threshold_value': 0, 'cancel_cycles': 1, 'adapter_kind_key': 'VMWARE',
                         'resource_kind_key': 'VirtualMachine', 'severity': 'CRITICAL',
                         'symptom_name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                         'operation': 'GT', 'metric_key': 'cpu|usage_average'}

        exepcted_return = None

        # call create symptom method under test
        actual_return = self.mon_plugin.create_symptom(symptom_param)

        #Verify that mocked method is not called
        m_post.assert_not_called()

        #Verify return value with expected value
        self.assertEqual(exepcted_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'post')
    def test_create_alarm_definition_valid_req_response(self, m_post):
        """Test create alarm definition method-valid response"""

        # Mock valid alarm params and mock responses
        alarm_param = {'description': 'CPU_Utilization_Above_Threshold', 'cancelCycles': 1, 'subType': 19,
                       'waitCycles': 1, 'severity': 'CRITICAL', 'impact': 'risk', 'adapterKindKey': 'VMWARE',
                       'name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4', 'resourceKindKey': 'VirtualMachine',
                       'symptomDefinitionId': 'SymptomDefinition-25278b06-bff8-4409-a141-9b4e064235df', 'type': 16}

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


    @mock.patch.object(monPlugin.requests, 'post')
    def test_create_alarm_definition_invalid_req_response(self, m_post):
        """Test create alarm definition method-invalid response"""

        # Mock valid alarm params and mock responses
        alarm_param = {'description': 'CPU_Utilization_Above_Threshold', 'cancelCycles': 1, 'subType': 19,
                       'waitCycles': 1, 'severity': 'CRITICAL', 'impact': 'risk', 'adapterKindKey': 'VMWARE',
                       'name': 'CPU_Utilization_Above_Thr-e14b203c-6bf2-4e2f-a91c-8c19d240eda4', 'resourceKindKey': 'VirtualMachine',
                       'symptomDefinitionId': 'SymptomDefinition-25278b06-bff8-4409-a141-9b4e064235df', 'type': 16}

        m_post.return_value.status_code = 404
        m_post.return_value.content = '404 Not Found'

        exepcted_return = None

        # call create alarm definition method under test
        actual_return = self.mon_plugin.create_alarm_definition(alarm_param)

        # verify that mocked method is called
        m_post.assert_called()

        # verify return value with expected value
        self.assertEqual(exepcted_return, actual_return)


    @mock.patch.object(monPlugin.requests, 'post')
    def test_create_alarm_definition_incorrect_data(self, m_post):
        """Test create alarm definition method-incorrect data"""

        # Mock incorrect alarm params
        alarm_param = {'description': 'CPU_Utilization_Above_Threshold', 'cancelCycles': 1, 'subType': 19,
                       'waitCycles': 1, 'severity': 'CRITICAL', 'impact': 'risk', 'adapterKindKey': 'VMWARE',
                       'symptomDefinitionId': 'SymptomDefinition-25278b06-bff8-4409-a141-9b4e064235df', 'type': 16}

        exepcted_return = None

        # call create symptom method under test
        actual_return = self.mon_plugin.create_alarm_definition(alarm_param)

        # verify that mocked method is not called
        m_post.assert_not_called()

        # verify return value with expected value
        self.assertEqual(exepcted_return, actual_return)


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
    def est_get_notification_rule_id_by_alarm_name_rule_not_found(self,m_get):
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


# For testing purpose
#if __name__ == '__main__':
#    unittest.main()


