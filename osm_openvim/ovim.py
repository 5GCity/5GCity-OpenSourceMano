#!/usr/bin/env python
# -*- coding: utf-8 -*-

##
# Copyright 2015 Telefónica Investigación y Desarrollo, S.A.U.
# This file is part of openvim
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

"""
This is the thread for the http server North API. 
Two thread will be launched, with normal and administrative permissions.
"""

import threading
import yaml
import vim_db
import logging
# import imp
import os.path
import argparse
from netaddr import IPNetwork
from jsonschema import validate as js_v, exceptions as js_e
import host_thread as ht
import dhcp_thread as dt
import openflow_thread as oft
import openflow_conn

__author__ = "Alfonso Tierno, Leonardo Mirabal"
__date__ = "$06-Feb-2017 12:07:15$"
__version__ = "0.5.24-r542"
version_date = "Mar 2018"
database_version = 23      #needed database schema version

HTTP_Bad_Request =          400
HTTP_Unauthorized =         401
HTTP_Not_Found =            404
HTTP_Forbidden =            403
HTTP_Method_Not_Allowed =   405
HTTP_Not_Acceptable =       406
HTTP_Request_Timeout =      408
HTTP_Conflict =             409
HTTP_Service_Unavailable =  503
HTTP_Internal_Server_Error= 500


def convert_boolean(data, items):
    '''Check recursively the content of data, and if there is an key contained in items, convert value from string to boolean
    It assumes that bandwidth is well formed
    Attributes:
        'data': dictionary bottle.FormsDict variable to be checked. None or empty is consideted valid
        'items': tuple of keys to convert
    Return:
        None
    '''
    if type(data) is dict:
        for k in data.keys():
            if type(data[k]) is dict or type(data[k]) is tuple or type(data[k]) is list:
                convert_boolean(data[k], items)
            if k in items:
                if type(data[k]) is str:
                    if data[k] == "false":
                        data[k] = False
                    elif data[k] == "true":
                        data[k] = True
    if type(data) is tuple or type(data) is list:
        for k in data:
            if type(k) is dict or type(k) is tuple or type(k) is list:
                convert_boolean(k, items)



class ovimException(Exception):
    def __init__(self, message, http_code=HTTP_Bad_Request):
        self.http_code = http_code
        Exception.__init__(self, message)


class ovim():
    running_info = {} #TODO OVIM move the info of running threads from config_dic to this static variable
    of_module = {}

    def __init__(self, configuration):
        self.config = configuration
        self.logger_name = configuration.get("logger_name", "openvim")
        self.logger = logging.getLogger(self.logger_name)
        self.db = None
        self.db = self._create_database_connection()
        self.of_test_mode = False

    def _create_database_connection(self):
        db = vim_db.vim_db((self.config["network_vlan_range_start"], self.config["network_vlan_range_end"]),
                           self.logger_name + ".db", self.config.get('log_level_db'))
        if db.connect(self.config['db_host'], self.config['db_user'], self.config['db_passwd'],
                      self.config['db_name']) == -1:
            # self.logger.error("Cannot connect to database %s at %s@%s", self.config['db_name'], self.config['db_user'],
            #              self.config['db_host'])
            raise ovimException("Cannot connect to database {} at {}@{}".format(self.config['db_name'],
                                                                                self.config['db_user'],
                                                                                self.config['db_host']) )
        return db

    @staticmethod
    def get_version():
        return __version__

    @staticmethod
    def get_version_date():
        return version_date

    @staticmethod
    def get_database_version():
        return database_version

    @staticmethod
    def _check_dhcp_data_integrity(network):
        """
        Check if all dhcp parameter for anet are valid, if not will be calculated from cidr value
        :param network: list with user nets paramters
        :return:
        """
        if "cidr" in network:
            cidr = network["cidr"]
            ip_tools = IPNetwork(cidr)
            cidr_len = ip_tools.prefixlen
            if cidr_len > 29:
                return False

            ips = IPNetwork(cidr)
            if "dhcp_first_ip" not in network:
                network["dhcp_first_ip"] = str(ips[3])
            if "dhcp_last_ip" not in network:
                network["dhcp_last_ip"] = str(ips[-2])
            if "gateway_ip" not in network:
                network["gateway_ip"] = str(ips[1])

            return True
        else:
            return False

    @staticmethod
    def _check_valid_uuid(uuid):
        id_schema = {"type": "string", "pattern": "^[a-fA-F0-9]{8}(-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}$"}
        try:
            js_v(uuid, id_schema)
            return True
        except js_e.ValidationError:
            return False

    def start_service(self):
        """
        Start ovim services
        :return:
        """
        global database_version
        # if self.running_info:
        #    return  #TODO service can be checked and rebuild broken threads
        r = self.db.get_db_version()
        db_path = __file__
        db_path = db_path[:db_path.rfind("/")]
        if os.path.exists(db_path + "/database_utils/migrate_vim_db.sh"):
            db_path += "/database_utils"
        else:
            db_path += "/../database_utils"

        if r[0] < 0:
            raise ovimException("DATABASE is not valid. If you think it is corrupted, you can init it with"
                                " '{db_path}/init_vim_db.sh' script".format(db_path=db_path))
        elif r[0] != database_version:
            raise ovimException("DATABASE wrong version '{current}'. Try to upgrade/downgrade to version '{target}'"
                                " with '{db_path}/migrate_vim_db.sh {target}'".format(
                                current=r[0], target=database_version,  db_path=db_path))
        self.logger.critical("Starting ovim server version: '{} {}' database version '{}'".format(
            self.get_version(), self.get_version_date(), self.get_database_version()))
        # create database connection for openflow threads
        self.config["db"] = self._create_database_connection()
        self.config["db_lock"] = threading.Lock()

        self.of_test_mode = False if self.config['mode'] == 'normal' or self.config['mode'] == "OF only" else True

        # Create one thread for each host
        host_test_mode = True if self.config['mode'] == 'test' or self.config['mode'] == "OF only" else False
        host_develop_mode = True if self.config['mode'] == 'development' else False
        host_develop_bridge_iface = self.config.get('development_bridge', None)

        # get host list from data base before starting threads
        r, hosts = self.db.get_table(SELECT=('name', 'ip_name', 'user', 'uuid', 'hypervisors', 'password', 'keyfile'),
                                     FROM='hosts', WHERE={'status': 'ok'}) #Unikernels extension
        if r < 0:
            raise ovimException("Cannot get hosts from database {}".format(hosts))

        self.config['host_threads'] = {}

        for host in hosts:
            thread = ht.host_thread(name=host['name'], user=host['user'], host=host['ip_name'], db=self.config["db"],
                                    password=host['password'],
                                    keyfile=host.get('keyfile', self.config["host_ssh_keyfile"]),
                                    db_lock=self.config["db_lock"], test=host_test_mode,
                                    image_path=self.config['host_image_path'],
                                    version=self.config['version'], host_id=host['uuid'],
                                    develop_mode=host_develop_mode,
                                    develop_bridge_iface=host_develop_bridge_iface,
                                    hypervisors=host['hypervisors'],  #Unikernels extension
                                    logger_name=self.logger_name + ".host." + host['name'],
                                    debug=self.config.get('log_level_host'))

            try:
                thread.check_connectivity()
            except Exception as e:
                self.logger.critical('Error detected for compute = {} with ip = {}'
                                     .format(host['name'], host['ip_name']))
            thread.start()
            self.config['host_threads'][host['uuid']] = thread

        # precreate interfaces; [bridge:<host_bridge_name>, VLAN used at Host, uuid of network camping in this bridge,
        # speed in Gbit/s

        self.config['dhcp_nets'] = []
        self.config['bridge_nets'] = []
        for bridge, vlan_speed in self.config["bridge_ifaces"].items():
            # skip 'development_bridge'
            if self.config['mode'] == 'development' and self.config['development_bridge'] == bridge:
                continue
            self.config['bridge_nets'].append([bridge, vlan_speed[0], vlan_speed[1], None])

        # check if this bridge is already used (present at database) for a network)
        used_bridge_nets = []
        for brnet in self.config['bridge_nets']:
            r, nets = self.db.get_table(SELECT=('uuid',), FROM='nets', WHERE={'provider': "bridge:" + brnet[0]})
            if r > 0:
                brnet[3] = nets[0]['uuid']
                used_bridge_nets.append(brnet[0])
                if self.config.get("dhcp_server"):
                    if brnet[0] in self.config["dhcp_server"]["bridge_ifaces"]:
                        self.config['dhcp_nets'].append(nets[0]['uuid'])
        if len(used_bridge_nets) > 0:
            self.logger.info("found used bridge nets: " + ",".join(used_bridge_nets))
        # get nets used by dhcp
        if self.config.get("dhcp_server"):
            for net in self.config["dhcp_server"].get("nets", ()):
                r, nets = self.db.get_table(SELECT=('uuid',), FROM='nets', WHERE={'name': net})
                if r > 0:
                    self.config['dhcp_nets'].append(nets[0]['uuid'])

        # OFC default
        self._start_ofc_default_task()

        # OFC per tenant in DB
        self._start_of_db_tasks()

        # create dhcp_server thread
        host_test_mode = True if self.config['mode'] == 'test' or self.config['mode'] == "OF only" else False
        dhcp_params = self.config.get("dhcp_server")
        if dhcp_params:
            thread = dt.dhcp_thread(dhcp_params=dhcp_params, test=host_test_mode, dhcp_nets=self.config["dhcp_nets"],
                                    db=self.config["db"], db_lock=self.config["db_lock"],
                                    logger_name=self.logger_name + ".dhcp",
                                    debug=self.config.get('log_level_of'))
            thread.start()
            self.config['dhcp_thread'] = thread



        # create ovs dhcp thread
        result, content = self.db.get_table(FROM='nets')
        if result < 0:
            self.logger.error("http_get_ports Error %d %s", result, content)
            raise ovimException(str(content), -result)

        for net in content:
            net_type = net['type']
            if net['status'] != "INACTIVE" and (net_type == 'bridge_data' or net_type == 'bridge_man') and \
                    net["provider"][:4] == 'OVS:' and net["enable_dhcp"] == "true":
                try:
                    config_routes = net.get('routes')
                    if config_routes:
                        routes = yaml.safe_load(config_routes)
                    else:
                        routes = None

                    config_dns = net.get('dns')
                    if config_dns:
                        dns = yaml.safe_load(config_dns)
                    else:
                        dns = None

                    links = net.get('links')
                    if links:
                        links = yaml.safe_load(net.get('links'))
                    if net.get('enable_dhcp'):
                        self.launch_dhcp_server(net.get('vlan'),
                                                net.get('dhcp_first_ip'),
                                                net.get('dhcp_last_ip'),
                                                net.get('cidr'),
                                                net.get('gateway_ip'),
                                                dns,
                                                routes)
                    self.launch_link_bridge_to_ovs(net['vlan'], net.get('gateway_ip'), net.get('cidr'), links, routes)
                    if net["status"] == "ERROR":
                        self.db.update_rows("nets", UPDATE={"status": "ACTIVE", "last_error": None},
                                            WHERE={"uuid": net["uuid"]})
                except Exception as e:
                    self.logger.error("Fail at launching dhcp server for net_id='%s' net_name='%s': %s",
                                      net["uuid"], net["name"], str(e))
                    self.db.update_rows("nets", UPDATE={"status": "ERROR",
                                                 "last_error": "Fail at launching dhcp server: " + str(e)},
                                        WHERE={"uuid": net["uuid"]})

    def _start_of_db_tasks(self):
        """
        Start ofc task for existing ofcs in database
        :param db_of:
        :param db_lock:
        :return:
        """
        ofcs = self.get_of_controllers()

        for ofc in ofcs:
            of_conn = self._load_of_module(ofc)
            # create ofc thread per of controller
            self._create_ofc_task(ofc['uuid'], ofc['dpid'], of_conn)

    def _create_ofc_task(self, ofc_uuid, dpid, of_conn):
        """
        Create an ofc thread for handle each sdn controllers
        :param ofc_uuid: sdn controller uuid
        :param dpid:  sdn controller dpid
        :param of_conn: OF_conn module
        :return:
        """
        if 'ofcs_thread' not in self.config and 'ofcs_thread_dpid' not in self.config:
            ofcs_threads = {}
            ofcs_thread_dpid = []
        else:
            ofcs_threads = self.config['ofcs_thread']
            ofcs_thread_dpid = self.config['ofcs_thread_dpid']

        if ofc_uuid not in ofcs_threads:
            ofc_thread = self._create_ofc_thread(of_conn, ofc_uuid)
            if ofc_uuid == "Default":
                self.config['of_thread'] = ofc_thread

            ofcs_threads[ofc_uuid] = ofc_thread
            self.config['ofcs_thread'] = ofcs_threads

            ofcs_thread_dpid.append({dpid: ofc_thread})
            self.config['ofcs_thread_dpid'] = ofcs_thread_dpid

    def _start_ofc_default_task(self):
        """
        Create default ofc thread
        """
        if 'of_controller' not in self.config \
                and 'of_controller_ip' not in self.config \
                and 'of_controller_port' not in self.config \
                and 'of_controller_dpid' not in self.config:
            return

        # OF THREAD
        db_config = {}
        db_config['ip'] = self.config.get('of_controller_ip')
        db_config['port'] = self.config.get('of_controller_port')
        db_config['dpid'] = self.config.get('of_controller_dpid')
        db_config['type'] = self.config.get('of_controller')
        db_config['user'] = self.config.get('of_user')
        db_config['password'] = self.config.get('of_password')

        # create connector to the openflow controller
        # load other parameters starting by of_ from config dict in a temporal dict

        of_conn = self._load_of_module(db_config)
        # create openflow thread
        self._create_ofc_task("Default", db_config['dpid'], of_conn)

    def _load_of_module(self, db_config):
        """
        import python module for each SDN controller supported
        :param db_config: SDN dn information
        :return: Module
        """
        if not db_config:
            raise ovimException("No module found it", HTTP_Internal_Server_Error)

        module_info = None

        try:
            if self.of_test_mode:
                return openflow_conn.OfTestConnector({"name": db_config['type'],
                                                      "dpid": db_config['dpid'],
                                                      "of_debug": self.config['log_level_of']})
            temp_dict = {}

            if db_config:
                temp_dict['of_ip'] = db_config['ip']
                temp_dict['of_port'] = db_config['port']
                temp_dict['of_dpid'] = db_config['dpid']
                temp_dict['of_controller'] = db_config['type']
                temp_dict['of_user'] = db_config.get('user')
                temp_dict['of_password'] = db_config.get('password')

            temp_dict['of_debug'] = self.config['log_level_of']

            if temp_dict['of_controller'] == 'opendaylight':
                module = "ODL"
            else:
                module = temp_dict['of_controller']

            if module not in ovim.of_module:
                try:
                    pkg = __import__("osm_openvim." + module)
                    of_conn_module = getattr(pkg, module)
                    ovim.of_module[module] = of_conn_module
                    self.logger.debug("Module load from {}".format("osm_openvim." + module))
                except Exception as e:
                    self.logger.error("Cannot open openflow controller module of type '%s'", module)
                    raise ovimException("Cannot open openflow controller of type module '{}'"
                                        "Revise it is installed".format(module),
                                        HTTP_Internal_Server_Error)
            else:
                of_conn_module = ovim.of_module[module]
            return of_conn_module.OF_conn(temp_dict)
        except Exception as e:
            self.logger.error("Cannot open the Openflow controller '%s': %s", type(e).__name__, str(e))
            raise ovimException("Cannot open the Openflow controller '{}': '{}'".format(type(e).__name__, str(e)),
                                HTTP_Internal_Server_Error)

    def _create_ofc_thread(self, of_conn, ofc_uuid="Default"):
        """
        Create and launch a of thread
        :return: thread obj
        """
        # create openflow thread

        #if 'of_controller_nets_with_same_vlan' in self.config:
        #    ofc_net_same_vlan = self.config['of_controller_nets_with_same_vlan']
        #else:
        #    ofc_net_same_vlan = False
        ofc_net_same_vlan = False

        thread = oft.openflow_thread(ofc_uuid, of_conn, of_test=self.of_test_mode, db=self.config["db"],
                                     db_lock=self.config["db_lock"],
                                     pmp_with_same_vlan=ofc_net_same_vlan,
                                     logger_name=self.logger_name + ".ofc." + ofc_uuid,
                                     debug=self.config.get('log_level_of'))
        #r, c = thread.OF_connector.obtain_port_correspondence()
        #if r < 0:
        #    raise ovimException("Cannot get openflow information %s", c)
        thread.start()
        return thread

    def stop_service(self):
        threads = self.config.get('host_threads', {})
        if 'of_thread' in self.config:
            threads['of'] = (self.config['of_thread'])
        if 'ofcs_thread' in self.config:
            ofcs_thread = self.config['ofcs_thread']
            for ofc in ofcs_thread:
                threads[ofc] = ofcs_thread[ofc]

        if 'dhcp_thread' in self.config:
            threads['dhcp'] = (self.config['dhcp_thread'])

        for thread_id, thread in threads.items():
            if thread_id == 'openvim_controller':
                continue
            thread.insert_task("exit")
        for thread_id, thread in threads.items():
            if thread_id == 'openvim_controller':
                continue
            thread.join()

    def get_networks(self, columns=None, db_filter={}, limit=None):
        """
        Retreive networks available
        :param columns: List with select query parameters
        :param db_filter: List with where query parameters
        :param limit: Query limit result
        :return:
        """
        result, content = self.db.get_table(SELECT=columns, FROM='nets', WHERE=db_filter, LIMIT=limit)

        if result < 0:
            raise ovimException(str(content), -result)

        convert_boolean(content, ('shared', 'admin_state_up', 'enable_dhcp'))

        return content

    def show_network(self, network_id, db_filter={}):
        """
        Get network from DB by id
        :param network_id: net Id
        :param db_filter: List with where query parameters
        :return:
        """
        # obtain data
        if not network_id:
            raise ovimException("Not network id was not found")
        db_filter['uuid'] = network_id

        result, content = self.db.get_table(FROM='nets', WHERE=db_filter, LIMIT=100)

        if result < 0:
            raise ovimException(str(content), -result)
        elif result == 0:
            raise ovimException("show_network network '%s' not found" % network_id, -result)
        else:
            convert_boolean(content, ('shared', 'admin_state_up', 'enable_dhcp'))
            # get ports from DB
            result, ports = self.db.get_table(FROM='ports', SELECT=('uuid as port_id',),
                                              WHERE={'net_id': network_id}, LIMIT=100)
            if len(ports) > 0:
                content[0]['ports'] = ports

            convert_boolean(content, ('shared', 'admin_state_up', 'enable_dhcp'))
            return content[0]

    def new_network(self, network):
        """
        Create a net in DB
        :return:
        """
        tenant_id = network.get('tenant_id')

        if tenant_id:
            result, _ = self.db.get_table(FROM='tenants', SELECT=('uuid',), WHERE={'uuid': tenant_id, "enabled": True})
            if result <= 0:
                raise ovimException("set_network error, no tenant founded", -result)

        bridge_net = None
        # check valid params
        net_provider = network.get('provider')
        net_type = network.get('type')
        net_vlan = network.get("vlan")
        net_bind_net = network.get("bind_net")
        net_bind_type = network.get("bind_type")
        net_region = network.get("region")
        name = network["name"]

        # check if network name ends with :<vlan_tag> and network exist in order to make and automated bindning
        vlan_index = name.rfind(":")
        if not net_bind_net and not net_bind_type and vlan_index > 1:
            try:
                vlan_tag = int(name[vlan_index + 1:])
                if not vlan_tag and vlan_tag < 4096:
                    net_bind_net = name[:vlan_index]
                    net_bind_type = "vlan:" + name[vlan_index + 1:]
            except:
                pass

        if net_bind_net:
            # look for a valid net
            if self._check_valid_uuid(net_bind_net):
                net_bind_key = "uuid"
            else:
                net_bind_key = "name"
            result, content = self.db.get_table(FROM='nets', WHERE={net_bind_key: net_bind_net})
            if result < 0:
                raise ovimException(' getting nets from db ' + content, HTTP_Internal_Server_Error)
            elif result == 0:
                raise ovimException(" bind_net %s '%s'not found" % (net_bind_key, net_bind_net), HTTP_Bad_Request)
            elif result > 1:
                raise ovimException(" more than one bind_net %s '%s' found, use uuid" % (net_bind_key, net_bind_net), HTTP_Bad_Request)
            network["bind_net"] = content[0]["uuid"]

        if net_bind_type:
            if net_bind_type[0:5] != "vlan:":
                raise ovimException("bad format for 'bind_type', must be 'vlan:<tag>'", HTTP_Bad_Request)
            if int(net_bind_type[5:]) > 4095 or int(net_bind_type[5:]) <= 0:
                raise ovimException("bad format for 'bind_type', must be 'vlan:<tag>' with a tag between 1 and 4095",
                                    HTTP_Bad_Request)
            network["bind_type"] = net_bind_type

        if net_provider:
            if net_provider[:9] == "openflow:":
                if net_type:
                    if net_type != "ptp" and net_type != "data":
                        raise ovimException(" only 'ptp' or 'data' net types can be bound to 'openflow'",
                                            HTTP_Bad_Request)
                else:
                    net_type = 'data'
            else:
                if net_type:
                    if net_type != "bridge_man" and net_type != "bridge_data":
                        raise ovimException("Only 'bridge_man' or 'bridge_data' net types can be bound "
                                            "to 'bridge', 'macvtap' or 'default", HTTP_Bad_Request)
                else:
                    net_type = 'bridge_man'

        if not net_type:
            net_type = 'bridge_man'

        if net_provider:
            if net_provider[:7] == 'bridge:':
                # check it is one of the pre-provisioned bridges
                bridge_net_name = net_provider[7:]
                for brnet in self.config['bridge_nets']:
                    if brnet[0] == bridge_net_name:  # free
                        if brnet[3]:
                            raise ovimException("invalid 'provider:physical', "
                                                "bridge '%s' is already used" % bridge_net_name, HTTP_Conflict)
                        bridge_net = brnet
                        net_vlan = brnet[1]
                        break
                        # if bridge_net==None:
                        #    bottle.abort(HTTP_Bad_Request, "invalid 'provider:physical', bridge '%s' is not one of the
                        #                    provisioned 'bridge_ifaces' in the configuration file" % bridge_net_name)
                        #    return

        elif self.config['network_type'] == 'bridge' and (net_type == 'bridge_data' or net_type == 'bridge_man'):
            # look for a free precreated nets
            for brnet in self.config['bridge_nets']:
                if not brnet[3]:  # free
                    if not bridge_net:
                        if net_type == 'bridge_man':  # look for the smaller speed
                            if brnet[2] < bridge_net[2]:
                                bridge_net = brnet
                        else:  # look for the larger speed
                            if brnet[2] > bridge_net[2]:
                                bridge_net = brnet
                    else:
                        bridge_net = brnet
                        net_vlan = brnet[1]
            if not bridge_net:
                raise ovimException("Max limits of bridge networks reached. Future versions of VIM "
                                    "will overcome this limit", HTTP_Bad_Request)
            else:
                self.logger.debug("using net " + bridge_net)
                net_provider = "bridge:" + bridge_net[0]
                net_vlan = bridge_net[1]
        elif net_type == 'bridge_data' or net_type == 'bridge_man' and self.config['network_type'] == 'ovs':
            net_provider = 'OVS'
        if not net_region:
            if net_type == "data" or net_type == "ptp":
                net_region = "__DATA__"
            elif net_provider == "OVS":
                net_region = "__OVS__"
        if not net_vlan and (net_type == "data" or net_type == "ptp" or net_provider == "OVS"):
            net_vlan = self.db.get_free_net_vlan(net_region)
            if net_vlan < 0:
                raise ovimException("Error getting an available vlan", HTTP_Internal_Server_Error)
        if net_provider == 'OVS':
            net_provider = 'OVS' + ":" + str(net_vlan)

        network['provider'] = net_provider
        network['type'] = net_type
        network['vlan'] = net_vlan
        network['region'] = net_region
        dhcp_integrity = True
        if network.get('enable_dhcp'):
            dhcp_integrity = self._check_dhcp_data_integrity(network)
        
        if network.get('links'):
            network['links'] = yaml.safe_dump(network['links'], default_flow_style=True, width=256)
        if network.get('dns'):
            network['dns'] = yaml.safe_dump(network['dns'], default_flow_style=True, width=256)
        if network.get('routes'):
            network['routes'] = yaml.safe_dump(network['routes'], default_flow_style=True, width=256)

        result, content = self.db.new_row('nets', network, True, True)
        if result >= 0:  # and dhcp_integrity:
            if bridge_net:
                bridge_net[3] = content
            if self.config.get("dhcp_server") and self.config['network_type'] == 'bridge':
                if network["name"] in self.config["dhcp_server"].get("nets", ()):
                    self.config["dhcp_nets"].append(content)
                    self.logger.debug("dhcp_server: add new net", content)
                elif bridge_net and bridge_net[0] in self.config["dhcp_server"].get("bridge_ifaces", ()):
                    self.config["dhcp_nets"].append(content)
                    self.logger.debug("dhcp_server: add new net", content, content)
            return content
        else:
            raise ovimException("Error creating network: {}".format(content), -result)

# TODO kei change update->edit

    def edit_network(self, network_id, network):
        """
        Update entwork data byt id
        :return:
        """
        # Look for the previous data
        where_ = {'uuid': network_id}
        result, network_old = self.db.get_table(FROM='nets', WHERE=where_)
        if result < 0:
            raise ovimException("Error updating network %s" % network_old, HTTP_Internal_Server_Error)
        elif result == 0:
            raise ovimException('network %s not found' % network_id, HTTP_Not_Found)
        # get ports
        nbports, content = self.db.get_table(FROM='ports', SELECT=('uuid as port_id',),
                                             WHERE={'net_id': network_id}, LIMIT=100)
        if result < 0:
            raise ovimException("http_put_network_id error %d %s" % (result, network_old), HTTP_Internal_Server_Error)
        if nbports > 0:
            if 'type' in network and network['type'] != network_old[0]['type']:
                raise ovimException("Can not change type of network while having ports attached",
                                    HTTP_Method_Not_Allowed)
            if 'vlan' in network and network['vlan'] != network_old[0]['vlan']:
                raise ovimException("Can not change vlan of network while having ports attached",
                                    HTTP_Method_Not_Allowed)

        # check valid params
        net_provider = network.get('provider', network_old[0]['provider'])
        net_type = network.get('type', network_old[0]['type'])
        net_bind_net = network.get("bind_net")
        net_bind_type = network.get("bind_type")
        if net_bind_net:
            # look for a valid net
            if self._check_valid_uuid(net_bind_net):
                net_bind_key = "uuid"
            else:
                net_bind_key = "name"
            result, content = self.db.get_table(FROM='nets', WHERE={net_bind_key: net_bind_net})
            if result < 0:
                raise ovimException('Getting nets from db ' + content, HTTP_Internal_Server_Error)
            elif result == 0:
                raise ovimException("bind_net %s '%s'not found" % (net_bind_key, net_bind_net), HTTP_Bad_Request)
            elif result > 1:
                raise ovimException("More than one bind_net %s '%s' found, use uuid" % (net_bind_key, net_bind_net),
                                    HTTP_Bad_Request)
            network["bind_net"] = content[0]["uuid"]
        if net_bind_type:
            if net_bind_type[0:5] != "vlan:":
                raise ovimException("Bad format for 'bind_type', must be 'vlan:<tag>'", HTTP_Bad_Request)
            if int(net_bind_type[5:]) > 4095 or int(net_bind_type[5:]) <= 0:
                raise ovimException("bad format for 'bind_type', must be 'vlan:<tag>' with a tag between 1 and 4095",
                                    HTTP_Bad_Request)
        if net_provider:
            if net_provider[:9] == "openflow:":
                if net_type != "ptp" and net_type != "data":
                    raise ovimException("Only 'ptp' or 'data' net types can be bound to 'openflow'", HTTP_Bad_Request)
            else:
                if net_type != "bridge_man" and net_type != "bridge_data":
                    raise ovimException("Only 'bridge_man' or 'bridge_data' net types can be bound to "
                                        "'bridge', 'macvtap' or 'default", HTTP_Bad_Request)

        # insert in data base
        result, content = self.db.update_rows('nets', network, WHERE={'uuid': network_id}, log=True)
        if result >= 0:
            # if result > 0 and nbports>0 and 'admin_state_up' in network
            #     and network['admin_state_up'] != network_old[0]['admin_state_up']:
            if result > 0:

                try:
                    if nbports:
                        self.net_update_ofc_thread(network_id)
                except ovimException as e:
                    raise ovimException("Error while launching openflow rules in network '{}' {}"
                                        .format(network_id, str(e)), HTTP_Internal_Server_Error)
                except Exception as e:
                    raise ovimException("Error while launching openflow rules in network '{}' {}"
                                        .format(network_id, str(e)), HTTP_Internal_Server_Error)

                if self.config.get("dhcp_server"):
                    if network_id in self.config["dhcp_nets"]:
                        self.config["dhcp_nets"].remove(network_id)
                    if network.get("name", network_old[0]["name"]) in self.config["dhcp_server"].get("nets", ()):
                        self.config["dhcp_nets"].append(network_id)
                    else:
                        net_bind = network.get("bind_type", network_old[0]["bind_type"])
                        if net_bind and net_bind and net_bind[:7] == "bridge:" and net_bind[7:] in self.config["dhcp_server"].get(
                                "bridge_ifaces", ()):
                            self.config["dhcp_nets"].append(network_id)
            return network_id
        else:
            raise ovimException(content, -result)

    def delete_network(self, network_id):
        """
        Delete network by network id
        :param network_id:  network id
        :return:
        """
        net_data = self.show_network(network_id)

        # delete from the data base
        result, content = self.db.delete_row('nets', network_id)

        if result == 0:
            raise ovimException("Network %s not found " % network_id, HTTP_Not_Found)
        elif result > 0:
            for brnet in self.config['bridge_nets']:
                if brnet[3] == network_id:
                    brnet[3] = None
                    break
            if self.config.get("dhcp_server") and network_id in self.config["dhcp_nets"]:
                self.config["dhcp_nets"].remove(network_id)

            if net_data.get('enable_dhcp'):
                dhcp_path = self.config['ovs_controller_file_path']
                dhcp_controller = self.get_dhcp_controller()
                dhcp_controller.delete_dhcp_server(net_data['vlan'], network_id, dhcp_path)
                dhcp_controller.delete_dhcp_port(net_data['vlan'], network_id, dhcp_path)
                links = yaml.load(net_data.get('links'))
                if links:
                    links = yaml.load(net_data.get('links'))
                    self.delete_link_bridge_to_ovs(net_data['vlan'], links)

                return content
        else:
            raise ovimException("Error deleting network '{}': {}".format(network_id, content), -result)

    def get_openflow_rules(self, network_id=None):
        """
        Get openflow id from DB
        :param network_id: Network id, if none all networks will be retrieved
        :return: Return a list with Openflow rules per net
        """
        # ignore input data
        if not network_id:
            where_ = {}
        else:
            where_ = {"net_id": network_id}
        result, content = self.db.get_table(
            SELECT=("name", "net_id", "ofc_id", "priority", "vlan_id", "ingress_port", "src_mac", "dst_mac", "actions"),
            WHERE=where_, FROM='of_flows')

        if result < 0:
            raise ovimException(str(content), -result)
        return content

    def edit_openflow_rules(self, network_id=None):

        """
        To make actions over the net. The action is to reinstall the openflow rules
        network_id can be 'all'
        :param network_id: Network id, if none all networks will be retrieved
        :return : Number of nets updated
        """

        # ignore input data
        if not network_id:
            where_ = {}
        else:
            where_ = {"uuid": network_id}
        result, content = self.db.get_table(SELECT=("uuid", "type"), WHERE=where_, FROM='nets')

        if result < 0:
            raise ovimException(str(content), -result)

        for net in content:
            if net["type"] != "ptp" and net["type"] != "data":
                result -= 1
                continue

            try:
                self.net_update_ofc_thread(net['uuid'])
            except ovimException as e:
                raise ovimException("Error updating network'{}' {}".format(net['uuid'], str(e)),
                                    HTTP_Internal_Server_Error)
            except Exception as e:
                raise ovimException("Error updating network '{}' {}".format(net['uuid'], str(e)),
                                    HTTP_Internal_Server_Error)

        return result

    def delete_openflow_rules(self, ofc_id=None):
        """
        To make actions over the net. The action is to delete ALL openflow rules
        :return: return operation result
        """

        if not ofc_id:
            if 'Default' in self.config['ofcs_thread']:
                r, c = self.config['ofcs_thread']['Default'].insert_task("clear-all")
            else:
                raise ovimException("Default Openflow controller not not running", HTTP_Not_Found)

        elif ofc_id in self.config['ofcs_thread']:
            r, c = self.config['ofcs_thread'][ofc_id].insert_task("clear-all")

            # ignore input data
            if r < 0:
                raise ovimException(str(c), -r)
        else:
            raise ovimException("Openflow controller not found with ofc_id={}".format(ofc_id), HTTP_Not_Found)
        return r

    def get_openflow_ports(self, ofc_id=None):
        """
        Obtain switch ports names of openflow controller
        :return: Return flow ports in DB
        """
        if not ofc_id:
            if 'Default' in self.config['ofcs_thread']:
                conn = self.config['ofcs_thread']['Default'].OF_connector
            else:
                raise ovimException("Default Openflow controller not not running", HTTP_Not_Found)

        elif ofc_id in self.config['ofcs_thread']:
            conn = self.config['ofcs_thread'][ofc_id].OF_connector
        else:
            raise ovimException("Openflow controller not found with ofc_id={}".format(ofc_id), HTTP_Not_Found)
        return conn.pp2ofi

    def get_ports(self, columns=None, filter={}, limit=None):
        # result, content = my.db.get_ports(where_)
        result, content = self.db.get_table(SELECT=columns, WHERE=filter, FROM='ports', LIMIT=limit)
        if result < 0:
            self.logger.error("http_get_ports Error %d %s", result, content)
            raise ovimException(str(content), -result)
        else:
            convert_boolean(content, ('admin_state_up',))
            return content

    def new_port(self, port_data):
        port_data['type'] = 'external'
        if port_data.get('net_id'):
            # check that new net has the correct type
            result, new_net = self.db.check_target_net(port_data['net_id'], None, 'external')
            if result < 0:
                raise ovimException(str(new_net), -result)
        # insert in data base
        result, uuid = self.db.new_row('ports', port_data, True, True)
        if result > 0:
            if 'net_id' in port_data:
                try:
                    self.net_update_ofc_thread(port_data['net_id'])
                except ovimException as e:
                    raise ovimException("Cannot insert a task for updating network '{}' {}"
                                        .format(port_data['net_id'], str(e)), HTTP_Internal_Server_Error)
                except Exception as e:
                    raise ovimException("Cannot insert a task for updating network '{}' {}"
                                        .format(port_data['net_id'], str(e)), HTTP_Internal_Server_Error)

            return uuid
        else:
            raise ovimException(str(uuid), -result)

    def new_external_port(self, port_data):
        """
        Create new external port and check port mapping correspondence
        :param port_data: port_data = {
            'region': 'datacenter region',
            'compute_node': 'compute node id',
            'pci': 'pci port address',
            'vlan': 'net vlan',
            'net_id': 'net id',
            'tenant_id': 'tenant id',
            'mac': 'switch mac',
            'name': 'port name'
            'ip_address': 'ip address - optional'}
        :return:
        """

        port_data['type'] = 'external'

        if port_data.get('net_id'):
            # check that new net has the correct type
            result, new_net = self.db.check_target_net(port_data['net_id'], None, 'external')
            if result < 0:
                raise ovimException(str(new_net), -result)
        # insert in data base
        db_filter = {}

        if port_data.get('region'):
            db_filter['region'] = port_data['region']
        if port_data.get('pci'):
            db_filter['pci'] = port_data['pci']
        if port_data.get('compute_node'):
            db_filter['compute_node'] = port_data['compute_node']

        columns = ['ofc_id', 'switch_dpid', 'switch_port', 'switch_mac', 'pci']
        port_mapping_data = self.get_of_port_mappings(columns, db_filter)

        if not len(port_mapping_data):
            raise ovimException("No port mapping founded for '{}'".format(str(db_filter)),
                                HTTP_Not_Found)
        elif len(port_mapping_data) > 1:
            raise ovimException("Wrong port data was given, please check pci, region & compute id data",
                                HTTP_Conflict)

        port_data['ofc_id'] = port_mapping_data[0]['ofc_id']
        port_data['switch_dpid'] = port_mapping_data[0]['switch_dpid']
        port_data['switch_port'] = port_mapping_data[0]['switch_port']
        port_data['switch_mac'] = port_mapping_data[0]['switch_mac']

        # remove from compute_node, region and pci of_port_data to adapt to 'ports' structure
        if 'region' in port_data:
            del port_data['region']
        if 'pci' in port_data:
            del port_data['pci']
        if 'compute_node' in port_data:
            del port_data['compute_node']

        result, uuid = self.db.new_row('ports', port_data, True, True)
        if result > 0:
            try:
                self.net_update_ofc_thread(port_data['net_id'], port_data['ofc_id'])
            except ovimException as e:
                raise ovimException("Cannot insert a task for updating network '{}' {}".
                                    format(port_data['net_id'], str(e)), HTTP_Internal_Server_Error)
            except Exception as e:
                raise ovimException("Cannot insert a task for updating network '{}' {}"
                                    .format(port_data['net_id'], e), HTTP_Internal_Server_Error)
            return uuid
        else:
            raise ovimException(str(uuid), -result)

    def net_update_ofc_thread(self, net_id, ofc_id=None, switch_dpid=None):
        """
        Insert a update net task by net id or ofc_id for each ofc thread
        :param net_id: network id
        :param ofc_id: openflow controller id
        :param switch_dpid: switch dpid
        :return:
        """
        if not net_id:
            raise ovimException("No net_id received", HTTP_Internal_Server_Error)

        r = -1
        c = 'No valid ofc_id or switch_dpid received'

        if not ofc_id:
            ports = self.get_ports(filter={"net_id": net_id})
            for port in ports:
                port_ofc_id = port.get('ofc_id', None)
                if port_ofc_id:
                    ofc_id = port['ofc_id']
                    switch_dpid = port['switch_dpid']
                    break
        #TODO if not ofc_id: look at database table ofcs


        # If no ofc_id found it, default ofc_id is used.
        if not ofc_id and not switch_dpid:
            ofc_id = "Default"

        if ofc_id and ofc_id in self.config['ofcs_thread']:
            r, c = self.config['ofcs_thread'][ofc_id].insert_task("update-net", net_id)
        elif switch_dpid:

            ofcs_dpid_list = self.config['ofcs_thread_dpid']
            for ofc_t in ofcs_dpid_list:
                if switch_dpid in ofc_t:
                    r, c = ofc_t[switch_dpid].insert_task("update-net", net_id)

        if r < 0:
            message = "Cannot insert a task for updating network '{}', {}".format(net_id, c)
            self.logger.error(message)
            raise ovimException(message, HTTP_Internal_Server_Error)

    def delete_port(self, port_id):
        # Look for the previous port data
        result, ports = self.db.get_table(WHERE={'uuid': port_id, "type": "external"}, FROM='ports')
        if result < 0:
            raise ovimException("Cannot get port info from database: {}".format(ports), http_code=-result)
        # delete from the data base
        result, content = self.db.delete_row('ports', port_id)
        if result == 0:
            raise ovimException("External port '{}' not found".format(port_id), http_code=HTTP_Not_Found)
        elif result < 0:
            raise ovimException("Cannot delete port from database: {}".format(content), http_code=-result)
        # update network
        network = ports[0].get('net_id', None)
        if network:
            # change of net.

            try:
                self.net_update_ofc_thread(network, ofc_id=ports[0]["ofc_id"], switch_dpid=ports[0]["switch_dpid"])
            except ovimException as e:
                raise ovimException("Cannot insert a task for delete network '{}' {}".format(network, str(e)),
                                    HTTP_Internal_Server_Error)
            except Exception as e:
                raise ovimException("Cannot insert a task for delete network '{}' {}".format(network, str(e)),
                                    HTTP_Internal_Server_Error)

        return content

    def edit_port(self, port_id, port_data, admin=True):
        # Look for the previous port data
        result, content = self.db.get_table(FROM="ports", WHERE={'uuid': port_id})
        if result < 0:
            raise ovimException("Cannot get port info from database: {}".format(content), http_code=-result)
        elif result == 0:
            raise ovimException("Port '{}' not found".format(port_id), http_code=HTTP_Not_Found)
        port = content[0]
        nets = []
        host_id = None
        result = 1
        if 'net_id' in port_data:
            # change of net.
            old_net = port.get('net_id', None)
            new_net = port_data['net_id']
            if old_net != new_net:

                if new_net:
                    nets.append(new_net)  # put first the new net, so that new openflow rules are created before removing the old ones
                if old_net:
                    nets.append(old_net)
                if port['type'] == 'instance:bridge' or port['type'] == 'instance:ovs':
                    raise ovimException("bridge interfaces cannot be attached to a different net", http_code=HTTP_Forbidden)
                elif port['type'] == 'external' and not admin:
                    raise ovimException("Needed admin privileges",http_code=HTTP_Unauthorized)
                if new_net:
                    # check that new net has the correct type
                    result, new_net_dict = self.db.check_target_net(new_net, None, port['type'])
                    if result < 0:
                        raise ovimException("Error {}".format(new_net_dict), http_code=HTTP_Conflict)
                # change VLAN for SR-IOV ports
                if result >= 0 and port["type"] == "instance:data" and port["model"] == "VF":  # TODO consider also VFnotShared
                    if new_net:
                        port_data["vlan"] = None
                    else:
                        port_data["vlan"] = new_net_dict["vlan"]
                    # get host where this VM is allocated
                    result, content = self.db.get_table(FROM="instances", WHERE={"uuid": port["instance_id"]})
                    if result > 0:
                        host_id = content[0]["host_id"]

        # insert in data base
        if result >= 0:
            result, content = self.db.update_rows('ports', port_data, WHERE={'uuid': port_id}, log=False)
            port.update(port_data)

        # Insert task to complete actions
        if result > 0:
            for net_id in nets:
                try:
                    self.net_update_ofc_thread(net_id, port["ofc_id"], switch_dpid=port["switch_dpid"])
                except ovimException as e:
                    raise ovimException("Error updating network'{}' {}".format(net_id, str(e)),
                                        HTTP_Internal_Server_Error)
                except Exception as e:
                    raise ovimException("Error updating network '{}' {}".format(net_id, str(e)),
                                        HTTP_Internal_Server_Error)

            if host_id:
                r, v = self.config['host_threads'][host_id].insert_task("edit-iface", port_id, old_net, new_net)
                if r < 0:
                    self.logger.error("Error updating network '{}' {}".format(r,v))
                    # TODO Do something if fails
        if result >= 0:
            return port_id
        else:
            raise ovimException("Error {}".format(content), http_code=-result)

    def new_of_controller(self, ofc_data):
        """
        Create a new openflow controller into DB
        :param ofc_data: Dict openflow controller data
        :return: openflow controller dpid
        """

        result, ofc_uuid = self.db.new_row('ofcs', ofc_data, True, True)
        if result < 0:
            raise ovimException("New ofc Error %s" % ofc_uuid, HTTP_Internal_Server_Error)

        ofc_data['uuid'] = ofc_uuid
        of_conn = self._load_of_module(ofc_data)
        self._create_ofc_task(ofc_uuid, ofc_data['dpid'], of_conn)

        return ofc_uuid

    def edit_of_controller(self, of_id, ofc_data):
        """
        Edit an openflow controller entry from DB
        :return:
        """
        if not ofc_data:
            raise ovimException("No data received during uptade OF contorller", http_code=HTTP_Internal_Server_Error)

        old_of_controller = self.show_of_controller(of_id)

        if old_of_controller:
            result, content = self.db.update_rows('ofcs', ofc_data, WHERE={'uuid': of_id}, log=False)
            if result >= 0:
                return ofc_data
            else:
                raise ovimException("Error uptating OF contorller with uuid {}".format(of_id),
                                    http_code=-result)
        else:
            raise ovimException("Error uptating OF contorller with uuid {}".format(of_id),
                                http_code=HTTP_Internal_Server_Error)

    def delete_of_controller(self, of_id):
        """
        Delete an openflow controller from DB.
        :param of_id: openflow controller dpid
        :return:
        """

        ofc = self.show_of_controller(of_id)

        result, content = self.db.delete_row("ofcs", of_id)
        if result < 0:
            raise ovimException("Cannot delete ofc from database: {}".format(content), http_code=-result)
        elif result == 0:
            raise ovimException("ofc {} not found ".format(content), http_code=HTTP_Not_Found)

        ofc_thread = self.config['ofcs_thread'][of_id]
        del self.config['ofcs_thread'][of_id]
        for ofc_th in self.config['ofcs_thread_dpid']:
            if ofc['dpid'] in ofc_th:
                self.config['ofcs_thread_dpid'].remove(ofc_th)

        ofc_thread.insert_task("exit")
        #ofc_thread.join()

        return content

    def show_of_controller(self, uuid):
        """
        Show an openflow controller by dpid from DB.
        :param db_filter: List with where query parameters
        :return:
        """

        result, content = self.db.get_table(FROM='ofcs', WHERE={"uuid": uuid}, LIMIT=100)

        if result == 0:
            raise ovimException("Openflow controller with uuid '{}' not found".format(uuid),
                                http_code=HTTP_Not_Found)
        elif result < 0:
            raise ovimException("Openflow controller with uuid '{}' error".format(uuid),
                                http_code=HTTP_Internal_Server_Error)
        return content[0]

    def get_of_controllers(self, columns=None, db_filter={}, limit=None):
        """
        Show an openflow controllers from DB.
        :param columns:  List with SELECT query parameters
        :param db_filter: List with where query parameters
        :param limit: result Limit
        :return:
        """
        result, content = self.db.get_table(SELECT=columns, FROM='ofcs', WHERE=db_filter, LIMIT=limit)

        if result < 0:
            raise ovimException(str(content), -result)

        return content

    def get_tenants(self, columns=None, db_filter={}, limit=None):
        """
        Retrieve tenant list from DB
        :param columns:  List with SELECT query parameters
        :param db_filter: List with where query parameters
        :param limit: result limit
        :return:
        """
        result, content = self.db.get_table(FROM='tenants', SELECT=columns, WHERE=db_filter, LIMIT=limit)
        if result < 0:
            raise ovimException('get_tenatns Error {}'.format(str(content)), -result)
        else:
            convert_boolean(content, ('enabled',))
            return content

    def show_tenant_id(self, tenant_id):
        """
        Get tenant from DB by id
        :param tenant_id: tenant id
        :return:
        """
        result, content = self.db.get_table(FROM='tenants', SELECT=('uuid', 'name', 'description', 'enabled'),
                                            WHERE={"uuid": tenant_id})
        if result < 0:
            raise ovimException(str(content), -result)
        elif result == 0:
            raise ovimException("tenant with uuid='{}' not found".format(tenant_id), HTTP_Not_Found)
        else:
            convert_boolean(content, ('enabled',))
            return content[0]

    def new_tentant(self, tenant):
        """
        Create a tenant and store in DB
        :param tenant: Dictionary with tenant data
        :return: the uuid of created tenant. Raise exception upon error
        """

        # insert in data base
        result, tenant_uuid = self.db.new_tenant(tenant)

        if result >= 0:
            return tenant_uuid
        else:
            raise ovimException(str(tenant_uuid), -result)

    def delete_tentant(self, tenant_id):
        """
        Delete a tenant from the database.
        :param tenant_id: Tenant id
        :return: delete tenant id
        """

        # check permissions
        r, tenants_flavors = self.db.get_table(FROM='tenants_flavors', SELECT=('flavor_id', 'tenant_id'),
                                               WHERE={'tenant_id': tenant_id})
        if r <= 0:
            tenants_flavors = ()
        r, tenants_images = self.db.get_table(FROM='tenants_images', SELECT=('image_id', 'tenant_id'),
                                              WHERE={'tenant_id': tenant_id})
        if r <= 0:
            tenants_images = ()

        result, content = self.db.delete_row('tenants', tenant_id)
        if result == 0:
            raise ovimException("tenant '%s' not found" % tenant_id, HTTP_Not_Found)
        elif result > 0:
            for flavor in tenants_flavors:
                self.db.delete_row_by_key("flavors", "uuid", flavor['flavor_id'])
            for image in tenants_images:
                self.db.delete_row_by_key("images", "uuid", image['image_id'])
            return content
        else:
            raise ovimException("Error deleting tenant '%s' " % tenant_id, HTTP_Internal_Server_Error)

    def edit_tenant(self, tenant_id, tenant_data):
        """
        Update a tenant data identified by tenant id
        :param tenant_id: tenant id
        :param tenant_data: Dictionary with tenant data
        :return:
        """

        # Look for the previous data
        result, tenant_data_old = self.db.get_table(FROM='tenants', WHERE={'uuid': tenant_id})
        if result < 0:
            raise ovimException("Error updating tenant with uuid='{}': {}".format(tenant_id, tenant_data_old),
                                HTTP_Internal_Server_Error)
        elif result == 0:
            raise ovimException("tenant with uuid='{}' not found".format(tenant_id), HTTP_Not_Found)

        # insert in data base
        result, content = self.db.update_rows('tenants', tenant_data, WHERE={'uuid': tenant_id}, log=True)
        if result >= 0:
            return content
        else:
            raise ovimException(str(content), -result)

    def set_of_port_mapping(self, of_maps, ofc_id=None, switch_dpid=None, region=None):
        """
        Create new port mapping entry
        :param of_maps: List with port mapping information
        # maps =[{"ofc_id": <ofc_id>,"region": datacenter region,"compute_node": compute uuid,"pci": pci adress,
                "switch_dpid": swith dpid,"switch_port": port name,"switch_mac": mac}]
        :param ofc_id: ofc id
        :param switch_dpid: switch  dpid
        :param region: datacenter region id
        :return:
        """

        for map in of_maps:
            if ofc_id:
                map['ofc_id'] = ofc_id
            if switch_dpid:
                map['switch_dpid'] = switch_dpid
            if region:
                map['region'] = region
            if map.get("pci"):
                map["pci"] = map["pci"].lower()

        for of_map in of_maps:
            result, uuid = self.db.new_row('of_port_mappings', of_map, True)
            if result > 0:
                of_map["uuid"] = uuid
            else:
                raise ovimException(str(uuid), -result)
        return of_maps

    def clear_of_port_mapping(self, db_filter={}):
        """
        Clear port mapping filtering using db_filter dict
        :param db_filter: Parameter to filter during remove process
        :return:
        """
        result, content = self.db.delete_row_by_dict(FROM='of_port_mappings', WHERE=db_filter)
        # delete_row_by_key
        if result >= 0:
            return content
        else:
            raise ovimException("Error deleting of_port_mappings with filter='{}'".format(str(db_filter)),
                                HTTP_Internal_Server_Error)

    def get_of_port_mappings(self, column=None, db_filter=None, db_limit=None):
        """
        Retrive port mapping from DB
        :param column:
        :param db_filter:
        :return:
        """
        result, content = self.db.get_table(SELECT=column, WHERE=db_filter, FROM='of_port_mappings', LIMIT=db_limit)

        if result < 0:
            self.logger.error("get_of_port_mappings Error %d %s", result, content)
            raise ovimException(str(content), -result)
        else:
            return content

    def get_dhcp_controller(self):
        """
        Create an host_thread object for manage openvim controller and not create a thread for itself
        :return: dhcp_host openvim controller object
        """

        if 'openvim_controller' in self.config['host_threads']:
            return self.config['host_threads']['openvim_controller']

        bridge_ifaces = []
        controller_ip = self.config['ovs_controller_ip']
        ovs_controller_user = self.config.get('ovs_controller_user')

        host_test_mode = True if self.config['mode'] == 'test' or self.config['mode'] == "OF only" else False
        host_develop_mode = True if self.config['mode'] == 'development' else False

        dhcp_host = ht.host_thread(name='openvim_controller', user=ovs_controller_user, host=controller_ip,
                                   password=self.config.get('ovs_controller_password'),
                                   keyfile=self.config.get('ovs_controller_keyfile'),
                                   db=self.config["db"], db_lock=self.config["db_lock"], test=host_test_mode,
                                   image_path=self.config['host_image_path'], version=self.config['version'],
                                   host_id='openvim_controller', develop_mode=host_develop_mode,
                                   develop_bridge_iface=bridge_ifaces,
                                   logger_name=self.logger_name + ".host.controller",
                                   debug=self.config.get('log_level_host'))
        # dhcp_host.start()
        self.config['host_threads']['openvim_controller'] = dhcp_host
        try:
            dhcp_host.check_connectivity()
        except Exception as e:
           pass

        return dhcp_host

    def launch_dhcp_server(self, vlan, first_ip, last_ip, cidr, gateway, dns, routes):
        """
        Launch a dhcpserver base on dnsmasq attached to the net base on vlan id across the the openvim computes
        :param vlan: vlan identifier
        :param first_ip: First dhcp range ip
        :param last_ip: Last dhcp range ip
        :param cidr: net cidr
        :param gateway: net gateway
        :return:
        """
        ip_tools = IPNetwork(cidr)
        dhcp_netmask = str(ip_tools.netmask)
        ip_range = [first_ip, last_ip]

        dhcp_path = self.config['ovs_controller_file_path']

        controller_host = self.get_dhcp_controller()

        # controller_host.create_linux_bridge(vlan)
        controller_host.create_dhcp_interfaces(vlan, first_ip, dhcp_netmask)
        dhcp_path = self.config['ovs_controller_file_path']
        controller_host.launch_dhcp_server(vlan, ip_range, dhcp_netmask, dhcp_path, gateway, dns, routes)

    def launch_link_bridge_to_ovs(self, vlan, gateway, dhcp_cidr, links=None, routes=None):
        """
        Launch creating of connections (veth) between user bridge (link) and OVS
        :param vlan: 
        :param gateway: 
        :param links: 
        :return: 
        """

        if links:
            controller_host = self.get_dhcp_controller()
            for link in links:
                if 'iface' in link and 'nat' not in link:
                        controller_host.create_link_bridge_to_ovs(vlan, link['iface'])
                elif 'nat' in link:
                    controller_host.create_qrouter_ovs_connection(vlan, gateway, dhcp_cidr)
                    controller_host.create_qrouter_br_connection(vlan, dhcp_cidr, link)

            if len(routes):
                controller_host.add_ns_routes(vlan, routes)

    def delete_link_bridge_to_ovs(self, vlan,  links=None):
        """
        Delete connections (veth) between user bridge (link) and OVS
        :param vlan: 
        :param links: 
        :return: 
        """
        if links:
            controller_host = self.get_dhcp_controller()

            for link in links:
                if 'iface' in link and 'nat' not in link:
                    controller_host.remove_link_bridge_to_ovs(vlan, link['iface'])
                elif 'nat' in link:
                    controller_host.delete_qrouter_connection(vlan,  link['iface'])


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-v","--version", help="show ovim library version", action="store_true")
    parser.add_argument("--database-version", help="show required database version", action="store_true")
    args = parser.parse_args()
    if args.version:
        print ('openvimd version {} {}'.format(ovim.get_version(), ovim.get_version_date()))
        print ('(c) Copyright Telefonica')
    elif args.database_version:
        print ('required database version: {}'.format(ovim.get_database_version()))

