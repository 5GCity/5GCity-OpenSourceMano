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
# pylint: disable=E1101,E0203,W0201

"""Common logic for task management"""
import logging
from time import time
from types import StringTypes

from six.moves import range

import yaml

from ..utils import (
    filter_dict_keys,
    filter_out_dict_keys,
    merge_dicts,
    remove_none_items,
    truncate
)

PENDING, REFRESH, IGNORE = range(3)

TIMEOUT = 1 * 60 * 60  # 1 hour
MIN_ATTEMPTS = 10


class Action(object):
    """Create a basic object representing the action record.

    Arguments:
        record (dict): record as returned by the database
        **kwargs: extra keyword arguments to overwrite the fields in record
    """

    PROPERTIES = [
        'task_index',          # MD - Index number of the task.
                               #      This together with the instance_action_id
                               #      forms a unique key identifier
        'action',              # MD - CREATE, DELETE, FIND
        'item',                # MD - table name, eg. instance_wim_nets
        'item_id',             # MD - uuid of the referenced entry in the
                               #      previous table
        'instance_action_id',  # MD - reference to a cohesive group of actions
                               #      related to the same instance-scenario
        'wim_account_id',      # MD - reference to the WIM account used
                               #      by the thread/connector
        'wim_internal_id',     # MD - internal ID used by the WIM to refer to
                               #      the item
        'datacenter_vim_id',   # MD - reference to the VIM account used
                               #      by the thread/connector
        'vim_id',              # MD - internal ID used by the VIM to refer to
                               #      the item
        'status',              # MD - SCHEDULED,BUILD,DONE,FAILED,SUPERSEDED
        'extra',               # MD - text with yaml format at database,
        #                             dict at memory with:
        # `- params:     list with the params to be sent to the VIM for CREATE
        #                or FIND. For DELETE the vim_id is taken from other
        #                related tasks
        # `- find:       (only for CREATE tasks) if present it should FIND
        #                before creating and use if existing.
        #                Contains the FIND params
        # `- depends_on: list with the 'task_index'es of tasks that must be
        #                completed before. e.g. a vm creation depends on a net
        #                creation
        # `- sdn_net_id: used for net.
        # `- tries
        # `- created_items:
        #                dictionary with extra elements created that need
        #                to be deleted. e.g. ports,
        # `- volumes,...
        # `- created:    False if the VIM element is not created by
        #                other actions, and it should not be deleted
        # `- wim_status: WIM status of the element. Stored also at database
        #                in the item table
        'params',              # M  - similar to extra[params]
        'depends_on',          # M  - similar to extra[depends_on]
        'depends',             # M  - dict with task_index(from depends_on) to
                               #      task class
        'error_msg',           # MD - descriptive text upon an error
        'created_at',          # MD - task DB creation time
        'modified_at',         # MD - last DB update time
        'process_at',          # M  - unix epoch when to process the task
    ]

    __slots__ = PROPERTIES + [
        'logger',
    ]

    def __init__(self, record, logger=None, **kwargs):
        self.logger = logger or logging.getLogger('openmano.wim.action')
        attrs = merge_dicts(dict.fromkeys(self.PROPERTIES), record, kwargs)
        self.update(_expand_extra(attrs))

    def __repr__(self):
        return super(Action, self).__repr__() + repr(self.as_dict())

    def as_dict(self, *fields):
        """Representation of the object as a dict"""
        attrs = (set(self.PROPERTIES) & set(fields)
                 if fields else self.PROPERTIES)
        return {k: getattr(self, k) for k in attrs}

    def as_record(self):
        """Returns a dict that can be send to the persistence layer"""
        special = ['params', 'depends_on', 'depends']
        record = self.as_dict()
        record['extra'].update(self.as_dict(*special))
        non_fields = special + ['process_at']

        return remove_none_items(filter_out_dict_keys(record, non_fields))

    def update(self, values=None, **kwargs):
        """Update the in-memory representation of the task (works similarly to
        dict.update). The update is NOT automatically persisted.
        """
        # "white-listed mass assignment"
        updates = merge_dicts(values, kwargs)
        for attr in set(self.PROPERTIES) & set(updates.keys()):
            setattr(self, attr, updates[attr])

    def save(self, persistence, **kwargs):
        """Persist current state of the object to the database.

        Arguments:
            persistence: object encapsulating the database
            **kwargs: extra properties to be updated before saving

        Note:
            If any key word argument is passed, the object itself will be
            changed as an extra side-effect.
        """
        action_id = self.instance_action_id
        index = self.task_index
        if kwargs:
            self.update(kwargs)
        properties = self.as_record()

        return persistence.update_action(action_id, index, properties)

    def fail(self, persistence, reason, status='FAILED'):
        """Mark action as FAILED, updating tables accordingly"""
        persistence.update_instance_action_counters(
            self.instance_action_id,
            failed=1,
            done=(-1 if self.status == 'DONE' else 0))

        self.status = status
        self.error_msg = truncate(reason)
        self.logger.error('%s %s: %s', self.id, status, reason)
        return self.save(persistence)

    def succeed(self, persistence, status='DONE'):
        """Mark action as DONE, updating tables accordingly"""
        persistence.update_instance_action_counters(
            self.instance_action_id, done=1)
        self.status = status
        self.logger.debug('%s %s', self.id, status)
        return self.save(persistence)

    def defer(self, persistence, reason,
              timeout=TIMEOUT, min_attempts=MIN_ATTEMPTS):
        """Postpone the task processing, taking care to not timeout.

        Arguments:
            persistence: object encapsulating the database
            reason (str): explanation for the delay
            timeout (int): maximum delay tolerated since the first attempt.
                Note that this number is a time delta, in seconds
            min_attempts (int): Number of attempts to try before giving up.
        """
        now = time()
        last_attempt = self.extra.get('last_attempted_at') or time()
        attempts = self.extra.get('attempts') or 0

        if last_attempt - now > timeout and attempts > min_attempts:
            self.fail(persistence,
                      'Timeout reached. {} attempts in the last {:d} min'
                      .format(attempts, last_attempt / 60))

        self.extra['last_attempted_at'] = time()
        self.extra['attempts'] = attempts + 1
        self.logger.info('%s DEFERRED: %s', self.id, reason)
        return self.save(persistence)

    @property
    def group_key(self):
        """Key defining the group to which this tasks belongs"""
        return (self.item, self.item_id)

    @property
    def processing(self):
        """Processing status for the task (PENDING, REFRESH, IGNORE)"""
        if self.status == 'SCHEDULED':
            return PENDING

        return IGNORE

    @property
    def id(self):
        """Unique identifier of this particular action"""
        return '{}[{}]'.format(self.instance_action_id, self.task_index)

    @property
    def is_scheduled(self):
        return self.status == 'SCHEDULED'

    @property
    def is_build(self):
        return self.status == 'BUILD'

    @property
    def is_done(self):
        return self.status == 'DONE'

    @property
    def is_failed(self):
        return self.status == 'FAILED'

    @property
    def is_superseded(self):
        return self.status == 'SUPERSEDED'

    def refresh(self, connector, persistence):
        """Use the connector/persistence to refresh the status of the item.

        After the item status is refreshed any change in the task should be
        persisted to the database.

        Arguments:
            connector: object containing the classes to access the WIM or VIM
            persistence: object containing the methods necessary to query the
                database and to persist the updates
        """
        self.logger.debug(
            'Action `%s` has no refresh to be done',
            self.__class__.__name__)

    def expand_dependency_links(self, task_group):
        """Expand task indexes into actual IDs"""
        if not self.depends_on or (
                isinstance(self.depends, dict) and self.depends):
            return

        num_tasks = len(task_group)
        references = {
            "TASK-{}".format(i): task_group[i]
            for i in self.depends_on
            if i < num_tasks and task_group[i].task_index == i and
            task_group[i].instance_action_id == self.instance_action_id
        }
        self.depends = references

    def become_superseded(self, superseding):
        """When another action tries to supersede this one,
        we need to change both of them, so the surviving actions will be
        logic consistent.

        This method should do the required internal changes, and also
        suggest changes for the other, superseding, action.

        Arguments:
            superseding: other task superseding this one

        Returns:
            dict: changes suggested to the action superseding this one.
                  A special key ``superseding_needed`` is used to
                  suggest if the superseding is actually required or not.
                  If not present, ``superseding_needed`` is assumed to
                  be False.
        """
        self.status = 'SUPERSEDED'
        self.logger.debug(
            'Action `%s` was superseded by `%s`',
            self.__class__.__name__, superseding.__class__.__name__)
        return {}

    def supersede(self, others):
        """Supersede other tasks, if necessary

        Arguments:
            others (list): action objects being superseded

        When the task decide to supersede others, this method should call
        ``become_superseded`` on the other actions, collect the suggested
        updates and perform the necessary changes
        """
        # By default actions don't supersede others
        self.logger.debug(
            'Action `%s` does not supersede other actions',
            self.__class__.__name__)

    def process(self, connector, persistence, ovim):
        """Abstract method, that needs to be implemented.
        Process the current task.

        Arguments:
            connector: object with API for accessing the WAN
                Infrastructure Manager system
            persistence: abstraction layer for the database
            ovim: instance of openvim, abstraction layer that enable
                SDN-related operations
        """
        raise NotImplementedError


class FindAction(Action):
    """Abstract class that should be inherited for FIND actions, depending on
    the item type.
    """
    @property
    def processing(self):
        if self.status in ('DONE', 'BUILD'):
            return REFRESH

        return super(FindAction, self).processing

    def become_superseded(self, superseding):
        super(FindAction, self).become_superseded(superseding)
        info = ('vim_id', 'wim_internal_id')
        return remove_none_items({f: getattr(self, f) for f in info})


class CreateAction(Action):
    """Abstract class that should be inherited for CREATE actions, depending on
    the item type.
    """
    @property
    def processing(self):
        if self.status in ('DONE', 'BUILD'):
            return REFRESH

        return super(CreateAction, self).processing

    def become_superseded(self, superseding):
        super(CreateAction, self).become_superseded(superseding)

        created = self.extra.get('created', True)
        sdn_net_id = self.extra.get('sdn_net_id')
        pending_info = self.wim_internal_id or self.vim_id or sdn_net_id
        if not(created and pending_info):
            return {}

        extra_fields = ('sdn_net_id', 'interfaces', 'created_items')
        extra_info = filter_dict_keys(self.extra or {}, extra_fields)

        return {'superseding_needed': True,
                'wim_internal_id': self.wim_internal_id,
                'vim_id': self.vim_id,
                'extra': remove_none_items(extra_info)}


class DeleteAction(Action):
    """Abstract class that should be inherited for DELETE actions, depending on
    the item type.
    """
    def supersede(self, others):
        self.logger.debug('%s %s %s %s might supersede other actions',
                          self.id, self.action, self.item, self.item_id)
        # First collect all the changes from the superseded tasks
        changes = [other.become_superseded(self) for other in others]
        needed = any(change.pop('superseding_needed', False)
                     for change in changes)

        # Deal with the nested ones first
        extras = [change.pop('extra', None) or {} for change in changes]
        items = [extra.pop('created_items', None) or {} for extra in extras]
        items = merge_dicts(self.extra.get('created_items', {}), *items)
        self.extra = merge_dicts(self.extra, {'created_items': items}, *extras)

        # Accept the other ones
        change = ((key, value) for key, value in merge_dicts(*changes).items()
                  if key in self.PROPERTIES)
        for attr, value in change:
            setattr(self, attr, value)

        # Reevaluate if the action itself is needed
        if not needed:
            self.status = 'SUPERSEDED'


def _expand_extra(record):
    extra = record.pop('extra', None) or {}
    if isinstance(extra, StringTypes):
        extra = yaml.safe_load(extra)

    record['params'] = extra.get('params')
    record['depends_on'] = extra.get('depends_on', [])
    record['depends'] = extra.get('depends', None)
    record['extra'] = extra

    return record
