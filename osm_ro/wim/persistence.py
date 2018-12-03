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

"""This module contains only logic related to managing records in a database
which includes data format normalization, data format validation and etc.
(It works as an extension to `nfvo_db.py` for the WIM feature)

No domain logic/architectural concern should be present in this file.
"""
import json
import logging
from contextlib import contextmanager
from hashlib import sha1
from itertools import groupby
from operator import itemgetter
from sys import exc_info
from threading import Lock
from time import time
from uuid import uuid1 as generate_uuid

from six import reraise

import yaml

from ..utils import (
    check_valid_uuid,
    convert_float_timestamp2str,
    expand_joined_fields,
    filter_dict_keys,
    filter_out_dict_keys,
    merge_dicts,
    remove_none_items
)
from .errors import (
    DbBaseException,
    InvalidParameters,
    MultipleRecordsFound,
    NoRecordFound,
    UndefinedUuidOrName,
    UndefinedWanMappingType,
    UnexpectedDatabaseError,
    WimAccountOverwrite,
    WimAndTenantAlreadyAttached
)

_WIM = 'wims AS wim '

_WIM_JOIN = (
    _WIM +
    ' JOIN wim_nfvo_tenants AS association '
    '   ON association.wim_id=wim.uuid '
    ' JOIN nfvo_tenants AS nfvo_tenant '
    '   ON association.nfvo_tenant_id=nfvo_tenant.uuid '
    ' JOIN wim_accounts AS wim_account '
    '   ON association.wim_account_id=wim_account.uuid '
)

_WIM_ACCOUNT_JOIN = (
    'wim_accounts AS wim_account '
    ' JOIN wim_nfvo_tenants AS association '
    '   ON association.wim_account_id=wim_account.uuid '
    ' JOIN wims AS wim '
    '   ON association.wim_id=wim.uuid '
    ' JOIN nfvo_tenants AS nfvo_tenant '
    '   ON association.nfvo_tenant_id=nfvo_tenant.uuid '
)

_DATACENTER_JOIN = (
    'datacenters AS datacenter '
    ' JOIN tenants_datacenters AS association '
    '   ON association.datacenter_id=datacenter.uuid '
    ' JOIN datacenter_tenants as datacenter_account '
    '   ON association.datacenter_tenant_id=datacenter_account.uuid '
    ' JOIN nfvo_tenants AS nfvo_tenant '
    '   ON association.nfvo_tenant_id=nfvo_tenant.uuid '
)

_PORT_MAPPING = 'wim_port_mappings as wim_port_mapping '

_PORT_MAPPING_JOIN_WIM = (
    ' JOIN wims as wim '
    '   ON wim_port_mapping.wim_id=wim.uuid '
)

_PORT_MAPPING_JOIN_DATACENTER = (
    ' JOIN datacenters as datacenter '
    '   ON wim_port_mapping.datacenter_id=datacenter.uuid '
)

_WIM_SELECT = [
    'wim.{0} as {0}'.format(_field)
    for _field in 'uuid name description wim_url type config '
                  'created_at modified_at'.split()
]

_WIM_ACCOUNT_SELECT = 'uuid name user password config'.split()

_PORT_MAPPING_SELECT = ('wim_port_mapping.*', )

_CONFIDENTIAL_FIELDS = ('password', 'passwd')

_SERIALIZED_FIELDS = ('config', 'vim_info', 'wim_info', 'conn_info', 'extra',
                      'wan_service_mapping_info')

UNIQUE_PORT_MAPPING_INFO_FIELDS = {
    'dpid-port': ('wan_switch_dpid', 'wan_switch_port')
}
"""Fields that should be unique for each port mapping that relies on
wan_service_mapping_info.

For example, for port mappings of type 'dpid-port', each combination of
wan_switch_dpid and wan_switch_port should be unique (the same switch cannot
be connected to two different places using the same port)
"""


class WimPersistence(object):
    """High level interactions with the WIM tables in the database"""

    def __init__(self, db, logger=None, lock=None):
        self.db = db
        self.logger = logger or logging.getLogger('openmano.wim.persistence')
        self.lock = lock or Lock()

    def query(self,
              FROM=None,
              SELECT=None,
              WHERE=None,
              ORDER_BY=None,
              LIMIT=None,
              OFFSET=None,
              error_if_none=True,
              error_if_multiple=False,
              postprocess=None,
              hide=_CONFIDENTIAL_FIELDS,
              **kwargs):
        """Retrieve records from the database.

        Keyword Arguments:
            SELECT, FROM, WHERE, LIMIT, ORDER_BY: used to compose the SQL
                query. See ``nfvo_db.get_rows``.
            OFFSET: only valid when used togheter with LIMIT.
                    Ignore the OFFSET first results of the query.
            error_if_none: by default an error is raised if no record is
                found. With this option it is possible to disable this error.
            error_if_multiple: by default no error is raised if more then one
                record is found.
                With this option it is possible to enable this error.
            postprocess: function applied to every retrieved record.
                This function receives a dict as input and must return it
                after modifications. Moreover this function should accept a
                second optional parameter ``hide`` indicating
                the confidential fiels to be obfuscated.
                By default a minimal postprocessing function is applied,
                obfuscating confidential fields and converting timestamps.
            hide: option proxied to postprocess

        All the remaining keyword arguments will be assumed to be ``name``s or
        ``uuid``s to compose the WHERE statement, according to their format.
        If the value corresponds to an array, the first element will determine
        if it is an name or UUID.

        For example:
            - ``wim="abcdef"``` will be turned into ``wim.name="abcdef"``,
            - ``datacenter="5286a274-8a1b-4b8d-a667-9c94261ad855"``
               will be turned into
               ``datacenter.uuid="5286a274-8a1b-4b8d-a667-9c94261ad855"``.
            - ``wim=["5286a274-8a1b-4b8d-a667-9c94261ad855", ...]``
               will be turned into
               ``wim.uuid=["5286a274-8a1b-4b8d-a667-9c94261ad855", ...]``

        Raises:
            NoRecordFound: if the query result set is empty
            DbBaseException: errors occuring during the execution of the query.
        """
        # Defaults:
        postprocess = postprocess or _postprocess_record
        WHERE = WHERE or {}

        # Find remaining keywords by name or uuid
        WHERE.update(_compose_where_from_uuids_or_names(**kwargs))
        WHERE = WHERE or None
        # ^ If the where statement is empty, it is better to leave it as None,
        #   so it can be filtered out at a later stage
        LIMIT = ('{:d},{:d}'.format(OFFSET, LIMIT)
                 if LIMIT and OFFSET else LIMIT)

        query = remove_none_items({
            'SELECT': SELECT, 'FROM': FROM, 'WHERE': WHERE,
            'LIMIT': LIMIT, 'ORDER_BY': ORDER_BY})

        with self.lock:
            records = self.db.get_rows(**query)

        table = FROM.split()[0]
        if error_if_none and not records:
            raise NoRecordFound(WHERE, table)

        if error_if_multiple and len(records) > 1:
            self.logger.error('Multiple records '
                              'FROM %s WHERE %s:\n\n%s\n\n',
                              FROM, WHERE, json.dumps(records, indent=4))
            raise MultipleRecordsFound(WHERE, table)

        return [
            expand_joined_fields(postprocess(record, hide))
            for record in records
        ]

    def query_one(self, *args, **kwargs):
        """Similar to ``query``, but ensuring just one result.
        ``error_if_multiple`` is enabled by default.
        """
        kwargs.setdefault('error_if_multiple', True)
        records = self.query(*args, **kwargs)
        return records[0] if records else None

    def get_by_uuid(self, table, uuid, **kwargs):
        """Retrieve one record from the database based on its uuid

        Arguments:
            table (str): table name (to be used in SQL's FROM statement).
            uuid (str): unique identifier for record.

        For additional keyword arguments and exceptions see :obj:`~.query`
        (``error_if_multiple`` is enabled by default).
        """
        if uuid is None:
            raise UndefinedUuidOrName(table)
        return self.query_one(table, WHERE={'uuid': uuid}, **kwargs)

    def get_by_name_or_uuid(self, table, uuid_or_name, **kwargs):
        """Retrieve a record from the database based on a value that can be its
        uuid or name.

        Arguments:
            table (str): table name (to be used in SQL's FROM statement).
            uuid_or_name (str): this value can correspond to either uuid or
                name
        For additional keyword arguments and exceptions see :obj:`~.query`
        (``error_if_multiple`` is enabled by default).
        """
        if uuid_or_name is None:
            raise UndefinedUuidOrName(table)

        key = 'uuid' if check_valid_uuid(uuid_or_name) else 'name'
        return self.query_one(table, WHERE={key: uuid_or_name}, **kwargs)

    def get_wims(self, uuid_or_name=None, tenant=None, **kwargs):
        """Retrieve information about one or more WIMs stored in the database

        Arguments:
            uuid_or_name (str): uuid or name for WIM
            tenant (str): [optional] uuid or name for NFVO tenant

        See :obj:`~.query` for additional keyword arguments.
        """
        kwargs.update(wim=uuid_or_name, tenant=tenant)
        from_ = _WIM_JOIN if tenant else _WIM
        select_ = _WIM_SELECT[:] + (['wim_account.*'] if tenant else [])

        kwargs.setdefault('SELECT', select_)
        return self.query(from_, **kwargs)

    def get_wim(self, wim, tenant=None, **kwargs):
        """Similar to ``get_wims`` but ensure only one result is returned"""
        kwargs.setdefault('error_if_multiple', True)
        return self.get_wims(wim, tenant)[0]

    def create_wim(self, wim_descriptor):
        """Create a new wim record inside the database and returns its uuid

        Arguments:
            wim_descriptor (dict): properties of the record
                (usually each field corresponds to a database column, but extra
                information can be offloaded to another table or serialized as
                JSON/YAML)
        Returns:
            str: UUID of the created WIM
        """
        if "config" in wim_descriptor:
            wim_descriptor["config"] = _serialize(wim_descriptor["config"])

        with self.lock:
            return self.db.new_row(
                "wims", wim_descriptor, add_uuid=True, confidential_data=True)

    def update_wim(self, uuid_or_name, wim_descriptor):
        """Change an existing WIM record on the database"""
        # obtain data, check that only one exist
        wim = self.get_by_name_or_uuid('wims', uuid_or_name)

        # edit data
        wim_id = wim['uuid']
        where = {'uuid': wim['uuid']}

        # unserialize config, edit and serialize it again
        if wim_descriptor.get('config'):
            new_config_dict = wim_descriptor["config"]
            config_dict = remove_none_items(merge_dicts(
                wim.get('config') or {}, new_config_dict))
            wim_descriptor['config'] = (
                _serialize(config_dict) if config_dict else None)

        with self.lock:
            self.db.update_rows('wims', wim_descriptor, where)

        return wim_id

    def delete_wim(self, wim):
        # get nfvo_tenant info
        wim = self.get_by_name_or_uuid('wims', wim)

        with self.lock:
            self.db.delete_row_by_id('wims', wim['uuid'])

        return wim['uuid'] + ' ' + wim['name']

    def get_wim_accounts_by(self, wim=None, tenant=None, uuid=None, **kwargs):
        """Retrieve WIM account information from the database together
        with the related records (wim, nfvo_tenant and wim_nfvo_tenant)

        Arguments:
            wim (str): uuid or name for WIM
            tenant (str): [optional] uuid or name for NFVO tenant

        See :obj:`~.query` for additional keyword arguments.
        """
        kwargs.update(wim=wim, tenant=tenant)
        kwargs.setdefault('postprocess', _postprocess_wim_account)
        if uuid:
            kwargs.setdefault('WHERE', {'wim_account.uuid': uuid})
        return self.query(FROM=_WIM_ACCOUNT_JOIN, **kwargs)

    def get_wim_account_by(self, wim=None, tenant=None, **kwargs):
        """Similar to ``get_wim_accounts_by``, but ensuring just one result"""
        kwargs.setdefault('error_if_multiple', True)
        return self.get_wim_accounts_by(wim, tenant, **kwargs)[0]

    def get_wim_accounts(self, **kwargs):
        """Retrieve all the accounts from the database"""
        kwargs.setdefault('postprocess', _postprocess_wim_account)
        return self.query(FROM=_WIM_ACCOUNT_JOIN, **kwargs)

    def get_wim_account(self, uuid_or_name, **kwargs):
        """Retrieve WIM Account record by UUID or name,
        See :obj:`get_by_name_or_uuid` for keyword arguments.
        """
        kwargs.setdefault('postprocess', _postprocess_wim_account)
        kwargs.setdefault('SELECT', _WIM_ACCOUNT_SELECT)
        return self.get_by_name_or_uuid('wim_accounts', uuid_or_name, **kwargs)

    @contextmanager
    def _associate(self, wim_id, nfvo_tenant_id):
        """Auxiliary method for ``create_wim_account``

        This method just create a row in the association table
        ``wim_nfvo_tenants``
        """
        try:
            with self.lock:
                yield
        except DbBaseException as db_exception:
            error_msg = str(db_exception)
            if all([msg in error_msg
                    for msg in ("already in use", "'wim_nfvo_tenant'")]):
                ex = WimAndTenantAlreadyAttached(wim_id, nfvo_tenant_id)
                reraise(ex.__class__, ex, exc_info()[2])

            raise

    def create_wim_account(self, wim, tenant, properties):
        """Associate a wim to a tenant using the ``wim_nfvo_tenants`` table
        and create a ``wim_account`` to store credentials and configurations.

        For the sake of simplification, we assume that each NFVO tenant can be
        attached to a WIM using only one WIM account. This is automatically
        guaranteed via database constraints.
        For corner cases, the same WIM can be registered twice using another
        name.

        Arguments:
            wim (str): name or uuid of the WIM related to the account being
                created
            tenant (str): name or uuid of the nfvo tenant to which the account
                will be created
            properties (dict): properties of the account
                (eg. user, password, ...)
        """
        wim_id = self.get_by_name_or_uuid('wims', wim, SELECT=['uuid'])['uuid']
        tenant = self.get_by_name_or_uuid('nfvo_tenants', tenant,
                                          SELECT=['uuid', 'name'])
        account = properties.setdefault('name', tenant['name'])

        wim_account = self.query_one('wim_accounts',
                                     WHERE={'wim_id': wim_id, 'name': account},
                                     error_if_none=False)

        transaction = []
        used_uuids = []

        if wim_account is None:
            # If a row for the wim account doesn't exist yet, we need to
            # create one, otherwise we can just re-use it.
            account_id = str(generate_uuid())
            used_uuids.append(account_id)
            row = merge_dicts(properties, wim_id=wim_id, uuid=account_id)
            transaction.append({'wim_accounts': _preprocess_wim_account(row)})
        else:
            account_id = wim_account['uuid']
            properties.pop('config', None)  # Config is too complex to compare
            diff = {k: v for k, v in properties.items() if v != wim_account[k]}
            if diff:
                tip = 'Edit the account first, and then attach it to a tenant'
                raise WimAccountOverwrite(wim_account, diff, tip)

        transaction.append({
            'wim_nfvo_tenants': {'nfvo_tenant_id': tenant['uuid'],
                                 'wim_id': wim_id,
                                 'wim_account_id': account_id}})

        with self._associate(wim_id, tenant['uuid']):
            self.db.new_rows(transaction, used_uuids, confidential_data=True)

        return account_id

    def update_wim_account(self, uuid, properties, hide=_CONFIDENTIAL_FIELDS):
        """Update WIM account record by overwriting fields with new values

        Specially for the field ``config`` this means that a new dict will be
        merged to the existing one.

        Attributes:
            uuid (str): UUID for the WIM account
            properties (dict): fields that should be overwritten

        Returns:
            Updated wim_account
        """
        wim_account = self.get_by_uuid('wim_accounts', uuid)
        safe_fields = 'user password name created'.split()
        updates = _preprocess_wim_account(
            merge_dicts(wim_account, filter_dict_keys(properties, safe_fields))
        )

        if properties.get('config'):
            old_config = wim_account.get('config') or {}
            new_config = merge_dicts(old_config, properties['config'])
            updates['config'] = _serialize(new_config)

        with self.lock:
            num_changes = self.db.update_rows(
                'wim_accounts', UPDATE=updates,
                WHERE={'uuid': wim_account['uuid']})

        if num_changes is None:
            raise UnexpectedDatabaseError('Impossible to update wim_account '
                                          '{name}:{uuid}'.format(*wim_account))

        return self.get_wim_account(wim_account['uuid'], hide=hide)

    def delete_wim_account(self, uuid):
        """Remove WIM account record from the database"""
        # Since we have foreign keys configured with ON CASCADE, we can rely
        # on the database engine to guarantee consistency, deleting the
        # dependant records
        with self.lock:
            return self.db.delete_row_by_id('wim_accounts', uuid)

    def get_datacenters_by(self, datacenter=None, tenant=None, **kwargs):
        """Retrieve datacenter information from the database together
        with the related records (nfvo_tenant)

        Arguments:
            datacenter (str): uuid or name for datacenter
            tenant (str): [optional] uuid or name for NFVO tenant

        See :obj:`~.query` for additional keyword arguments.
        """
        kwargs.update(datacenter=datacenter, tenant=tenant)
        return self.query(_DATACENTER_JOIN, **kwargs)

    def get_datacenter_by(self, datacenter=None, tenant=None, **kwargs):
        """Similar to ``get_datacenters_by``, but ensuring just one result"""
        kwargs.setdefault('error_if_multiple', True)
        return self.get_datacenters_by(datacenter, tenant, **kwargs)[0]

    def _create_single_port_mapping(self, properties):
        info = properties.setdefault('wan_service_mapping_info', {})
        endpoint_id = properties.get('wan_service_endpoint_id')

        if info.get('mapping_type') and not endpoint_id:
            properties['wan_service_endpoint_id'] = (
                self._generate_port_mapping_id(info))

        properties['wan_service_mapping_info'] = _serialize(info)

        try:
            with self.lock:
                self.db.new_row('wim_port_mappings', properties,
                                add_uuid=False, confidential_data=True)
        except DbBaseException as old_exception:
            self.logger.exception(old_exception)
            ex = InvalidParameters(
                "The mapping must contain the "
                "'pop_switch_dpid', 'pop_switch_port',  and "
                "wan_service_mapping_info: "
                "('wan_switch_dpid' and 'wan_switch_port') or "
                "'wan_service_endpoint_id}'")
            reraise(ex.__class__, ex, exc_info()[2])

        return properties

    def create_wim_port_mappings(self, wim, port_mappings, tenant=None):
        if not isinstance(wim, dict):
            wim = self.get_by_name_or_uuid('wims', wim)

        for port_mapping in port_mappings:
            port_mapping['wim_name'] = wim['name']
            datacenter = self.get_datacenter_by(
                port_mapping['datacenter_name'], tenant)
            for pop_wan_port_mapping in port_mapping['pop_wan_mappings']:
                element = merge_dicts(pop_wan_port_mapping, {
                    'wim_id': wim['uuid'],
                    'datacenter_id': datacenter['uuid']})
                self._create_single_port_mapping(element)

        return port_mappings

    def _filter_port_mappings_by_tenant(self, mappings, tenant):
        """Make sure all the datacenters and wims listed in the port mapping
        belong to an specific tenant
        """

        # NOTE: Theoretically this could be done at SQL level, but given the
        #       number of tables involved (wim_port_mappings, wim_accounts,
        #       wims, wim_nfvo_tenants, datacenters, datacenter_tenants,
        #       tenants_datacents and nfvo_tenants), it would result in a
        #       extremely complex query. Moreover, the predicate can vary:
        #       for `get_wim_port_mappings` we can have any combination of
        #       (wim, datacenter, tenant), not all of them having the 3 values
        #       so we have combinatorial trouble to write the 'FROM' statement.

        kwargs = {'tenant': tenant, 'error_if_none': False}
        # Cache results to speedup things
        datacenters = {}
        wims = {}

        def _get_datacenter(uuid):
            return (
                datacenters.get(uuid) or
                datacenters.setdefault(
                    uuid, self.get_datacenters_by(uuid, **kwargs)))

        def _get_wims(uuid):
            return (wims.get(uuid) or
                    wims.setdefault(uuid, self.get_wims(uuid, **kwargs)))

        return [
            mapping
            for mapping in mappings
            if (_get_datacenter(mapping['datacenter_id']) and
                _get_wims(mapping['wim_id']))
        ]

    def get_wim_port_mappings(self, wim=None, datacenter=None, tenant=None,
                              **kwargs):
        """List all the port mappings, optionally filtering by wim, datacenter
        AND/OR tenant
        """
        from_ = [_PORT_MAPPING,
                 _PORT_MAPPING_JOIN_WIM if wim else '',
                 _PORT_MAPPING_JOIN_DATACENTER if datacenter else '']

        criteria = ('wim_id', 'datacenter_id')
        kwargs.setdefault('error_if_none', False)
        mappings = self.query(
            ' '.join(from_),
            SELECT=_PORT_MAPPING_SELECT,
            ORDER_BY=['wim_port_mapping.{}'.format(c) for c in criteria],
            wim=wim, datacenter=datacenter,
            postprocess=_postprocess_wim_port_mapping,
            **kwargs)

        if tenant:
            mappings = self._filter_port_mappings_by_tenant(mappings, tenant)

        # We don't have to sort, since we have used 'ORDER_BY'
        grouped_mappings = groupby(mappings, key=itemgetter(*criteria))

        return [
            {'wim_id': key[0],
             'datacenter_id': key[1],
             'wan_pop_port_mappings': [
                 filter_out_dict_keys(mapping, (
                     'id', 'wim_id', 'datacenter_id',
                     'created_at', 'modified_at'))
                 for mapping in group]}
            for key, group in grouped_mappings
        ]

    def delete_wim_port_mappings(self, wim_id):
        with self.lock:
            self.db.delete_row(FROM='wim_port_mappings',
                               WHERE={"wim_id": wim_id})
        return "port mapping for wim {} deleted.".format(wim_id)

    def update_wim_port_mapping(self, id, properties):
        original = self.query_one('wim_port_mappings', WHERE={'id': id})

        mapping_info = remove_none_items(merge_dicts(
            original.get('wan_service_mapping_info') or {},
            properties.get('wan_service_mapping_info') or {}))

        updates = preprocess_record(
            merge_dicts(original, remove_none_items(properties),
                        wan_service_mapping_info=mapping_info))

        with self.lock:
            num_changes = self.db.update_rows(
                'wim_port_mappings', UPDATE=updates, WHERE={'id': id})

        if num_changes is None:
            raise UnexpectedDatabaseError(
                'Impossible to update wim_port_mappings %s:\n%s\n',
                id, _serialize(properties))

        return num_changes

    def get_actions_in_groups(self, wim_account_id,
                              item_types=('instance_wim_nets',),
                              group_offset=0, group_limit=150):
        """Retrieve actions from the database in groups.
        Each group contains all the actions that have the same ``item`` type
        and ``item_id``.

        Arguments:
            wim_account_id: restrict the search to actions to be performed
                using the same account
            item_types (list): [optional] filter the actions to the given
                item types
            group_limit (int): maximum number of groups returned by the
                function
            group_offset (int): skip the N first groups. Used together with
                group_limit for pagination purposes.

        Returns:
            List of groups, where each group is a tuple ``(key, actions)``.
            In turn, ``key`` is a tuple containing the values of
            ``(item, item_id)`` used to create the group and ``actions`` is a
            list of ``vim_wim_actions`` records (dicts).
        """

        type_options = set(
            '"{}"'.format(self.db.escape_string(t)) for t in item_types)

        items = ('SELECT DISTINCT a.item, a.item_id, a.wim_account_id '
                 'FROM vim_wim_actions AS a '
                 'WHERE a.wim_account_id="{}" AND a.item IN ({}) '
                 'ORDER BY a.item, a.item_id '
                 'LIMIT {:d},{:d}').format(
                     self.safe_str(wim_account_id),
                     ','.join(type_options),
                     group_offset, group_limit
                 )

        join = 'vim_wim_actions NATURAL JOIN ({}) AS items'.format(items)
        with self.lock:
            db_results = self.db.get_rows(
                FROM=join, ORDER_BY=('item', 'item_id', 'created_at'))

        results = (_postprocess_action(r) for r in db_results)
        criteria = itemgetter('item', 'item_id')
        return [(k, list(g)) for k, g in groupby(results, key=criteria)]

    def update_action(self, instance_action_id, task_index, properties):
        condition = {'instance_action_id': instance_action_id,
                     'task_index': task_index}
        action = self.query_one('vim_wim_actions', WHERE=condition)

        extra = remove_none_items(merge_dicts(
            action.get('extra') or {},
            properties.get('extra') or {}))

        updates = preprocess_record(
            merge_dicts(action, properties, extra=extra))

        with self.lock:
            num_changes = self.db.update_rows('vim_wim_actions',
                                              UPDATE=updates, WHERE=condition)

        if num_changes is None:
            raise UnexpectedDatabaseError(
                'Impossible to update vim_wim_actions '
                '{instance_action_id}[{task_index}]'.format(*action))

        return num_changes

    def get_wan_links(self, uuid=None, **kwargs):
        """Retrieve WAN link records from the database

        Keyword Arguments:
            uuid, instance_scenario_id, sce_net_id, wim_id, wim_account_id:
                attributes that can be used at the WHERE clause
        """
        kwargs.setdefault('uuid', uuid)
        kwargs.setdefault('error_if_none', False)

        criteria_fields = ('uuid', 'instance_scenario_id', 'sce_net_id',
                           'wim_id', 'wim_account_id')
        criteria = remove_none_items(filter_dict_keys(kwargs, criteria_fields))
        kwargs = filter_out_dict_keys(kwargs, criteria_fields)

        return self.query('instance_wim_nets', WHERE=criteria, **kwargs)

    def update_wan_link(self, uuid, properties):
        wan_link = self.get_by_uuid('instance_wim_nets', uuid)

        wim_info = remove_none_items(merge_dicts(
            wan_link.get('wim_info') or {},
            properties.get('wim_info') or {}))

        updates = preprocess_record(
            merge_dicts(wan_link, properties, wim_info=wim_info))

        self.logger.debug({'UPDATE': updates})
        with self.lock:
            num_changes = self.db.update_rows(
                'instance_wim_nets', UPDATE=updates,
                WHERE={'uuid': wan_link['uuid']})

        if num_changes is None:
            raise UnexpectedDatabaseError(
                'Impossible to update instance_wim_nets ' + wan_link['uuid'])

        return num_changes

    def get_instance_nets(self, instance_scenario_id, sce_net_id, **kwargs):
        """Retrieve all the instance nets related to the same instance_scenario
        and scenario network
        """
        return self.query(
            'instance_nets',
            WHERE={'instance_scenario_id': instance_scenario_id,
                   'sce_net_id': sce_net_id},
            ORDER_BY=kwargs.pop(
                'ORDER_BY', ('instance_scenario_id', 'sce_net_id')),
            **kwargs)

    def update_instance_action_counters(self, uuid, failed=None, done=None):
        """Atomically increment/decrement number_done and number_failed fields
        in the instance action table
        """
        changes = remove_none_items({
            'number_failed': failed and {'INCREMENT': failed},
            'number_done': done and {'INCREMENT': done}
        })

        if not changes:
            return 0

        with self.lock:
            return self.db.update_rows('instance_actions',
                                       WHERE={'uuid': uuid}, UPDATE=changes)

    def get_only_vm_with_external_net(self, instance_net_id, **kwargs):
        """Return an instance VM if that is the only VM connected to an
        external network identified by instance_net_id
        """
        counting = ('SELECT DISTINCT instance_net_id '
                    'FROM instance_interfaces '
                    'WHERE instance_net_id="{}" AND type="external" '
                    'GROUP BY instance_net_id '
                    'HAVING COUNT(*)=1').format(self.safe_str(instance_net_id))

        vm_item = ('SELECT DISTINCT instance_vm_id '
                   'FROM instance_interfaces NATURAL JOIN ({}) AS a'
                   .format(counting))

        return self.query_one(
            'instance_vms JOIN ({}) as instance_interface '
            'ON instance_vms.uuid=instance_interface.instance_vm_id'
            .format(vm_item), **kwargs)

    def safe_str(self, string):
        """Return a SQL safe string"""
        return self.db.escape_string(string)

    def _generate_port_mapping_id(self, mapping_info):
        """Given a port mapping represented by a dict with a 'type' field,
        generate a unique string, in a injective way.
        """
        mapping_info = mapping_info.copy()  # Avoid mutating original object
        mapping_type = mapping_info.pop('mapping_type', None)
        if not mapping_type:
            raise UndefinedWanMappingType(mapping_info)

        unique_fields = UNIQUE_PORT_MAPPING_INFO_FIELDS.get(mapping_type)

        if unique_fields:
            mapping_info = filter_dict_keys(mapping_info, unique_fields)
        else:
            self.logger.warning('Unique fields for WIM port mapping of type '
                                '%s not defined. Please add a list of fields '
                                'which combination should be unique in '
                                'UNIQUE_PORT_MAPPING_INFO_FIELDS '
                                '(`wim/persistency.py) ', mapping_type)

        repeatable_repr = json.dumps(mapping_info, encoding='utf-8',
                                     sort_keys=True, indent=False)

        return ':'.join([mapping_type, _str2id(repeatable_repr)])


def _serialize(value):
    """Serialize an arbitrary value in a consistent way,
    so it can be stored in a database inside a text field
    """
    return yaml.safe_dump(value, default_flow_style=True, width=256)


def _unserialize(text):
    """Unserialize text representation into an arbitrary value,
    so it can be loaded from the database
    """
    return yaml.safe_load(text)


def preprocess_record(record):
    """Small transformations to be applied to the data that cames from the
    user before writing it to the database. By default, filter out timestamps,
    and serialize the ``config`` field.
    """
    automatic_fields = ['created_at', 'modified_at']
    record = serialize_fields(filter_out_dict_keys(record, automatic_fields))

    return record


def _preprocess_wim_account(wim_account):
    """Do the default preprocessing and convert the 'created' field from
    boolean to string
    """
    wim_account = preprocess_record(wim_account)

    created = wim_account.get('created')
    wim_account['created'] = (
        'true' if created is True or created == 'true' else 'false')

    return wim_account


def _postprocess_record(record, hide=_CONFIDENTIAL_FIELDS):
    """By default, hide passwords fields, unserialize ``config`` fields, and
    convert float timestamps to strings
    """
    record = hide_confidential_fields(record, hide)
    record = unserialize_fields(record, hide)

    convert_float_timestamp2str(record)

    return record


def _postprocess_action(action):
    if action.get('extra'):
        action['extra'] = _unserialize(action['extra'])

    return action


def _postprocess_wim_account(wim_account, hide=_CONFIDENTIAL_FIELDS):
    """Do the default postprocessing and convert the 'created' field from
    string to boolean
    """
    # Fix fields from join
    for field in ('type', 'description', 'wim_url'):
        if field in wim_account:
            wim_account['wim.'+field] = wim_account.pop(field)

    for field in ('id', 'nfvo_tenant_id', 'wim_account_id'):
        if field in wim_account:
            wim_account['association.'+field] = wim_account.pop(field)

    wim_account = _postprocess_record(wim_account, hide)

    created = wim_account.get('created')
    wim_account['created'] = (created is True or created == 'true')

    return wim_account


def _postprocess_wim_port_mapping(mapping, hide=_CONFIDENTIAL_FIELDS):
    mapping = _postprocess_record(mapping, hide=hide)
    mapping_info = mapping.get('wan_service_mapping_info', None) or {}
    mapping['wan_service_mapping_info'] = mapping_info
    return mapping


def hide_confidential_fields(record, fields=_CONFIDENTIAL_FIELDS):
    """Obfuscate confidential fields from the input dict.

    Note:
        This function performs a SHALLOW operation.
    """
    if not(isinstance(record, dict) and fields):
        return record

    keys = record.iterkeys()
    keys = (k for k in keys for f in fields if k == f or k.endswith('.'+f))

    return merge_dicts(record, {k: '********' for k in keys if record[k]})


def unserialize_fields(record, hide=_CONFIDENTIAL_FIELDS,
                       fields=_SERIALIZED_FIELDS):
    """Unserialize fields that where stored in the database as a serialized
    YAML (or JSON)
    """
    keys = record.iterkeys()
    keys = (k for k in keys for f in fields if k == f or k.endswith('.'+f))

    return merge_dicts(record, {
        key: hide_confidential_fields(_unserialize(record[key]), hide)
        for key in keys if record[key]
    })


def serialize_fields(record, fields=_SERIALIZED_FIELDS):
    """Serialize fields to be stored in the database as YAML"""
    keys = record.iterkeys()
    keys = (k for k in keys for f in fields if k == f or k.endswith('.'+f))

    return merge_dicts(record, {
        key: _serialize(record[key])
        for key in keys if record[key] is not None
    })


def _decide_name_or_uuid(value):
    reference = value

    if isinstance(value, (list, tuple)):
        reference = value[0] if value else ''

    return 'uuid' if check_valid_uuid(reference) else 'name'


def _compose_where_from_uuids_or_names(**conditions):
    """Create a dict containing the right conditions to be used in a database
    query.

    This function chooses between ``names`` and ``uuid`` fields based on the
    format of the passed string.
    If a list is passed, the first element of the list will be used to choose
    the name of the field.
    If a ``None`` value is passed, ``uuid`` is used.

    Note that this function automatically translates ``tenant`` to
    ``nfvo_tenant`` for the sake of brevity.

    Example:
        >>> _compose_where_from_uuids_or_names(
                wim='abcdef',
                tenant=['xyz123', 'def456']
                datacenter='5286a274-8a1b-4b8d-a667-9c94261ad855')
        {'wim.name': 'abcdef',
         'nfvo_tenant.name': ['xyz123', 'def456']
         'datacenter.uuid': '5286a274-8a1b-4b8d-a667-9c94261ad855'}
    """
    if 'tenant' in conditions:
        conditions['nfvo_tenant'] = conditions.pop('tenant')

    return {
        '{}.{}'.format(kind, _decide_name_or_uuid(value)): value
        for kind, value in conditions.items() if value
    }


def _str2id(text):
    """Create an ID (following the UUID format) from a piece of arbitrary
    text.

    Different texts should generate different IDs, and the same text should
    generate the same ID in a repeatable way.
    """
    return sha1(text).hexdigest()
