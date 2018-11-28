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
from time import time

from ..utils import filter_dict_keys as filter_keys
from ..utils import merge_dicts, remove_none_items, safe_get, truncate
from .actions import CreateAction, DeleteAction, FindAction
from .errors import (
    InconsistentState,
    MultipleRecordsFound,
    NoRecordFound,
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
                  **wim_id**, **datacenter_id**, **pop_switch_id** (the local
                  network is expected to be connected at this switch),
                  **pop_switch_port**, **wan_service_endpoint_id**,
                  **wan_service_mapping_info**.
        """
        wim_account = persistence.get_wim_account_by(uuid=self.wim_account_id)

        # TODO: make more generic to support networks that are not created with
        # the SDN assist. This method should have a consistent way of getting
        # the endpoint for all different types of networks used in the VIM
        # (provider networks, SDN assist, overlay networks, ...)
        if instance_net.get('sdn_net_id'):
            return self._get_connection_point_info_sdn(
                persistence, ovim, instance_net, wim_account['wim_id'])
        else:
            raise InconsistentState(
                'The field `instance_nets.sdn_net_id` was expected to be '
                'found in the database for the record %s after the network '
                'become active, but it is still NULL', instance_net['uuid'])

    def _get_connection_point_info_sdn(self, persistence, ovim,
                                       instance_net, wim_id):
        criteria = {'net_id': instance_net['sdn_net_id']}
        local_port_mapping = ovim.get_ports(filter=criteria)

        if len(local_port_mapping) > 1:
            raise MultipleRecordsFound(criteria, 'ovim.ports')
        local_port_mapping = local_port_mapping[0]

        criteria = {
            'wim_id': wim_id,
            'pop_switch_dpid': local_port_mapping['switch_dpid'],
            'pop_switch_port': local_port_mapping['switch_port'],
            'datacenter_id': instance_net['datacenter_id']}

        wan_port_mapping = persistence.query_one(
            FROM='wim_port_mappings',
            WHERE=criteria)

        if local_port_mapping.get('vlan'):
            wan_port_mapping['wan_service_mapping_info']['vlan'] = (
                local_port_mapping['vlan'])

        return wan_port_mapping

    @staticmethod
    def _derive_connection_point(wan_info):
        point = {'service_endpoint_id': wan_info['wan_service_endpoint_id']}
        # TODO: Cover other scenarios, e.g. VXLAN.
        details = wan_info.get('wan_service_mapping_info', {})
        if 'vlan' in details:
            point['service_endpoint_encapsulation_type'] = 'dot1q'
            point['service_endpoint_encapsulation_info'] = {
                'vlan': details['vlan']
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
        except (WimConnectorError, InconsistentState) as ex:
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
