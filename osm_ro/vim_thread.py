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
This is thread that interacts with a VIM. It processes TASKs sequentially against a single VIM.
The tasks are stored at database in table vim_actions
The task content is:
    MD  instance_action_id:  reference a global action over an instance-scenario: database instance_actions
    MD  task_index:     index number of the task. This with the previous are a key
    MD  datacenter_vim_id:  should contain the uuid of the VIM managed by this thread
    MD  vim_id:     id of the vm,net,etc at VIM
    MD  action:     CREATE, DELETE, LOOK, TODO: LOOK_CREATE
    MD  item:       database table name, can be instance_vms, instance_nets, TODO: datacenter_flavors, datacenter_images
    MD  item_id:    uuid of the referenced entry in the preious table
    MD  status:     SCHEDULED,BUILD,DONE,FAILED,SUPERSEDED
    MD  extra:      text with yaml format at database, dict at memory with:
            params:     list with the params to be sent to the VIM for CREATE or LOOK. For DELETE the vim_id is taken from other related tasks
            depends_on: list with the 'task_index'es of tasks that must be completed before. e.g. a vm depends on a net
            sdn_net_id: used for net.
            tries:
            interfaces: used for VMs. Each key is the uuid of the instance_interfaces entry at database
                iface_id: uuid of intance_interfaces
                sdn_port_id:
                sdn_net_id:
            created:    False if the VIM element is not created by other actions, and it should not be deleted
            vim_status: VIM status of the element. Stored also at database in the instance_XXX
    M   depends:    dict with task_index(from depends_on) to task class
    M   params:     same as extra[params] but with the resolved dependencies
    M   vim_interfaces: similar to extra[interfaces] but with VIM information. Stored at database in the instance_XXX but not at vim_actions
    M   vim_info:   Detailed information of a vm,net from the VIM. Stored at database in the instance_XXX but not at vim_actions
    MD  error_msg:  descriptive text upon an error.Stored also at database instance_XXX
    MD  created_at: task creation time
    MD  modified_at: last task update time. On refresh it contains when this task need to be refreshed

"""

import threading
import time
import Queue
import logging
import vimconn
import yaml
from db_base import db_base_Exception
from lib_osm_openvim.ovim import ovimException

__author__ = "Alfonso Tierno, Pablo Montes"
__date__ = "$28-Sep-2017 12:07:15$"

# from logging import Logger
# import auxiliary_functions as af


def is_task_id(task_id):
    return task_id.startswith("TASK-")


class VimThreadException(Exception):
    pass


class vim_thread(threading.Thread):
    REFRESH_BUILD = 5      # 5 seconds
    REFRESH_ACTIVE = 60    # 1 minute

    def __init__(self, vimconn, task_lock, name=None, datacenter_name=None, datacenter_tenant_id=None,
                 db=None, db_lock=None, ovim=None):
        """Init a thread.
        Arguments:
            'id' number of thead
            'name' name of thread
            'host','user':  host ip or name to manage and user
            'db', 'db_lock': database class and lock to use it in exclusion
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

        self.refresh_tasks = []
        """Contains time ordered task list for refreshing the status of VIM VMs and nets"""

        self.pending_tasks = []
        """Contains time ordered task list for creation, deletion of VIM VMs and nets"""

        self.grouped_tasks = {}
        """ It contains all the creation/deletion pending tasks grouped by its concrete vm, net, etc
            <item><item_id>:
                -   <task1>  # e.g. CREATE task
                    <task2>  # e.g. DELETE task
        """

    def _reload_vim_actions(self):
        """
        Read actions from database and reload them at memory. Fill self.refresh_list, pending_list, vim_actions
        :return: None
        """
        action_completed = False
        task_list = []
        old_action_key = None

        with self.db_lock:
            vim_actions = self.db.get_rows(FROM="vim_actions",
                                           WHERE={"datacenter_vim_id":  self.datacenter_tenant_id },
                                           ORDER_BY=("item", "item_id", "created_at",))
        for task in vim_actions:
            item = task["item"]
            item_id = task["item_id"]
            action_key = item + item_id
            if old_action_key != action_key:
                if not action_completed and task_list:
                    # This will fill needed task parameters into memory, and insert the task if needed in
                    # self.pending_tasks or self.refresh_tasks
                    self._insert_pending_tasks(task_list)
                task_list = []
                old_action_key = action_key
                action_completed = False
            elif action_completed:
                continue

            if task["status"] == "SCHEDULED" or task["action"] == "CREATE" or task["action"] == "FIND":
                task_list.append(task)
            elif task["action"] == "DELETE":
                # action completed because deleted and status is not SCHEDULED. Not needed anything
                action_completed = True

        # Last actions group need to be inserted too
        if not action_completed and task_list:
            self._insert_pending_tasks(task_list)

    def _refres_elements(self):
        """Call VIM to get VMs and networks status until 10 elements"""
        now = time.time()
        nb_processed = 0
        vm_to_refresh_list = []
        net_to_refresh_list = []
        vm_to_refresh_dict = {}
        net_to_refresh_dict = {}
        items_to_refresh = 0
        while self.refresh_tasks:
            task = self.refresh_tasks[0]
            with self.task_lock:
                if task['status'] == 'SUPERSEDED':
                    self.refresh_tasks.pop(0)
                    continue
                if task['modified_at'] > now:
                    break
                # task["status"] = "processing"
                nb_processed += 1
            self.refresh_tasks.pop(0)
            if task["item"] == 'instance_vms':
                vm_to_refresh_list.append(task["vim_id"])
                vm_to_refresh_dict[task["vim_id"]] = task
            elif task["item"] == 'instance_nets':
                net_to_refresh_list.append(task["vim_id"])
                net_to_refresh_dict[task["vim_id"]] = task
            else:
                error_text = "unknown task {}".format(task["item"])
                self.logger.error(error_text)
            items_to_refresh += 1
            if items_to_refresh == 10:
                break

        if vm_to_refresh_list:
            try:
                now = time.time()
                vim_dict = self.vim.refresh_vms_status(vm_to_refresh_list)
                for vim_id, vim_info in vim_dict.items():
                    # look for task
                    task_need_update = False
                    task = vm_to_refresh_dict[vim_id]
                    self.logger.debug("get-vm vm_id=%s result=%s", task["vim_id"], str(vim_info))

                    # update database
                    task_vim_info = task.get("vim_info")
                    task_error_msg = task.get("error_msg")
                    task_vim_status = task["extra"].get("vim_status")
                    if vim_info.get("error_msg"):
                        vim_info["error_msg"] = self._format_vim_error_msg(vim_info["error_msg"])
                    if task_vim_status != vim_info["status"] or task_error_msg != vim_info.get("error_msg") or \
                                    task_vim_info != vim_info.get("vim_info"):
                        with self.db_lock:
                            temp_dict = {"status": vim_info["status"],
                                         "error_msg": vim_info.get("error_msg"),
                                         "vim_info": vim_info.get("vim_info")}
                            self.db.update_rows('instance_vms', UPDATE=temp_dict, WHERE={"uuid": task["item_id"]})
                        task["extra"]["vim_status"] = vim_info["status"]
                        task["error_msg"] = vim_info.get("error_msg")
                        task["vim_info"] = vim_info.get("vim_info")
                        task_need_update = True
                    for interface in vim_info.get("interfaces", ()):
                        vim_interface_id = interface["vim_interface_id"]
                        if vim_interface_id not in task["extra"]["interfaces"]:
                            self.logger.critical("Interface not found {} on task info {}".format(
                                vim_interface_id, task["extra"]["interfaces"]), exc_info=True)
                            continue
                        task_interface = task["extra"]["interfaces"][vim_interface_id]
                        task_vim_interface = task["vim_interfaces"].get(vim_interface_id)
                        if task_vim_interface != interface:
                            # delete old port
                            if task_interface.get("sdn_port_id"):
                                try:
                                    with self.db_lock:
                                        self.ovim.delete_port(task_interface["sdn_port_id"])
                                        task_interface["sdn_port_id"] = None
                                        task_need_update = True
                                except ovimException as e:
                                    self.logger.error("ovimException deleting external_port={} ".format(
                                        task_interface["sdn_port_id"]) + str(e), exc_info=True)
                                    # TODO Set error_msg at instance_nets

                            # Create SDN port
                            sdn_net_id = task_interface.get("sdn_net_id")
                            if sdn_net_id and interface.get("compute_node") and interface.get("pci"):
                                sdn_port_name = sdn_net_id + "." + task["vim_id"]
                                sdn_port_name = sdn_port_name[:63]
                                try:
                                    with self.db_lock:
                                        sdn_port_id = self.ovim.new_external_port(
                                            {"compute_node": interface["compute_node"],
                                             "pci": interface["pci"],
                                             "vlan": interface.get("vlan"),
                                             "net_id": sdn_net_id,
                                             "region": self.vim["config"]["datacenter_id"],
                                             "name": sdn_port_name,
                                             "mac": interface.get("mac_address")})
                                        task_interface["sdn_port_id"] = sdn_port_id
                                        task_need_update = True
                                except (ovimException, Exception) as e:
                                    self.logger.error(
                                        "ovimException creating new_external_port compute_node={} "
                                        "pci={} vlan={} ".format(
                                            interface["compute_node"],
                                            interface["pci"],
                                            interface.get("vlan")) + str(e),
                                        exc_info=True)
                                    # TODO Set error_msg at instance_nets
                            with self.db_lock:
                                self.db.update_rows(
                                    'instance_interfaces',
                                    UPDATE={"mac_address": interface.get("mac_address"),
                                            "ip_address": interface.get("ip_address"),
                                            "vim_info": interface.get("vim_info"),
                                            "sdn_port_id": task_interface.get("sdn_port_id"),
                                            "compute_node": interface.get("compute_node"),
                                            "pci": interface.get("pci"),
                                            "vlan": interface.get("vlan"),
                                    },
                                    WHERE={'uuid': task_interface["iface_id"]})
                            task["vim_interfaces"][vim_interface_id] = interface
                    if task_need_update:
                        with self.db_lock:
                            self.db.update_rows(
                                'vim_actions',
                                UPDATE={"extra": yaml.safe_dump(task["extra"], default_flow_style=True, width=256),
                                        "error_msg": task.get("error_msg"), "modified_at": now},
                                WHERE={'instance_action_id': task['instance_action_id'],
                                       'task_index': task['task_index']})
                    if task["extra"].get("vim_status") == "BUILD":
                        self._insert_refresh(task, now + self.REFRESH_BUILD)
                    else:
                        self._insert_refresh(task, now + self.REFRESH_ACTIVE)
            except vimconn.vimconnException as e:
                self.logger.error("vimconnException Exception when trying to refresh vms " + str(e))
                self._insert_refresh(task, now + self.REFRESH_ACTIVE)

        if net_to_refresh_list:
            try:
                now = time.time()
                vim_dict = self.vim.refresh_nets_status(net_to_refresh_list)
                for vim_id, vim_info in vim_dict.items():
                    # look for task
                    task = net_to_refresh_dict[vim_id]
                    self.logger.debug("get-net net_id=%s result=%s", task["vim_id"], str(vim_info))

                    task_vim_info = task.get("vim_info")
                    task_vim_status = task["extra"].get("vim_status")
                    task_error_msg = task.get("error_msg")
                    task_sdn_net_id = task["extra"].get("sdn_net_id")

                    # get ovim status
                    if task_sdn_net_id:
                        try:
                            with self.db_lock:
                                sdn_net = self.ovim.show_network(task_sdn_net_id)
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
                                "ovimException getting network infor snd_net_id={}".format(task_sdn_net_id),
                                exc_info=True)
                            # TODO Set error_msg at instance_nets

                    # update database
                    if vim_info.get("error_msg"):
                        vim_info["error_msg"] = self._format_vim_error_msg(vim_info["error_msg"])
                    if task_vim_status != vim_info["status"] or task_error_msg != vim_info.get("error_msg") or \
                            task_vim_info != vim_info["vim_info"]:
                        task["extra"]["vim_status"] = vim_info["status"]
                        task["error_msg"] = vim_info.get("error_msg")
                        task["vim_info"] = vim_info["vim_info"]
                        temp_dict = {"status": vim_info["status"],
                                         "error_msg": vim_info.get("error_msg"),
                                         "vim_info": vim_info["vim_info"]}
                        with self.db_lock:
                            self.db.update_rows('instance_nets', UPDATE=temp_dict, WHERE={"uuid": task["item_id"]})
                            self.db.update_rows(
                                'vim_actions',
                                UPDATE={"extra": yaml.safe_dump(task["extra"], default_flow_style=True, width=256),
                                        "error_msg": task.get("error_msg"), "modified_at": now},
                                WHERE={'instance_action_id': task['instance_action_id'],
                                        'task_index': task['task_index']})
                    if task["extra"].get("vim_status") == "BUILD":
                        self._insert_refresh(task, now + self.REFRESH_BUILD)
                    else:
                        self._insert_refresh(task, now + self.REFRESH_ACTIVE)
            except vimconn.vimconnException as e:
                self.logger.error("vimconnException Exception when trying to refresh nets " + str(e))
                self._insert_refresh(task, now + self.REFRESH_ACTIVE)

        return nb_processed

    def _insert_refresh(self, task, threshold_time=None):
        """Insert a task at list of refreshing elements. The refreshing list is ordered by threshold_time (task['modified_at']
        It is assumed that this is called inside this thread
        """
        if not threshold_time:
            threshold_time = time.time()
        task["modified_at"] = threshold_time
        task_name = task["item"][9:] + "-" + task["action"]
        task_id = task["instance_action_id"] + "." + str(task["task_index"])
        for index in range(0, len(self.refresh_tasks)):
            if self.refresh_tasks[index]["modified_at"] > threshold_time:
                self.refresh_tasks.insert(index, task)
                break
        else:
            index = len(self.refresh_tasks)
            self.refresh_tasks.append(task)
        self.logger.debug("new refresh task={} name={}, modified_at={} index={}".format(
            task_id, task_name, task["modified_at"], index))

    def _remove_refresh(self, task_name, vim_id):
        """Remove a task with this name and vim_id from the list of refreshing elements.
        It is assumed that this is called inside this thread outside _refres_elements method
        Return True if self.refresh_list is modified, task is found
        Return False if not found
        """
        index_to_delete = None
        for index in range(0, len(self.refresh_tasks)):
            if self.refresh_tasks[index]["name"] == task_name and self.refresh_tasks[index]["vim_id"] == vim_id:
                index_to_delete = index
                break
        else:
            return False
        if index_to_delete != None:
            del self.refresh_tasks[index_to_delete]
        return True

    def _proccess_pending_tasks(self):
        nb_created = 0
        nb_processed = 0
        while self.pending_tasks:
            task = self.pending_tasks.pop(0)
            nb_processed += 1
            if task["status"] == "SUPERSEDED":
                # not needed to do anything but update database with the new status
                result = True
                database_update = None
            elif task["item"] == 'instance_vms':
                if task["action"] == "CREATE":
                    result, database_update = self.new_vm(task)
                    nb_created += 1
                elif task["action"] == "DELETE":
                    result, database_update = self.del_vm(task)
                else:
                    raise vimconn.vimconnException(self.name + "unknown task action {}".format(task["action"]))
            elif task["item"] == 'instance_nets':
                if task["action"] == "CREATE":
                    result, database_update = self.new_net(task)
                    nb_created += 1
                elif task["action"] == "DELETE":
                    result, database_update = self.del_net(task)
                elif task["action"] == "FIND":
                    result, database_update = self.get_net(task)
                else:
                    raise vimconn.vimconnException(self.name + "unknown task action {}".format(task["action"]))
            else:
                raise vimconn.vimconnException(self.name + "unknown task item {}".format(task["item"]))
                # TODO

            if task["status"] == "SCHEDULED":
                # This is because a depend task is not completed. Moved to the end. NOT USED YET
                if task["extra"].get("tries", 0) > 3:
                    task["status"] == "FAILED"
                else:
                    task["extra"]["tries"] = task["extra"].get("tries", 0) + 1
                    self.pending_tasks.append(task)
            elif task["action"] == "DELETE":
                action_key = task["item"] + task["item_id"]
                del self.grouped_tasks[action_key]
            elif task["action"] in ("CREATE", "FIND") and task["status"] in ("DONE", "BUILD"):
                self._insert_refresh(task)

            self.logger.debug("vim_action id={}.{} item={} action={} result={}:{} params={}".format(
                task["instance_action_id"], task["task_index"], task["item"], task["action"],
                task["status"], task["vim_id"] if task["status"] == "DONE" else task.get("error_msg"),
                task["params"]))
            try:
                now = time.time()
                with self.db_lock:
                    self.db.update_rows(
                        table="vim_actions",
                        UPDATE={"status": task["status"], "vim_id": task["vim_id"], "modified_at": now,
                                "error_msg": task["error_msg"],
                                "extra": yaml.safe_dump(task["extra"], default_flow_style=True, width=256)},
                        WHERE={"instance_action_id": task["instance_action_id"], "task_index": task["task_index"]})
                    if result is not None:
                        self.db.update_rows(
                            table="instance_actions",
                            UPDATE={("number_done" if result else "number_failed"): {"INCREMENT": 1},
                                    "modified_at": now},
                            WHERE={"uuid": task["instance_action_id"]})
                    if database_update:
                        self.db.update_rows(table=task["item"],
                                            UPDATE=database_update,
                                            WHERE={"uuid": task["item_id"]})
            except db_base_Exception as e:
                self.logger.error("Error updating database %s", str(e), exc_info=True)

            if nb_created == 10:
                break
        return nb_processed

    def _insert_pending_tasks(self, vim_actions_list):
        now = time.time()
        for task in vim_actions_list:
            if task["datacenter_vim_id"] != self.datacenter_tenant_id:
                continue
            item = task["item"]
            item_id = task["item_id"]
            action_key = item + item_id
            if action_key not in self.grouped_tasks:
                self.grouped_tasks[action_key] = []
            task["params"] = None
            task["depends"] = {}
            if task["extra"]:
                extra = yaml.load(task["extra"])
                task["extra"] = extra
                task["params"] = extra.get("params")
                depends_on_list = extra.get("depends_on")
                if depends_on_list:
                    for index in depends_on_list:
                        if index < len(vim_actions_list) and vim_actions_list[index]["task_index"] == index and\
                                    vim_actions_list[index]["instance_action_id"] == task["instance_action_id"]:
                            task["depends"]["TASK-" + str(index)] = vim_actions_list[index]
                if extra.get("interfaces"):
                    task["vim_interfaces"] = {}
            else:
                task["extra"] = {}
            if "error_msg" not in task:
                task["error_msg"] = None
            if "vim_id" not in task:
                task["vim_id"] = None

            if task["action"] == "DELETE":
                need_delete_action = False
                for to_supersede in self.grouped_tasks.get(action_key, ()):
                    if to_supersede["action"] == "FIND" and to_supersede.get("vim_id"):
                        task["vim_id"] = to_supersede["vim_id"]
                    if to_supersede["action"] == "CREATE" and to_supersede.get("vim_id"):
                        need_delete_action = True
                        task["vim_id"] = to_supersede["vim_id"]
                        if to_supersede["extra"].get("sdn_vim_id"):
                            task["extra"]["sdn_vim_id"] = to_supersede["extra"]["sdn_vim_id"]
                        if to_supersede["extra"].get("interfaces"):
                            task["extra"]["interfaces"] = to_supersede["extra"]["interfaces"]
                    # Mark task as SUPERSEDED.
                    #   If task is in self.pending_tasks, it will be removed and database will be update
                    #   If task is in self.refresh_tasks, it will be removed
                    to_supersede["status"] = "SUPERSEDED"
                if not need_delete_action:
                    task["status"] = "SUPERSEDED"

                self.grouped_tasks[action_key].append(task)
                self.pending_tasks.append(task)
            elif task["status"] == "SCHEDULED":
                self.grouped_tasks[action_key].append(task)
                self.pending_tasks.append(task)
            elif task["action"] in ("CREATE", "FIND"):
                self.grouped_tasks[action_key].append(task)
                if task["status"] in ("DONE", "BUILD"):
                    self._insert_refresh(task)
            # TODO add VM reset, get console, etc...
            else:
                raise vimconn.vimconnException(self.name + "unknown vim_action action {}".format(task["action"]))

    def insert_task(self, task):
        try:
            self.task_queue.put(task, False)
            return None
        except Queue.Full:
            raise vimconn.vimconnException(self.name + ": timeout inserting a task")

    def del_task(self, task):
        with self.task_lock:
            if task["status"] == "SCHEDULED":
                task["status"] == "SUPERSEDED"
                return True
            else:   # task["status"] == "processing"
                self.task_lock.release()
                return False

    def run(self):
        self.logger.debug("Starting")
        while True:
            self._reload_vim_actions()
            reload_thread = False
            while True:
                try:
                    while not self.task_queue.empty():
                        task = self.task_queue.get()
                        if isinstance(task, list):
                            self._insert_pending_tasks(task)
                        elif isinstance(task, str):
                            if task == 'exit':
                                return 0
                            elif task == 'reload':
                                reload_thread = True
                                break
                        self.task_queue.task_done()
                    if reload_thread:
                        break
                    nb_processed = self._proccess_pending_tasks()
                    nb_processed += self._refres_elements()
                    if not nb_processed:
                        time.sleep(1)

                except Exception as e:
                    self.logger.critical("Unexpected exception at run: " + str(e), exc_info=True)

        self.logger.debug("Finishing")

    def terminate(self, task):
        return True, None

    def _look_for_task(self, instance_action_id, task_id):
        task_index = task_id.split("-")[-1]
        with self.db_lock:
            tasks = self.db.get_rows(FROM="vim_actions", WHERE={"instance_action_id": instance_action_id,
                                                                 "task_index": task_index})
        if not tasks:
            return None
        task = tasks[0]
        task["params"] = None
        task["depends"] = {}
        if task["extra"]:
            extra = yaml.load(task["extra"])
            task["extra"] = extra
            task["params"] = extra.get("params")
            if extra.get("interfaces"):
                task["vim_interfaces"] = {}
        else:
            task["extra"] = {}
        return task

    def _format_vim_error_msg(self, error_text, max_length=1024):
        if error_text and len(error_text) >= max_length:
            return error_text[:max_length//2-3] + " ... " + error_text[-max_length//2+3:]
        return error_text

    def new_net(self, task):
        try:
            task_id = task["instance_action_id"] + "." + str(task["task_index"])
            params = task["params"]
            vim_net_id = self.vim.new_network(*params)

            net_name = params[0]
            net_type = params[1]

            network = None
            sdn_net_id = None
            sdn_controller = self.vim.config.get('sdn-controller')
            if sdn_controller and (net_type == "data" or net_type == "ptp"):
                network = {"name": net_name, "type": net_type, "region": self.vim["config"]["datacenter_id"]}

                vim_net = self.vim.get_network(vim_net_id)
                if vim_net.get('encapsulation') != 'vlan':
                    raise vimconn.vimconnException(
                        "net '{}' defined as type '{}' has not vlan encapsulation '{}'".format(
                            net_name, net_type, vim_net['encapsulation']))
                network["vlan"] = vim_net.get('segmentation_id')
                try:
                    with self.db_lock:
                        sdn_net_id = self.ovim.new_network(network)
                except (ovimException, Exception) as e:
                    self.logger.error("task=%s cannot create SDN network vim_net_id=%s input='%s' ovimException='%s'",
                                      str(task_id), vim_net_id, str(network), str(e))
            task["status"] = "DONE"
            task["extra"]["vim_info"] = {}
            task["extra"]["sdn_net_id"] = sdn_net_id
            task["error_msg"] = None
            task["vim_id"] = vim_net_id
            instance_element_update = {"vim_net_id": vim_net_id, "sdn_net_id": sdn_net_id, "status": "BUILD", "error_msg": None}
            return True, instance_element_update
        except vimconn.vimconnException as e:
            self.logger.error("Error creating NET, task=%s: %s", str(task_id), str(e))
            task["status"] = "FAILED"
            task["vim_id"] = None
            task["error_msg"] = self._format_vim_error_msg(str(e))
            instance_element_update = {"vim_net_id": None, "sdn_net_id": None, "status": "VIM_ERROR", "error_msg": task["error_msg"]}
            return False, instance_element_update

    def new_vm(self, task):
        try:
            params = task["params"]
            task_id = task["instance_action_id"] + "." + str(task["task_index"])
            depends = task.get("depends")
            net_list = params[5]
            error_text = ""
            for net in net_list:
                if "net_id" in net and is_task_id(net["net_id"]):  # change task_id into network_id
                    if net["net_id"] in depends:
                        task_net = depends[net["net_id"]]
                    else:
                        task_net = self._look_for_task(task["instance_action_id"], net["net_id"])
                    if not task_net:
                        raise VimThreadException(
                            "Error trying to get depending task from task_index={}".format(net["net_id"]))
                    network_id = task_net.get("vim_id")
                    if not network_id:
                        raise VimThreadException(
                            "Cannot create VM because depends on a network not created or found: " +
                            str(task_net["error_msg"]))
                    net["net_id"] = network_id
            vim_vm_id = self.vim.new_vminstance(*params)

            # fill task_interfaces. Look for snd_net_id at database for each interface
            task_interfaces = {}
            for iface in net_list:
                task_interfaces[iface["vim_id"]] = {"iface_id": iface["uuid"]}
                with self.db_lock:
                    result = self.db.get_rows(SELECT=('sdn_net_id',),
                        FROM='instance_nets as ine join instance_interfaces as ii on ii.instance_net_id=ine.uuid',
                        WHERE={'ii.uuid': iface["uuid"]})
                if result:
                    task_interfaces[iface["vim_id"]]["sdn_net_id"] = result[0]['sdn_net_id']
                else:
                    self.logger.critical("Error creating VM, task=%s Network {} not found at DB", task_id,
                                         iface["uuid"], exc_info=True)

            task["vim_info"] = {}
            task["vim_interfaces"] = {}
            task["extra"]["interfaces"] = task_interfaces
            task["error_msg"] = None
            task["status"] = "DONE"
            task["vim_id"] = vim_vm_id
            instance_element_update = {"status": "BUILD", "vim_vm_id": vim_vm_id, "error_msg": None}
            return True, instance_element_update

        except (vimconn.vimconnException, VimThreadException) as e:
            self.logger.error("Error creating VM, task=%s: %s", task_id, str(e))
            error_text = self._format_vim_error_msg(str(e))
            task["error_msg"] = error_text
            task["status"] = "FAILED"
            task["vim_id"] = None
            instance_element_update = {"status": "VIM_ERROR", "vim_vm_id": None, "error_msg": error_text}
            return False, instance_element_update

    def del_vm(self, task):
        vm_vim_id = task["vim_id"]
        interfaces = task["extra"].get("interfaces", ())
        try:
            for iface in interfaces.values():
                if iface.get("sdn_port_id"):
                    try:
                        with self.db_lock:
                            self.ovim.delete_port(iface["sdn_port_id"])
                    except ovimException as e:
                        self.logger.error("ovimException deleting external_port={} at VM vim_id={} deletion ".format(
                            iface["sdn_port_id"], vm_vim_id) + str(e), exc_info=True)
                        # TODO Set error_msg at instance_nets

            self.vim.delete_vminstance(vm_vim_id)
            task["status"] = "DONE"
            task["error_msg"] = None
            return True, None

        except vimconn.vimconnException as e:
            task["error_msg"] = self._format_vim_error_msg(str(e))
            if isinstance(e, vimconn.vimconnNotFoundException):
                # If not found mark as Done and fill error_msg
                task["status"] = "DONE"
                return True, None
            task["status"] = "FAILED"
            return False, None

    def del_net(self, task):
        net_vim_id = task["vim_id"]
        sdn_net_id = task["extra"].get("sdn_net_id")
        try:
            if sdn_net_id:
                # Delete any attached port to this sdn network. There can be ports associated to this network in case
                # it was manually done using 'openmano vim-net-sdn-attach'
                with self.db_lock:
                    port_list = self.ovim.get_ports(columns={'uuid'},
                                                    filter={'name': 'external_port', 'net_id': sdn_net_id})
                    for port in port_list:
                        self.ovim.delete_port(port['uuid'])
                    self.ovim.delete_network(sdn_net_id)
            self.vim.delete_network(net_vim_id)
            task["status"] = "DONE"
            task["error_msg"] = None
            return True, None
        except ovimException as e:
            task["error_msg"] = self._format_vim_error_msg("ovimException obtaining and deleting external "
                                                           "ports for net {}: {}".format(sdn_net_id, str(e)))
        except vimconn.vimconnException as e:
            task["error_msg"] = self._format_vim_error_msg(str(e))
            if isinstance(e, vimconn.vimconnNotFoundException):
                # If not found mark as Done and fill error_msg
                task["status"] = "DONE"
                return True, None
        task["status"] = "FAILED"
        return False, None

    def get_net(self, task):
        try:
            task_id = task["instance_action_id"] + "." + str(task["task_index"])
            params = task["params"]
            filter = params[0]
            vim_nets = self.vim.get_network_list(filter)
            if not vim_nets:
                raise VimThreadException("Network not found with this criteria: '{}'".format(filter))
            elif len(vim_nets) > 1:
                raise VimThreadException("More than one network found with this criteria: '{}'".format(filter))
            vim_net_id = vim_nets[0]["id"]

            # Discover if this network is managed by a sdn controller
            sdn_net_id = None
            with self.db_lock:
                result = self.db.get_rows(SELECT=('sdn_net_id',), FROM='instance_nets',
                    WHERE={'vim_net_id': vim_net_id, 'instance_scenario_id': None,
                           'datacenter_tenant_id': self.datacenter_tenant_id})
            if result:
                sdn_net_id = result[0]['sdn_net_id']

            task["status"] = "DONE"
            task["extra"]["vim_info"] = {}
            task["extra"]["created"] = False
            task["extra"]["sdn_net_id"] = sdn_net_id
            task["error_msg"] = None
            task["vim_id"] = vim_net_id
            instance_element_update = {"vim_net_id": vim_net_id, "created": False, "status": "BUILD",
                                       "error_msg": None}
            return True, instance_element_update
        except (vimconn.vimconnException, VimThreadException) as e:
            self.logger.error("Error looking for  NET, task=%s: %s", str(task_id), str(e))
            task["status"] = "FAILED"
            task["vim_id"] = None
            task["error_msg"] = self._format_vim_error_msg(str(e))
            instance_element_update = {"vim_net_id": None, "status": "VIM_ERROR",
                                       "error_msg": task["error_msg"]}
            return False, instance_element_update
