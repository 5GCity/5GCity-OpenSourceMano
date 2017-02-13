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
__author__ = "Alfonso Tierno"
__date__ = "$10-feb-2017 12:07:15$"

import threading
import time
import Queue
import logging
import vimconn



# from logging import Logger
# import auxiliary_functions as af

# TODO: insert a logging system


class vim_thread(threading.Thread):

    def __init__(self, vimconn, name=None):
        '''Init a thread.
        Arguments:
            'id' number of thead
            'name' name of thread
            'host','user':  host ip or name to manage and user
            'db', 'db_lock': database class and lock to use it in exclusion
        '''
        threading.Thread.__init__(self)
        self.vim = vimconn
        if not name:
            self.name = vimconn["id"] + "-" + vimconn["config"]["datacenter_tenant_id"]
        else:
            self.name = name

        self.logger = logging.getLogger('openmano.vim.'+self.name)

        self.queueLock = threading.Lock()
        self.taskQueue = Queue.Queue(2000)


    def insert_task(self, task, *aditional):
        try:
            self.queueLock.acquire()
            task = self.taskQueue.put( (task,) + aditional, timeout=5) 
            self.queueLock.release()
            return 1, None
        except Queue.Full:
            return -1, "timeout inserting a task over host " + self.name

    def run(self):
        self.logger.debug("Starting")
        while True:
            #TODO reload service
            while True:
                self.queueLock.acquire()
                if not self.taskQueue.empty():
                    task = self.taskQueue.get()
                else:
                    task = None
                self.queueLock.release()
    
                if task is None:
                    now=time.time()
                    time.sleep(1)
                    continue        
    
                if task[0] == 'instance':
                    pass
                elif task[0] == 'image':
                    pass
                elif task[0] == 'exit':
                    print self.name, ": processing task exit"
                    self.terminate()
                    return 0
                elif task[0] == 'reload':
                    print self.name, ": processing task reload terminating and relaunching"
                    self.terminate()
                    break
                elif task[0] == 'edit-iface':
                    pass
                elif task[0] == 'restore-iface':
                    pass
                elif task[0] == 'new-ovsbridge':
                    pass
                elif task[0] == 'new-vxlan':
                    pass
                elif task[0] == 'del-ovsbridge':
                    pass
                elif task[0] == 'del-vxlan':
                    pass
                elif task[0] == 'create-ovs-bridge-port':
                    pass
                elif task[0] == 'del-ovs-port':
                    pass
                else:
                    self.logger.error("unknown task %s", str(task))

        self.logger.debug("Finishing")

    def terminate(self):
        pass

