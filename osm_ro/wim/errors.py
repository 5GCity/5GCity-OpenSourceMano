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
from six.moves import queue

from ..db_base import db_base_Exception as DbBaseException
from ..http_tools.errors import (
    Bad_Request,
    Conflict,
    HttpMappedError,
    Internal_Server_Error,
    Not_Found
)


class NoRecordFound(DbBaseException):
    """No record was found in the database"""

    def __init__(self, criteria, table=None):
        table_info = '{} - '.format(table) if table else ''
        super(NoRecordFound, self).__init__(
            '{}: {}`{}`'.format(self.__class__.__doc__, table_info, criteria),
            http_code=Not_Found)


class MultipleRecordsFound(DbBaseException):
    """More than one record was found in the database"""

    def __init__(self, criteria, table=None):
        table_info = '{} - '.format(table) if table else ''
        super(MultipleRecordsFound, self).__init__(
            '{}: {}`{}`'.format(self.__class__.__doc__, table_info, criteria),
            http_code=Conflict)


class WimAndTenantNotAttached(DbBaseException):
    """Wim and Tenant are not attached"""

    def __init__(self, wim, tenant):
        super(WimAndTenantNotAttached, self).__init__(
            '{}: `{}` <> `{}`'.format(self.__class__.__doc__, wim, tenant),
            http_code=Conflict)


class WimAndTenantAlreadyAttached(DbBaseException):
    """There is already a wim account attaching the given wim and tenant"""

    def __init__(self, wim, tenant):
        super(WimAndTenantAlreadyAttached, self).__init__(
            '{}: `{}` <> `{}`'.format(self.__class__.__doc__, wim, tenant),
            http_code=Conflict)


class NoWimConnectedToDatacenters(NoRecordFound):
    """No WIM that is able to connect the given datacenters was found"""


class InvalidParameters(DbBaseException):
    """The given parameters are invalid"""

    def __init__(self, message, http_code=Bad_Request):
        super(InvalidParameters, self).__init__(message, http_code)


class UndefinedAction(HttpMappedError):
    """No action found"""

    def __init__(self, item_type, action, http_code=Internal_Server_Error):
        message = ('The action {} {} is not defined'.format(action, item_type))
        super(UndefinedAction, self).__init__(message, http_code)


class UndefinedWimConnector(DbBaseException):
    """The connector class for the specified wim type is not implemented"""

    def __init__(self, wim_type, module_name, location_reference):
        super(UndefinedWimConnector, self).__init__(
            ('{}: `{}`. Could not find module `{}` '
             '(check if it is necessary to install a plugin)'
             .format(self.__class__.__doc__, wim_type, module_name)),
            http_code=Bad_Request)


class WimAccountOverwrite(DbBaseException):
    """An attempt to overwrite an existing WIM account was identified"""

    def __init__(self, wim_account, diff=None, tip=None):
        message = self.__class__.__doc__
        account_info = (
            'Account -- name: {name}, uuid: {uuid}'.format(**wim_account)
            if wim_account else '')
        diff_info = (
            'Differing fields: ' + ', '.join(diff.keys()) if diff else '')

        super(WimAccountOverwrite, self).__init__(
            '\n'.join(m for m in (message, account_info, diff_info, tip) if m),
            http_code=Conflict)


class UnexpectedDatabaseError(DbBaseException):
    """The database didn't raised an exception but also the query was not
    executed (maybe the connection had some problems?)
    """


class UndefinedUuidOrName(DbBaseException):
    """Trying to query for a record using an empty uuid or name"""

    def __init__(self, table=None):
        table_info = '{} - '.format(table.split()[0]) if table else ''
        super(UndefinedUuidOrName, self).__init__(
            table_info + self.__class__.__doc__, http_status=Bad_Request)


class UndefinedWanMappingType(InvalidParameters):
    """The dict wan_service_mapping_info MUST contain a `type` field"""

    def __init__(self, given):
        super(UndefinedWanMappingType, self).__init__(
            '{}. Given: `{}`'.format(self.__class__.__doc__, given))


class QueueFull(HttpMappedError, queue.Full):
    """Thread queue is full"""

    def __init__(self, thread_name, http_code=Internal_Server_Error):
        message = ('Thread {} queue is full'.format(thread_name))
        super(QueueFull, self).__init__(message, http_code)


class InconsistentState(HttpMappedError):
    """An unexpected inconsistency was find in the state of the program"""

    def __init__(self, arg, http_code=Internal_Server_Error):
        if isinstance(arg, HttpMappedError):
            http_code = arg.http_code
            message = str(arg)
        else:
            message = arg

        super(InconsistentState, self).__init__(message, http_code)


class WimAccountNotActive(HttpMappedError, KeyError):
    """WIM Account is not active yet (no thread is running)"""

    def __init__(self, message, http_code=Internal_Server_Error):
        message += ('\nThe thread responsible for processing the actions have '
                    'suddenly stopped, or have never being spawned')
        super(WimAccountNotActive, self).__init__(message, http_code)
