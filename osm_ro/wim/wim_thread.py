# -*- coding: utf-8 -*-
##
# Copyright 2018 University of Bristol - High Performance Networks Research
# Group
# All Rights Reserved.
#
# Contributors: Anderson Bravalheri, Dimitrios Gkounis, Abubakar Siddique
# Muqaddas, Navdeep Uniyal, Reza Nejabati and Dimitra Simeonidou
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
# contact with: <highperformance-networks@bristol.ac.uk>
#
# Neither the name of the University of Bristol nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# This work has been performed in the context of DCMS UK 5G Testbeds
# & Trials Programme and in the framework of the Metro-Haul project -
# funded by the European Commission under Grant number 761727 through the
# Horizon 2020 and 5G-PPP programmes.
##

"""
Thread-based interaction with WIMs. Tasks are stored in the
database (vim_wim_actions table) and processed sequentially

Please check the Action class for information about the content of each action.
"""

import logging
import threading
from contextlib import contextmanager
from functools import partial
from itertools import islice, chain, takewhile
from operator import itemgetter, attrgetter
from sys import exc_info
from time import time, sleep

from six import reraise
from six.moves import queue

from . import wan_link_actions
from ..utils import ensure, partition, pipe
from .actions import IGNORE, PENDING, REFRESH
from .errors import (
    DbBaseException,
    QueueFull,
    InvalidParameters as Invalid,
    UndefinedAction,
)
from .failing_connector import FailingConnector
from .wimconn import WimConnectorError
from .wimconn_dynpac import DynpacConnector
from .wimconn_fake import FakeConnector
from .wimconn_ietfl2vpn import WimconnectorIETFL2VPN

ACTIONS = {
    'instance_wim_nets': wan_link_actions.ACTIONS
}

CONNECTORS = {
    # "odl": wimconn_odl.OdlConnector,
    "dynpac": DynpacConnector,
    "fake": FakeConnector,
    "ietfl2vpn": WimconnectorIETFL2VPN,
    # Add extra connectors here
}


class WimThread(threading.Thread):
    """Specialized task queue implementation that runs in an isolated thread.

    Objects of this class have a few methods that are intended to be used
    outside of the thread:

    - start
    - insert_task
    - reload
    - exit

    All the other methods are used internally to manipulate/process the task
    queue.
    """
    RETRY_SCHEDULED = 10  # 10 seconds
    REFRESH_BUILD = 10    # 10 seconds
    REFRESH_ACTIVE = 60   # 1 minute
    BATCH = 10            # 10 actions per round
    QUEUE_SIZE = 2000
    RECOVERY_TIME = 5     # Sleep 5s to leave the system some time to recover
    MAX_RECOVERY_TIME = 180
    WAITING_TIME = 1      # Wait 1s for taks to arrive, when there are none

    def __init__(self, persistence, wim_account, logger=None, ovim=None):
        """Init a thread.

        Arguments:
            persistence: Database abstraction layer
            wim_account: Record containing wim_account, tenant and wim
                information.
        """
        name = '{}.{}.{}'.format(wim_account['wim']['name'],
                                 wim_account['name'], wim_account['uuid'])
        super(WimThread, self).__init__(name=name)

        self.name = name
        self.connector = None
        self.wim_account = wim_account

        self.logger = logger or logging.getLogger('openmano.wim.'+self.name)
        self.persist = persistence
        self.ovim = ovim

        self.task_queue = queue.Queue(self.QUEUE_SIZE)

        self.refresh_tasks = []
        """Time ordered task list for refreshing the status of WIM nets"""

        self.pending_tasks = []
        """Time ordered task list for creation, deletion of WIM nets"""

        self.grouped_tasks = {}
        """ It contains all the creation/deletion pending tasks grouped by
        its concrete vm, net, etc

            <item><item_id>:
                -   <task1>  # e.g. CREATE task
                    <task2>  # e.g. DELETE task
        """

        self._insert_task = {
            PENDING: partial(self.schedule, list_name='pending'),
            REFRESH: partial(self.schedule, list_name='refresh'),
            IGNORE: lambda task, *_, **__: task.save(self.persist)}
        """Send the task to the right processing queue"""

    def on_start(self):
        """Run a series of procedures every time the thread (re)starts"""
        self.connector = self.get_connector()
        self.reload_actions()

    def get_connector(self):
        """Create an WimConnector instance according to the wim.type"""
        error_msg = ''
        account_id = self.wim_account['uuid']
        try:
            account = self.persist.get_wim_account_by(
                uuid=account_id, hide=None)  # Credentials need to be available
            wim = account['wim']
            mapping = self.persist.query('wim_port_mappings',
                                         WHERE={'wim_id': wim['uuid']},
                                         error_if_none=False)
            return CONNECTORS[wim['type']](wim, account, {
                'service_endpoint_mapping': mapping or []
            })
        except DbBaseException as ex:
            error_msg = ('Error when retrieving WIM account ({})\n'
                         .format(account_id)) + str(ex)
            self.logger.error(error_msg, exc_info=True)
        except KeyError as ex:
            error_msg = ('Unable to find the WIM connector for WIM ({})\n'
                         .format(wim['type'])) + str(ex)
            self.logger.error(error_msg, exc_info=True)
        except (WimConnectorError, Exception) as ex:
            # TODO: Remove the Exception class here when the connector class is
            # ready
            error_msg = ('Error when loading WIM connector for WIM ({})\n'
                         .format(wim['type'])) + str(ex)
            self.logger.error(error_msg, exc_info=True)

        error_msg_extra = ('Any task targeting WIM account {} ({}) will fail.'
                           .format(account_id, self.wim_account.get('name')))
        self.logger.warning(error_msg_extra)
        return FailingConnector(error_msg + '\n' + error_msg_extra)

    @contextmanager
    def avoid_exceptions(self):
        """Make a real effort to keep the thread alive, by avoiding the
        exceptions. They are instead logged as a critical errors.
        """
        try:
            yield
        except Exception as ex:
            self.logger.critical("Unexpected exception %s", ex, exc_info=True)
            sleep(self.RECOVERY_TIME)

    def reload_actions(self, group_limit=100):
        """Read actions from database and reload them at memory.

        This method will clean and reload the attributes ``refresh_tasks``,
        ``pending_tasks`` and ``grouped_tasks``

        Attributes:
            group_limit (int): maximum number of action groups (those that
                refer to the same ``<item, item_id>``) to be retrieved from the
                database in each batch.
        """

        # First we clean the cache to let the garbage collector work
        self.refresh_tasks = []
        self.pending_tasks = []
        self.grouped_tasks = {}

        offset = 0

        while True:
            # Do things in batches
            task_groups = self.persist.get_actions_in_groups(
                self.wim_account['uuid'], item_types=('instance_wim_nets',),
                group_offset=offset, group_limit=group_limit)
            offset += (group_limit - 1)  # Update for the next batch

            if not task_groups:
                break

            pending_groups = (g for _, g in task_groups if is_pending_group(g))

            for task_list in pending_groups:
                with self.avoid_exceptions():
                    self.insert_pending_tasks(filter_pending_tasks(task_list))

            self.logger.debug(
                'Reloaded wim actions pending: %d refresh: %d',
                len(self.pending_tasks), len(self.refresh_tasks))

    def insert_pending_tasks(self, task_list):
        """Insert task in the list of actions being processed"""
        task_list = [action_from(task, self.logger) for task in task_list]

        for task in task_list:
            group = task.group_key
            self.grouped_tasks.setdefault(group, [])
            # Each task can try to supersede the other ones,
            # but just DELETE actions will actually do
            task.supersede(self.grouped_tasks[group])
            self.grouped_tasks[group].append(task)

        # We need a separate loop so each task can check all the other
        # ones before deciding
        for task in task_list:
            self._insert_task[task.processing](task)
            self.logger.debug('Insert WIM task: %s (%s): %s %s',
                              task.id, task.status, task.action, task.item)

    def schedule(self, task, when=None, list_name='pending'):
        """Insert a task in the correct list, respecting the schedule.
        The refreshing list is ordered by threshold_time (task.process_at)
        It is assumed that this is called inside this thread

        Arguments:
            task (Action): object representing the task.
                This object must implement the ``process`` method and inherit
                from the ``Action`` class
            list_name: either 'refresh' or 'pending'
            when (float): unix time in seconds since as a float number
        """
        processing_list = {'refresh': self.refresh_tasks,
                           'pending': self.pending_tasks}[list_name]

        when = when or time()
        task.process_at = when

        schedule = (t.process_at for t in processing_list)
        index = len(list(takewhile(lambda moment: moment <= when, schedule)))

        processing_list.insert(index, task)
        self.logger.debug(
            'Schedule of %s in "%s" - waiting position: %d (%f)',
            task.id, list_name, index, task.process_at)

        return task

    def process_list(self, list_name='pending'):
        """Process actions in batches and reschedule them if necessary"""
        task_list, handler = {
            'refresh': (self.refresh_tasks, self._refresh_single),
            'pending': (self.pending_tasks, self._process_single)}[list_name]

        now = time()
        waiting = ((i, task) for i, task in enumerate(task_list)
                   if task.process_at is None or task.process_at <= now)

        is_superseded = pipe(itemgetter(1), attrgetter('is_superseded'))
        superseded, active = partition(is_superseded, waiting)
        superseded = [(i, t.save(self.persist)) for i, t in superseded]

        batch = islice(active, self.BATCH)
        refreshed = [(i, handler(t)) for i, t in batch]

        # Since pop changes the indexes in the list, we need to do it backwards
        remove = sorted([i for i, _ in chain(refreshed, superseded)])
        return len([task_list.pop(i) for i in reversed(remove)])

    def _refresh_single(self, task):
        """Refresh just a single task, and reschedule it if necessary"""
        now = time()

        result = task.refresh(self.connector, self.persist)
        self.logger.debug('Refreshing WIM task: %s (%s): %s %s => %r',
                          task.id, task.status, task.action, task.item, result)

        interval = self.REFRESH_BUILD if task.is_build else self.REFRESH_ACTIVE
        self.schedule(task, now + interval, 'refresh')

        return result

    def _process_single(self, task):
        """Process just a single task, and reschedule it if necessary"""
        now = time()

        result = task.process(self.connector, self.persist, self.ovim)
        self.logger.debug('Executing WIM task: %s (%s): %s %s => %r',
                          task.id, task.status, task.action, task.item, result)

        if task.action == 'DELETE':
            del self.grouped_tasks[task.group_key]

        self._insert_task[task.processing](task, now + self.RETRY_SCHEDULED)

        return result

    def insert_task(self, task):
        """Send a message to the running thread

        This function is supposed to be called outside of the WIM Thread.

        Arguments:
            task (str or dict): `"exit"`, `"reload"` or dict representing a
                task. For more information about the fields in task, please
                check the Action class.
        """
        try:
            self.task_queue.put(task, False)
            return None
        except queue.Full:
            ex = QueueFull(self.name)
            reraise(ex.__class__, ex, exc_info()[2])

    def reload(self):
        """Send a message to the running thread to reload itself"""
        self.insert_task('reload')

    def exit(self):
        """Send a message to the running thread to kill itself"""
        self.insert_task('exit')

    def run(self):
        self.logger.debug('Starting: %s', self.name)
        recovery_time = 0
        while True:
            self.on_start()
            reload_thread = False
            self.logger.debug('Reloaded: %s', self.name)

            while True:
                with self.avoid_exceptions():
                    while not self.task_queue.empty():
                        task = self.task_queue.get()
                        if isinstance(task, dict):
                            self.insert_pending_tasks([task])
                        elif isinstance(task, list):
                            self.insert_pending_tasks(task)
                        elif isinstance(task, str):
                            if task == 'exit':
                                self.logger.debug('Finishing: %s', self.name)
                                return 0
                            elif task == 'reload':
                                reload_thread = True
                                break
                        self.task_queue.task_done()

                    if reload_thread:
                        break

                    if not(self.process_list('pending') +
                           self.process_list('refresh')):
                        sleep(self.WAITING_TIME)

                    if isinstance(self.connector, FailingConnector):
                        # Wait sometime to try instantiating the connector
                        # again and restart
                        # Increase the recovery time if restarting is not
                        # working (up to a limit)
                        recovery_time = min(self.MAX_RECOVERY_TIME,
                                            recovery_time + self.RECOVERY_TIME)
                        sleep(recovery_time)
                        break
                    else:
                        recovery_time = 0

        self.logger.debug("Finishing")


def is_pending_group(group):
    return all(task['action'] != 'DELETE' or
               task['status'] == 'SCHEDULED'
               for task in group)


def filter_pending_tasks(group):
    return (t for t in group
            if (t['status'] == 'SCHEDULED' or
                t['action'] in ('CREATE', 'FIND')))


def action_from(record, logger=None, mapping=ACTIONS):
    """Create an Action object from a action record (dict)

    Arguments:
        mapping (dict): Nested data structure that maps the relationship
            between action properties and object constructors.  This data
            structure should be a dict with 2 levels of keys: item type and
            action type. Example::
                {'wan_link':
                    {'CREATE': WanLinkCreate}
                    ...}
                ...}
        record (dict): action information

    Return:
        (Action.Base): Object representing the action
    """
    ensure('item' in record, Invalid('`record` should contain "item"'))
    ensure('action' in record, Invalid('`record` should contain "action"'))

    try:
        factory = mapping[record['item']][record['action']]
        return factory(record, logger=logger)
    except KeyError:
        ex = UndefinedAction(record['item'], record['action'])
        reraise(ex.__class__, ex, exc_info()[2])
