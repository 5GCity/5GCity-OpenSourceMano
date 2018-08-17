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

"""This module works as an extension to the toplevel ``httpserver`` module,
implementing callbacks for the HTTP routes related to the WIM features of OSM.

Acting as a front-end, it is responsible for converting the HTTP request
payload into native python objects, calling the correct engine methods
and converting back the response objects into strings to be send in the HTTP
response payload.

Direct domain/persistence logic should be avoided in this file, instead
calls to other layers should be done.
"""
import logging

from bottle import request

from .. import utils
from ..http_tools.errors import ErrorHandler
from ..http_tools.handler import BaseHandler, route
from ..http_tools.request_processing import (
    filter_query_string,
    format_in,
    format_out
)
from .engine import WimEngine
from .persistence import WimPersistence
from .schemas import (
    wim_account_schema,
    wim_edit_schema,
    wim_port_mapping_schema,
    wim_schema
)


class WimHandler(BaseHandler):
    """HTTP route implementations for WIM related URLs

    Arguments:
        db: instance of mydb [optional]. This argument must be provided
            if not ``persistence`` is passed
        persistence (WimPersistence): High-level data storage abstraction
            [optional]. If this argument is not present, ``db`` must be.
        engine (WimEngine): Implementation of the business logic
            for the engine of WAN networks
        logger (logging.Logger): logger object [optional]
        url_base(str): Path fragment to be prepended to the routes [optional]
        plugins(list): List of bottle plugins to be applied to routes
            [optional]
    """
    def __init__(self, db=None, persistence=None, engine=None,
                 url_base='', logger=None, plugins=()):
        self.persist = persistence or WimPersistence(db)
        self.engine = engine or WimEngine(self.persist)
        self.url_base = url_base
        self.logger = logger or logging.getLogger('openmano.wim.http')
        error_handler = ErrorHandler(self.logger)
        self.plugins = [error_handler] + list(plugins)

    @route('GET', '/<tenant_id>/wims')
    def http_list_wims(self, tenant_id):
        allowed_fields = ('uuid', 'name', 'wim_url', 'type', 'created_at')
        select_, where_, limit_ = filter_query_string(
            request.query, None, allowed_fields)
        # ^  Since we allow the user to customize the db query using the HTTP
        #    query and it is quite difficult to re-use this query, let's just
        #    do a ad-hoc call to the db

        from_ = 'wims'
        if tenant_id != 'any':
            where_['nfvo_tenant_id'] = tenant_id
            if 'created_at' in select_:
                select_[select_.index('created_at')] = (
                    'w.created_at as created_at')
            if 'created_at' in where_:
                where_['w.created_at'] = where_.pop('created_at')
            from_ = ('wims as w join wim_nfvo_tenants as wt '
                     'on w.uuid=wt.wim_id')

        wims = self.persist.query(
            FROM=from_, SELECT=select_, WHERE=where_, LIMIT=limit_,
            error_if_none=False)

        utils.convert_float_timestamp2str(wims)
        return format_out({'wims': wims})

    @route('GET', '/<tenant_id>/wims/<wim_id>')
    def http_get_wim(self, tenant_id, wim_id):
        tenant_id = None if tenant_id == 'any' else tenant_id
        wim = self.engine.get_wim(wim_id, tenant_id)
        return format_out({'wim': wim})

    @route('POST', '/wims')
    def http_create_wim(self):
        http_content, _ = format_in(wim_schema, confidential_data=True)
        r = utils.remove_extra_items(http_content, wim_schema)
        if r:
            self.logger.debug("Remove extra items received %r", r)
        data = self.engine.create_wim(http_content['wim'])
        return self.http_get_wim('any', data)

    @route('PUT', '/wims/<wim_id>')
    def http_update_wim(self, wim_id):
        '''edit wim details, can use both uuid or name'''
        # parse input data
        http_content, _ = format_in(wim_edit_schema)
        r = utils.remove_extra_items(http_content, wim_edit_schema)
        if r:
            self.logger.debug("Remove received extra items %s", r)

        wim_id = self.engine.update_wim(wim_id, http_content['wim'])
        return self.http_get_wim('any', wim_id)

    @route('DELETE', '/wims/<wim_id>')
    def http_delete_wim(self, wim_id):
        """Delete a wim from a database, can use both uuid or name"""
        data = self.engine.delete_wim(wim_id)
        # TODO Remove WIM in orchestrator
        return format_out({"result": "wim '" + data + "' deleted"})

    @route('POST', '/<tenant_id>/wims/<wim_id>')
    def http_create_wim_account(self, tenant_id, wim_id):
        """Associate an existing wim to this tenant"""
        # parse input data
        http_content, _ = format_in(
            wim_account_schema, confidential_data=True)
        removed = utils.remove_extra_items(http_content, wim_account_schema)
        removed and self.logger.debug("Remove extra items %r", removed)
        account = self.engine.create_wim_account(
            wim_id, tenant_id, http_content['wim_account'])
        # check update succeeded
        return format_out({"wim_account": account})

    @route('PUT', '/<tenant_id>/wims/<wim_id>')
    def http_update_wim_accounts(self, tenant_id, wim_id):
        """Edit the association of an existing wim to this tenant"""
        tenant_id = None if tenant_id == 'any' else tenant_id
        # parse input data
        http_content, _ = format_in(
            wim_account_schema, confidential_data=True)
        removed = utils.remove_extra_items(http_content, wim_account_schema)
        removed and self.logger.debug("Remove extra items %r", removed)
        accounts = self.engine.update_wim_accounts(
            wim_id, tenant_id, http_content['wim_account'])

        if tenant_id:
            return format_out({'wim_account': accounts[0]})

        return format_out({'wim_accounts': accounts})

    @route('DELETE', '/<tenant_id>/wims/<wim_id>')
    def http_delete_wim_accounts(self, tenant_id, wim_id):
        """Deassociate an existing wim to this tenant"""
        tenant_id = None if tenant_id == 'any' else tenant_id
        accounts = self.engine.delete_wim_accounts(wim_id, tenant_id,
                                                   error_if_none=True)

        properties = (
            (account['name'], wim_id,
             utils.safe_get(account, 'association.nfvo_tenant_id', tenant_id))
            for account in accounts)

        return format_out({
            'result': '\n'.join('WIM account `{}` deleted. '
                                'Tenant `{}` detached from WIM `{}`'
                                .format(*p) for p in properties)
        })

    @route('POST', '/<tenant_id>/wims/<wim_id>/port_mapping')
    def http_create_wim_port_mappings(self, tenant_id, wim_id):
        """Set the wim port mapping for a wim"""
        # parse input data
        http_content, _ = format_in(wim_port_mapping_schema)

        data = self.engine.create_wim_port_mappings(
            wim_id, http_content['wim_port_mapping'], tenant_id)
        return format_out({"wim_port_mapping": data})

    @route('GET', '/<tenant_id>/wims/<wim_id>/port_mapping')
    def http_get_wim_port_mappings(self, tenant_id, wim_id):
        """Get wim port mapping details"""
        # TODO: tenant_id is never used, so it should be removed
        data = self.engine.get_wim_port_mappings(wim_id)
        return format_out({"wim_port_mapping": data})

    @route('DELETE', '/<tenant_id>/wims/<wim_id>/port_mapping')
    def http_delete_wim_port_mappings(self, tenant_id, wim_id):
        """Clean wim port mapping"""
        # TODO: tenant_id is never used, so it should be removed
        data = self.engine.delete_wim_port_mappings(wim_id)
        return format_out({"result": data})
