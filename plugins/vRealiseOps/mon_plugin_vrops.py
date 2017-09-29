# -*- coding: utf-8 -*-

##
# Copyright 2016-2017 VMware Inc.
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

"""
Montoring metrics & creating Alarm definations in vROPs
"""

import requests
import logging
from pyvcloud.vcloudair import VCA
from xml.etree import ElementTree as XmlElementTree
import traceback
import time
import json
from OpenSSL.crypto import load_certificate, FILETYPE_PEM
import os
import datetime
from socket import gethostname

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

OPERATION_MAPPING = {'GE':'GT_EQ', 'LE':'LT_EQ', 'GT':'GT', 'LT':'LT', 'EQ':'EQ'}
severity_mano2vrops = {'WARNING':'WARNING', 'MINOR':'WARNING', 'MAJOR':"IMMEDIATE",\
                        'CRITICAL':'CRITICAL', 'INDETERMINATE':'UNKNOWN'}
PERIOD_MSEC = {'HR':3600000,'DAY':86400000,'WEEK':604800000,'MONTH':2678400000,'YEAR':31536000000}

#To Do - Add actual webhook url & certificate
#SSL_CERTIFICATE_FILE_NAME = 'vROPs_Webservice/SSL_certificate/www.vrops_webservice.com.cert'
#webhook_url = "https://mano-dev-1:8080/notify/" #for testing
webhook_url = "https://" + gethostname() + ":8080/notify/"
SSL_CERTIFICATE_FILE_NAME = ('vROPs_Webservice/SSL_certificate/' + gethostname() + ".cert")
#SSL_CERTIFICATE_FILE_NAME = 'vROPs_Webservice/SSL_certificate/10.172.137.214.cert' #for testing

MODULE_DIR = os.path.dirname(__file__)
CONFIG_FILE_NAME = 'vrops_config.xml'
CONFIG_FILE_PATH = os.path.join(MODULE_DIR, CONFIG_FILE_NAME)
SSL_CERTIFICATE_FILE_PATH = os.path.join(MODULE_DIR, SSL_CERTIFICATE_FILE_NAME)

class MonPlugin():
    """MON Plugin class for vROPs telemetry plugin
    """
    def __init__(self):
        """Constructor of MON plugin
        Params:
            'access_config': dictionary with VIM access information based on VIM type.
            This contains a consolidate version of VIM & monitoring tool config at creation and
            particular VIM config at their attachment.
            For VIM type: 'vmware',
            access_config - {'vrops_site':<>, 'vrops_user':<>, 'vrops_password':<>,
                            'vcloud-site':<>,'admin_username':<>,'admin_password':<>,
                            'nsx_manager':<>,'nsx_user':<>,'nsx_password':<>,
                            'vcenter_ip':<>,'vcenter_port':<>,'vcenter_user':<>,'vcenter_password':<>,
                            'vim_tenant_name':<>,'orgname':<>}

        #To Do
        Returns: Raise an exception if some needed parameter is missing, but it must not do any connectivity
            check against the VIM
        """
        self.logger = logging.getLogger('PluginReceiver.MonPlugin')
        self.logger.setLevel(logging.DEBUG)

        access_config = self.get_default_Params('Access_Config')
        self.access_config = access_config
        if not bool(access_config):
            self.logger.error("Access configuration not provided in vROPs Config file")
            raise KeyError("Access configuration not provided in vROPs Config file")

        try:
            self.vrops_site =  access_config['vrops_site']
            self.vrops_user = access_config['vrops_user']
            self.vrops_password = access_config['vrops_password']
            self.vcloud_site = access_config['vcloud-site']
            self.admin_username = access_config['admin_username']
            self.admin_password = access_config['admin_password']
            self.tenant_id = access_config['tenant_id']
        except KeyError as exp:
            self.logger.error("Check Access configuration in vROPs Config file: {}".format(exp))
            raise KeyError("Check Access configuration in vROPs Config file: {}".format(exp))


    def configure_alarm(self, config_dict = {}):
        """Configures or creates a new alarm using the input parameters in config_dict
        Params:
        "alarm_name": Alarm name in string format
        "description": Description of alarm in string format
        "resource_uuid": Resource UUID for which alarm needs to be configured. in string format
        "Resource type": String resource type: 'VDU' or 'host'
        "Severity": 'WARNING', 'MINOR', 'MAJOR', 'CRITICAL'
        "metric_name": Metric key in string format
        "operation": One of ('GE', 'LE', 'GT', 'LT', 'EQ')
        "threshold_value": Defines the threshold (up to 2 fraction digits) that,
                            if crossed, will trigger the alarm.
        "unit": Unit of measurement in string format
        "statistic": AVERAGE, MINIMUM, MAXIMUM, COUNT, SUM

        Default parameters for each alarm are read from the plugin specific config file.
        Dict of default parameters is as follows:
        default_params keys = {'cancel_cycles','wait_cycles','resource_kind','adapter_kind',
                               'alarm_type','alarm_subType',impact}

        Returns the UUID of created alarm or None
        """
        alarm_def = None
        #1) get alarm & metrics parameters from plugin specific file
        def_a_params = self.get_default_Params(config_dict['alarm_name'])
        if not def_a_params:
            self.logger.warn("Alarm not supported: {}".format(config_dict['alarm_name']))
            return None
        metric_key_params = self.get_default_Params(config_dict['metric_name'])
        if not metric_key_params:
            self.logger.warn("Metric not supported: {}".format(config_dict['metric_name']))
            return None
        #2) create symptom definition
        vrops_alarm_name = def_a_params['vrops_alarm']+ '-' + config_dict['resource_uuid']
        symptom_params ={'cancel_cycles': (def_a_params['cancel_period']/300)*def_a_params['cancel_cycles'],
                        'wait_cycles': (def_a_params['period']/300)*def_a_params['evaluation'],
                        'resource_kind_key': def_a_params['resource_kind'],
                        'adapter_kind_key': def_a_params['adapter_kind'],
                        'symptom_name':vrops_alarm_name,
                        'severity': severity_mano2vrops[config_dict['severity']],
                        'metric_key':metric_key_params['metric_key'],
                        'operation':OPERATION_MAPPING[config_dict['operation']],
                        'threshold_value':config_dict['threshold_value']}
        symptom_uuid = self.create_symptom(symptom_params)
        if symptom_uuid is not None:
            self.logger.info("Symptom defined: {} with ID: {}".format(symptom_params['symptom_name'],symptom_uuid))
        else:
            self.logger.warn("Failed to create Symptom: {}".format(symptom_params['symptom_name']))
            return None
        #3) create alert definition
        #To Do - Get type & subtypes for all 5 alarms
        alarm_params = {'name':vrops_alarm_name,
                        'description':config_dict['description']\
                        if config_dict['description'] is not None else config_dict['alarm_name'],
                        'adapterKindKey':def_a_params['adapter_kind'],
                        'resourceKindKey':def_a_params['resource_kind'],
                        'waitCycles':1, 'cancelCycles':1,
                        'type':def_a_params['alarm_type'], 'subType':def_a_params['alarm_subType'],
                        'severity':severity_mano2vrops[config_dict['severity']],
                        'symptomDefinitionId':symptom_uuid,
                        'impact':def_a_params['impact']}

        alarm_def = self.create_alarm_definition(alarm_params)
        if alarm_def is None:
            self.logger.warn("Failed to create Alert: {}".format(alarm_params['name']))
            return None

        self.logger.info("Alarm defined: {} with ID: {}".format(alarm_params['name'],alarm_def))

        #4) Find vm_moref_id from vApp uuid in vCD
        vm_moref_id = self.get_vm_moref_id(config_dict['resource_uuid'])
        if vm_moref_id is None:
            self.logger.warn("Failed to find vm morefid for vApp in vCD: {}".format(config_dict['resource_uuid']))
            return None

        #5) Based on vm_moref_id, find VM's corresponding resource_id in vROPs to set notification
        resource_id = self.get_vm_resource_id(vm_moref_id)
        if resource_id is None:
            self.logger.warn("Failed to find resource in vROPs: {}".format(config_dict['resource_uuid']))
            return None

        #6) Configure alarm notification for a particular VM using it's resource_id
        notification_id = self.create_alarm_notification_rule(vrops_alarm_name, alarm_def, resource_id)
        if notification_id is None:
            return None
        else:
            alarm_def_uuid = alarm_def.split('-', 1)[1]
            self.logger.info("Alarm defination created with notification: {} with ID: {}"\
                    .format(alarm_params['name'],alarm_def_uuid))
            #Return alarm defination UUID by removing 'AlertDefinition' from UUID
            return (alarm_def_uuid)

    def get_default_Params(self, metric_alarm_name):
        """
        Read the default config parameters from plugin specific file stored with plugin file.
        Params:
            metric_alarm_name: Name of the alarm, whose congif params to be read from the config file.
        """
        a_params = {}
        try:
            source = open(CONFIG_FILE_PATH, 'r')
        except IOError as exp:
            msg = ("Could not read Config file: {}, \nException: {}"\
                        .format(CONFIG_FILE_PATH, exp))
            self.logger.error(msg)
            raise IOError(msg)

        tree = XmlElementTree.parse(source)
        alarms = tree.getroot()
        for alarm in alarms:
            if alarm.tag == metric_alarm_name:
                for param in alarm:
                    if param.tag in ("period", "evaluation", "cancel_period", "alarm_type",\
                                    "cancel_cycles", "alarm_subType"):
                        a_params[param.tag] = int(param.text)
                    elif param.tag in ("enabled", "repeat"):
                        if(param.text.lower() == "true"):
                            a_params[param.tag] = True
                        else:
                            a_params[param.tag] = False
                    else:
                        a_params[param.tag] = param.text
        source.close()
        return a_params


    def create_symptom(self, symptom_params):
        """Create Symptom definition for an alarm
        Params:
        symptom_params: Dict of parameters required for defining a symptom as follows
            cancel_cycles
            wait_cycles
            resource_kind_key = "VirtualMachine"
            adapter_kind_key = "VMWARE"
            symptom_name = Test_Memory_Usage_TooHigh
            severity
            metric_key
            operation = GT_EQ
            threshold_value = 85
        Returns the uuid of Symptom definition
        """
        symptom_id = None

        try:
            api_url = '/suite-api/api/symptomdefinitions'
            headers = {'Content-Type': 'application/xml'}
            data = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                        <ops:symptom-definition cancelCycles="{0:s}" waitCycles="{1:s}"
                            resourceKindKey="{2:s}" adapterKindKey="{3:s}"
                            xmlns:xs="http://www.w3.org/2001/XMLSchema"
                            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                            xmlns:ops="http://webservice.vmware.com/vRealizeOpsMgr/1.0/">
                            <ops:name>{4:s}</ops:name>
                            <ops:state severity="{5:s}">
                                <ops:condition xsi:type="ops:htCondition">
                                    <ops:key>{6:s}</ops:key>
                                    <ops:operator>{7:s}</ops:operator>
                                    <ops:value>{8:s}</ops:value>
                                    <ops:valueType>NUMERIC</ops:valueType>
                                    <ops:instanced>false</ops:instanced>
                                    <ops:thresholdType>STATIC</ops:thresholdType>
                                </ops:condition>
                            </ops:state>
                        </ops:symptom-definition>"""\
                        .format(str(symptom_params['cancel_cycles']),str(symptom_params['wait_cycles']),
                                symptom_params['resource_kind_key'], symptom_params['adapter_kind_key'],
                                symptom_params['symptom_name'],symptom_params['severity'],
                                symptom_params['metric_key'],symptom_params['operation'],
                                str(symptom_params['threshold_value']))

            resp = requests.post(self.vrops_site + api_url,
                                 auth=(self.vrops_user, self.vrops_password),
                                 headers=headers,
                                 verify = False,
                                 data=data)

            if resp.status_code != 201:
                self.logger.warn("Failed to create Symptom definition: {}, response {}"\
                        .format(symptom_params['symptom_name'], resp.content))
                return None

            symptom_xmlroot = XmlElementTree.fromstring(resp.content)
            if symptom_xmlroot is not None and 'id' in symptom_xmlroot.attrib:
                symptom_id = symptom_xmlroot.attrib['id']

            return symptom_id

        except Exception as exp:
            self.logger.warn("Error creating symptom definition : {}\n{}"\
            .format(exp, traceback.format_exc()))


    def create_alarm_definition(self, alarm_params):
        """
        Create an alarm definition in vROPs
        Params:
            'name': Alarm Name,
            'description':Alarm description,
            'adapterKindKey': Adapter type in vROPs "VMWARE",
            'resourceKindKey':Resource type in vROPs "VirtualMachine",
            'waitCycles': No of wait cycles,
            'cancelCycles': No of cancel cycles,
            'type': Alarm type,
            'subType': Alarm subtype,
            'severity': Severity in vROPs "CRITICAL",
            'symptomDefinitionId':symptom Definition uuid,
            'impact': impact 'risk'
        Returns:
            'alarm_uuid': returns alarm uuid
        """

        alarm_uuid = None

        try:
            api_url = '/suite-api/api/alertdefinitions'
            headers = {'Content-Type': 'application/xml'}
            data = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                        <ops:alert-definition xmlns:xs="http://www.w3.org/2001/XMLSchema"
                            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                            xmlns:ops="http://webservice.vmware.com/vRealizeOpsMgr/1.0/">
                            <ops:name>{0:s}</ops:name>
                            <ops:description>{1:s}</ops:description>
                            <ops:adapterKindKey>{2:s}</ops:adapterKindKey>
                            <ops:resourceKindKey>{3:s}</ops:resourceKindKey>
                            <ops:waitCycles>1</ops:waitCycles>
                            <ops:cancelCycles>1</ops:cancelCycles>
                            <ops:type>{4:s}</ops:type>
                            <ops:subType>{5:s}</ops:subType>
                            <ops:states>
                                <ops:state severity="{6:s}">
                                    <ops:symptom-set>
                                        <ops:symptomDefinitionIds>
                                            <ops:symptomDefinitionId>{7:s}</ops:symptomDefinitionId>
                                        </ops:symptomDefinitionIds>
                                        <ops:relation>SELF</ops:relation>
                                        <ops:aggregation>ALL</ops:aggregation>
                                        <ops:symptomSetOperator>AND</ops:symptomSetOperator>
                                    </ops:symptom-set>
                                    <ops:impact>
                                        <ops:impactType>BADGE</ops:impactType>
                                        <ops:detail>{8:s}</ops:detail>
                                    </ops:impact>
                                </ops:state>
                            </ops:states>
                        </ops:alert-definition>"""\
                        .format(alarm_params['name'],alarm_params['description'],
                                alarm_params['adapterKindKey'],alarm_params['resourceKindKey'],
                                str(alarm_params['type']),str(alarm_params['subType']),
                                alarm_params['severity'],alarm_params['symptomDefinitionId'],
                                alarm_params['impact'])

            resp = requests.post(self.vrops_site + api_url,
                                 auth=(self.vrops_user, self.vrops_password),
                                 headers=headers,
                                 verify = False,
                                 data=data)

            if resp.status_code != 201:
                self.logger.warn("Failed to create Alarm definition: {}, response {}"\
                        .format(alarm_params['name'], resp.content))
                return None

            alarm_xmlroot = XmlElementTree.fromstring(resp.content)
            for child in alarm_xmlroot:
                if child.tag.split("}")[1] == 'id':
                    alarm_uuid = child.text

            return alarm_uuid

        except Exception as exp:
            self.logger.warn("Error creating alarm definition : {}\n{}".format(exp, traceback.format_exc()))


    def configure_rest_plugin(self):
        """
        Creates REST Plug-in for vROPs outbound alerts

        Returns Plugin ID
        """
        plugin_id = None
        plugin_name = 'MON_module_REST_Plugin'
        plugin_id = self.check_if_plugin_configured(plugin_name)

        #If REST plugin not configured, configure it
        if plugin_id is not None:
            return plugin_id
        else:
            try:
                cert_file_string = open(SSL_CERTIFICATE_FILE_PATH, "rb").read()
            except IOError as exp:
                msg = ("Could not read SSL certificate file: {}".format(SSL_CERTIFICATE_FILE_PATH))
                self.logger.error(msg)
                raise IOError(msg)
            cert = load_certificate(FILETYPE_PEM, cert_file_string)
            certificate = cert.digest("sha1")
            api_url = '/suite-api/api/alertplugins'
            headers = {'Content-Type': 'application/xml'}
            data =   """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                        <ops:notification-plugin version="0" xmlns:xs="http://www.w3.org/2001/XMLSchema"
                            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                            xmlns:ops="http://webservice.vmware.com/vRealizeOpsMgr/1.0/">
                            <ops:pluginTypeId>RestPlugin</ops:pluginTypeId>
                            <ops:name>{0:s}</ops:name>
                            <ops:configValues>
                                <ops:configValue name="Url">{1:s}</ops:configValue>
                                <ops:configValue name="Content-type">application/json</ops:configValue>
                                <ops:configValue name="Certificate">{2:s}</ops:configValue>
                                <ops:configValue name="ConnectionCount">20</ops:configValue>
                            </ops:configValues>
                        </ops:notification-plugin>""".format(plugin_name, webhook_url, certificate)

            resp = requests.post(self.vrops_site + api_url,
                                 auth=(self.vrops_user, self.vrops_password),
                                 headers=headers,
                                 verify = False,
                                 data=data)

            if resp.status_code is not 201:
                self.logger.warn("Failed to create REST Plugin: {} for url: {}, \nresponse code: {},"\
                            "\nresponse content: {}".format(plugin_name, webhook_url,\
                            resp.status_code, resp.content))
                return None

            plugin_xmlroot = XmlElementTree.fromstring(resp.content)
            if plugin_xmlroot is not None:
                for child in plugin_xmlroot:
                    if child.tag.split("}")[1] == 'pluginId':
                        plugin_id = plugin_xmlroot.find('{http://webservice.vmware.com/vRealizeOpsMgr/1.0/}pluginId').text

            if plugin_id is None:
                self.logger.warn("Failed to get REST Plugin ID for {}, url: {}".format(plugin_name, webhook_url))
                return None
            else:
                self.logger.info("Created REST Plugin: {} with ID : {} for url: {}".format(plugin_name, plugin_id, webhook_url))
                status = self.enable_rest_plugin(plugin_id, plugin_name)
                if status is False:
                    self.logger.warn("Failed to enable created REST Plugin: {} for url: {}".format(plugin_name, webhook_url))
                    return None
                else:
                    self.logger.info("Enabled REST Plugin: {} for url: {}".format(plugin_name, webhook_url))
                    return plugin_id

    def check_if_plugin_configured(self, plugin_name):
        """Check if the REST plugin is already created
        Returns: plugin_id: if already created, None: if needs to be created
        """
        plugin_id = None
        #Find the REST Plugin id details for - MON_module_REST_Plugin
        api_url = '/suite-api/api/alertplugins'
        headers = {'Accept': 'application/xml'}
        namespace = {'params':"http://webservice.vmware.com/vRealizeOpsMgr/1.0/"}

        resp = requests.get(self.vrops_site + api_url,
                            auth=(self.vrops_user, self.vrops_password),
                            verify = False, headers = headers)

        if resp.status_code is not 200:
            self.logger.warn("Failed to REST GET Alarm plugin details \nResponse code: {}\nResponse content: {}"\
            .format(resp.status_code, resp.content))
            return None

        # Look for specific plugin & parse pluginId for 'MON_module_REST_Plugin'
        xmlroot_resp = XmlElementTree.fromstring(resp.content)
        for notify_plugin in xmlroot_resp.findall('params:notification-plugin',namespace):
            if notify_plugin.find('params:name',namespace) is not None and\
                notify_plugin.find('params:pluginId',namespace) is not None:
                if notify_plugin.find('params:name',namespace).text == plugin_name:
                    plugin_id = notify_plugin.find('params:pluginId',namespace).text

        if plugin_id is None:
            self.logger.warn("REST plugin {} not found".format('MON_module_REST_Plugin'))
            return None
        else:
            self.logger.info("Found REST Plugin: {}".format(plugin_name))
            return plugin_id


    def enable_rest_plugin(self, plugin_id, plugin_name):
        """
        Enable the REST plugin using plugin_id
        Params: plugin_id: plugin ID string that is to be enabled
        Returns: status (Boolean) - True for success, False for failure
        """

        if plugin_id is None or plugin_name is None:
            self.logger.debug("enable_rest_plugin() : Plugin ID or plugin_name not provided for {} plugin"\
                        .format(plugin_name))
            return False

        try:
            api_url = "/suite-api/api/alertplugins/{}/enable/True".format(plugin_id)

            resp = requests.put(self.vrops_site + api_url,
                                auth=(self.vrops_user, self.vrops_password),
                                verify = False)

            if resp.status_code is not 204:
                self.logger.warn("Failed to enable REST plugin {}. \nResponse code {}\nResponse Content: {}"\
                        .format(plugin_name, resp.status_code, resp.content))
                return False

            self.logger.info("Enabled REST plugin {}.".format(plugin_name))
            return True

        except Exception as exp:
            self.logger.warn("Error enabling REST plugin for {} plugin: Exception: {}\n{}"\
                    .format(plugin_name, exp, traceback.format_exc()))

    def create_alarm_notification_rule(self, alarm_name, alarm_id, resource_id):
        """
        Create notification rule for each alarm
        Params:
            alarm_name
            alarm_id
            resource_id

        Returns:
            notification_id: notification_id or None
        """
        notification_name = 'notify_' + alarm_name
        notification_id = None
        plugin_name = 'MON_module_REST_Plugin'

        #1) Find the REST Plugin id details for - MON_module_REST_Plugin
        plugin_id = self.check_if_plugin_configured(plugin_name)
        if plugin_id is None:
            self.logger.warn("Failed to get REST plugin_id for : {}".format('MON_module_REST_Plugin'))
            return None

        #2) Create Alarm notification rule
        api_url = '/suite-api/api/notifications/rules'
        headers = {'Content-Type': 'application/xml'}
        data = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <ops:notification-rule xmlns:xs="http://www.w3.org/2001/XMLSchema"
                        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                        xmlns:ops="http://webservice.vmware.com/vRealizeOpsMgr/1.0/">
                        <ops:name>{0:s}</ops:name>
                        <ops:pluginId>{1:s}</ops:pluginId>
                        <ops:resourceFilter resourceId="{2:s}">
                            <ops:matchResourceIdOnly>true</ops:matchResourceIdOnly>
                        </ops:resourceFilter>
                        <ops:alertDefinitionIdFilters>
                            <ops:values>{3:s}</ops:values>
                        </ops:alertDefinitionIdFilters>
                    </ops:notification-rule>"""\
                    .format(notification_name, plugin_id, resource_id, alarm_id)

        resp = requests.post(self.vrops_site + api_url,
                             auth=(self.vrops_user, self.vrops_password),
                             headers=headers,
                             verify = False,
                             data=data)

        if resp.status_code is not 201:
            self.logger.warn("Failed to create Alarm notification rule {} for {} alarm."\
                        "\nResponse code: {}\nResponse content: {}"\
                        .format(notification_name, alarm_name, resp.status_code, resp.content))
            return None

        #parse notification id from response
        xmlroot_resp = XmlElementTree.fromstring(resp.content)
        if xmlroot_resp is not None and 'id' in xmlroot_resp.attrib:
            notification_id = xmlroot_resp.attrib.get('id')

        self.logger.info("Created Alarm notification rule {} for {} alarm.".format(notification_name, alarm_name))
        return notification_id

    def get_vm_moref_id(self, vapp_uuid):
        """
        Get the moref_id of given VM
        """
        try:
            if vapp_uuid:
                vm_details = self.get_vapp_details_rest(vapp_uuid)
                if vm_details and "vm_vcenter_info" in vm_details:
                    vm_moref_id = vm_details["vm_vcenter_info"].get("vm_moref_id", None)

            self.logger.info("Found vm_moref_id: {} for vApp UUID: {}".format(vm_moref_id, vapp_uuid))
            return vm_moref_id

        except Exception as exp:
            self.logger.warn("Error occurred while getting VM moref ID for VM : {}\n{}"\
                        .format(exp, traceback.format_exc()))


    def get_vapp_details_rest(self, vapp_uuid=None):
        """
        Method retrieve vapp detail from vCloud director

        Args:
            vapp_uuid - is vapp identifier.

            Returns:
                Returns VM MOref ID or return None
        """

        parsed_respond = {}
        vca = None

        vca = self.connect_as_admin()

        if not vca:
            self.logger.warn("connect() to vCD is failed")
        if vapp_uuid is None:
            return None

        url_list = [vca.host, '/api/vApp/vapp-', vapp_uuid]
        get_vapp_restcall = ''.join(url_list)

        if vca.vcloud_session and vca.vcloud_session.organization:
            response = requests.get(get_vapp_restcall,
                                    headers=vca.vcloud_session.get_vcloud_headers(),
                                    verify=vca.verify)

            if response.status_code != 200:
                self.logger.warn("REST API call {} failed. Return status code {}"\
                            .format(get_vapp_restcall, response.content))
                return parsed_respond

            try:
                xmlroot_respond = XmlElementTree.fromstring(response.content)

                namespaces = {'vm': 'http://www.vmware.com/vcloud/v1.5',
                              "vmext":"http://www.vmware.com/vcloud/extension/v1.5",
                              "xmlns":"http://www.vmware.com/vcloud/v1.5"
                             }

                # parse children section for other attrib
                children_section = xmlroot_respond.find('vm:Children/', namespaces)
                if children_section is not None:
                    vCloud_extension_section = children_section.find('xmlns:VCloudExtension', namespaces)
                    if vCloud_extension_section is not None:
                        vm_vcenter_info = {}
                        vim_info = vCloud_extension_section.find('vmext:VmVimInfo', namespaces)
                        vmext = vim_info.find('vmext:VmVimObjectRef', namespaces)
                        if vmext is not None:
                            vm_vcenter_info["vm_moref_id"] = vmext.find('vmext:MoRef', namespaces).text
                        parsed_respond["vm_vcenter_info"]= vm_vcenter_info

            except Exception as exp :
                self.logger.warn("Error occurred calling rest api for getting vApp details: {}\n{}"\
                            .format(exp, traceback.format_exc()))

        return parsed_respond


    def connect_as_admin(self):
        """ Method connect as pvdc admin user to vCloud director.
            There are certain action that can be done only by provider vdc admin user.
            Organization creation / provider network creation etc.

            Returns:
                The return vca object that letter can be used to connect to vcloud direct as admin for provider vdc
        """

        self.logger.info("Logging in to a VCD org as admin.")

        vca_admin = VCA(host=self.vcloud_site,
                        username=self.admin_username,
                        service_type='standalone',
                        version='5.9',
                        verify=False,
                        log=False)
        result = vca_admin.login(password=self.admin_password, org='System')
        if not result:
            self.logger.warn("Can't connect to a vCloud director as: {}".format(self.admin_username))
        result = vca_admin.login(token=vca_admin.token, org='System', org_url=vca_admin.vcloud_session.org_url)
        if result is True:
            self.logger.info("Successfully logged to a vcloud direct org: {} as user: {}"\
                        .format('System', self.admin_username))

        return vca_admin


    def get_vm_resource_id(self, vm_moref_id):
        """ Find resource ID in vROPs using vm_moref_id
        """
        if vm_moref_id is None:
            return None

        api_url = '/suite-api/api/resources'
        headers = {'Accept': 'application/xml'}
        namespace = {'params':"http://webservice.vmware.com/vRealizeOpsMgr/1.0/"}

        resp = requests.get(self.vrops_site + api_url,
                            auth=(self.vrops_user, self.vrops_password),
                            verify = False, headers = headers)

        if resp.status_code is not 200:
            self.logger.warn("Failed to get resource details from vROPs for {}\nResponse code:{}\nResponse Content: {}"\
                    .format(vm_moref_id, resp.status_code, resp.content))
            return None

        try:
            xmlroot_respond = XmlElementTree.fromstring(resp.content)
            for resource in xmlroot_respond.findall('params:resource',namespace):
                if resource is not None:
                    resource_key = resource.find('params:resourceKey',namespace)
                    if resource_key is not None:
                        if resource_key.find('params:adapterKindKey',namespace).text == 'VMWARE' and \
                        resource_key.find('params:resourceKindKey',namespace).text == 'VirtualMachine':
                            for child in resource_key:
                                if child.tag.split('}')[1]=='resourceIdentifiers':
                                    resourceIdentifiers = child
                                    for r_id in resourceIdentifiers:
                                        if r_id.find('params:value',namespace).text == vm_moref_id:
                                            self.logger.info("Found Resource ID : {} in vROPs for {}"\
                                                    .format(resource.attrib['identifier'], vm_moref_id))
                                            return resource.attrib['identifier']
        except Exception as exp:
            self.logger.warn("Error in parsing {}\n{}".format(exp, traceback.format_exc()))


    def get_metrics_data(self, metric={}):
        """Get an individual metric's data of a resource.
        Params:
            'metric_name': Normalized name of metric (string)
            'resource_uuid': Resource UUID (string)
            'period': Time period in Period Unit for which metrics data to be collected from
                        Monitoring tool from now.
            'period_unit': Period measurement unit can be one of 'HR', 'DAY', 'MONTH', 'YEAR'

        Return a dict that contains:
            'metric_name': Normalized name of metric (string)
            'resource_uuid': Resource UUID (string)
            'tenant_id': tenent id name in which the resource is present in string format
            'metrics_data': Dictionary containing time_series & metric_series data.
                'time_series': List of individual time stamp values in msec
                'metric_series': List of individual metrics data values
        Raises an exception upon error or when network is not found
        """
        return_data = {}
        return_data['schema_version'] = 1.0
        return_data['schema_type'] = 'read_metric_data_response'
        return_data['metric_name'] = metric['metric_name']
        #To do - No metric_uuid in vROPs, thus returning '0'
        return_data['metric_uuid'] = '0'
        return_data['correlation_id'] = metric['correlation_id']
        return_data['resource_uuid'] = metric['resource_uuid']
        return_data['metrics_data'] = {'time_series':[], 'metric_series':[]}
        #To do - Need confirmation about uuid & id
        if 'tenant_uuid' in metric and metric['tenant_uuid'] is not None:
            return_data['tenant_uuid'] = metric['tenant_uuid']
        else:
            return_data['tenant_uuid'] = None
        return_data['unit'] = None
        #return_data['tenant_id'] = self.tenant_id
        #self.logger.warn("return_data: {}".format(return_data))

        #1) Get metric details from plugin specific file & format it into vROPs metrics
        metric_key_params = self.get_default_Params(metric['metric_name'])

        if not metric_key_params:
            self.logger.warn("Metric not supported: {}".format(metric['metric_name']))
            #To Do: Return message
            return return_data

        return_data['unit'] = metric_key_params['unit']

        #2) Find the resource id in vROPs based on OSM resource_uuid
        #2.a) Find vm_moref_id from vApp uuid in vCD
        vm_moref_id = self.get_vm_moref_id(metric['resource_uuid'])
        if vm_moref_id is None:
            self.logger.warn("Failed to find vm morefid for vApp in vCD: {}".format(config_dict['resource_uuid']))
            return return_data
        #2.b) Based on vm_moref_id, find VM's corresponding resource_id in vROPs to set notification
        resource_id = self.get_vm_resource_id(vm_moref_id)
        if resource_id is None:
            self.logger.warn("Failed to find resource in vROPs: {}".format(config_dict['resource_uuid']))
            return return_data

        #3) Calculate begin & end time for period & period unit
        end_time = int(round(time.time() * 1000))
        if metric['collection_unit'] == 'YR':
            time_diff = PERIOD_MSEC[metric['collection_unit']]
        else:
            time_diff = metric['collection_period']* PERIOD_MSEC[metric['collection_unit']]
        begin_time = end_time - time_diff

        #4) Get the metrics data
        self.logger.info("metric_key_params['metric_key'] = {}".format(metric_key_params['metric_key']))
        self.logger.info("end_time: {}, begin_time: {}".format(end_time, begin_time))

        url_list = ['/suite-api/api/resources/', resource_id, '/stats?statKey=',\
                    metric_key_params['metric_key'], '&begin=', str(begin_time),'&end=',str(end_time)]
        api_url = ''.join(url_list)
        headers = {'Accept': 'application/json'}

        resp = requests.get(self.vrops_site + api_url,
                            auth=(self.vrops_user, self.vrops_password),
                            verify = False, headers = headers)

        if resp.status_code is not 200:
            self.logger.warn("Failed to retrive Metric data from vROPs for {}\nResponse code:{}\nResponse Content: {}"\
                    .format(metric['metric_name'], resp.status_code, resp.content))
            return return_data

        #5) Convert to required format
        metrics_data = {}
        json_data = json.loads(resp.content)
        for resp_key,resp_val in json_data.iteritems():
            if resp_key == 'values':
                data = json_data['values'][0]
                for data_k,data_v in data.iteritems():
                    if data_k == 'stat-list':
                        stat_list = data_v
                        for stat_list_k,stat_list_v in stat_list.iteritems():
                            for stat_keys,stat_vals in stat_list_v[0].iteritems():
                                if stat_keys == 'timestamps':
                                    metrics_data['time_series'] = stat_list_v[0]['timestamps']
                                if stat_keys == 'data':
                                    metrics_data['metric_series'] = stat_list_v[0]['data']

        return_data['metrics_data'] = metrics_data

        return return_data

    def update_alarm_configuration(self, new_alarm_config):
        """Update alarm configuration (i.e. Symptom & alarm) as per request
        """
        #1) Get Alarm details from it's uuid & find the symptom defination
        alarm_details_json, alarm_details = self.get_alarm_defination_details(new_alarm_config['alarm_uuid'])
        if alarm_details_json is None:
            return None

        try:
            #2) Update the symptom defination
            if alarm_details['alarm_id'] is not None and alarm_details['symptom_definition_id'] is not None:
                symptom_defination_id = alarm_details['symptom_definition_id']
            else:
                self.logger.info("Symptom Defination ID not found for {}".format(new_alarm_config['alarm_uuid']))
                return None

            symptom_uuid = self.update_symptom_defination(symptom_defination_id, new_alarm_config)

            #3) Update the alarm defination & Return UUID if successful update
            if symptom_uuid is None:
                self.logger.info("Symptom Defination details not found for {}"\
                                .format(new_alarm_config['alarm_uuid']))
                return None
            else:
                alarm_uuid = self.reconfigure_alarm(alarm_details_json, new_alarm_config)
                if alarm_uuid is None:
                    return None
                else:
                    return alarm_uuid
        except:
            self.logger.error("Exception while updating alarm: {}".format(traceback.format_exc()))

    def get_alarm_defination_details(self, alarm_uuid):
        """Get alarm details based on alarm UUID
        """
        if alarm_uuid is None:
            self.logger.warn("get_alarm_defination_details: Alarm UUID not provided")
            return None, None

        alarm_details = {}
        json_data = {}
        api_url = '/suite-api/api/alertdefinitions/AlertDefinition-'
        headers = {'Accept': 'application/json'}

        resp = requests.get(self.vrops_site + api_url + alarm_uuid,
                            auth=(self.vrops_user, self.vrops_password),
                            verify = False, headers = headers)

        if resp.status_code is not 200:
            self.logger.warn("Alarm to be updated not found: {}\nResponse code:{}\nResponse Content: {}"\
                    .format(alarm_uuid, resp.status_code, resp.content))
            return None, None

        try:
            json_data = json.loads(resp.content)
            if json_data['id'] is not None:
                alarm_details['alarm_id'] = json_data['id']
                alarm_details['alarm_name'] = json_data['name']
                alarm_details['adapter_kind'] = json_data['adapterKindKey']
                alarm_details['resource_kind'] = json_data['resourceKindKey']
                alarm_details['type'] = json_data['type']
                alarm_details['sub_type'] = json_data['subType']
                alarm_details['symptom_definition_id'] = json_data['states'][0]['base-symptom-set']['symptomDefinitionIds'][0]
        except exception as exp:
            self.logger.warn("Exception while retriving alarm defination details: {}".format(exp))
            return None, None

        return json_data, alarm_details


    def update_symptom_defination(self, symptom_uuid, new_alarm_config):
        """Update symptom defination based on new alarm input configuration
        """
        #1) Get symptom defination details
        symptom_details = self.get_symptom_defination_details(symptom_uuid)
        #print "\n\nsymptom_details: {}".format(symptom_details)
        if symptom_details is None:
            return None

        if new_alarm_config.has_key('severity') and new_alarm_config['severity'] is not None:
            symptom_details['state']['severity'] = severity_mano2vrops[new_alarm_config['severity']]
        if new_alarm_config.has_key('operation') and new_alarm_config['operation'] is not None:
            symptom_details['state']['condition']['operator'] = OPERATION_MAPPING[new_alarm_config['operation']]
        if new_alarm_config.has_key('threshold_value') and new_alarm_config['threshold_value'] is not None:
            symptom_details['state']['condition']['value'] = new_alarm_config['threshold_value']
        #Find vrops metric key from metric_name, if required
        """
        if new_alarm_config.has_key('metric_name') and new_alarm_config['metric_name'] is not None:
            metric_key_params = self.get_default_Params(new_alarm_config['metric_name'])
            if not metric_key_params:
                self.logger.warn("Metric not supported: {}".format(config_dict['metric_name']))
                return None
            symptom_details['state']['condition']['key'] = metric_key_params['metric_key']
        """
        self.logger.info("Fetched Symptom details : {}".format(symptom_details))

        api_url = '/suite-api/api/symptomdefinitions'
        headers = {'Content-Type': 'application/json', 'Accept':'application/json'}
        data = json.dumps(symptom_details)
        resp = requests.put(self.vrops_site + api_url,
                             auth=(self.vrops_user, self.vrops_password),
                             headers=headers,
                             verify = False,
                             data=data)

        if resp.status_code != 200:
            self.logger.warn("Failed to update Symptom definition: {}, response {}"\
                    .format(symptom_uuid, resp.content))
            return None


        if symptom_uuid is not None:
            self.logger.info("Symptom defination updated {} for alarm: {}"\
                    .format(symptom_uuid, new_alarm_config['alarm_uuid']))
            return symptom_uuid
        else:
            self.logger.warn("Failed to update Symptom Defination {} for : {}"\
                    .format(symptom_uuid, new_alarm_config['alarm_uuid']))
            return None


    def get_symptom_defination_details(self, symptom_uuid):
        """Get symptom defination details
        """
        symptom_details = {}
        if symptom_uuid is None:
            self.logger.warn("get_symptom_defination_details: Symptom UUID not provided")
            return None

        api_url = '/suite-api/api/symptomdefinitions/'
        headers = {'Accept': 'application/json'}

        resp = requests.get(self.vrops_site + api_url + symptom_uuid,
                            auth=(self.vrops_user, self.vrops_password),
                            verify = False, headers = headers)

        if resp.status_code is not 200:
            self.logger.warn("Symptom defination not found {} \nResponse code:{}\nResponse Content: {}"\
                    .format(symptom_uuid, resp.status_code, resp.content))
            return None

        symptom_details = json.loads(resp.content)
        #print "New symptom Details: {}".format(symptom_details)
        return symptom_details


    def reconfigure_alarm(self, alarm_details_json, new_alarm_config):
        """Reconfigure alarm defination as per input
        """
        if new_alarm_config.has_key('severity') and new_alarm_config['severity'] is not None:
            alarm_details_json['states'][0]['severity'] = new_alarm_config['severity']
        if new_alarm_config.has_key('description') and new_alarm_config['description'] is not None:
            alarm_details_json['description'] = new_alarm_config['description']

        api_url = '/suite-api/api/alertdefinitions'
        headers = {'Content-Type': 'application/json', 'Accept':'application/json'}
        data = json.dumps(alarm_details_json)
        resp = requests.put(self.vrops_site + api_url,
                             auth=(self.vrops_user, self.vrops_password),
                             headers=headers,
                             verify = False,
                             data=data)

        if resp.status_code != 200:
            self.logger.warn("Failed to create Symptom definition: {}, response code {}, response content: {}"\
                    .format(symptom_uuid, resp.status_code, resp.content))
            return None
        else:
            parsed_alarm_details = json.loads(resp.content)
            alarm_def_uuid = parsed_alarm_details['id'].split('-', 1)[1]
            self.logger.info("Successfully updated Alarm defination: {}".format(alarm_def_uuid))
            return alarm_def_uuid

    def delete_alarm_configuration(self, delete_alarm_req_dict):
        """Delete complete alarm configuration
        """
        if delete_alarm_req_dict['alarm_uuid'] is None:
            self.logger.info("delete_alarm_configuration: Alarm UUID not provided")
            return None
        #1)Get alarm & symptom defination details
        alarm_details_json, alarm_details = self.get_alarm_defination_details(delete_alarm_req_dict['alarm_uuid'])
        if alarm_details is None or alarm_details_json is None:
            return None

        #2) Delete alarm notfication
        rule_id = self.delete_notification_rule(alarm_details['alarm_name'])
        if rule_id is None:
            return None

        #3) Delete alarm configuraion
        alarm_id = self.delete_alarm_defination(alarm_details['alarm_id'])
        if alarm_id is None:
            return None

        #4) Delete alarm symptom
        symptom_id = self.delete_symptom_definition(alarm_details['symptom_definition_id'])
        if symptom_id is None:
            return None
        else:
            self.logger.info("Completed deleting alarm configuration: {}"\
                    .format(delete_alarm_req_dict['alarm_uuid']))
            return delete_alarm_req_dict['alarm_uuid']

    def delete_notification_rule(self, alarm_name):
        """Deleted notification rule defined for a particular alarm
        """
        rule_id = self.get_notification_rule_id_by_alarm_name(alarm_name)
        if rule_id is None:
            return None
        else:
            api_url = '/suite-api/api/notifications/rules/'
            headers = {'Accept':'application/json'}
            resp = requests.delete(self.vrops_site + api_url + rule_id,
                                auth=(self.vrops_user, self.vrops_password),
                                verify = False, headers = headers)
            if resp.status_code is not 204:
                self.logger.warn("Failed to delete notification rules for {}".format(alarm_name))
                return None
            else:
                self.logger.info("Deleted notification rules for {}".format(alarm_name))
                return rule_id

    def get_notification_rule_id_by_alarm_name(self, alarm_name):
        """Find created Alarm notification rule id by alarm name
        """
        alarm_notify_id = 'notify_' + alarm_name
        api_url = '/suite-api/api/notifications/rules'
        headers = {'Content-Type': 'application/json', 'Accept':'application/json'}
        resp = requests.get(self.vrops_site + api_url,
                            auth=(self.vrops_user, self.vrops_password),
                            verify = False, headers = headers)

        if resp.status_code is not 200:
            self.logger.warn("Failed to get notification rules details for {}"\
                    .format(delete_alarm_req_dict['alarm_name']))
            return None

        notifications = json.loads(resp.content)
        if notifications is not None and notifications.has_key('notification-rule'):
            notifications_list = notifications['notification-rule']
            for dict in notifications_list:
                if dict['name'] is not None and dict['name'] == alarm_notify_id:
                    notification_id = dict['id']
                    self.logger.info("Found Notification id to be deleted: {} for {}"\
                            .format(notification_id, alarm_name))
                    return notification_id

            self.logger.warn("Notification id to be deleted not found for {}"\
                            .format(notification_id, alarm_name))
            return None

    def delete_alarm_defination(self, alarm_id):
        """Delete created Alarm defination
        """
        api_url = '/suite-api/api/alertdefinitions/'
        headers = {'Accept':'application/json'}
        resp = requests.delete(self.vrops_site + api_url + alarm_id,
                            auth=(self.vrops_user, self.vrops_password),
                            verify = False, headers = headers)
        if resp.status_code is not 204:
            self.logger.warn("Failed to delete alarm definition {}".format(alarm_id))
            return None
        else:
            self.logger.info("Deleted alarm definition {}".format(alarm_id))
            return alarm_id

    def delete_symptom_definition(self, symptom_id):
        """Delete symptom defination
        """
        api_url = '/suite-api/api/symptomdefinitions/'
        headers = {'Accept':'application/json'}
        resp = requests.delete(self.vrops_site + api_url + symptom_id,
                            auth=(self.vrops_user, self.vrops_password),
                            verify = False, headers = headers)
        if resp.status_code is not 204:
            self.logger.warn("Failed to delete symptom definition {}".format(symptom_id))
            return None
        else:
            self.logger.info("Deleted symptom definition {}".format(symptom_id))
            return symptom_id


    def verify_metric_support(self, metric_info):
        """Verify, if Metric is supported by vROPs plugin, verify metric unit & return status
            Returns:
            status: True if supported, False if not supported
        """
        status = False
        if 'metric_name' not in metric_info:
            self.logger.debug("Metric name not provided: {}".format(metric_info))
            return status
        metric_key_params = self.get_default_Params(metric_info['metric_name'])
        if not metric_key_params:
            self.logger.warn("Metric not supported: {}".format(metric_info['metric_name']))
            return status
        else:
            #If Metric is supported, verify optional metric unit & return status
            if 'metric_unit' in metric_info:
                if metric_key_params.get('unit') == metric_info['metric_unit']:
                    self.logger.info("Metric is supported with unit: {}".format(metric_info['metric_name']))
                    status = True
                else:
                    self.logger.debug("Metric supported but there is unit mismatch for: {}."\
                                    "Supported unit: {}"\
                                    .format(metric_info['metric_name'],metric_key_params['unit']))
                    status = True
        return status

    def get_triggered_alarms_list(self, list_alarm_input):
        """Get list of triggered alarms on a resource based on alarm input request.
        """
        #TO Do - Need to add filtering of alarms based on Severity & alarm name

        triggered_alarms_list = []
        if list_alarm_input['resource_uuid'] is None:
            return triggered_alarms_list

        #1)Find vROPs resource ID using RO resource UUID
        vrops_resource_id = self.get_vrops_resourceid_from_ro_uuid(list_alarm_input['resource_uuid'])
        if vrops_resource_id is None:
            return triggered_alarms_list

        #2)Get triggered alarms on particular resource
        triggered_alarms_list = self.get_triggered_alarms_on_resource(list_alarm_input['resource_uuid'], vrops_resource_id)
        return triggered_alarms_list

    def get_vrops_resourceid_from_ro_uuid(self, ro_resource_uuid):
        """Fetch vROPs resource ID using resource UUID from RO/SO
        """
        #1) Find vm_moref_id from vApp uuid in vCD
        vm_moref_id = self.get_vm_moref_id(ro_resource_uuid)
        if vm_moref_id is None:
            self.logger.warn("Failed to find vm morefid for vApp in vCD: {}".format(ro_resource_uuid))
            return None

        #2) Based on vm_moref_id, find VM's corresponding resource_id in vROPs to set notification
        vrops_resource_id = self.get_vm_resource_id(vm_moref_id)
        if vrops_resource_id is None:
            self.logger.warn("Failed to find resource in vROPs: {}".format(ro_resource_uuid))
            return None
        return vrops_resource_id


    def get_triggered_alarms_on_resource(self, ro_resource_uuid, vrops_resource_id):
        """Get triggered alarms on particular resource & return list of dictionary of alarms
        """
        resource_alarms = []
        api_url = '/suite-api/api/alerts?resourceId='
        headers = {'Accept':'application/json'}
        resp = requests.get(self.vrops_site + api_url + vrops_resource_id,
                            auth=(self.vrops_user, self.vrops_password),
                            verify = False, headers = headers)

        if resp.status_code is not 200:
            self.logger.warn("Failed to get notification rules details for {}"\
                    .format(delete_alarm_req_dict['alarm_name']))
            return None

        all_alerts = json.loads(resp.content)
        if all_alerts.has_key('alerts'):
            if not all_alerts['alerts']:
                self.logger.info("No alarms present on resource {}".format(ro_resource_uuid))
                return resource_alarms
            all_alerts_list = all_alerts['alerts']
            for alarm in all_alerts_list:
                #self.logger.info("Triggered Alarm {}".format(alarm))
                if alarm['alertDefinitionName'] is not None and\
                    len(alarm['alertDefinitionName'].split('-', 1)) == 2:
                        if alarm['alertDefinitionName'].split('-', 1)[1] == ro_resource_uuid:
                            alarm_instance = {}
                            alarm_instance['alarm_uuid'] = alarm['alertDefinitionId'].split('-', 1)[1]
                            alarm_instance['resource_uuid'] = ro_resource_uuid
                            alarm_instance['alarm_instance_uuid'] = alarm['alertId']
                            alarm_instance['vim_type'] = 'VMware'
                            #find severity of alarm
                            severity = None
                            for key,value in severity_mano2vrops.iteritems():
                                if value == alarm['alertLevel']:
                                    severity = key
                            if severity is None:
                                severity = 'INDETERMINATE'
                            alarm_instance['severity'] = severity
                            alarm_instance['status'] = alarm['status']
                            alarm_instance['start_date'] = self.convert_date_time(alarm['startTimeUTC'])
                            alarm_instance['update_date'] = self.convert_date_time(alarm['updateTimeUTC'])
                            alarm_instance['cancel_date'] = self.convert_date_time(alarm['cancelTimeUTC'])
                            self.logger.info("Triggered Alarm on resource {}".format(alarm_instance))
                            resource_alarms.append(alarm_instance)
        if not resource_alarms:
            self.logger.info("No alarms present on resource {}".format(ro_resource_uuid))
        return resource_alarms

    def convert_date_time(self, date_time):
        """Convert the input UTC time in msec to OSM date time format
        """
        date_time_formatted = '0000-00-00T00:00:00'
        if date_time != 0:
            complete_datetime = datetime.datetime.fromtimestamp(date_time/1000.0).isoformat('T')
            date_time_formatted = complete_datetime.split('.',1)[0]
        return date_time_formatted


