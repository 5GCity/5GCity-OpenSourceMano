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

""""
This is thread that interact with the host and the libvirt to manage VM
One thread will be launched per host 
"""

import threading
import time
import Queue
import logging
import vimconn
from db_base import db_base_Exception
from lib_osm_openvim.ovim import ovimException

__author__ = "Alfonso Tierno, Pablo Montes"
__date__ = "$10-feb-2017 12:07:15$"

# from logging import Logger
# import auxiliary_functions as af


def is_task_id(task_id):
    return True if task_id[:5] == "TASK." else False


class vim_thread(threading.Thread):

    def __init__(self, vimconn, task_lock, name=None, datacenter_name=None, datacenter_tenant_id=None,
                 db=None, db_lock=None, ovim=None):
        """Init a thread.
        Arguments:
            'id' number of thead
            'name' name of thread
            'host','user':  host ip or name to manage and user
            'db', 'db_lock': database class and lock to use it in exclusion
        """
        self.tasksResult = {}
        """ It will contain a dictionary with
            task_id:
                status: enqueued,done,error,deleted,processing
                result: VIM result,
        """
        threading.Thread.__init__(self)
        self.vim = vimconn
        self.datacenter_name = datacenter_name
        self.datacenter_tenant_id = datacenter_tenant_id
        self.ovim = ovim
        if not name:
            self.name = vimconn["id"] + "." + vimconn["config"]["datacenter_tenant_id"]
        else:
            self.name = name

        self.logger = logging.getLogger('openmano.vim.'+self.name)
        self.db = db
        self.db_lock = db_lock

        self.task_lock = task_lock
        self.task_queue = Queue.Queue(2000)
        self.refresh_list = []
        """Contains time ordered task list for refreshing the status of VIM VMs and nets"""

    def _refres_elements(self):
        """Call VIM to get VMs and networks status until 10 elements"""
        now = time.time()
        vm_to_refresh_list = []
        net_to_refresh_list = []
        vm_to_refresh_dict = {}
        net_to_refresh_dict = {}
        items_to_refresh = 0
        while self.refresh_list:
            task = self.refresh_list[0]
            with self.task_lock:
                if task['status'] == 'deleted':
                    self.refresh_list.pop(0)
                    continue
                if task['time'] > now:
                    break
                task["status"] = "processing"
            self.refresh_list.pop(0)
            if task["name"] == 'get-vm':
                vm_to_refresh_list.append(task["vim_id"])
                vm_to_refresh_dict[task["vim_id"]] = task
            elif task["name"] == 'get-net':
                net_to_refresh_list.append(task["vim_id"])
                net_to_refresh_dict[task["vim_id"]] = task
            else:
                error_text = "unknown task {}".format(task["name"])
                self.logger.error(error_text)
            items_to_refresh += 1
            if items_to_refresh == 10:
                break

        if vm_to_refresh_list:
            try:
                vim_dict = self.vim.refresh_vms_status(vm_to_refresh_list)
                for vim_id, vim_info in vim_dict.items():
                    #look for task
                    task = vm_to_refresh_dict[vim_id]
                    self.logger.debug("get-vm vm_id=%s result=%s", task["vim_id"], str(vim_info))

                    # update database
                    if vim_info.get("error_msg"):
                        vim_info["error_msg"] = self._format_vim_error_msg(vim_info["error_msg"])
                    if task["vim_info"].get("status") != vim_info["status"] or \
                        task["vim_info"].get("error_msg") != vim_info.get("error_msg") or \
                        task["vim_info"].get("vim_info") != vim_info["vim_info"]:
                        with self.db_lock:
                            temp_dict = {"status": vim_info["status"],
                                         "error_msg": vim_info.get("error_msg"),
                                         "vim_info": vim_info["vim_info"]}
                            self.db.update_rows('instance_vms', UPDATE=temp_dict, WHERE={"vim_vm_id": vim_id})
                    for interface in vim_info["interfaces"]:
                        for task_interface in task["vim_info"]["interfaces"]:
                            if task_interface["vim_net_id"] == interface["vim_net_id"]:
                                break
                        else:
                            task_interface = {"vim_net_id": interface["vim_net_id"]}
                            task["vim_info"]["interfaces"].append(task_interface)
                        if task_interface != interface:
                            #delete old port
                            if task_interface.get("sdn_port_id"):
                                try:
                                    self.ovim.delete_port(task_interface["sdn_port_id"])
                                    task_interface["sdn_port_id"] = None
                                except ovimException as e:
                                    self.logger.error("ovimException deleting external_port={} ".format(
                                        task_interface["sdn_port_id"]) + str(e), exc_info=True)
                                    # TODO Set error_msg at instance_nets
                            vim_net_id = interface["vim_net_id"]
                            sdn_net_id = None
                            sdn_port_name = None
                            with self.db_lock:
                                where_= {'iv.vim_vm_id': vim_id, "ine.vim_net_id": vim_net_id,
                                            'ine.datacenter_tenant_id': self.datacenter_tenant_id}
                                # TODO check why vim_interface_id is not present at database
                                # if interface.get("vim_interface_id"):
                                #     where_["vim_interface_id"] = interface["vim_interface_id"]
                                db_ifaces = self.db.get_rows(
                                    FROM="instance_interfaces as ii left join instance_nets as ine on "
                                         "ii.instance_net_id=ine.uuid left join instance_vms as iv on "
                                         "ii.instance_vm_id=iv.uuid",
                                    SELECT=("ii.uuid as iface_id", "ine.uuid as net_id", "iv.uuid as vm_id", "sdn_net_id", "vim_net_id"),
                                    WHERE=where_)
                            if len(db_ifaces)>1:
                                self.logger.critical("Refresing interfaces. "
                                                  "Found more than one interface at database for '{}'".format(where_))
                            elif len(db_ifaces)==0:
                                self.logger.critical("Refresing interfaces. "
                                                  "Not found any interface at database for '{}'".format(where_))
                                continue
                            else:
                                db_iface = db_ifaces[0]
                                #If there is no sdn_net_id, check if it is because an already created vim network is being used
                                #in that case, the sdn_net_id will be in that entry of the instance_nets table
                                if not db_iface.get("sdn_net_id"):
                                    result = self.db.get_rows(SELECT=('sdn_net_id',), FROM='instance_nets',
                                                                  WHERE={'vim_net_id': db_iface.get("vim_net_id"), 'instance_scenario_id': None, "datacenter_tenant_id":  self.datacenter_tenant_id})
                                    if len(result) == 1:
                                        db_iface["sdn_net_id"] = result[0]['sdn_net_id']

                                if db_iface.get("sdn_net_id") and interface.get("compute_node") and interface.get("pci"):
                                    sdn_net_id = db_iface["sdn_net_id"]
                                    sdn_port_name = sdn_net_id + "." + db_iface["vm_id"]
                                    sdn_port_name = sdn_port_name[:63]
                                    try:
                                        sdn_port_id = self.ovim.new_external_port(
                                            {"compute_node": interface["compute_node"],
                                             "pci": interface["pci"],
                                             "vlan": interface.get("vlan"),
                                             "net_id": sdn_net_id,
                                             "region": self.vim["config"]["datacenter_id"],
                                             "name": sdn_port_name,
                                             "mac": interface.get("mac_address")})
                                        interface["sdn_port_id"] = sdn_port_id
                                    except (ovimException, Exception) as e:
                                        self.logger.error(
                                            "ovimException creating new_external_port compute_node={} " \
                                            "pci={} vlan={} ".format(
                                                interface["compute_node"],
                                                interface["pci"],
                                                interface.get("vlan")) + str(e),
                                            exc_info=True)
                                        # TODO Set error_msg at instance_nets
                                with self.db_lock:
                                    vim_net_id = interface.pop("vim_net_id")
                                    self.db.update_rows('instance_interfaces', UPDATE=interface,
                                                    WHERE={'uuid': db_iface["iface_id"]})
                                    interface["vim_net_id"] = vim_net_id
                                # TODO insert instance_id

                    task["vim_info"] = vim_info
                    if task["vim_info"]["status"] == "BUILD":
                        self._insert_refresh(task, now+5)  # 5seconds
                    else:
                        self._insert_refresh(task, now+300) # 5minutes
            except vimconn.vimconnException as e:
                self.logger.error("vimconnException Exception when trying to refresh vms " + str(e))
                self._insert_refresh(task, now + 300)  # 5minutes

        if net_to_refresh_list:
            try:
                vim_dict = self.vim.refresh_nets_status(net_to_refresh_list)
                for vim_id, vim_info in vim_dict.items():
                    #look for task
                    task = net_to_refresh_dict[vim_id]
                    self.logger.debug("get-net net_id=%s result=%s", task["vim_id"], str(vim_info))

                    #get database info
                    where_ = {"vim_net_id": vim_id, 'datacenter_tenant_id': self.datacenter_tenant_id}
                    with self.db_lock:
                        db_nets = self.db.get_rows(
                            FROM="instance_nets",
                            SELECT=("uuid as net_id", "sdn_net_id"),
                            WHERE=where_)
                    if len(db_nets) > 1:
                        self.logger.critical("Refresing networks. "
                                          "Found more than one instance-networks at database for '{}'".format(where_))
                    elif len(db_nets) == 0:
                        self.logger.critical("Refresing networks. "
                                          "Not found any instance-network at database for '{}'".format(where_))
                        continue
                    else:
                        db_net = db_nets[0]
                        if db_net.get("sdn_net_id"):
                            # get ovim status
                            try:
                                sdn_net = self.ovim.show_network(db_net["sdn_net_id"])
                                if sdn_net["status"] == "ERROR":
                                    if not vim_info.get("error_msg"):
                                        vim_info["error_msg"] = sdn_net["error_msg"]
                                    else:
                                        vim_info["error_msg"] = "VIM_ERROR: {} && SDN_ERROR: {}".format(
                                            self._format_vim_error_msg(vim_info["error_msg"], 1024//2-14),
                                            self._format_vim_error_msg(sdn_net["error_msg"], 1024//2-14))
                                    if vim_info["status"] == "VIM_ERROR":
                                        vim_info["status"] = "VIM_SDN_ERROR"
                                    else:
                                        vim_info["status"] = "SDN_ERROR"

                            except (ovimException, Exception) as e:
                                self.logger.error(
                                    "ovimException getting network infor snd_net_id={}".format(db_net["sdn_net_id"]),
                                    exc_info=True)
                                # TODO Set error_msg at instance_nets

                    # update database
                    if vim_info.get("error_msg"):
                        vim_info["error_msg"] = self._format_vim_error_msg(vim_info["error_msg"])
                    if task["vim_info"].get("status") != vim_info["status"] or \
                                    task["vim_info"].get("error_msg") != vim_info.get("error_msg") or \
                                    task["vim_info"].get("vim_info") != vim_info["vim_info"]:
                        with self.db_lock:
                            temp_dict = {"status": vim_info["status"],
                                         "error_msg": vim_info.get("error_msg"),
                                         "vim_info": vim_info["vim_info"]}
                            self.db.update_rows('instance_nets', UPDATE=temp_dict, WHERE={"vim_net_id": vim_id})

                    task["vim_info"] = vim_info
                    if task["vim_info"]["status"] == "BUILD":
                        self._insert_refresh(task, now+5)    # 5seconds
                    else:
                        self._insert_refresh(task, now+300)  # 5minutes
            except vimconn.vimconnException as e:
                self.logger.error("vimconnException Exception when trying to refresh nets " + str(e))
                self._insert_refresh(task, now + 300)  # 5minutes

        if not items_to_refresh:
            time.sleep(1)

    def _insert_refresh(self, task, threshold_time):
        """Insert a task at list of refreshing elements. The refreshing list is ordered by threshold_time (task['time']
        It is assumed that this is called inside this thread
        """
        task["time"] = threshold_time
        for index in range(0, len(self.refresh_list)):
            if self.refresh_list[index]["time"] > threshold_time:
                self.refresh_list.insert(index, task)
                break
        else:
            index = len(self.refresh_list)
            self.refresh_list.append(task)
        self.logger.debug("new refresh task={} name={}, time={} index={}".format(
            task["id"], task["name"], task["time"], index))

    def _remove_refresh(self, task_name, vim_id):
        """Remove a task with this name and vim_id from the list of refreshing elements.
        It is assumed that this is called inside this thread outside _refres_elements method
        Return True if self.refresh_list is modified, task is found
        Return False if not found
        """
        index_to_delete = None
        for index in range(0, len(self.refresh_list)):
            if self.refresh_list[index]["name"] == task_name and self.refresh_list[index]["vim_id"] == vim_id:
                index_to_delete = index
                break
        else:
            return False
        if index_to_delete != None:
            del self.refresh_list[index_to_delete]
        return True

    def insert_task(self, task):
        try:
            self.task_queue.put(task, False)
            return task["id"]
        except Queue.Full:
            raise vimconn.vimconnException(self.name + ": timeout inserting a task")

    def del_task(self, task):
        with self.task_lock:
            if task["status"] == "enqueued":
                task["status"] == "deleted"
                return True
            else:   # task["status"] == "processing"
                self.task_lock.release()
                return False

    def run(self):
        self.logger.debug("Starting")
        while True:
            #TODO reload service
            while True:
                try:
                    if not self.task_queue.empty():
                        task = self.task_queue.get()
                        self.task_lock.acquire()
                        if task["status"] == "deleted":
                            self.task_lock.release()
                            continue
                        task["status"] = "processing"
                        self.task_lock.release()
                    else:
                        self._refres_elements()
                        continue
                    self.logger.debug("processing task id={} name={} params={}".format(task["id"], task["name"],
                                                                                       str(task["params"])))
                    if task["name"] == 'exit' or task["name"] == 'reload':
                        result, content = self.terminate(task)
                    elif task["name"] == 'new-vm':
                        result, content = self.new_vm(task)
                    elif task["name"] == 'del-vm':
                        result, content = self.del_vm(task)
                    elif task["name"] == 'new-net':
                        result, content = self.new_net(task)
                    elif task["name"] == 'del-net':
                        result, content = self.del_net(task)
                    else:
                        error_text = "unknown task {}".format(task["name"])
                        self.logger.error(error_text)
                        result = False
                        content = error_text
                    self.logger.debug("task id={} name={} result={}:{} params={}".format(task["id"], task["name"],
                                                                                        result, content,
                                                                                        str(task["params"])))

                    with self.task_lock:
                        task["status"] = "done" if result else "error"
                        task["result"] = content
                    self.task_queue.task_done()

                    if task["name"] == 'exit':
                        return 0
                    elif task["name"] == 'reload':
                        break
                except Exception as e:
                    self.logger.critical("Unexpected exception at run: " + str(e), exc_info=True)

        self.logger.debug("Finishing")

    def terminate(self, task):
        return True, None

    def _format_vim_error_msg(self, error_text, max_length=1024):
        if error_text and len(error_text) >= max_length:
            return error_text[:max_length//2-3] + " ... " + error_text[-max_length//2+3:]
        return error_text

    def new_net(self, task):
        try:
            task_id = task["id"]
            params = task["params"]
            net_id = self.vim.new_network(*params)

            net_name = params[0]
            net_type = params[1]

            network = None
            sdn_net_id = None
            sdn_controller = self.vim.config.get('sdn-controller')
            if sdn_controller and (net_type == "data" or net_type == "ptp"):
                network = {"name": net_name, "type": net_type}

                vim_net = self.vim.get_network(net_id)
                if vim_net.get('encapsulation') != 'vlan':
                    raise vimconn.vimconnException(
                        "net '{}' defined as type '{}' has not vlan encapsulation '{}'".format(
                            net_name, net_type, vim_net['encapsulation']))
                network["vlan"] = vim_net.get('segmentation_id')
                try:
                    sdn_net_id = self.ovim.new_network(network)
                except (ovimException, Exception) as e:
                    self.logger.error("task=%s cannot create SDN network vim_net_id=%s input='%s' ovimException='%s'",
                                      str(task_id), net_id, str(network), str(e))
            with self.db_lock:
                self.db.update_rows("instance_nets", UPDATE={"vim_net_id": net_id, "sdn_net_id": sdn_net_id},
                                    WHERE={"vim_net_id": task_id})
            new_refresh_task = {"status": "enqueued",
                                "id": task_id,
                                "name": "get-net",
                                "vim_id": net_id,
                                "vim_info": {} }
            self._insert_refresh(new_refresh_task, time.time())
            return True, net_id
        except db_base_Exception as e:
            self.logger.error("Error updating database %s", str(e))
            return True, net_id
        except vimconn.vimconnException as e:
            self.logger.error("Error creating NET, task=%s: %s", str(task_id), str(e))
            try:
                with self.db_lock:
                    self.db.update_rows("instance_nets",
                                        UPDATE={"error_msg": self._format_vim_error_msg(str(e)), "status": "VIM_ERROR"},
                                        WHERE={"vim_net_id": task_id})
            except db_base_Exception as e:
                self.logger.error("Error updating database %s", str(e))
            return False, str(e)
        #except ovimException as e:
        #    self.logger.error("Error creating NET in ovim, task=%s: %s", str(task_id), str(e))
        #    return False, str(e)

    def new_vm(self, task):
        try:
            params = task["params"]
            task_id = task["id"]
            depends = task.get("depends")
            net_list = params[5]
            error_text = ""
            for net in net_list:
                if "net_id" in net and is_task_id(net["net_id"]):  # change task_id into network_id
                    try:
                        task_net = depends[net["net_id"]]
                        with self.task_lock:
                            if task_net["status"] == "error":
                                error_text = "Cannot create VM because depends on a network that cannot be created: " +\
                                       str(task_net["result"])
                                break
                            elif task_net["status"] == "enqueued" or task_net["status"] == "processing":
                                error_text = "Cannot create VM because depends on a network still not created"
                                break
                            network_id = task_net["result"]
                        net["net_id"] = network_id
                    except Exception as e:
                        error_text = "Error trying to map from task_id={} to task result: {}".format(
                            net["net_id"],str(e))
                        break
            if not error_text:
                vm_id = self.vim.new_vminstance(*params)
            try:
                with self.db_lock:
                    if error_text:
                        update = self.db.update_rows("instance_vms",
                                                     UPDATE={"status": "VIM_ERROR", "error_msg": error_text},
                                                     WHERE={"vim_vm_id": task_id})
                    else:
                        update = self.db.update_rows("instance_vms", UPDATE={"vim_vm_id": vm_id}, WHERE={"vim_vm_id": task_id})
                    if not update:
                        self.logger.error("task id={} name={} database not updated vim_vm_id={}".format(
                            task["id"], task["name"], vm_id))
            except db_base_Exception as e:
                self.logger.error("Error updating database %s", str(e))
            if error_text:
                return False, error_text
            new_refresh_task = {"status": "enqueued",
                                "id": task_id,
                                "name": "get-vm",
                                "vim_id": vm_id,
                                "vim_info": {"interfaces":[]} }
            self._insert_refresh(new_refresh_task, time.time())
            return True, vm_id
        except vimconn.vimconnException as e:
            self.logger.error("Error creating VM, task=%s: %s", str(task_id), str(e))
            try:
                with self.db_lock:
                    self.db.update_rows("instance_vms",
                                        UPDATE={"error_msg": self._format_vim_error_msg(str(e)), "status": "VIM_ERROR"},
                                        WHERE={"vim_vm_id": task_id})
            except db_base_Exception as edb:
                self.logger.error("Error updating database %s", str(edb))
            return False, str(e)

    def del_vm(self, task):
        vm_id = task["params"][0]
        interfaces = task["params"][1]
        if is_task_id(vm_id):
            try:
                task_create = task["depends"][vm_id]
                with self.task_lock:
                    if task_create["status"] == "error":
                        return True, "VM was not created. It has error: " + str(task_create["result"])
                    elif task_create["status"] == "enqueued" or task_create["status"] == "processing":
                        return False, "Cannot delete VM vim_id={} because still creating".format(vm_id)
                    vm_id = task_create["result"]
            except Exception as e:
                return False, "Error trying to get task_id='{}':".format(vm_id, str(e))
        try:
            self._remove_refresh("get-vm", vm_id)
            for iface in interfaces:
                if iface.get("sdn_port_id"):
                    try:
                        self.ovim.delete_port(iface["sdn_port_id"])
                    except ovimException as e:
                        self.logger.error("ovimException deleting external_port={} at VM vim_id={} deletion ".format(
                            iface["sdn_port_id"], vm_id) + str(e), exc_info=True)
                        # TODO Set error_msg at instance_nets

            return True, self.vim.delete_vminstance(vm_id)
        except vimconn.vimconnException as e:
            return False, str(e)

    def del_net(self, task):
        net_id = task["params"][0]
        sdn_net_id = task["params"][1]
        if is_task_id(net_id):
            try:
                task_create = task["depends"][net_id]
                with self.task_lock:
                    if task_create["status"] == "error":
                        return True, "net was not created. It has error: " + str(task_create["result"])
                    elif task_create["status"] == "enqueued" or task_create["status"] == "processing":
                        return False, "Cannot delete net because still creating"
                    net_id = task_create["result"]
            except Exception as e:
                return False, "Error trying to get task_id='{}':".format(net_id, str(e))
        try:
            self._remove_refresh("get-net", net_id)
            result = self.vim.delete_network(net_id)
            if sdn_net_id:
                #Delete any attached port to this sdn network
                #At this point, there will be ports associated to this network in case it was manually done using 'openmano vim-net-sdn-attach'
                try:
                    port_list = self.ovim.get_ports(columns={'uuid'}, filter={'name': 'external_port', 'net_id': sdn_net_id})
                except ovimException as e:
                    raise vimconn.vimconnException(
                        "ovimException obtaining external ports for net {}. ".format(sdn_net_id) + str(e))

                for port in port_list:
                    try:
                        self.ovim.delete_port(port['uuid'])
                    except ovimException as e:
                        raise vimconn.vimconnException(
                            "ovimException deleting port {} for net {}. ".format(port['uuid'], sdn_net_id) + str(e))
                with self.db_lock:
                    self.ovim.delete_network(sdn_net_id)
            return True, result
        except vimconn.vimconnException as e:
            return False, str(e)
        except ovimException as e:
            logging.error("Error deleting network from ovim. net_id: {}, sdn_net_id: {}".format(net_id, sdn_net_id))
            return False, str(e)


