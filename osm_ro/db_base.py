# -*- coding: utf-8 -*-

##
# Copyright 2015 Telefonica Investigacion y Desarrollo, S.A.U.
# This file is part of openmano
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
Base class for openmano database manipulation
'''
__author__="Alfonso Tierno"
__date__ ="$4-Apr-2016 10:05:01$"

import MySQLdb as mdb
import uuid as myUuid
import  utils as af
import json
#import yaml
import time
import logging
import datetime
from contextlib import contextmanager
from functools import wraps, partial
from threading import Lock
from jsonschema import validate as js_v, exceptions as js_e

from .http_tools import errors as httperrors
from .utils import Attempt, get_arg, inject_args


RECOVERY_TIME = 3

_ATTEMPT = Attempt()


def with_transaction(fn=None, cursor=None):
    """Decorator that can be used together with instances of the ``db_base``
    class, to perform database actions wrapped in a commit/rollback fashion

    This decorator basically executes the function inside the context object
    given by the ``transaction`` method in ``db_base``

    Arguments:
        cursor: [Optional] cursor class
    """
    if fn is None:  # Allows calling the decorator directly or with parameters
        return partial(with_transaction, cursor=cursor)

    @wraps(fn)
    def _wrapper(self, *args, **kwargs):
        cursor_type = None
        if cursor == 'dict':
            # MySQLdB define the "cursors" module attribute lazily,
            # so we have to defer references to mdb.cursors.DictCursor
            cursor_type = mdb.cursors.DictCursor

        with self.transaction(cursor_type):
            return fn(self, *args, **kwargs)

    return _wrapper


def retry(fn=None, max_attempts=Attempt.MAX, **info):
    """Decorator that can be used together with instances of the ``db_base``
    class, to replay a method again after a unexpected error.

    The function being decorated needs to either be a method of ``db_base``
    subclasses or accept an ``db_base`` instance as the first parameter.

    All the extra keyword arguments will be passed to the ``_format_error``
    method
    """
    if fn is None:  # Allows calling the decorator directly or with parameters
        return partial(retry, max_attempts=max_attempts, **info)

    @wraps(fn)
    def _wrapper(*args, **kwargs):
        self = args[0]
        info.setdefault('table', get_arg('table', fn, args, kwargs))
        attempt = Attempt(max_attempts=max_attempts, info=info)
        while attempt.countdown >= 0:
            try:
                return inject_args(fn, attempt=attempt)(*args, **kwargs)
            except (mdb.Error, AttributeError) as ex:
                self.logger.debug("Attempt #%d", attempt.number)
                try:
                    # The format error will throw exceptions, however it can
                    # tolerate a certain amount of retries if it judges that
                    # the error can be solved with retrying
                    self._format_error(ex, attempt.countdown, **attempt.info)
                    # Anyway, unexpected/unknown errors can still be retried
                except db_base_Exception as db_ex:
                    if (attempt.countdown < 0 or db_ex.http_code !=
                            httperrors.Internal_Server_Error):
                        raise

            attempt.count += 1

    return _wrapper


def _check_valid_uuid(uuid):
    id_schema = {"type" : "string", "pattern": "^[a-fA-F0-9]{8}(-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}$"}
    id_schema2 = {"type" : "string", "pattern": "^[a-fA-F0-9]{32}$"}
    try:
        js_v(uuid, id_schema)
        return True
    except js_e.ValidationError:
        try:
            js_v(uuid, id_schema2)
            return True
        except js_e.ValidationError:
            return False
    return False

def _convert_datetime2str(var):
    '''Converts a datetime variable to a string with the format '%Y-%m-%dT%H:%i:%s'
    It enters recursively in the dict var finding this kind of variables
    '''
    if type(var) is dict:
        for k,v in var.items():
            if type(v) is datetime.datetime:
                var[k]= v.strftime('%Y-%m-%dT%H:%M:%S')
            elif type(v) is dict or type(v) is list or type(v) is tuple:
                _convert_datetime2str(v)
        if len(var) == 0: return True
    elif type(var) is list or type(var) is tuple:
        for v in var:
            _convert_datetime2str(v)

def _convert_bandwidth(data, reverse=False, logger=None):
    '''Check the field bandwidth recursivelly and when found, it removes units and convert to number
    It assumes that bandwidth is well formed
    Attributes:
        'data': dictionary bottle.FormsDict variable to be checked. None or empty is consideted valid
        'reverse': by default convert form str to int (Mbps), if True it convert from number to units
    Return:
        None
    '''
    if type(data) is dict:
        for k in data.keys():
            if type(data[k]) is dict or type(data[k]) is tuple or type(data[k]) is list:
                _convert_bandwidth(data[k], reverse, logger)
        if "bandwidth" in data:
            try:
                value=str(data["bandwidth"])
                if not reverse:
                    pos = value.find("bps")
                    if pos>0:
                        if value[pos-1]=="G": data["bandwidth"] =  int(data["bandwidth"][:pos-1]) * 1000
                        elif value[pos-1]=="k": data["bandwidth"]= int(data["bandwidth"][:pos-1]) / 1000
                        else: data["bandwidth"]= int(data["bandwidth"][:pos-1])
                else:
                    value = int(data["bandwidth"])
                    if value % 1000 == 0: data["bandwidth"]=str(value/1000) + " Gbps"
                    else: data["bandwidth"]=str(value) + " Mbps"
            except:
                if logger:
                    logger.error("convert_bandwidth exception for type '%s' data '%s'", type(data["bandwidth"]), data["bandwidth"])
                return
    if type(data) is tuple or type(data) is list:
        for k in data:
            if type(k) is dict or type(k) is tuple or type(k) is list:
                _convert_bandwidth(k, reverse, logger)

def _convert_str2boolean(data, items):
    '''Check recursively the content of data, and if there is an key contained in items, convert value from string to boolean
    Done recursively
    Attributes:
        'data': dictionary variable to be checked. None or empty is considered valid
        'items': tuple of keys to convert
    Return:
        None
    '''
    if type(data) is dict:
        for k in data.keys():
            if type(data[k]) is dict or type(data[k]) is tuple or type(data[k]) is list:
                _convert_str2boolean(data[k], items)
            if k in items:
                if type(data[k]) is str:
                    if   data[k]=="false" or data[k]=="False" or data[k]=="0": data[k]=False
                    elif data[k]=="true"  or data[k]=="True" or data[k]=="1":  data[k]=True
                elif type(data[k]) is int:
                    if   data[k]==0: data[k]=False
                    elif  data[k]==1:  data[k]=True
    if type(data) is tuple or type(data) is list:
        for k in data:
            if type(k) is dict or type(k) is tuple or type(k) is list:
                _convert_str2boolean(k, items)

class db_base_Exception(httperrors.HttpMappedError):
    '''Common Exception for all database exceptions'''

    def __init__(self, message, http_code=httperrors.Bad_Request):
        super(db_base_Exception, self).__init__(message, http_code)

class db_base():
    tables_with_created_field=()

    def __init__(self, host=None, user=None, passwd=None, database=None,
                 log_name='db', log_level=None, lock=None):
        self.host = host
        self.user = user
        self.passwd = passwd
        self.database = database
        self.con = None
        self.log_level=log_level
        self.logger = logging.getLogger(log_name)
        if self.log_level:
            self.logger.setLevel( getattr(logging, log_level) )
        self.lock = lock or Lock()

    def connect(self, host=None, user=None, passwd=None, database=None):
        '''Connect to specific data base.
        The first time a valid host, user, passwd and database must be provided,
        Following calls can skip this parameters
        '''
        try:
            if host:        self.host = host
            if user:        self.user = user
            if passwd:      self.passwd = passwd
            if database:    self.database = database

            self.con = mdb.connect(self.host, self.user, self.passwd, self.database)
            self.logger.debug("DB: connected to '%s' at '%s@%s'", self.database, self.user, self.host)
        except mdb.Error as e:
            raise db_base_Exception("Cannot connect to DataBase '{}' at '{}@{}' Error {}: {}".format(
                                    self.database, self.user, self.host, e.args[0], e.args[1]),
                                    http_code = httperrors.Unauthorized )

    def escape(self, value):
        return self.con.escape(value)

    def escape_string(self, value):
        if isinstance(value, unicode):
            value = value.encode("utf8")
        return self.con.escape_string(value)

    @retry
    @with_transaction
    def get_db_version(self):
        ''' Obtain the database schema version.
        Return: (negative, text) if error or version 0.0 where schema_version table is missing
                (version_int, version_text) if ok
        '''
        cmd = "SELECT version_int,version FROM schema_version"
        self.logger.debug(cmd)
        self.cur.execute(cmd)
        rows = self.cur.fetchall()
        highest_version_int=0
        highest_version=""
        for row in rows: #look for the latest version
            if row[0]>highest_version_int:
                highest_version_int, highest_version = row[0:2]
        return highest_version_int, highest_version

    def disconnect(self):
        '''disconnect from specific data base'''
        try:
            self.con.close()
            self.con = None
        except mdb.Error as e:
            self.logger.error("while disconnecting from DB: Error %d: %s",e.args[0], e.args[1])
            return
        except AttributeError as e: #self.con not defined
            if e[0][-5:] == "'con'":
                self.logger.warn("while disconnecting from DB: Error %d: %s",e.args[0], e.args[1])
                return
            else:
                raise

    def reconnect(self):
        """Try to gracefully to the database in case of error"""
        try:
            self.con.ping(True)  # auto-reconnect if the server is available
        except:
            # The server is probably not available...
            # Let's wait a bit
            time.sleep(RECOVERY_TIME)
            self.con = None
            self.connect()

    def fork_connection(self):
        """Return a new database object, with a separated connection to the
        database (and lock), so it can act independently
        """
        obj =  self.__class__(
            host=self.host,
            user=self.user,
            passwd=self.passwd,
            database=self.database,
            log_name=self.logger.name,
            log_level=self.log_level,
            lock=Lock()
        )

        obj.connect()

        return obj

    @contextmanager
    def transaction(self, cursor_type=None):
        """DB changes that are executed inside this context will be
        automatically rolled back in case of error.

        This implementation also adds a lock, so threads sharing the same
        connection object are synchronized.

        Arguments:
            cursor_type: default: MySQLdb.cursors.DictCursor

        Yields:
            Cursor object

        References:
            https://www.oreilly.com/library/view/mysql-cookbook-2nd/059652708X/ch15s08.html
            https://github.com/PyMySQL/mysqlclient-python/commit/c64915b1e5c705f4fb10e86db5dcfed0b58552cc
        """
        # Previously MySQLdb had built-in support for that using the context
        # API for the connection object.
        # This support was removed in version 1.40
        # https://github.com/PyMySQL/mysqlclient-python/blob/master/HISTORY.rst#whats-new-in-140
        with self.lock:
            try:
                if self.con.get_autocommit():
                    self.con.query("BEGIN")

                self.cur = self.con.cursor(cursor_type)
                yield self.cur
            except:  # noqa
                self.con.rollback()
                raise
            else:
                self.con.commit()


    def _format_error(self, e, tries=1, command=None,
                      extra=None, table=None, cmd=None, **_):
        '''Creates a text error base on the produced exception
            Params:
                e: mdb exception
                retry: in case of timeout, if reconnecting to database and retry, or raise and exception
                cmd: database command that produce the exception
                command: if the intention is update or delete
                extra: extra information to add to some commands
            Return
                HTTP error in negative, formatted error text
        '''  # the **_ ignores extra kwargs
        table_info = ' (table `{}`)'.format(table) if table else ''
        if cmd:
            self.logger.debug("Exception '%s' with command '%s'%s",
                              e, cmd, table_info)

        if isinstance(e,AttributeError ):
            self.logger.debug(str(e), exc_info=True)
            raise db_base_Exception("DB Exception " + str(e), httperrors.Internal_Server_Error)
        if e.args[0]==2006 or e.args[0]==2013 : #MySQL server has gone away (((or)))    Exception 2013: Lost connection to MySQL server during query
            # Let's aways reconnect if the connection is lost
            # so future calls are not affected.
            self.reconnect()

            if tries > 1:
                self.logger.warn("DB Exception '%s'. Retry", str(e))
                return
            else:
                raise db_base_Exception("Database connection timeout Try Again", httperrors.Request_Timeout)

        fk=e.args[1].find("foreign key constraint fails")
        if fk>=0:
            if command=="update":
                raise db_base_Exception("tenant_id '{}' not found.".format(extra), httperrors.Not_Found)
            elif command=="delete":
                raise db_base_Exception("Resource is not free. There are {} that prevent deleting it.".format(extra), httperrors.Conflict)
        de = e.args[1].find("Duplicate entry")
        fk = e.args[1].find("for key")
        uk = e.args[1].find("Unknown column")
        wc = e.args[1].find("in 'where clause'")
        fl = e.args[1].find("in 'field list'")
        #print de, fk, uk, wc,fl
        if de>=0:
            if fk>=0: #error 1062
                raise db_base_Exception(
                    "Value {} already in use for {}{}".format(
                        e.args[1][de+15:fk], e.args[1][fk+7:], table_info),
                    httperrors.Conflict)
        if uk>=0:
            if wc>=0:
                raise db_base_Exception(
                    "Field {} can not be used for filtering{}".format(
                        e.args[1][uk+14:wc], table_info),
                    httperrors.Bad_Request)
            if fl>=0:
                raise db_base_Exception(
                    "Field {} does not exist{}".format(
                        e.args[1][uk+14:wc], table_info),
                    httperrors.Bad_Request)
        raise db_base_Exception(
                "Database internal Error{} {}: {}".format(
                    table_info, e.args[0], e.args[1]),
                httperrors.Internal_Server_Error)

    def __str2db_format(self, data):
        """Convert string data to database format.
        If data is None it returns the 'Null' text,
        otherwise it returns the text surrounded by quotes ensuring internal quotes are escaped.
        """
        if data is None:
            return 'Null'
        elif isinstance(data[1], (str, unicode)):
            return json.dumps(data)
        else:
            return json.dumps(str(data))

    def __tuple2db_format_set(self, data):
        """Compose the needed text for a SQL SET, parameter 'data' is a pair tuple (A,B),
        and it returns the text 'A="B"', where A is a field of a table and B is the value
        If B is None it returns the 'A=Null' text, without surrounding Null by quotes
        If B is not None it returns the text "A='B'" or 'A="B"' where B is surrounded by quotes,
        and it ensures internal quotes of B are escaped.
        B can be also a dict with special keys:
            {"INCREMENT": NUMBER}, then it produce "A=A+NUMBER"
        """
        if data[1] is None:
            return str(data[0]) + "=Null"
        elif isinstance(data[1], (str, unicode)):
            return str(data[0]) + '=' + json.dumps(data[1])
        elif isinstance(data[1], dict):
            if "INCREMENT" in data[1]:
                return "{A}={A}{N:+d}".format(A=data[0], N=data[1]["INCREMENT"])
            raise db_base_Exception("Format error for UPDATE field: {!r}".format(data[0]))
        else:
            return str(data[0]) + '=' + json.dumps(str(data[1]))

    def __create_where(self, data, use_or=None):
        """
        Compose the needed text for a SQL WHERE, parameter 'data' can be a dict or a list of dict. By default lists are
        concatenated with OR and dict with AND, unless parameter 'use_or' indicates other thing.
        If a dict it will generate 'key1="value1" AND key2="value2" AND ...'.
            If value is None, it will produce 'key is null'
            If value is a list or tuple, it will produce 'key="value[0]" OR key="value[1]" OR ...'
            keys can be suffixed by >,<,<>,>=,<=,' LIKE ' so that this is used to compare key and value instead of "="
        The special keys "OR", "AND" with a dict value is used to create a nested WHERE
        If a list, each item will be a dictionary that will be concatenated with OR by default
        :param data: dict or list of dicts
        :param use_or: Can be None (use default behaviour), True (use OR) or False (use AND)
        :return: a string with the content to send to mysql
        """
        cmd = []
        if isinstance(data, dict):
            for k, v in data.items():
                if k == "OR":
                    cmd.append("(" + self.__create_where(v, use_or=True) + ")")
                    continue
                elif k == "AND":
                    cmd.append("(" + self.__create_where(v, use_or=False) + ")")
                    continue

                if k.endswith(">") or k.endswith("<") or k.endswith("=") or k.endswith(" LIKE "):
                    pass
                else:
                    k += "="

                if v is None:
                    cmd.append(k.replace("=", " is").replace("<>", " is not") + " Null")
                elif isinstance(v, (tuple, list)):
                    cmd2 = []
                    for v2 in v:
                        if v2 is None:
                            cmd2.append(k.replace("=", " is").replace("<>", " is not") + " Null")
                        elif isinstance(v2, (str, unicode)):
                            cmd2.append(k + json.dumps(v2))
                        else:
                            cmd2.append(k + json.dumps(str(v2)))
                    cmd.append("(" + " OR ".join(cmd2) + ")")
                elif isinstance(v, (str, unicode)):
                    cmd.append(k + json.dumps(v))
                else:
                    cmd.append(k + json.dumps(str(v)))
        elif isinstance(data, (tuple, list)):
            if use_or is None:
                use_or = True
            for k in data:
                cmd.append("(" + self.__create_where(k) + ")")
        else:
            raise db_base_Exception("invalid WHERE clause at '{}'".format(data))
        if use_or:
            return " OR ".join(cmd)
        return " AND ".join(cmd)

    def __remove_quotes(self, data):
        '''remove single quotes ' of any string content of data dictionary'''
        for k,v in data.items():
            if type(v) == str:
                if "'" in v:
                    data[k] = data[k].replace("'","_")

    def _update_rows(self, table, UPDATE, WHERE, modified_time=0):
        """ Update one or several rows of a table.
        :param UPDATE: dictionary with the changes. dict keys are database columns that will be set with the dict values
        :param table: database table to update
        :param WHERE: dict or list of dicts to compose the SQL WHERE clause.
            If a dict it will generate 'key1="value1" AND key2="value2" AND ...'.
                If value is None, it will produce 'key is null'
                If value is a list or tuple, it will produce 'key="value[0]" OR key="value[1]" OR ...'
                keys can be suffixed by >,<,<>,>=,<= so that this is used to compare key and value instead of "="
                The special keys "OR", "AND" with a dict value is used to create a nested WHERE
            If a list, each item will be a dictionary that will be concatenated with OR
        :return: the number of updated rows, raises exception upon error
        """
        # gettting uuid
        values = ",".join(map(self.__tuple2db_format_set, UPDATE.iteritems() ))
        if modified_time:
            values += ",modified_at={:f}".format(modified_time)
        cmd= "UPDATE " + table + " SET " + values + " WHERE " + self.__create_where(WHERE)
        self.logger.debug(cmd)
        self.cur.execute(cmd)
        return self.cur.rowcount

    def _new_uuid(self, root_uuid=None, used_table=None, created_time=0):
        """
        Generate a new uuid. It DOES NOT begin or end the transaction, so self.con.cursor must be created
        :param root_uuid: master uuid of the transaction
        :param used_table: the table this uuid is intended for
        :param created_time: time of creation
        :return: the created uuid
        """

        uuid = str(myUuid.uuid1())
        # defining root_uuid if not provided
        if root_uuid is None:
            root_uuid = uuid
        if created_time:
            created_at = created_time
        else:
            created_at = time.time()
        # inserting new uuid
        cmd = "INSERT INTO uuids (uuid, root_uuid, used_at, created_at) VALUES ('{:s}','{:s}','{:s}', {:f})".format(
            uuid, root_uuid, used_table, created_at)
        self.logger.debug(cmd)
        self.cur.execute(cmd)
        return uuid

    def _new_row_internal(self, table, INSERT, add_uuid=False, root_uuid=None, created_time=0, confidential_data=False):
        ''' Add one row into a table. It DOES NOT begin or end the transaction, so self.con.cursor must be created
        Attribute
            INSERT: dictionary with the key:value to insert
            table: table where to insert
            add_uuid: if True, it will create an uuid key entry at INSERT if not provided
            created_time: time to add to the created_at column
        It checks presence of uuid and add one automatically otherwise
        Return: uuid
        '''

        if add_uuid:
            #create uuid if not provided
            if 'uuid' not in INSERT:
                uuid = INSERT['uuid'] = str(myUuid.uuid1()) # create_uuid
            else:
                uuid = str(INSERT['uuid'])
        else:
            uuid=None
        if add_uuid:
            #defining root_uuid if not provided
            if root_uuid is None:
                root_uuid = uuid
            if created_time:
                created_at = created_time
            else:
                created_at=time.time()
            #inserting new uuid
            cmd = "INSERT INTO uuids (uuid, root_uuid, used_at, created_at) VALUES ('{:s}','{:s}','{:s}', {:f})".format(uuid, root_uuid, table, created_at)
            self.logger.debug(cmd)
            self.cur.execute(cmd)
        #insertion
        cmd= "INSERT INTO " + table +" SET " + \
            ",".join(map(self.__tuple2db_format_set, INSERT.iteritems() ))
        if created_time:
            cmd += ",created_at={time:.9f},modified_at={time:.9f}".format(time=created_time)
        if confidential_data:
            index = cmd.find("SET")
            subcmd = cmd[:index] + 'SET...'
            self.logger.debug(subcmd)
        else:
            self.logger.debug(cmd)
        self.cur.execute(cmd)
        self.cur.rowcount
        return uuid

    def _get_rows(self,table,uuid):
        cmd = "SELECT * FROM {} WHERE uuid='{}'".format(str(table), str(uuid))
        self.logger.debug(cmd)
        self.cur.execute(cmd)
        rows = self.cur.fetchall()
        return rows

    @retry
    @with_transaction
    def new_row(self, table, INSERT, add_uuid=False, created_time=0, confidential_data=False):
        ''' Add one row into a table.
        Attribute
            INSERT: dictionary with the key: value to insert
            table: table where to insert
            tenant_id: only useful for logs. If provided, logs will use this tenant_id
            add_uuid: if True, it will create an uuid key entry at INSERT if not provided
        It checks presence of uuid and add one automatically otherwise
        Return: uuid
        '''
        if table in self.tables_with_created_field and created_time==0:
            created_time=time.time()
        return self._new_row_internal(table, INSERT, add_uuid, None, created_time, confidential_data)

    @retry
    @with_transaction
    def update_rows(self, table, UPDATE, WHERE, modified_time=None, attempt=_ATTEMPT):
        """ Update one or several rows of a table.
        :param UPDATE: dictionary with the changes. dict keys are database columns that will be set with the dict values
        :param table: database table to update
        :param WHERE: dict or list of dicts to compose the SQL WHERE clause.
            If a dict it will generate 'key1="value1" AND key2="value2" AND ...'.
                If value is None, it will produce 'key is null'
                If value is a list or tuple, it will produce 'key="value[0]" OR key="value[1]" OR ...'
                keys can be suffixed by >,<,<>,>=,<= so that this is used to compare key and value instead of "="
                The special keys "OR", "AND" with a dict value is used to create a nested WHERE
            If a list, each item will be a dictionary that will be concatenated with OR
        :param modified_time: Can contain the time to be set to the table row.
            None to set automatically, 0 to do not modify it
        :return: the number of updated rows, raises exception upon error
        """
        if table in self.tables_with_created_field and modified_time is None:
            modified_time = time.time()

        return self._update_rows(table, UPDATE, WHERE, modified_time)

    def _delete_row_by_id_internal(self, table, uuid):
        cmd = "DELETE FROM {} WHERE uuid = '{}'".format(table, uuid)
        self.logger.debug(cmd)
        self.cur.execute(cmd)
        deleted = self.cur.rowcount
        # delete uuid
        self.cur = self.con.cursor()
        cmd = "DELETE FROM uuids WHERE root_uuid = '{}'".format(uuid)
        self.logger.debug(cmd)
        self.cur.execute(cmd)
        return deleted

    @retry(command='delete', extra='dependencies')
    @with_transaction
    def delete_row_by_id(self, table, uuid):
        return self._delete_row_by_id_internal(table, uuid)

    @retry
    def delete_row(self, attempt=_ATTEMPT, **sql_dict):
        """ Deletes rows from a table.
        :param UPDATE: dictionary with the changes. dict keys are database columns that will be set with the dict values
        :param FROM: string with table name (Mandatory)
        :param WHERE: dict or list of dicts to compose the SQL WHERE clause. (Optional)
            If a dict it will generate 'key1="value1" AND key2="value2" AND ...'.
                If value is None, it will produce 'key is null'
                If value is a list or tuple, it will produce 'key="value[0]" OR key="value[1]" OR ...'
                keys can be suffixed by >,<,<>,>=,<= so that this is used to compare key and value instead of "="
                The special keys "OR", "AND" with a dict value is used to create a nested WHERE
            If a list, each item will be a dictionary that will be concatenated with OR
        :return: the number of deleted rows, raises exception upon error
        """
        # print sql_dict
        cmd = "DELETE FROM " + str(sql_dict['FROM'])
        if sql_dict.get('WHERE'):
            cmd += " WHERE " + self.__create_where(sql_dict['WHERE'])
        if sql_dict.get('LIMIT'):
            cmd += " LIMIT " + str(sql_dict['LIMIT'])

        attempt.info['cmd'] = cmd

        with self.transaction():
            self.logger.debug(cmd)
            self.cur.execute(cmd)
            deleted = self.cur.rowcount
        return deleted

    @retry
    @with_transaction(cursor='dict')
    def get_rows_by_id(self, table, uuid, attempt=_ATTEMPT):
        '''get row from a table based on uuid'''
        cmd="SELECT * FROM {} where uuid='{}'".format(str(table), str(uuid))
        attempt.info['cmd'] = cmd
        self.logger.debug(cmd)
        self.cur.execute(cmd)
        rows = self.cur.fetchall()
        return rows

    @retry
    def get_rows(self, attempt=_ATTEMPT, **sql_dict):
        """ Obtain rows from a table.
        :param SELECT: list or tuple of fields to retrieve) (by default all)
        :param FROM: string with table name (Mandatory)
        :param WHERE: dict or list of dicts to compose the SQL WHERE clause. (Optional)
            If a dict it will generate 'key1="value1" AND key2="value2" AND ...'.
                If value is None, it will produce 'key is null'
                If value is a list or tuple, it will produce 'key="value[0]" OR key="value[1]" OR ...'
                keys can be suffixed by >,<,<>,>=,<= so that this is used to compare key and value instead of "="
                The special keys "OR", "AND" with a dict value is used to create a nested WHERE
            If a list, each item will be a dictionary that will be concatenated with OR
        :param LIMIT: limit the number of obtained entries (Optional)
        :param ORDER_BY:  list or tuple of fields to order, add ' DESC' to each item if inverse order is required
        :return: a list with dictionaries at each row, raises exception upon error
        """
        # print sql_dict
        cmd = "SELECT "
        if 'SELECT' in sql_dict:
            if isinstance(sql_dict['SELECT'], (tuple, list)):
                cmd += ",".join(map(str, sql_dict['SELECT']))
            else:
                cmd += sql_dict['SELECT']
        else:
            cmd += "*"

        cmd += " FROM " + str(sql_dict['FROM'])
        if sql_dict.get('WHERE'):
            cmd += " WHERE " + self.__create_where(sql_dict['WHERE'])

        if 'ORDER_BY' in sql_dict:
            cmd += " ORDER BY "
            if isinstance(sql_dict['ORDER_BY'], (tuple, list)):
                cmd += ",".join(map(str, sql_dict['ORDER_BY']))
            else:
                cmd += str(sql_dict['ORDER_BY'])

        if 'LIMIT' in sql_dict:
            cmd += " LIMIT " + str(sql_dict['LIMIT'])

        attempt.info['cmd'] = cmd

        with self.transaction(mdb.cursors.DictCursor):
            self.logger.debug(cmd)
            self.cur.execute(cmd)
            rows = self.cur.fetchall()
            return rows

    @retry
    def get_table_by_uuid_name(self, table, uuid_name, error_item_text=None, allow_several=False, WHERE_OR={}, WHERE_AND_OR="OR", attempt=_ATTEMPT):
        ''' Obtain One row from a table based on name or uuid.
        Attribute:
            table: string of table name
            uuid_name: name or uuid. If not uuid format is found, it is considered a name
            allow_several: if False return ERROR if more than one row are found
            error_item_text: in case of error it identifies the 'item' name for a proper output text
            'WHERE_OR': dict of key:values, translated to key=value OR ... (Optional)
            'WHERE_AND_OR: str 'AND' or 'OR'(by default) mark the priority to 'WHERE AND (WHERE_OR)' or (WHERE) OR WHERE_OR' (Optional
        Return: if allow_several==False, a dictionary with this row, or error if no item is found or more than one is found
                if allow_several==True, a list of dictionaries with the row or rows, error if no item is found
        '''

        if error_item_text==None:
            error_item_text = table
        what = 'uuid' if af.check_valid_uuid(uuid_name) else 'name'
        cmd = " SELECT * FROM {} WHERE {}='{}'".format(table, what, uuid_name)
        if WHERE_OR:
            where_or = self.__create_where(WHERE_OR, use_or=True)
            if WHERE_AND_OR == "AND":
                cmd += " AND (" + where_or + ")"
            else:
                cmd += " OR " + where_or

        attempt.info['cmd'] = cmd

        with self.transaction(mdb.cursors.DictCursor):
            self.logger.debug(cmd)
            self.cur.execute(cmd)
            number = self.cur.rowcount
            if number == 0:
                raise db_base_Exception("No {} found with {} '{}'".format(error_item_text, what, uuid_name), http_code=httperrors.Not_Found)
            elif number > 1 and not allow_several:
                raise db_base_Exception("More than one {} found with {} '{}'".format(error_item_text, what, uuid_name), http_code=httperrors.Conflict)
            if allow_several:
                rows = self.cur.fetchall()
            else:
                rows = self.cur.fetchone()
            return rows

    @retry(table='uuids')
    @with_transaction(cursor='dict')
    def get_uuid(self, uuid):
        '''check in the database if this uuid is already present'''
        self.cur.execute("SELECT * FROM uuids where uuid='" + str(uuid) + "'")
        rows = self.cur.fetchall()
        return self.cur.rowcount, rows

    @retry
    @with_transaction(cursor='dict')
    def get_uuid_from_name(self, table, name):
        '''Searchs in table the name and returns the uuid
        '''
        where_text = "name='" + name +"'"
        self.cur.execute("SELECT * FROM " + table + " WHERE "+ where_text)
        rows = self.cur.fetchall()
        if self.cur.rowcount==0:
            return 0, "Name %s not found in table %s" %(name, table)
        elif self.cur.rowcount>1:
            return self.cur.rowcount, "More than one VNF with name %s found in table %s" %(name, table)
        return self.cur.rowcount, rows[0]["uuid"]
