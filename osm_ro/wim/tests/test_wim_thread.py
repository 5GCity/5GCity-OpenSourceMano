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

from __future__ import unicode_literals, print_function

import unittest
from difflib import unified_diff
from operator import itemgetter
from time import time

import json

from mock import MagicMock, patch

from . import fixtures as eg
from ...tests.db_helpers import (
    TestCaseWithDatabasePerTest,
    disable_foreign_keys,
    uuid
)
from ..engine import WimEngine
from ..persistence import WimPersistence
from ..wim_thread import WimThread


ignore_connector = patch('osm_ro.wim.wim_thread.CONNECTORS', MagicMock())


def _repr(value):
    return json.dumps(value, indent=4, sort_keys=True)


@ignore_connector
class TestWimThreadWithDb(TestCaseWithDatabasePerTest):
    def setUp(self):
        super(TestWimThreadWithDb, self).setUp()
        self.persist = WimPersistence(self.db)
        wim = eg.wim(0)
        account = eg.wim_account(0, 0)
        account['wim'] = wim
        self.thread = WimThread(self.persist, account)
        self.thread.connector = MagicMock()

    def assertTasksEqual(self, left, right):
        fields = itemgetter('item', 'item_id', 'action', 'status')
        left_ = (t.as_dict() for t in left)
        left_ = [fields(t) for t in left_]
        right_ = [fields(t) for t in right]

        try:
            self.assertItemsEqual(left_, right_)
        except AssertionError:
            print('left', _repr(left))
            print('left', len(left_), 'items')
            print('right', len(right_), 'items')
            result = list(unified_diff(_repr(sorted(left_)).split('\n'),
                                       _repr(sorted(right_)).split('\n'),
                                       'left', 'right'))
            print('diff:\n', '\n'.join(result))
            raise

    def test_reload_actions__all_create(self):
        # Given we have 3 CREATE actions stored in the database
        actions = eg.wim_actions('CREATE',
                                 action_id=uuid('action0'), num_links=3)
        self.populate([
            {'nfvo_tenants': eg.tenant()}
        ] + eg.wim_set() + [
            {'instance_actions':
                eg.instance_action(action_id=uuid('action0'))},
            {'vim_wim_actions': actions}
        ])

        # When we reload the tasks
        self.thread.reload_actions()
        # All of them should be inserted as pending
        self.assertTasksEqual(self.thread.pending_tasks, actions)

    def test_reload_actions__all_refresh(self):
        # Given just DONE tasks are in the database
        actions = eg.wim_actions(status='DONE',
                                 action_id=uuid('action0'), num_links=3)
        self.populate([
            {'nfvo_tenants': eg.tenant()}
        ] + eg.wim_set() + [
            {'instance_actions':
                eg.instance_action(action_id=uuid('action0'))},
            {'vim_wim_actions': actions}
        ])

        # When we reload the tasks
        self.thread.reload_actions()
        # All of them should be inserted as refresh
        self.assertTasksEqual(self.thread.refresh_tasks, actions)

    def test_reload_actions__grouped(self):
        # Given we have 2 tasks for the same item in the database
        kwargs = {'action_id': uuid('action0')}
        actions = (eg.wim_actions('CREATE', **kwargs) +
                   eg.wim_actions('FIND', **kwargs))
        for i, action in enumerate(actions):
            action['task_index'] = i

        self.populate([
            {'nfvo_tenants': eg.tenant()}
        ] + eg.wim_set() + [
            {'instance_actions': eg.instance_action(**kwargs)},
            {'vim_wim_actions': actions}
        ])

        # When we reload the tasks
        self.thread.reload_actions()
        # Just one group should be created
        self.assertEqual(len(self.thread.grouped_tasks.values()), 1)

    def test_reload_actions__delete_scheduled(self):
        # Given we have 3 tasks for the same item in the database, but one of
        # them is a DELETE task and it is SCHEDULED
        kwargs = {'action_id': uuid('action0')}
        actions = (eg.wim_actions('CREATE', **kwargs) +
                   eg.wim_actions('FIND', **kwargs) +
                   eg.wim_actions('DELETE', status='SCHEDULED', **kwargs))
        for i, action in enumerate(actions):
            action['task_index'] = i

        self.populate([
            {'nfvo_tenants': eg.tenant()}
        ] + eg.wim_set() + [
            {'instance_actions': eg.instance_action(**kwargs)},
            {'vim_wim_actions': actions}
        ])

        # When we reload the tasks
        self.thread.reload_actions()
        # Just one group should be created
        self.assertEqual(len(self.thread.grouped_tasks.values()), 1)

    def test_reload_actions__delete_done(self):
        # Given we have 3 tasks for the same item in the database, but one of
        # them is a DELETE task and it is not SCHEDULED
        kwargs = {'action_id': uuid('action0')}
        actions = (eg.wim_actions('CREATE', **kwargs) +
                   eg.wim_actions('FIND', **kwargs) +
                   eg.wim_actions('DELETE', status='DONE', **kwargs))
        for i, action in enumerate(actions):
            action['task_index'] = i

        self.populate([
            {'nfvo_tenants': eg.tenant()}
        ] + eg.wim_set() + [
            {'instance_actions': eg.instance_action(**kwargs)},
            {'vim_wim_actions': actions}
        ])

        # When we reload the tasks
        self.thread.reload_actions()
        # No pending task should be found
        self.assertEqual(self.thread.pending_tasks, [])

    def test_reload_actions__batch(self):
        # Given the group_limit is 10, and we have 24
        group_limit = 10
        kwargs = {'action_id': uuid('action0')}
        actions = (eg.wim_actions('CREATE', num_links=8, **kwargs) +
                   eg.wim_actions('FIND', num_links=8, **kwargs) +
                   eg.wim_actions('FIND', num_links=8, **kwargs))
        for i, action in enumerate(actions):
            action['task_index'] = i

        self.populate([
            {'nfvo_tenants': eg.tenant()}
        ] + eg.wim_set() + [
            {'instance_actions': eg.instance_action(**kwargs)},
            {'vim_wim_actions': actions}
        ])

        # When we reload the tasks
        self.thread.reload_actions(group_limit)

        # Then we should still see the actions in memory properly
        self.assertTasksEqual(self.thread.pending_tasks, actions)
        self.assertEqual(len(self.thread.grouped_tasks.values()), 8)

    @disable_foreign_keys
    def test_process_list__refresh(self):
        update_wan_link = MagicMock(wrap=self.persist.update_wan_link)
        update_action = MagicMock(wrap=self.persist.update_wan_link)
        patches = dict(update_wan_link=update_wan_link,
                       update_action=update_action)

        with patch.multiple(self.persist, **patches):
            # Given we have 2 tasks in the refresh queue
            kwargs = {'action_id': uuid('action0')}
            actions = (eg.wim_actions('FIND', 'DONE', **kwargs) +
                       eg.wim_actions('CREATE', 'BUILD', **kwargs))
            for i, action in enumerate(actions):
                action['task_index'] = i

            self.populate(
                [{'instance_wim_nets': eg.instance_wim_nets()}] +
                [{'instance_actions':
                    eg.instance_action(num_tasks=2, **kwargs)}] +
                [{'vim_wim_actions': actions}])

            self.thread.insert_pending_tasks(actions)

            # When we process the refresh list
            processed = self.thread.process_list('refresh')

            # Then we should have 2 updates
            self.assertEqual(processed, 2)

            # And the database should be updated accordingly
            self.assertEqual(update_wan_link.call_count, 2)
            self.assertEqual(update_action.call_count, 2)

    @disable_foreign_keys
    def test_delete_superseed_create(self):
        # Given we insert a scheduled CREATE task
        instance_action = eg.instance_action(num_tasks=1)
        self.thread.pending_tasks = []
        engine = WimEngine(persistence=self.persist)
        self.addCleanup(engine.stop_threads)
        wan_links = eg.instance_wim_nets()
        create_actions = engine.create_actions(wan_links)
        delete_actions = engine.delete_actions(wan_links)
        engine.incorporate_actions(create_actions + delete_actions,
                                   instance_action)

        self.populate(instance_actions=instance_action,
                      vim_wim_actions=create_actions + delete_actions)

        self.thread.insert_pending_tasks(create_actions)

        assert self.thread.pending_tasks[0].is_scheduled

        # When we insert the equivalent DELETE task
        self.thread.insert_pending_tasks(delete_actions)

        # Then the CREATE task should be superseded
        self.assertEqual(self.thread.pending_tasks[0].action, 'CREATE')
        assert self.thread.pending_tasks[0].is_superseded

        self.thread.process_list('pending')
        self.thread.process_list('refresh')
        self.assertFalse(self.thread.pending_tasks)


@ignore_connector
class TestWimThread(unittest.TestCase):
    def setUp(self):
        wim = eg.wim(0)
        account = eg.wim_account(0, 0)
        account['wim'] = wim
        self.persist = MagicMock()
        self.thread = WimThread(self.persist, account)
        self.thread.connector = MagicMock()

        super(TestWimThread, self).setUp()

    def test_process_refresh(self):
        # Given we have 30 tasks in the refresh queue
        kwargs = {'action_id': uuid('action0')}
        actions = eg.wim_actions('FIND', 'DONE', num_links=30, **kwargs)
        self.thread.insert_pending_tasks(actions)

        # When we process the refresh list
        processed = self.thread.process_list('refresh')

        # Then we should have REFRESH_BATCH updates
        self.assertEqual(processed, self.thread.BATCH)

    def test_process_refresh__with_superseded(self):
        # Given we have 30 tasks but 15 of them are superseded
        kwargs = {'action_id': uuid('action0')}
        actions = eg.wim_actions('FIND', 'DONE', num_links=30, **kwargs)
        self.thread.insert_pending_tasks(actions)
        for task in self.thread.refresh_tasks[0:30:2]:
            task.status = 'SUPERSEDED'

        now = time()

        # When we call the refresh_elements
        processed = self.thread.process_list('refresh')

        # Then we should have 25 updates (since SUPERSEDED updates are cheap,
        # they are not counted for the limits)
        self.assertEqual(processed, 25)

        # The SUPERSEDED tasks should be removed, 5 tasks should be untouched,
        # and 10 tasks should be rescheduled
        refresh_tasks = self.thread.refresh_tasks
        old = [t for t in refresh_tasks if t.process_at <= now]
        new = [t for t in refresh_tasks if t.process_at > now]
        self.assertEqual(len(old), 5)
        self.assertEqual(len(new), 10)
        self.assertEqual(len(self.thread.refresh_tasks), 15)


if __name__ == '__main__':
    unittest.main()
