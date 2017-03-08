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

'''
This is thread that interact with the host and the libvirt to manage VM
One thread will be launched per host 
'''
__author__ = "Alfonso Tierno, Pablo Montes"
__date__ = "$10-feb-2017 12:07:15$"

import threading
import time
import Queue
import logging
import vimconn
from db_base import db_base_Exception
from openvim.ovim import ovimException


# from logging import Logger
# import auxiliary_functions as af


def is_task_id(id):
    return True if id[:5] == "TASK." else False


class vim_thread(threading.Thread):

    def __init__(self, vimconn, task_lock, name=None, datacenter_name=None, datacenter_tenant_id=None, db=None, db_lock=None, ovim=None):
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
                if not self.task_queue.empty():
                    task = self.task_queue.get()
                    self.task_lock.acquire()
                    if task["status"] == "deleted":
                        self.task_lock.release()
                        continue
                    task["status"] == "processing"
                    self.task_lock.release()
                else:
                    now=time.time()
                    time.sleep(1)
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

                with self.task_lock:
                    task["status"] = "done" if result else "error"
                    task["result"] = content
                self.task_queue.task_done()

                if task["name"] == 'exit':
                    return 0
                elif task["name"] == 'reload':
                    break

        self.logger.debug("Finishing")

    def terminate(self, task):
        return True, None

    def _format_vim_error_msg(self, error_text):
        if len(error_text) >= 1024:
            return error_text[:516] + " ... " + error_text[-500:]
        return error_text

    def new_net(self, task):
        try:
            task_id = task["id"]
            params = task["params"]
            net_id = self.vim.new_network(*params)

            net_name = params[0]
            net_type = params[1]

            network = None
            sdn_controller = self.vim.config.get('sdn-controller')
            if sdn_controller and (net_type == "data" or net_type == "ptp"):
                network = {"name": net_name, "type": net_type}

                vim_net = self.vim.get_network(net_id)
                if vim_net.get('network_type') != 'vlan':
                    raise vimconn.vimconnException(net_name + "defined as type " + net_type + " but the created network in vim is " + vim_net['provider:network_type'])

                network["vlan"] = vim_net.get('segmentation_id')

            sdn_net_id = None
            with self.db_lock:
                if network:
                    sdn_net_id = self.ovim.new_network(network)
                self.db.update_rows("instance_nets", UPDATE={"vim_net_id": net_id, "sdn_net_id": sdn_net_id}, WHERE={"vim_net_id": task_id})

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
        except ovimException as e:
            self.logger.error("Error creating NET in ovim, task=%s: %s", str(task_id), str(e))
            return False, str(e)

    def new_vm(self, task):
        try:
            params = task["params"]
            task_id = task["id"]
            depends = task.get("depends")
            net_list = params[5]
            for net in net_list:
                if is_task_id(net["net_id"]):  # change task_id into network_id
                    try:
                        task_net = depends[net["net_id"]]
                        with self.task_lock:
                            if task_net["status"] == "error":
                                return False, "Cannot create VM because depends on a network that cannot be created: " + \
                                       str(task_net["result"])
                            elif task_net["status"] == "enqueued" or task_net["status"] == "processing":
                                return False, "Cannot create VM because depends on a network still not created"
                            network_id = task_net["result"]
                        net["net_id"] = network_id
                    except Exception as e:
                        return False, "Error trying to map from task_id={} to task result: {}".format(net["net_id"],
                                                                                                      str(e))
            vm_id = self.vim.new_vminstance(*params)
            try:
                with self.db_lock:
                    self.db.update_rows("instance_vms", UPDATE={"vim_vm_id": vm_id}, WHERE={"vim_vm_id": task_id})
            except db_base_Exception as e:
                self.logger.error("Error updating database %s", str(e))
            return True, vm_id
        except vimconn.vimconnException as e:
            self.logger.error("Error creating VM, task=%s: %s", str(task_id), str(e))
            try:
                with self.db_lock:
                    self.db.update_rows("instance_vms",
                                        UPDATE={"error_msg": self._format_vim_error_msg(str(e)), "status": "VIM_ERROR"},
                                        WHERE={"vim_vm_id": task_id})
            except db_base_Exception as e:
                self.logger.error("Error updating database %s", str(e))
            return False, str(e)

    def del_vm(self, task):
        vm_id = task["params"]
        if is_task_id(vm_id):
            try:
                task_create = task["depends"][vm_id]
                with self.task_lock:
                    if task_create["status"] == "error":
                        return True, "VM was not created. It has error: " + str(task_create["result"])
                    elif task_create["status"] == "enqueued" or task_create["status"] == "processing":
                        return False, "Cannot delete VM because still creating"
                    vm_id = task_create["result"]
            except Exception as e:
                return False, "Error trying to get task_id='{}':".format(vm_id, str(e))
        try:
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
            result = self.vim.delete_network(net_id)
            if sdn_net_id:
                with self.db_lock:
                    self.ovim.delete_network(sdn_net_id)
            return True, result
        except vimconn.vimconnException as e:
            return False, str(e)
        except ovimException as e:
            logging.error("Error deleting network from ovim. net_id: {}, sdn_net_id: {}".format(net_id, sdn_net_id))
            return False, str(e)


