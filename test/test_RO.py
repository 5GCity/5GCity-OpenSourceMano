#!/usr/bin/env python2
# -*- coding: utf-8 -*-

##
# Copyright 2015 Telefónica Investigación y Desarrollo, S.A.U.
# This file is part of openmano
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
# contact with: nfvlabs@tid.es
##

'''
Module for testing openmano functionality. It uses openmanoclient.py for invoking openmano
'''
__author__="Pablo Montes"
__date__ ="$16-Feb-2017 17:08:16$"
__version__="0.0.1"
version_date="Feb 2017"

import logging
import imp
import os
from optparse import OptionParser
import unittest
import string
import inspect
import random
import traceback
import glob
import yaml
import sys
import time

global test_number
global test_directory
global scenario_test_folder
global test_image_name
global management_network

'''
IMPORTANT NOTE
All unittest classes for code based tests must have prefix 'test_' in order to be taken into account for tests
'''
class test_tenant_operations(unittest.TestCase):
    test_index = 1
    tenant_name = None
    test_text = None

    @classmethod
    def setUpClass(cls):
        logger.info("{}. {}".format(test_number, cls.__name__))

    @classmethod
    def tearDownClass(cls):
        globals().__setitem__('test_number', globals().__getitem__('test_number') + 1)

    def tearDown(self):
        exec_info = sys.exc_info()
        if exec_info == (None, None, None):
            logger.info(self.__class__.test_text+" -> TEST OK")
        else:
            logger.warning(self.__class__.test_text+" -> TEST NOK")
            error_trace = traceback.format_exception(exec_info[0], exec_info[1], exec_info[2])
            msg = ""
            for line in error_trace:
                msg = msg + line
            logger.critical("{}".format(msg))

    def test_000_create_RO_tenant(self):
        self.__class__.tenant_name = _get_random_string(20)
        self.__class__.test_text = "{}.{}. TEST {}".format(test_number, self.__class__.test_index,
                                                           inspect.currentframe().f_code.co_name)
        self.__class__.test_index += 1
        tenant = client.create_tenant(name=self.__class__.tenant_name, description=self.__class__.tenant_name)
        logger.debug("{}".format(tenant))
        self.assertEqual(tenant.get('tenant', {}).get('name', ''), self.__class__.tenant_name)

    def test_010_list_RO_tenant(self):
        self.__class__.test_text = "{}.{}. TEST {}".format(test_number, self.__class__.test_index,
                                                           inspect.currentframe().f_code.co_name)
        self.__class__.test_index += 1
        tenant = client.get_tenant(name=self.__class__.tenant_name)
        logger.debug("{}".format(tenant))
        self.assertEqual(tenant.get('tenant', {}).get('name', ''), self.__class__.tenant_name)

    def test_020_delete_RO_tenant(self):
        self.__class__.test_text = "{}.{}. TEST {}".format(test_number, self.__class__.test_index,
                                                           inspect.currentframe().f_code.co_name)
        self.__class__.test_index += 1
        tenant = client.delete_tenant(name=self.__class__.tenant_name)
        logger.debug("{}".format(tenant))
        assert('deleted' in tenant.get('result',""))

class test_datacenter_operations(unittest.TestCase):
    test_index = 1
    datacenter_name = None
    test_text = None

    @classmethod
    def setUpClass(cls):
        logger.info("{}. {}".format(test_number, cls.__name__))

    @classmethod
    def tearDownClass(cls):
        globals().__setitem__('test_number', globals().__getitem__('test_number') + 1)

    def tearDown(self):
        exec_info = sys.exc_info()
        if exec_info == (None, None, None):
            logger.info(self.__class__.test_text+" -> TEST OK")
        else:
            logger.warning(self.__class__.test_text+" -> TEST NOK")
            error_trace = traceback.format_exception(exec_info[0], exec_info[1], exec_info[2])
            msg = ""
            for line in error_trace:
                msg = msg + line
            logger.critical("{}".format(msg))

    def test_000_create_datacenter(self):
        self.__class__.test_text = "{}.{}. TEST {}".format(test_number, self.__class__.test_index,
                                                           inspect.currentframe().f_code.co_name)
        self.__class__.datacenter_name = _get_random_string(20)
        self.__class__.test_index += 1
        self.datacenter = client.create_datacenter(name=self.__class__.datacenter_name, vim_url="http://fakeurl/fake")
        logger.debug("{}".format(self.datacenter))
        self.assertEqual (self.datacenter.get('datacenter', {}).get('name',''), self.__class__.datacenter_name)

    def test_010_list_datacenter(self):
        self.__class__.test_text = "{}.{}. TEST {}".format(test_number, self.__class__.test_index,
                                                           inspect.currentframe().f_code.co_name)

        self.__class__.test_index += 1
        self.datacenter = client.get_datacenter(all_tenants=True, name=self.__class__.datacenter_name)
        logger.debug("{}".format(self.datacenter))
        self.assertEqual (self.datacenter.get('datacenter', {}).get('name', ''), self.__class__.datacenter_name)

    def test_020_attach_datacenter(self):
        self.__class__.test_text = "{}.{}. TEST {}".format(test_number, self.__class__.test_index,
                                                           inspect.currentframe().f_code.co_name)

        self.__class__.test_index += 1
        self.datacenter = client.attach_datacenter(name=self.__class__.datacenter_name, vim_tenant_name='fake')
        logger.debug("{}".format(self.datacenter))
        assert ('vim_tenants' in self.datacenter.get('datacenter', {}))

    def test_030_list_attached_datacenter(self):
        self.__class__.test_text = "{}.{}. TEST {}".format(test_number, self.__class__.test_index,
                                                           inspect.currentframe().f_code.co_name)

        self.__class__.test_index += 1
        self.datacenter = client.get_datacenter(all_tenants=False, name=self.__class__.datacenter_name)
        logger.debug("{}".format(self.datacenter))
        self.assertEqual (self.datacenter.get('datacenter', {}).get('name', ''), self.__class__.datacenter_name)

    def test_040_detach_datacenter(self):
        self.__class__.test_text = "{}.{}. TEST {}".format(test_number, self.__class__.test_index,
                                                           inspect.currentframe().f_code.co_name)

        self.__class__.test_index += 1
        self.datacenter = client.detach_datacenter(name=self.__class__.datacenter_name)
        logger.debug("{}".format(self.datacenter))
        assert ('detached' in self.datacenter.get('result', ""))

    def test_050_delete_datacenter(self):
        self.__class__.test_text = "{}.{}. TEST {}".format(test_number, self.__class__.test_index,
                                                           inspect.currentframe().f_code.co_name)

        self.__class__.test_index += 1
        self.datacenter = client.delete_datacenter(name=self.__class__.datacenter_name)
        logger.debug("{}".format(self.datacenter))
        assert('deleted' in self.datacenter.get('result',""))

class test_VIM_network_operations(unittest.TestCase):
    test_index = 1
    vim_network_name = None
    test_text = None
    vim_network_uuid = None

    @classmethod
    def setUpClass(cls):
        logger.info("{}. {}".format(test_number, cls.__name__))

    @classmethod
    def tearDownClass(cls):
        globals().__setitem__('test_number', globals().__getitem__('test_number') + 1)

    def tearDown(self):
        exec_info = sys.exc_info()
        if exec_info == (None, None, None):
            logger.info(self.__class__.test_text + " -> TEST OK")
        else:
            logger.warning(self.__class__.test_text + " -> TEST NOK")
            error_trace = traceback.format_exception(exec_info[0], exec_info[1], exec_info[2])
            msg = ""
            for line in error_trace:
                msg = msg + line
            logger.critical("{}".format(msg))

    def test_000_create_VIM_network(self):
        self.__class__.test_text = "{}.{}. TEST {}".format(test_number, self.__class__.test_index,
                                                           inspect.currentframe().f_code.co_name)
        self.__class__.vim_network_name = _get_random_string(20)
        self.__class__.test_index += 1
        network = client.vim_action("create", "networks", name=self.__class__.vim_network_name)
        logger.debug("{}".format(network))
        self.__class__.vim_network_uuid = network["network"]["id"]
        self.assertEqual(network.get('network', {}).get('name', ''), self.__class__.vim_network_name)

    def test_010_list_VIM_networks(self):
        self.__class__.test_text = "{}.{}. TEST {}".format(test_number, self.__class__.test_index,
                                                           inspect.currentframe().f_code.co_name)
        self.__class__.test_index += 1
        networks = client.vim_action("list", "networks")
        logger.debug("{}".format(networks))

    def test_020_get_VIM_network_by_uuid(self):
        self.__class__.test_text = "{}.{}. TEST {}".format(test_number, self.__class__.test_index,
                                                           inspect.currentframe().f_code.co_name)

        self.__class__.test_index += 1
        network = client.vim_action("show", "networks", uuid=self.__class__.vim_network_uuid)
        logger.debug("{}".format(network))
        self.assertEqual(network.get('network', {}).get('name', ''), self.__class__.vim_network_name)

    def test_030_delete_VIM_network_by_uuid(self):
        self.__class__.test_text = "{}.{}. TEST {}".format(test_number, self.__class__.test_index,
                                                           inspect.currentframe().f_code.co_name)

        self.__class__.test_index += 1
        network = client.vim_action("delete", "networks", uuid=self.__class__.vim_network_uuid)
        logger.debug("{}".format(network))
        assert ('deleted' in network.get('result', ""))

class test_VIM_image_operations(unittest.TestCase):
    test_index = 1
    test_text = None

    @classmethod
    def setUpClass(cls):
        logger.info("{}. {}".format(test_number, cls.__name__))

    @classmethod
    def tearDownClass(cls):
        globals().__setitem__('test_number', globals().__getitem__('test_number') + 1)

    def tearDown(self):
        exec_info = sys.exc_info()
        if exec_info == (None, None, None):
            logger.info(self.__class__.test_text + " -> TEST OK")
        else:
            logger.warning(self.__class__.test_text + " -> TEST NOK")
            error_trace = traceback.format_exception(exec_info[0], exec_info[1], exec_info[2])
            msg = ""
            for line in error_trace:
                msg = msg + line
            logger.critical("{}".format(msg))

    def test_000_list_VIM_images(self):
        self.__class__.test_text = "{}.{}. TEST {}".format(test_number, self.__class__.test_index,
                                                           inspect.currentframe().f_code.co_name)
        self.__class__.test_index += 1
        images = client.vim_action("list", "images")
        logger.debug("{}".format(images))

'''
The following is a non critical test that will fail most of the times.
In case of OpenStack datacenter these tests will only success if RO has access to the admin endpoint
This test will only be executed in case it is specifically requested by the user
'''
class test_VIM_tenant_operations(unittest.TestCase):
    test_index = 1
    vim_tenant_name = None
    test_text = None
    vim_tenant_uuid = None

    @classmethod
    def setUpClass(cls):
        logger.info("{}. {}".format(test_number, cls.__name__))
        logger.warning("In case of OpenStack datacenter these tests will only success "
                       "if RO has access to the admin endpoint")

    @classmethod
    def tearDownClass(cls):
        globals().__setitem__('test_number', globals().__getitem__('test_number') + 1)

    def tearDown(self):
        exec_info = sys.exc_info()
        if exec_info == (None, None, None):
            logger.info(self.__class__.test_text + " -> TEST OK")
        else:
            logger.warning(self.__class__.test_text + " -> TEST NOK")
            error_trace = traceback.format_exception(exec_info[0], exec_info[1], exec_info[2])
            msg = ""
            for line in error_trace:
                msg = msg + line
            logger.critical("{}".format(msg))

    def test_000_create_VIM_tenant(self):
        self.__class__.test_text = "{}.{}. TEST {}".format(test_number, self.__class__.test_index,
                                                           inspect.currentframe().f_code.co_name)
        self.__class__.vim_tenant_name = _get_random_string(20)
        self.__class__.test_index += 1
        tenant = client.vim_action("create", "tenants", name=self.__class__.vim_tenant_name)
        logger.debug("{}".format(tenant))
        self.__class__.vim_tenant_uuid = tenant["tenant"]["id"]
        self.assertEqual(tenant.get('tenant', {}).get('name', ''), self.__class__.vim_tenant_name)

    def test_010_list_VIM_tenants(self):
        self.__class__.test_text = "{}.{}. TEST {}".format(test_number, self.__class__.test_index,
                                                           inspect.currentframe().f_code.co_name)
        self.__class__.test_index += 1
        tenants = client.vim_action("list", "tenants")
        logger.debug("{}".format(tenants))

    def test_020_get_VIM_tenant_by_uuid(self):
        self.__class__.test_text = "{}.{}. TEST {}".format(test_number, self.__class__.test_index,
                                                           inspect.currentframe().f_code.co_name)

        self.__class__.test_index += 1
        tenant = client.vim_action("show", "tenants", uuid=self.__class__.vim_tenant_uuid)
        logger.debug("{}".format(tenant))
        self.assertEqual(tenant.get('tenant', {}).get('name', ''), self.__class__.vim_tenant_name)

    def test_030_delete_VIM_tenant_by_uuid(self):
        self.__class__.test_text = "{}.{}. TEST {}".format(test_number, self.__class__.test_index,
                                                           inspect.currentframe().f_code.co_name)

        self.__class__.test_index += 1
        tenant = client.vim_action("delete", "tenants", uuid=self.__class__.vim_tenant_uuid)
        logger.debug("{}".format(tenant))
        assert ('deleted' in tenant.get('result', ""))

'''
IMPORTANT NOTE
The following unittest class does not have the 'test_' on purpose. This test is the one used for the
scenario based tests.
'''
class descriptor_based_scenario_test(unittest.TestCase):
    test_index = 0
    test_text = None
    scenario_test_path = None
    scenario_uuid = None
    instance_scenario_uuid = None
    to_delete_list = []

    @classmethod
    def setUpClass(cls):
        cls.test_index = 1
        cls.to_delete_list = []
        cls.scenario_test_path = test_directory + '/' + scenario_test_folder
        logger.info("{}. {} {}".format(test_number, cls.__name__, scenario_test_folder))

    @classmethod
    def tearDownClass(cls):
        globals().__setitem__('test_number', globals().__getitem__('test_number') + 1)

    def tearDown(self):
        exec_info = sys.exc_info()
        if exec_info == (None, None, None):
            logger.info(self.__class__.test_text + " -> TEST OK")
        else:
            logger.warning(self.__class__.test_text + " -> TEST NOK")
            error_trace = traceback.format_exception(exec_info[0], exec_info[1], exec_info[2])
            msg = ""
            for line in error_trace:
                msg = msg + line
            logger.critical("{}".format(msg))


    def test_000_load_scenario(self):
        self.__class__.test_text = "{}.{}. TEST {} {}".format(test_number, self.__class__.test_index,
                                                           inspect.currentframe().f_code.co_name,
                                                           scenario_test_folder)
        self.__class__.test_index += 1
        vnfd_files = glob.glob(self.__class__.scenario_test_path+'/vnfd_*.yaml')
        scenario_file = glob.glob(self.__class__.scenario_test_path + '/scenario_*.yaml')
        if len(vnfd_files) == 0 or len(scenario_file) > 1:
            raise Exception('Test '+scenario_test_folder+' not valid. It must contain an scenario file and at least one'
                                                         ' vnfd file')

        #load all vnfd
        for vnfd in vnfd_files:
            with open(vnfd, 'r') as stream:
                vnf_descriptor = yaml.load(stream)

            vnfc_list = vnf_descriptor['vnf']['VNFC']
            for vnfc in vnfc_list:
                vnfc['image name'] = test_image_name
                devices = vnfc.get('devices',[])
                for device in devices:
                    if device['type'] == 'disk' and 'image name' in device:
                        device['image name'] = test_image_name

            logger.debug("VNF descriptor: {}".format(vnf_descriptor))
            vnf = client.create_vnf(descriptor=vnf_descriptor)
            logger.debug(vnf)
            self.__class__.to_delete_list.insert(0, {"item": "vnf", "function": client.delete_vnf,
                                                     "params": {"uuid": vnf['vnf']['uuid']}})

        #load the scenario definition
        with open(scenario_file[0], 'r') as stream:
            scenario_descriptor = yaml.load(stream)
        networks = scenario_descriptor['scenario']['networks']
        networks[management_network] = networks.pop('mgmt')
        logger.debug("Scenario descriptor: {}".format(scenario_descriptor))
        scenario = client.create_scenario(descriptor=scenario_descriptor)
        logger.debug(scenario)
        self.__class__.to_delete_list.insert(0,{"item": "scenario", "function": client.delete_scenario,
                                 "params":{"uuid": scenario['scenario']['uuid']} })
        self.__class__.scenario_uuid = scenario['scenario']['uuid']

    def test_010_instantiate_scenario(self):
        self.__class__.test_text = "{}.{}. TEST {} {}".format(test_number, self.__class__.test_index,
                                                           inspect.currentframe().f_code.co_name,
                                                           scenario_test_folder)
        self.__class__.test_index += 1

        instance = client.create_instance(scenario_id=self.__class__.scenario_uuid, name=self.__class__.test_text)
        logger.debug(instance)
        self.__class__.to_delete_list.insert(0, {"item": "instance", "function": client.delete_instance,
                                  "params": {"uuid": instance['uuid']}})

    def test_020_clean_deployment(self):
        self.__class__.test_text = "{}.{}. TEST {} {}".format(test_number, self.__class__.test_index,
                                                              inspect.currentframe().f_code.co_name,
                                                              scenario_test_folder)
        self.__class__.test_index += 1
        #At the moment if you delete an scenario right after creating it, in openstack datacenters
        #sometimes scenario ports get orphaned. This sleep is just a dirty workaround
        time.sleep(5)
        for item in self.__class__.to_delete_list:
            response = item["function"](**item["params"])
            logger.debug(response)

def _get_random_string(maxLength):
    '''generates a string with random characters string.letters and string.digits
    with a random length up to maxLength characters. If maxLength is <15 it will be changed automatically to 15
    '''
    prefix = 'testing_'
    min_string = 15
    minLength = min_string - len(prefix)
    if maxLength < min_string: maxLength = min_string
    maxLength -= len(prefix)
    length = random.randint(minLength,maxLength)
    return 'testing_'+"".join([random.choice(string.letters+string.digits) for i in xrange(length)])

if __name__=="__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import openmanoclient

    parser = OptionParser()

    #Optional arguments
    parser.add_option("-v",'--version', help='Show current version', dest='version', action="store_true", default=False)
    parser.add_option('--debug', help='Set logs to debug level', dest='debug', action="store_true", default=False)
    parser.add_option('--failed', help='Set logs to show only failed tests. --debug disables this option',
                      dest='failed', action="store_true", default=False)
    parser.add_option('-u', '--url', dest='endpoint_url', help='Set the openmano server url. By default '
                                                      'http://localhost:9090/openmano',
                      default='http://localhost:9090/openmano')
    default_logger_file = os.path.dirname(__file__)+'/'+os.path.splitext(os.path.basename(__file__))[0]+'.log'
    parser.add_option('--logger_file', dest='logger_file', help='Set the logger file. By default '+default_logger_file,
                      default=default_logger_file)
    parser.add_option('--list-tests', help='List all available tests', dest='list-tests', action="store_true",
                      default=False)
    parser.add_option('--test', '--tests', help='Specify the tests to run', dest='tests', default=None)

    #Mandatory arguments
    parser.add_option("-t", '--tenant', dest='tenant_name', help='MANDATORY. Set the tenant name to test')
    parser.add_option('-d', '--datacenter', dest='datacenter_name', help='MANDATORY, Set the datacenter name to test')
    parser.add_option("-i", '--image-name', dest='image-name', help='MANDATORY. Image name of an Ubuntu 16.04 image '
                                                                    'that will be used for testing available in the '
                                                                    'datacenter.')
    parser.add_option("-n", '--mgmt-net-name', dest='mgmt-net', help='MANDATORY. Set the tenant name to test')

    (options, args) = parser.parse_args()

    # default logger level is INFO. Options --debug and --failed override this, being --debug prioritary
    logger_level = 'INFO'
    if options.__dict__['debug']:
        logger_level = 'DEBUG'
    elif options.__dict__['failed']:
        logger_level = 'WARNING'
    logger_name = os.path.basename(__file__)
    logger = logging.getLogger(logger_name)
    logger.setLevel(logger_level)

    # Configure a logging handler to store in a logging file
    fileHandler = logging.FileHandler(options.__dict__['logger_file'])
    formatter_fileHandler = logging.Formatter('%(asctime)s %(name)s %(levelname)s: %(message)s')
    fileHandler.setFormatter(formatter_fileHandler)
    logger.addHandler(fileHandler)

    # Configure a handler to print to stdout
    consoleHandler = logging.StreamHandler(sys.stdout)
    formatter_consoleHandler = logging.Formatter('%(message)s')
    consoleHandler.setFormatter(formatter_consoleHandler)
    logger.addHandler(consoleHandler)

    logger.debug('Program started with the following arguments: ' + str(options.__dict__))

    #If version is required print it and exit
    if options.__dict__['version']:
        logger.info("{}".format((sys.argv[0], __version__+" version", version_date)))
        logger.info ("(c) Copyright Telefonica")
        sys.exit(0)

    test_directory = os.path.dirname(__file__) + "/RO_tests"
    test_directory_content = os.listdir(test_directory)
    clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)

    # If only want to obtain a tests list print it and exit
    if options.__dict__['list-tests']:
        tests_names = []
        for cls in clsmembers:
            if cls[0].startswith('test_'):
                tests_names.append(cls[0])

        msg = "The code based tests are:\n\t" + ', '.join(sorted(tests_names))+'\n'+\
              "The descriptor based tests are:\n\t"+ ', '.join(sorted(test_directory_content))+'\n'+\
              "NOTE: The test test_VIM_tenant_operations will fail in case the used datacenter is type OpenStack " \
              "unless RO has access to the admin endpoint. Therefore this test is excluded by default"

        logger.info(msg)
        sys.exit(0)

    #Make sure required arguments are present
    required = "tenant_name datacenter_name image-name mgmt-net".split()
    error = False
    for r in required:
        if options.__dict__[r] is None:
            print "ERROR: parameter "+r+" is required"
            error = True
    if error:
        parser.print_help()
        sys.exit(1)

    # set test image name and management network
    test_image_name = options.__dict__['image-name']
    management_network = options.__dict__['mgmt-net']

    #Create the list of tests to be run
    descriptor_based_tests = []
    code_based_tests = []
    if options.__dict__['tests'] != None:
        tests = sorted(options.__dict__['tests'].split(','))
        for test in tests:
            matches_code_based_tests = [item for item in clsmembers if item[0] == test]
            if test in test_directory_content:
                descriptor_based_tests.append(test)
            elif len(matches_code_based_tests) > 0:
                code_based_tests.append(matches_code_based_tests[0][1])
            else:
                logger.critical("Test {} is not among the possible ones".format(test))
                sys.exit(1)
    else:
        #include all tests
        descriptor_based_tests = test_directory_content
        for cls in clsmembers:
            #We exclude 'test_VIM_tenant_operations' unless it is specifically requested by the user
            if cls[0].startswith('test_') and cls[0] != 'test_VIM_tenant_operations':
                code_based_tests.append(cls[1])

    logger.debug("descriptor_based_tests to be executed: {}".format(descriptor_based_tests))
    logger.debug("code_based_tests to be executed: {}".format(code_based_tests))

    # import openmanoclient from relative path
    client = openmanoclient.openmanoclient(
                            endpoint_url=options.__dict__['endpoint_url'],
                            tenant_name=options.__dict__['tenant_name'],
                            datacenter_name = options.__dict__['datacenter_name'],
                            debug = options.__dict__['debug'], logger = logger_name)

    # TextTestRunner stream is set to /dev/null in order to avoid the method to directly print the result of tests.
    # This is handled in the tests using logging.
    stream = open('/dev/null', 'w')
    test_number=1
    executed = 0
    failed = 0

    #Run code based tests
    basic_tests_suite = unittest.TestSuite()
    for test in code_based_tests:
        basic_tests_suite.addTest(unittest.makeSuite(test))
    result = unittest.TextTestRunner(stream=stream).run(basic_tests_suite)
    executed += result.testsRun
    failed += len(result.failures) + len(result.errors)
    if len(result.failures) > 0:
        logger.debug("failures : {}".format(result.failures))
    if len(result.errors) > 0:
        logger.debug("errors : {}".format(result.errors))

    # Additionally to the previous tests, scenario based tests will be executed.
    # This scenario based tests are defined as directories inside the directory defined in 'test_directory'
    for test in descriptor_based_tests:
        scenario_test_folder = test
        test_suite = unittest.TestSuite()
        test_suite.addTest(unittest.makeSuite(descriptor_based_scenario_test))
        result = unittest.TextTestRunner(stream=stream).run(test_suite)
        executed += result.testsRun
        failed += len(result.failures) + len(result.errors)
        if len(result.failures) > 0:
            logger.debug("failures : {}".format(result.failures))
        if len(result.errors) > 0:
            logger.debug("errors : {}".format(result.errors))

    #Log summary
    logger.warning("Total number of tests: {}; Total number of failures/errors: {}".format(executed, failed))

    sys.exit(0)