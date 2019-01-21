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
import json
from pprint import pformat
from sys import exc_info
from time import time

from six import reraise

from ..utils import filter_dict_keys as filter_keys
from ..utils import merge_dicts, remove_none_items, safe_get, truncate
from .actions import CreateAction, DeleteAction, FindAction
from .errors import (
    InconsistentState,
    NoRecordFound,
    NoExternalPortFound
)
from wimconn import WimConnectorError

INSTANCE_NET_STATUS_ERROR = ('DOWN', 'ERROR', 'VIM_ERROR',
                             'DELETED', 'SCHEDULED_DELETION')
INSTANCE_NET_STATUS_PENDING = ('BUILD', 'INACTIVE', 'SCHEDULED_CREATION')
INSTANCE_VM_STATUS_ERROR = ('ERROR', 'VIM_ERROR',
                            'DELETED', 'SCHEDULED_DELETION')


class RefreshMixin(object):
    def refresh(self, connector, persistence):
        """Ask the external WAN Infrastructure Manager system for updates on
        the status of the task.

        Arguments:
            connector: object with API for accessing the WAN
                Infrastructure Manager system
            persistence: abstraction layer for the database
        """
        fields = ('wim_status', 'wim_info', 'error_msg')
        result = dict.fromkeys(fields)

        try:
            result.update(
                connector
                .get_connectivity_service_status(self.wim_internal_id))
        except WimConnectorError as ex:
            self.logger.exception(ex)
            result.update(wim_status='WIM_ERROR', error_msg=truncate(ex))

        result = filter_keys(result, fields)

        action_changes = remove_none_items({
            'extra': merge_dicts(self.extra, result),
            'status': 'BUILD' if result['wim_status'] == 'BUILD' else None,
            'error_msg': result['error_msg'],
            'modified_at': time()})
        link_changes = merge_dicts(result, status=result.pop('wim_status'))
        # ^  Rename field: wim_status => status

        persistence.update_wan_link(self.item_id,
                                    remove_none_items(link_changes))

        self.save(persistence, **action_changes)

        return result


class WanLinkCreate(RefreshMixin, CreateAction):
    def fail(self, persistence, reason, status='FAILED'):
        changes = {'status': 'ERROR', 'error_msg': truncate(reason)}
        persistence.update_wan_link(self.item_id, changes)
        return super(WanLinkCreate, self).fail(persistence, reason, status)

    def process(self, connector, persistence, ovim):
        """Process the current task.
        First we check if all the dependencies are ready,
        then we call ``execute`` to actually execute the action.

        Arguments:
            connector: object with API for accessing the WAN
                Infrastructure Manager system
            persistence: abstraction layer for the database
            ovim: instance of openvim, abstraction layer that enable
                SDN-related operations
        """
        wan_link = persistence.get_by_uuid('instance_wim_nets', self.item_id)

        # First we check if all the dependencies are solved
        instance_nets = persistence.get_instance_nets(
            wan_link['instance_scenario_id'], wan_link['sce_net_id'])

        try:
            dependency_statuses = [n['status'] for n in instance_nets]
        except KeyError:
            self.logger.debug('`status` not found in\n\n%s\n\n',
                              json.dumps(instance_nets, indent=4))
        errored = [instance_nets[i]
                   for i, status in enumerate(dependency_statuses)
                   if status in INSTANCE_NET_STATUS_ERROR]
        if errored:
            return self.fail(
                persistence,
                'Impossible to stablish WAN connectivity due to an issue '
                'with the local networks:\n\t' +
                '\n\t'.join('{uuid}: {status}'.format(**n) for n in errored))

        pending = [instance_nets[i]
                   for i, status in enumerate(dependency_statuses)
                   if status in INSTANCE_NET_STATUS_PENDING]
        if pending:
            return self.defer(
                persistence,
                'Still waiting for the local networks to be active:\n\t' +
                '\n\t'.join('{uuid}: {status}'.format(**n) for n in pending))

        return self.execute(connector, persistence, ovim, instance_nets)

    def _get_connection_point_info(self, persistence, ovim, instance_net):
        """Retrieve information about the connection PoP <> WAN

        Arguments:
            persistence: object that encapsulates persistence logic
                (e.g. db connection)
            ovim: object that encapsulates network management logic (openvim)
            instance_net: record with the information about a local network
                (inside a VIM). This network will be connected via a WAN link
                to a different network in a distinct VIM.
                This method is used to trace what would be the way this network
                can be accessed from the outside world.

        Returns:
            dict: Record representing the wan_port_mapping associated to the
                  given instance_net. The expected fields are:
                  **wim_id**, **datacenter_id**, **pop_switch_dpid** (the local
                  network is expected to be connected at this switch),
                  **pop_switch_port**, **wan_service_endpoint_id**,
                  **wan_service_mapping_info**.
        """
        # First, we need to find a route from the datacenter to the outside
        # world. For that, we can use the rules given in the datacenter
        # configuration:
        datacenter_id = instance_net['datacenter_id']
        datacenter = persistence.get_datacenter_by(datacenter_id)
        rules = safe_get(datacenter, 'config.external_connections', {}) or {}
        vim_info = instance_net.get('vim_info', {}) or {}
        # Alternatively, we can look for it, using the SDN assist
        external_port = (self._evaluate_rules(rules, vim_info) or
                         self._get_port_sdn(ovim, instance_net))

        if not external_port:
            raise NoExternalPortFound(instance_net)

        # Then, we find the WAN switch that is connected to this external port
        try:
            wim_account = persistence.get_wim_account_by(
                uuid=self.wim_account_id)

            criteria = {
                'wim_id': wim_account['wim_id'],
                'pop_switch_dpid': external_port[0],
                'pop_switch_port': external_port[1],
                'datacenter_id': datacenter_id}

            wan_port_mapping = persistence.query_one(
                FROM='wim_port_mappings',
                WHERE=criteria)
        except NoRecordFound:
            ex = InconsistentState('No WIM port mapping found:'
                                   'wim_account: {}\ncriteria:\n{}'.format(
                                       self.wim_account_id, pformat(criteria)))
            reraise(ex.__class__, ex, exc_info()[2])

        # It is important to return encapsulation information if present
        mapping = merge_dicts(
            wan_port_mapping.get('wan_service_mapping_info'),
            filter_keys(vim_info, ('encapsulation_type', 'encapsulation_id'))
        )

        return merge_dicts(wan_port_mapping, wan_service_mapping_info=mapping)

    def _get_port_sdn(self, ovim, instance_net):
        criteria = {'net_id': instance_net['sdn_net_id']}
        try:
            local_port_mapping = ovim.get_ports(filter=criteria)

            if local_port_mapping:
                return (local_port_mapping[0]['switch_dpid'],
                        local_port_mapping[0]['switch_port'])
        except:  # noqa
            self.logger.exception('Problems when calling OpenVIM')

        self.logger.debug('No ports found using criteria:\n%r\n.', criteria)
        return None

    def _evaluate_rules(self, rules, vim_info):
        """Given a ``vim_info`` dict from a ``instance_net`` record, evaluate
        the set of rules provided during the VIM/datacenter registration to
        determine an external port used to connect that VIM/datacenter to
        other ones where different parts of the NS will be instantiated.

        For example, considering a VIM/datacenter is registered like the
        following::

            vim_record = {
              "uuid": ...
              ...  # Other properties associated with the VIM/datacenter
              "config": {
                ...  # Other configuration
                "external_connections": [
                  {
                    "condition": {
                      "provider:physical_network": "provider_net1",
                      ...  # This method will look up all the keys listed here
                           # in the instance_nets.vim_info dict and compare the
                           # values. When all the values match, the associated
                           # vim_external_port will be selected.
                    },
                    "vim_external_port": {"switch": "switchA", "port": "portB"}
                  },
                  ...  # The user can provide as many rules as needed, however
                       # only the first one to match will be applied.
                ]
              }
            }

        When an ``instance_net`` record is instantiated in that datacenter with
        the following information::

            instance_net = {
              "uuid": ...
              ...
              "vim_info": {
                ...
                "provider_physical_network": "provider_net1",
              }
            }

        Then, ``switchA`` and ``portB`` will be used to stablish the WAN
        connection.

        Arguments:
            rules (list): Set of dicts containing the keys ``condition`` and
                ``vim_external_port``. This list should be extracted from
                ``vim['config']['external_connections']`` (as stored in the
                database).
            vim_info (dict): Information given by the VIM Connector, against
               which the rules will be evaluated.

        Returns:
            tuple: switch id (local datacenter switch) and port or None if
                the rule does not match.
        """
        rule = next((r for r in rules if self._evaluate_rule(r, vim_info)), {})
        if 'vim_external_port' not in rule:
            self.logger.debug('No external port found.\n'
                              'rules:\n%r\nvim_info:\n%r\n\n', rules, vim_info)
            return None

        return (rule['vim_external_port']['switch'],
                rule['vim_external_port']['port'])

    @staticmethod
    def _evaluate_rule(rule, vim_info):
        """Evaluate the conditions from a single rule to ``vim_info`` and
        determine if the rule should be applicable or not.

        Please check :obj:`~._evaluate_rules` for more information.

        Arguments:
            rule (dict): Data structure containing the keys ``condition`` and
                ``vim_external_port``. This should be one of the elements in
                ``vim['config']['external_connections']`` (as stored in the
                database).
            vim_info (dict): Information given by the VIM Connector, against
               which the rules will be evaluated.

        Returns:
            True or False: If all the conditions are met.
        """
        condition = rule.get('condition', {}) or {}
        return all(safe_get(vim_info, k) == v for k, v in condition.items())

    @staticmethod
    def _derive_connection_point(wan_info):
        point = {'service_endpoint_id': wan_info['wan_service_endpoint_id']}
        # TODO: Cover other scenarios, e.g. VXLAN.
        details = wan_info.get('wan_service_mapping_info', {})
        if details.get('encapsulation_type') == 'vlan':
            point['service_endpoint_encapsulation_type'] = 'dot1q'
            point['service_endpoint_encapsulation_info'] = {
                'vlan': details['encapsulation_id']
            }
        else:
            point['service_endpoint_encapsulation_type'] = 'none'
        return point

    @staticmethod
    def _derive_service_type(connection_points):
        # TODO: add multipoint and L3 connectivity.
        if len(connection_points) == 2:
            return 'ELINE'
        else:
            raise NotImplementedError('Multipoint connectivity is not '
                                      'supported yet.')

    def _update_persistent_data(self, persistence, service_uuid, conn_info):
        """Store plugin/connector specific information in the database"""
        persistence.update_wan_link(self.item_id, {
            'wim_internal_id': service_uuid,
            'wim_info': {'conn_info': conn_info},
            'status': 'BUILD'})

    def execute(self, connector, persistence, ovim, instance_nets):
        """Actually execute the action, since now we are sure all the
        dependencies are solved
        """
        try:
            wan_info = (self._get_connection_point_info(persistence, ovim, net)
                        for net in instance_nets)
            connection_points = [self._derive_connection_point(w)
                                 for w in wan_info]

            uuid, info = connector.create_connectivity_service(
                self._derive_service_type(connection_points),
                connection_points
                # TODO: other properties, e.g. bandwidth
            )
        except (WimConnectorError, InconsistentState,
                NoExternalPortFound) as ex:
            self.logger.exception(ex)
            return self.fail(
                persistence,
                'Impossible to stablish WAN connectivity.\n\t{}'.format(ex))

        self.logger.debug('WAN connectivity established %s\n%s\n',
                          uuid, json.dumps(info, indent=4))
        self.wim_internal_id = uuid
        self._update_persistent_data(persistence, uuid, info)
        self.succeed(persistence)
        return uuid


class WanLinkDelete(DeleteAction):
    def succeed(self, persistence):
        try:
            persistence.update_wan_link(self.item_id, {'status': 'DELETED'})
        except NoRecordFound:
            self.logger.debug('%s(%s) record already deleted',
                              self.item, self.item_id)

        return super(WanLinkDelete, self).succeed(persistence)

    def get_wan_link(self, persistence):
        """Retrieve information about the wan_link

        It might be cached, or arrive from the database
        """
        if self.extra.get('wan_link'):
            # First try a cached version of the data
            return self.extra['wan_link']

        return persistence.get_by_uuid(
            'instance_wim_nets', self.item_id)

    def process(self, connector, persistence, ovim):
        """Delete a WAN link previously created"""
        wan_link = self.get_wan_link(persistence)
        if 'ERROR' in (wan_link.get('status') or ''):
            return self.fail(
                persistence,
                'Impossible to delete WAN connectivity, '
                'it was never successfully established:'
                '\n\t{}'.format(wan_link['error_msg']))

        internal_id = wan_link.get('wim_internal_id') or self.internal_id

        if not internal_id:
            self.logger.debug('No wim_internal_id found in\n%s\n%s\n'
                              'Assuming no network was created yet, '
                              'so no network have to be deleted.',
                              json.dumps(wan_link, indent=4),
                              json.dumps(self.as_dict(), indent=4))
            return self.succeed(persistence)

        try:
            id = self.wim_internal_id
            conn_info = safe_get(wan_link, 'wim_info.conn_info')
            self.logger.debug('Connection Service %s (wan_link: %s):\n%s\n',
                              id, wan_link['uuid'],
                              json.dumps(conn_info, indent=4))
            result = connector.delete_connectivity_service(id, conn_info)
        except (WimConnectorError, InconsistentState) as ex:
            self.logger.exception(ex)
            return self.fail(
                persistence,
                'Impossible to delete WAN connectivity.\n\t{}'.format(ex))

        self.logger.debug('WAN connectivity removed %s', result)
        self.succeed(persistence)

        return result


class WanLinkFind(RefreshMixin, FindAction):
    pass


ACTIONS = {
    'CREATE': WanLinkCreate,
    'DELETE': WanLinkDelete,
    'FIND': WanLinkFind,
}
