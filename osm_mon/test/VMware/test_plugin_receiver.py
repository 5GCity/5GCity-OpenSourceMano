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

""" Mock tests for VMware vROPs plugin recevier """

import sys
#sys.path.append("/root/MON/")

import json

import logging

import unittest

import mock

import requests

import os

log = logging.getLogger(__name__)

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..",".."))

from osm_mon.plugins.vRealiseOps import plugin_receiver as monPluginRec


class Message(object):
    """A class to mock a message object value for alarm and matric requests"""

    def __init__(self):
        """Initialize a mocked message instance"""
        self.topic = "alarm_or_metric_request"
        self.key = None
        self.value = json.dumps({"mock_value": "mock_details"})
        self.partition = 1
        self.offset = 100


class TestPluginReceiver(unittest.TestCase):
    """Test class for Plugin Receiver class methods"""

    def setUp(self):
        """Setup the tests for plugin_receiver class methods"""
        super(TestPluginReceiver, self).setUp()
        self.plugin_receiver = monPluginRec.PluginReceiver()
        #self.mon_plugin = monPlugin.MonPlugin()

    @mock.patch.object(monPluginRec.PluginReceiver, 'publish_create_alarm_status')
    @mock.patch.object(monPluginRec.PluginReceiver, 'create_alarm')
    def test_consume_create_alarm_request_key(self, m_create_alarm, m_publish_create_alarm_status):
        """Test functionality of consume for create_alarm_request key"""

        # Mock a message
        msg = Message()
        msg.topic = "alarm_request"
        msg.key = "create_alarm_request"

        msg.value = json.dumps({"alarm_create_request":"alarm_details"})
        m_create_alarm.return_value = "test_alarm_id"

        config_alarm_info = json.loads(msg.value)

        # Call the consume method of plugin_receiver
        self.plugin_receiver.consume(msg)

        # verify if create_alarm and publish methods called with correct params
        m_create_alarm.assert_called_with("alarm_details")
        m_publish_create_alarm_status.assert_called_with("test_alarm_id", config_alarm_info)


    @mock.patch.object(monPluginRec.PluginReceiver, 'publish_update_alarm_status')
    @mock.patch.object(monPluginRec.PluginReceiver, 'update_alarm')
    def test_consume_update_alarm_request_key(self, m_update_alarm, m_publish_update_alarm_status):
        """Test functionality of consume for update_alarm_request key"""

        # Mock a message
        msg = Message()
        msg.topic = "alarm_request"
        msg.key = "update_alarm_request"

        msg.value = json.dumps({"alarm_update_request":"alarm_details"})

        # set return value to mocked method
        m_update_alarm.return_value = "test_alarm_id"

        update_alarm_info = json.loads(msg.value)

        # Call the consume method of plugin_receiver
        self.plugin_receiver.consume(msg)

        # verify update_alarm and publish method called with correct params
        m_update_alarm.assert_called_with("alarm_details")
        m_publish_update_alarm_status.assert_called_with("test_alarm_id", update_alarm_info)


    @mock.patch.object(monPluginRec.PluginReceiver, 'publish_delete_alarm_status')
    @mock.patch.object(monPluginRec.PluginReceiver, 'delete_alarm')
    def test_consume_delete_alarm_request_key(self, m_delete_alarm, m_publish_delete_alarm_status):
        """Test functionality of consume for delete_alarm_request key"""

        # Mock a message
        msg = Message()
        msg.topic = "alarm_request"
        msg.key = "delete_alarm_request"

        msg.value = json.dumps({"alarm_delete_request":"alarm_details"})
        m_delete_alarm.return_value = "test_alarm_id"

        delete_alarm_info = json.loads(msg.value)

        # Call the consume method of plugin_receiver and check delete_alarm request
        self.plugin_receiver.consume(msg)
        m_delete_alarm.assert_called_with("alarm_details")

        # Check if publish method called with correct parameters
        m_publish_delete_alarm_status.assert_called_with("test_alarm_id", delete_alarm_info)


    @mock.patch.object(monPluginRec.PluginReceiver, 'publish_list_alarm_response')
    @mock.patch.object(monPluginRec.PluginReceiver, 'list_alarms')
    def test_consume_list_alarm_request_key(self, m_list_alarms, m_publish_list_alarm_response):
        """ Test functionality of list alarm request key"""

        # Mock a message
        msg = Message()
        msg.topic = "alarm_request"
        msg.key = "list_alarm_request"
        test_alarm_list = [{"alarm_uuid":"alarm1_details"},{"alarm_uuid":"alarm2_details"}]

        msg.value = json.dumps({"alarm_list_request":"alarm_details"})
        m_list_alarms.return_value = test_alarm_list

        list_alarms_info = json.loads(msg.value)

        # Call the consume method of plugin_receiver and check delete_alarm request
        self.plugin_receiver.consume(msg)
        m_list_alarms.assert_called_with("alarm_details")

        # Check if publish method called with correct parameters
        m_publish_list_alarm_response.assert_called_with(test_alarm_list, list_alarms_info)


    @mock.patch.object(monPluginRec.PluginReceiver, 'publish_access_update_response')
    @mock.patch.object(monPluginRec.PluginReceiver, 'update_access_credentials')
    def test_consume_vim_access_request_key(self, m_update_access_credentials, m_publish_access_update_response):
        """Test functionality of consume for vim_access_credentials request key"""

        # Mock a message
        msg = Message()
        msg.topic = "access_credentials"
        msg.key = "vim_access_credentials"

        msg.value = json.dumps({"access_config":"access_details"})
        # set return value to mocked method
        m_update_access_credentials.return_value = True

        access_info = json.loads(msg.value)

        # Call the consume method of plugin_receiver
        self.plugin_receiver.consume(msg)

        # check if mocked method called with required parameters
        m_update_access_credentials.assert_called_with("access_details")

        # Check if publish method called with correct parameters
        m_publish_access_update_response.assert_called_with(True, access_info)


    @mock.patch.object(monPluginRec.PluginReceiver, 'publish_create_alarm_status')
    @mock.patch.object(monPluginRec.PluginReceiver, 'create_alarm')
    def test_consume_invalid_alarm_request_key(self, m_create_alarm, m_publish_create_alarm_status):
        """Test functionality of consume for vim_access_credentials invalid request key"""

        # Mock a message with invalid alarm request key
        msg = Message()
        msg.topic = "alarm_request"
        msg.key = "invalid_alarm_request" # invalid key

        # Call the consume method of plugin_receiver
        self.plugin_receiver.consume(msg)

        # verify that create_alarm and publish_create_alarm_status methods not called
        m_create_alarm.assert_not_called()
        m_publish_create_alarm_status.assert_not_called()


    @mock.patch.object(monPluginRec.PluginReceiver, 'publish_metrics_data_status')
    @mock.patch.object(monPluginRec.MonPlugin, 'get_metrics_data')
    def test_consume_invalid_metric_request_key(self, m_get_metrics_data, m_publish_metric_data_status):
        """Test functionality of invalid metric key request"""

        # Mock a message with invalid metric request key
        msg = Message()
        msg.topic = "metric_request"
        msg.key = "invalid_metric_data_request" #invalid key

        # Call the consume method of plugin_receiver
        self.plugin_receiver.consume(msg)

        # verify that get martics data and publish methods not called
        m_get_metrics_data.assert_not_called()
        m_publish_metric_data_status.assert_not_called()


    @mock.patch.object(monPluginRec.PluginReceiver, 'publish_metrics_data_status')
    @mock.patch.object(monPluginRec.MonPlugin, 'get_metrics_data')
    def test_consume_read_metric_data_request_key(self, m_get_metrics_data, m_publish_metric_data_status):
        """Test functionality of consume for read_metric_data_request key"""

        # Mock a message
        msg = Message()
        msg.topic = "metric_request"
        msg.key = "read_metric_data_request"

        msg.value = json.dumps({"metric_name":"metric_details"})
        m_get_metrics_data.return_value = {"metrics_data":"metrics_details"}

        metric_request_info = json.loads(msg.value)

        # Call the consume method of plugin_receiver
        self.plugin_receiver.consume(msg)
        m_get_metrics_data.assert_called_with(metric_request_info)

        # Check if publish method called with correct parameters
        m_publish_metric_data_status.assert_called_with({"metrics_data":"metrics_details"})


    @mock.patch.object(monPluginRec.PluginReceiver, 'publish_create_metric_response')
    @mock.patch.object(monPluginRec.PluginReceiver, 'verify_metric')
    def test_consume_create_metric_request_key(self, m_verify_metric, m_publish_create_metric_response):
        """Test functionality of consume for create_metric_request key"""

        # Mock a message
        msg = Message()
        msg.topic = "metric_request"
        msg.key = "create_metric_request"

        msg.value = json.dumps({"metric_create":"metric_details"})

        # set the return value
        m_verify_metric.return_value = True

        metric_info = json.loads(msg.value)

        # Call the consume method of plugin_receiver
        self.plugin_receiver.consume(msg)
        m_verify_metric.assert_called_with("metric_details")

        # Check if publish method called with correct parameters
        m_publish_create_metric_response.assert_called_with(metric_info, True)


    @mock.patch.object(monPluginRec.PluginReceiver, 'publish_update_metric_response')
    @mock.patch.object(monPluginRec.PluginReceiver, 'verify_metric')
    def test_consume_update_metric_request_key(self, m_verify_metric, m_publish_update_metric_response):
        """Test functionality of update metric request key"""

        # Mock a message
        msg = Message()
        msg.topic = "metric_request"
        msg.key = "update_metric_request"

        msg.value = json.dumps({"metric_create":"metric_details"})

        # set the return value
        m_verify_metric.return_value = True

        metric_info = json.loads(msg.value)

        # Call the consume method of plugin_receiver
        self.plugin_receiver.consume(msg)

        # verify mocked methods called with correct parameters
        m_verify_metric.assert_called_with("metric_details")
        m_publish_update_metric_response.assert_called_with(metric_info, True)


    @mock.patch.object(monPluginRec.PluginReceiver, 'publish_delete_metric_response')
    def test_consume_delete_metric_request_key(self, m_publish_delete_metric_response):
        """Test functionality of consume for delete_metric_request key"""

        # Note: vROPS doesn't support deleting metric data
        # Mock a message
        msg = Message()
        msg.topic = "metric_request"
        msg.key = "delete_metric_request"

        msg.value = json.dumps({"metric_name":"metric_details"})

        metric_info = json.loads(msg.value)

        # Call the consume method of plugin_receiver
        self.plugin_receiver.consume(msg)

        # Check if publish method called with correct parameters
        m_publish_delete_metric_response.assert_called_with(metric_info)


    @mock.patch.object(monPluginRec.MonPlugin, 'configure_alarm')
    @mock.patch.object(monPluginRec.MonPlugin, 'configure_rest_plugin')
    def test_create_alarm_successful(self, m_configure_rest_plugin, m_configure_alarm):
        """ Test functionality of create alarm method-positive case"""

        # Mock config_alarm_info
        config_alarm_info = {"correlation_id": 1,
                             "alarm_name": "CPU_Utilize_Threshold",
                             "metric_name": "CPU_UTILIZATION",
                             "tenant_uuid": "tenant_uuid",
                             "resource_uuid": "resource_uuid",
                             "description": "test_create_alarm",
                             "severity": "CRITICAL",
                             "operation": "GT",
                             "threshold_value": 10,
                             "unit": "%",
                             "statistic": "AVERAGE"}

        # set return value to plugin uuid
        m_configure_rest_plugin.retrun_value = "plugin_uuid"
        m_configure_alarm.return_value = "alarm_uuid"

        # call create alarm method under test
        self.plugin_receiver.create_alarm(config_alarm_info)

        # verify mocked methods get called with correct params
        m_configure_rest_plugin.assert_called_with()
        m_configure_alarm.assert_called_with(config_alarm_info)


    @mock.patch.object(monPluginRec.MonPlugin, 'configure_alarm')
    @mock.patch.object(monPluginRec.MonPlugin, 'configure_rest_plugin')
    def test_create_alarm_failed(self, m_configure_rest_plugin, m_configure_alarm):
        """ Test functionality of create alarm method negative case"""

        # Mock config_alarm_info
        config_alarm_info = {"correlation_id": 1,
                             "alarm_name": "CPU_Utilize_Threshold",
                             "metric_name": "CPU_UTILIZATION",
                             "tenant_uuid": "tenant_uuid",
                             "resource_uuid": "resource_uuid",
                             "description": "test_create_alarm",
                             "severity": "CRITICAL",
                             "operation": "GT",
                             "threshold_value": 10,
                             "unit": "%",
                             "statistic": "AVERAGE"}

        # set return value to plugin uuid and alarm_uuid to None
        m_configure_rest_plugin.retrun_value = "plugin_uuid"
        m_configure_alarm.return_value = None

        # call create alarm method under test
        alarm_uuid = self.plugin_receiver.create_alarm(config_alarm_info)

        # verify mocked method called with correct params
        m_configure_rest_plugin.assert_called_with()
        m_configure_alarm.assert_called_with(config_alarm_info)

        # verify create alarm method returns None when failed
        self.assertEqual(alarm_uuid, None)


    @mock.patch.object(monPluginRec.MonPlugin, 'update_alarm_configuration')
    def test_update_alarm_successful(self, m_update_alarm_configuration):
        """ Test functionality of update alarm method-positive case"""

        # Mock update_alarm_info
        update_alarm_info = {'alarm_uuid': 'abc', 'correlation_id': 14203}

        # set return value to mocked method
        m_update_alarm_configuration.return_value = "alarm_uuid"

        # check update alarm gets called and returned correct value
        ret_value = self.plugin_receiver.update_alarm(update_alarm_info)

        # check mocked method get called with correct param
        m_update_alarm_configuration.assert_called_with(update_alarm_info)

        # check return value and passed values are correct
        self.assertEqual(ret_value, "alarm_uuid")


    @mock.patch.object(monPluginRec.MonPlugin, 'update_alarm_configuration')
    def test_update_alarm_failed(self, m_update_alarm_configuration):
        """ Test functionality of update alarm method negative case"""

        # Mock update_alarm_info
        update_alarm_info = {'alarm_uuid': 'abc', 'correlation_id': 14203}

        # set return value to mocked method
        m_update_alarm_configuration.return_value = None

        # check update alarm gets called and returned correct value
        ret_value = self.plugin_receiver.update_alarm(update_alarm_info)

        # check mocked method get called with correct param
        m_update_alarm_configuration.assert_called_with(update_alarm_info)

        # check return value and passed values are correct
        self.assertEqual(ret_value, None)


    @mock.patch.object(monPluginRec.MonPlugin, 'delete_alarm_configuration')
    def test_delete_alarm_successful(self, m_delete_alarm_configuration):
        """ Test functionality of delete alarm method-positive case"""

        # Mock delete_alarm_info
        delete_alarm_info = {'alarm_uuid': 'abc', 'correlation_id': 14203}

        # set return value to mocked method
        m_delete_alarm_configuration.return_value = "alarm_uuid"

        # check delete alarm gets called and returned correct value
        ret_value = self.plugin_receiver.delete_alarm(delete_alarm_info)

        # check mocked method get called with correct param
        m_delete_alarm_configuration.assert_called_with(delete_alarm_info)

        # check return value and passed values are correct
        self.assertEqual(ret_value, "alarm_uuid")


    @mock.patch.object(monPluginRec.MonPlugin, 'delete_alarm_configuration')
    def test_delete_alarm_failed(self, m_delete_alarm_configuration):
        """ Test functionality of delete alarm method-negative case"""

        # Mock update_alarm_info
        delete_alarm_info = {'alarm_uuid': 'abc', 'correlation_id': 14203}

        # set return value to mocked method
        m_delete_alarm_configuration.return_value = None

        # check delete alarm gets called and returned correct value
        ret_value = self.plugin_receiver.delete_alarm(delete_alarm_info)

        # check mocked method get called with correct param
        m_delete_alarm_configuration.assert_called_with(delete_alarm_info)

        # check return value to check failed status
        self.assertEqual(ret_value, None)


    @mock.patch.object(monPluginRec.KafkaProducer, 'publish')
    def test_publish_create_alarm_status(self, m_publish):
        """ Test functionality of publish create alarm status method"""

        # Mock config_alarm_info
        config_alarm_info = {'vim_type': 'VMware',
                             'alarm_create_request': {'threshold_value': 0,
                                                      'severity': 'CRITICAL',
                                                      'alarm_name': 'CPU_Utilization_Above_Threshold',
                                                      'resource_uuid': 'e14b203c-6bf2-4e2f-a91c-8c19d240eda4',
                                                      'correlation_id': 1234,
                                                      'statistic': 'AVERAGE',
                                                      'metric_name': 'CPU_UTILIZATION'}
                            }

        alarm_uuid = "xyz"

        # call publish create status method under test
        self.plugin_receiver.publish_create_alarm_status(alarm_uuid, config_alarm_info)

        # verify mocked method called with correct params
        m_publish.assert_called_with(key='create_alarm_response', value=mock.ANY, topic='alarm_response')


    @mock.patch.object(monPluginRec.KafkaProducer, 'publish')
    def test_publish_update_alarm_status(self, m_publish):
        """ Test functionality of publish update alarm status method"""

        # Mock update_alarm_info
        update_alarm_info = {'vim_type' : 'VMware',
                             'alarm_update_request':{'alarm_uuid': '6486e69',
                                                     'correlation_id': 14203,
                                                     'operation': 'GT'
                                                     },
                             'schema_type': 'update_alarm_request'
                            }

        alarm_uuid = "xyz"

        # call publish update alarm status method under test
        self.plugin_receiver.publish_update_alarm_status(alarm_uuid, update_alarm_info)

        # verify mocked method called with correct params
        m_publish.assert_called_with(key='update_alarm_response', value=mock.ANY, topic='alarm_response')


    @mock.patch.object(monPluginRec.KafkaProducer, 'publish')
    def test_publish_delete_alarm_status(self, m_publish):
        """ Test functionality of publish delete alarm status method"""

        # Mock delete_alarm_info
        delete_alarm_info = {'vim_type' : 'VMware',
                             'alarm_delete_request':{'alarm_uuid': '6486e69',
                                                     'correlation_id': 14203,
                                                     'operation': 'GT'
                                                     },
                             'schema_type': 'delete_alarm_request'
                            }

        alarm_uuid = "xyz"

        # call publish delete alarm status method under test
        self.plugin_receiver.publish_delete_alarm_status(alarm_uuid, delete_alarm_info)

        # verify mocked method called with correct params
        m_publish.assert_called_with(key='delete_alarm_response', value=mock.ANY, topic='alarm_response')


    @mock.patch.object(monPluginRec.KafkaProducer, 'publish')
    def test_publish_metrics_data_status(self, m_publish):
        """ Test functionality of publish metrics data status method"""

        # Mock metrics data
        metrics_data = {
                        'metric_name': 'CPU_UTILIZATION', 'metric_uuid': '0',
                        'resource_uuid': 'e14b20', 'correlation_id': 'e14b2',
                        'metrics_data': {'time_series': [15162011, 15162044],
                        'metrics_series': [0.1166666671, 0.1266666650]},
                        'tenant_uuid': 123, 'unit': '%'
                       }

        # call publish metrics data status method under test
        self.plugin_receiver.publish_metrics_data_status(metrics_data)

        # verify mocked method called with correct params
        m_publish.assert_called_with(key='read_metric_data_response', value=mock.ANY, topic='metric_response')


    @mock.patch.object(monPluginRec.MonPlugin, 'verify_metric_support')
    def test_verify_metric_supported_metric(self, m_verify_metric_support):
        """ Test functionality of verify matric method"""

        # mock metric_info
        metric_info = {'metric_unit': '%', 'metric_name': 'CPU_UTILIZATION', 'resource_uuid': 'e14b203'}

        # set mocked function retrun value to true
        m_verify_metric_support.return_value = True

        # call verify_metric method under test
        ret_value = self.plugin_receiver.verify_metric(metric_info)

        # verify mocked method called with correct params
        m_verify_metric_support.assert_called_with(metric_info)

        # verify the return value
        self.assertEqual(ret_value, True)


    @mock.patch.object(monPluginRec.MonPlugin, 'verify_metric_support')
    def test_verify_metric_unsupported_metric(self, m_verify_metric_support):
        """ Test functionality of verify matric method-negative case"""

        # mock metric_info with unsupported matrics name
        metric_info = {'metric_unit': '%', 'metric_name': 'Invalid', 'resource_uuid': 'e14b203'}

        # set mocked function retrun value to true
        m_verify_metric_support.return_value = False

        # call verify_metric method under test
        ret_value = self.plugin_receiver.verify_metric(metric_info)

        # verify mocked method called with correct params
        m_verify_metric_support.assert_called_with(metric_info)

        # verify the return value
        self.assertEqual(ret_value, False)


    @mock.patch.object(monPluginRec.KafkaProducer, 'publish')
    def test_publish_create_metric_response(self, m_publish):
        """ Test functionality of publish create metric response method"""

        # Mock metric_info
        metric_info = {'vim_type' : 'VMware','correlation_id': 'e14b203c',
                       'metric_create':{
                                        'resource_uuid': '6486e69',
                                        'metric_name': 'CPU_UTILIZATION',
                                        'metric_unit': '%'
                                        },
                        'schema_type': 'create_metric_request'
                       }

        metric_status = True

        # call publish create metric method under test
        self.plugin_receiver.publish_create_metric_response(metric_info, metric_status)

        # verify mocked method called with correct params
        m_publish.assert_called_with(key='create_metric_response', value=mock.ANY, topic='metric_response')


    @mock.patch.object(monPluginRec.KafkaProducer, 'publish')
    def test_publish_update_metric_response(self, m_publish):
        """ Test functionality of publish update metric response method"""

        # Mock metric_info
        metric_info = {'vim_type' : 'VMware','correlation_id': 'e14b203c',
                       'metric_create':{
                                        'resource_uuid': '6486e69',
                                        'metric_name': 'CPU_UTILIZATION',
                                        'metric_unit': '%'
                                        },
                        'schema_type': 'update_metric_request'
                       }

        metric_status = True

        # call publish update metric method under test
        self.plugin_receiver.publish_update_metric_response(metric_info, metric_status)

        # verify mocked method called with correct params
        m_publish.assert_called_with(key='update_metric_response', value=mock.ANY, topic='metric_response')


    @mock.patch.object(monPluginRec.KafkaProducer, 'publish')
    def test_publish_delete_metric_response(self, m_publish):
        """ Test functionality of publish delete metric response method"""

        # Mock metric_info
        metric_info = {'vim_type' : 'VMware','correlation_id': 'e14b203c',
                       'metric_uuid': 'e14b203c', 'resource_uuid': '6486e69',
                       'metric_name': 'CPU_UTILIZATION',
                       'schema_type': 'delete_metric_request'}

        metric_status = True

        # call publish delete metric method under test-vROPS doesn't support
        # delete metric,just returns responce with success
        self.plugin_receiver.publish_delete_metric_response(metric_info)

        # verify mocked method called with correct params
        m_publish.assert_called_with(key='delete_metric_response', value=mock.ANY, topic='metric_response')


    @mock.patch.object(monPluginRec.MonPlugin, 'get_triggered_alarms_list')
    def test_list_alarms(self, m_get_triggered_alarms_list):
        """ Test functionality of list alarms method"""

        # Mock list alarm input
        list_alarm_input = {'severity': 'CRITICAL',
                            'correlation_id': 'e14b203c',
                            'alarm_name': 'CPU_Utilization_Above_Threshold',
                            'resource_uuid': 'd14b203c'}

        # set return value to mocked method
        m_return = m_get_triggered_alarms_list.return_value = [{'status': 'ACTIVE', 'update_date': '2018-01-12T08:34:05',
                                                                'severity': 'CRITICAL', 'resource_uuid': 'e14b203c',
                                                                'cancel_date': '0000-00-00T00:00:00','alarm_instance_uuid': 'd9e3bc84',
                                                                'alarm_uuid': '5714977d', 'vim_type': 'VMware',
                                                                'start_date': '2018-01-12T08:34:05'},
                                                               {'status': 'CANCELED', 'update_date': '2017-12-20T09:37:57',
                                                                'severity': 'CRITICAL', 'resource_uuid': 'e14b203c',
                                                                'cancel_date': '2018-01-12T06:49:19', 'alarm_instance_uuid': 'd3bbeef6',
                                                                'alarm_uuid': '7ba1bf3e', 'vim_type': 'VMware',
                                                                'start_date': '2017-12-20T09:37:57'}]

        # call list alarms method under test
        return_value = self.plugin_receiver.list_alarms(list_alarm_input)

        # verify mocked method called with correct params
        m_get_triggered_alarms_list.assert_called_with(list_alarm_input)

        # verify list alarm method returns correct list
        self.assertEqual(return_value, m_return)


    @mock.patch.object(monPluginRec.KafkaProducer, 'publish')
    def test_publish_list_alarm_response(self, m_publish):
        """ Test functionality of publish list alarm response method"""

        # Mock list alarm input
        msg_key = 'list_alarm_response'
        topic = 'alarm_response'
        list_alarm_input = {'alarm_list_request': {'severity': 'CRITICAL',
                            'correlation_id': 'e14b203c',
                            'alarm_name': 'CPU_Utilization_Above_Threshold',
                            'resource_uuid': 'd14b203c'},'vim_type' : 'VMware'}

        triggered_alarm_list = [{'status': 'ACTIVE', 'update_date': '2018-01-12T08:34:05', 'severity': 'CRITICAL',
                                 'resource_uuid': 'e14b203c', 'cancel_date': '0000-00-00T00:00:00','alarm_instance_uuid': 'd9e3bc84',
                                 'alarm_uuid': '5714977d', 'vim_type': 'VMware', 'start_date': '2018-01-12T08:34:05'}]

        # call publish list alarm response method under test
        self.plugin_receiver.publish_list_alarm_response(triggered_alarm_list, list_alarm_input)

        # verify mocked method called with correct params
        m_publish.assert_called_with(key=msg_key,value=mock.ANY, topic=topic)


    @mock.patch.object(monPluginRec.KafkaProducer, 'publish')
    def test_publish_access_update_response(self, m_publish):
        """ Test functionality of publish access update response method"""

        # Mock required inputs
        access_update_status = True
        msg_key = 'vim_access_credentials_response'
        topic = 'access_credentials'
        access_info_req = {'access_config': {'vrops_password': 'vmware', 'vcloud-site': 'https://192.169.241.105',
                           'vrops_user': 'Admin', 'correlation_id': 'e14b203c', 'tenant_id': 'Org2'}, 'vim_type': u'VMware'}

        # call publish access update response method under test
        self.plugin_receiver.publish_access_update_response(access_update_status, access_info_req)

        # verify mocked method called with correct params
        m_publish.assert_called_with(key=msg_key ,value=mock.ANY, topic=topic)


    @mock.patch.object(monPluginRec.PluginReceiver, 'write_access_config')
    def test_update_access_credentials_successful(self, m_write_access_config):
        """ Test functionality of update access credentials-positive case"""

        # Mock access_info
        access_info = {'vrops_site':'https://192.169.241.13','vrops_user':'admin', 'vrops_password':'vmware',
                       'vcloud-site':'https://192.169.241.15','admin_username':'admin','admin_password':'vmware',
                       'vcenter_ip':'192.169.241.13','vcenter_port':'443','vcenter_user':'admin','vcenter_password':'vmware',
                       'vim_tenant_name':'Org2','orgname':'Org2','tenant_id':'Org2'}

        # Mock return values
        expected_status = m_write_access_config.return_value = True

        # call publish update acccess credentials method under test
        actual_status = self.plugin_receiver.update_access_credentials(access_info)

        # check write_access_config called with correct params
        m_write_access_config.assert_called_with(access_info)

        # verify update access credentials returns correct status
        self.assertEqual(expected_status, actual_status)


    @mock.patch.object(monPluginRec.PluginReceiver, 'write_access_config')
    def test_update_access_credentials_less_config_params(self, m_write_access_config):
        """ Test functionality of update access credentials-negative case"""

        # Mock access_info
        access_info = {'vrops_site':'https://192.169.241.13','vrops_user':'admin', 'vrops_password':'vmware',
                       'vcloud-site':'https://192.169.241.15','admin_username':'admin','admin_password':'vmware',
                       'vcenter_ip':'192.169.241.13','vcenter_port':'443','vcenter_user':'admin',
                       'vim_tenant_name':'Org2','orgname':'Org2','tenant_id':'Org2'}

        # Mock return values
        expected_status = m_write_access_config.return_value = False

        # call publish update acccess credentials method under test
        actual_status = self.plugin_receiver.update_access_credentials(access_info)

        # check if mocked method not called
        m_write_access_config.assert_not_called()

        # verify update access credentials returns correct status
        self.assertEqual(expected_status, actual_status)


    @mock.patch.object(monPluginRec.PluginReceiver, 'write_access_config')
    def test_update_access_credentials_failed(self, m_write_access_config):
        """ Test functionality of update access credentials-failed case """

        # Mock access_info
        access_info = {'vrops_site':'https://192.169.241.13','vrops_user':'admin', 'vrops_password':'vmware',
                       'vcloud-site':'https://192.169.241.15','admin_username':'admin','admin_password':'vmware',
                       'vcenter_ip':'192.169.241.13','vcenter_port':'443','vcenter_user':'admin','vcenter_password':'vmware',
                       'vim_tenant_name':'Org2','orgname':'Org2','tenant_id':'Org2'}

        # Mock return values
        expected_status = m_write_access_config.return_value = False

        # call publish update acccess credentials method under test
        actual_status = self.plugin_receiver.update_access_credentials(access_info)

        # check write_access_config called with correct params
        m_write_access_config.assert_called_with(access_info)

        # verify update access credentials returns correct status
        self.assertEqual(expected_status, actual_status)


    def test_write_access_config_successful(self):
        """ Test functionality of write access config method-positive case"""

        # Mock access_info
        access_info = {'vrops_sit':'https://192.169.241.13','vrops_user':'admin', 'vrops_password':'vmware',
                       'vcloud-site':'https://192.169.241.15','admin_username':'admin','admin_password':'vmware',
                       'vcenter_ip':'192.169.241.13','vcenter_port':'443','vcenter_user':'admin','vcenter_password':'vmware',
                       'vim_tenant_name':'Org2','orgname':'Org2','tenant_id':'Org2'}

        # call write acccess config method under test
        actual_status = self.plugin_receiver.write_access_config(access_info)

        # verify write access config returns correct status
        self.assertEqual(True, actual_status)


    def test_write_access_config_failed(self):
        """ Test functionality of write access config method-negative case"""

        # Mock access_info
        access_info = [] # provided incorrect info to generate error

        # call write acccess config method under test
        actual_status = self.plugin_receiver.write_access_config(access_info)

        # verify write access config returns correct status
        self.assertEqual(False, actual_status)


# For testing purpose
#if __name__ == '__main__':

#    unittest.main()

