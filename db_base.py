# -*- coding: utf-8 -*-

##
# Copyright 2015 Telefónica Investigación y Desarrollo, S.A.U.
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
from jsonschema import validate as js_v, exceptions as js_e

HTTP_Bad_Request = 400
HTTP_Unauthorized = 401 
HTTP_Not_Found = 404 
HTTP_Method_Not_Allowed = 405 
HTTP_Request_Timeout = 408
HTTP_Conflict = 409
HTTP_Service_Unavailable = 503 
HTTP_Internal_Server_Error = 500 

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

class db_base_Exception(Exception):
    '''Common Exception for all database exceptions'''
    
    def __init__(self, message, http_code=HTTP_Bad_Request):
        Exception.__init__(self, message)
        self.http_code = http_code

class db_base():
    tables_with_created_field=()
    
    def __init__(self, host=None, user=None, passwd=None, database=None, log_name='db', log_level=None):
        self.host = host
        self.user = user
        self.passwd = passwd
        self.database = database
        self.con = None
        self.log_level=log_level
        self.logger = logging.getLogger(log_name)
        if self.log_level:
            self.logger.setLevel( getattr(logging, log_level) )
        
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
                                    http_code = HTTP_Unauthorized )
        
    def get_db_version(self):
        ''' Obtain the database schema version.
        Return: (negative, text) if error or version 0.0 where schema_version table is missing
                (version_int, version_text) if ok
        '''
        cmd = "SELECT version_int,version FROM schema_version"
        tries = 2
        while tries:
            try:
                with self.con:
                    self.cur = self.con.cursor()
                    self.logger.debug(cmd)
                    self.cur.execute(cmd)
                    rows = self.cur.fetchall()
                    highest_version_int=0
                    highest_version=""
                    for row in rows: #look for the latest version
                        if row[0]>highest_version_int:
                            highest_version_int, highest_version = row[0:2]
                    return highest_version_int, highest_version
            except (mdb.Error, AttributeError) as e:
                #self.logger.error("get_db_version DB Exception %d: %s. Command %s",e.args[0], e.args[1], cmd)
                self._format_error(e, tries)
            tries -= 1

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

    def _format_error(self, e, tries=1, command=None, extra=None): 
        '''Creates a text error base on the produced exception
            Params:
                e: mdb exception
                retry: in case of timeout, if reconnecting to database and retry, or raise and exception
                cmd: database command that produce the exception
                command: if the intention is update or delete
                extra: extra information to add to some commands
            Return
                HTTP error in negative, formatted error text
        '''
        if isinstance(e,AttributeError ):
            raise db_base_Exception("DB Exception " + str(e), HTTP_Internal_Server_Error)
        if e.args[0]==2006 or e.args[0]==2013 : #MySQL server has gone away (((or)))    Exception 2013: Lost connection to MySQL server during query
            if tries>1:
                self.logger.warn("DB Exception '%s'. Retry", str(e))
                #reconnect
                self.connect()
                return
            else:
                raise db_base_Exception("Database connection timeout Try Again", HTTP_Request_Timeout)
        
        fk=e.args[1].find("foreign key constraint fails")
        if fk>=0:
            if command=="update":
                raise db_base_Exception("tenant_id '{}' not found.".format(extra), HTTP_Not_Found)
            elif command=="delete":
                raise db_base_Exception("Resource is not free. There are {} that prevent deleting it.".format(extra), HTTP_Conflict)
        de = e.args[1].find("Duplicate entry")
        fk = e.args[1].find("for key")
        uk = e.args[1].find("Unknown column")
        wc = e.args[1].find("in 'where clause'")
        fl = e.args[1].find("in 'field list'")
        #print de, fk, uk, wc,fl
        if de>=0:
            if fk>=0: #error 1062
                raise db_base_Exception("Value {} already in use for {}".format(e.args[1][de+15:fk], e.args[1][fk+7:]), HTTP_Conflict)
        if uk>=0:
            if wc>=0:
                raise db_base_Exception("Field {} can not be used for filtering".format(e.args[1][uk+14:wc]), HTTP_Bad_Request)
            if fl>=0:
                raise db_base_Exception("Field {} does not exist".format(e.args[1][uk+14:wc]), HTTP_Bad_Request)
        raise db_base_Exception("Database internal Error {}: {}".format(e.args[0], e.args[1]), HTTP_Internal_Server_Error)
    
    def __str2db_format(self, data):
        '''Convert string data to database format. 
        If data is None it returns the 'Null' text,
        otherwise it returns the text surrounded by quotes ensuring internal quotes are escaped.
        '''
        if data==None:
            return 'Null'
        else:
            return json.dumps(str(data))
    
    def __tuple2db_format_set(self, data):
        '''Compose the needed text for a SQL SET, parameter 'data' is a pair tuple (A,B),
        and it returns the text 'A="B"', where A is a field of a table and B is the value 
        If B is None it returns the 'A=Null' text, without surrounding Null by quotes
        If B is not None it returns the text "A='B'" or 'A="B"' where B is surrounded by quotes,
        and it ensures internal quotes of B are escaped.
        '''
        if data[1]==None:
            return str(data[0]) + "=Null"
        else:
            return str(data[0]) + '=' + json.dumps(str(data[1]))
    
    def __tuple2db_format_where(self, data):
        '''Compose the needed text for a SQL WHERE, parameter 'data' is a pair tuple (A,B),
        and it returns the text 'A="B"', where A is a field of a table and B is the value 
        If B is None it returns the 'A is Null' text, without surrounding Null by quotes
        If B is not None it returns the text "A='B'" or 'A="B"' where B is surrounded by quotes,
        and it ensures internal quotes of B are escaped.
        '''
        if data[1]==None:
            return str(data[0]) + " is Null"
        
#         if type(data[1]) is tuple:  #this can only happen in a WHERE_OR clause
#             text =[]
#             for d in data[1]:
#                 if d==None:
#                     text.append(str(data[0]) + " is Null")
#                     continue
#                 out=str(d)
#                 if "'" not in out:
#                     text.append( str(data[0]) + "='" + out + "'" )
#                 elif '"' not in out:
#                     text.append( str(data[0]) + '="' + out + '"' )
#                 else:
#                     text.append( str(data[0]) + '=' + json.dumps(out) )
#             return " OR ".join(text)

        out=str(data[1])
        return str(data[0]) + '=' + json.dumps(out)

    def __tuple2db_format_where_not(self, data):
        '''Compose the needed text for a SQL WHERE(not). parameter 'data' is a pair tuple (A,B),
        and it returns the text 'A<>"B"', where A is a field of a table and B is the value 
        If B is None it returns the 'A is not Null' text, without surrounding Null by quotes
        If B is not None it returns the text "A<>'B'" or 'A<>"B"' where B is surrounded by quotes,
        and it ensures internal quotes of B are escaped.
        '''
        if data[1]==None:
            return str(data[0]) + " is not Null"
        out=str(data[1])
        return str(data[0]) + '<>' + json.dumps(out)
    
    def __remove_quotes(self, data):
        '''remove single quotes ' of any string content of data dictionary'''
        for k,v in data.items():
            if type(v) == str:
                if "'" in v: 
                    data[k] = data[k].replace("'","_")
    
    def _update_rows(self, table, UPDATE, WHERE, modified_time=0):
        ''' Update one or several rows into a table.
        Atributes
            UPDATE: dictionary with the key: value to change
            table: table where to update
            WHERE: dictionary of elements to update
        Return: the number of updated rows, exception if error
        '''
                #gettting uuid 
        values = ",".join(map(self.__tuple2db_format_set, UPDATE.iteritems() ))
        if modified_time:
            values += ",modified_at={:f}".format(modified_time)
        cmd= "UPDATE " + table +" SET " + values +\
            " WHERE " + " and ".join(map(self.__tuple2db_format_where, WHERE.iteritems() ))
        self.logger.debug(cmd)
        self.cur.execute(cmd) 
        return self.cur.rowcount
    
    def _new_row_internal(self, table, INSERT, add_uuid=False, root_uuid=None, created_time=0):
        ''' Add one row into a table. It DOES NOT begin or end the transaction, so self.con.cursor must be created
        Attribute 
            INSERT: dictionary with the key:value to insert
            table: table where to insert
            add_uuid: if True, it will create an uuid key entry at INSERT if not provided
            created_time: time to add to the created_time column
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
            cmd += ",created_at=%f" % created_time
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
    
    def new_row(self, table, INSERT, add_uuid=False, created_time=0):
        ''' Add one row into a table.
        Attribute 
            INSERT: dictionary with the key: value to insert
            table: table where to insert
            tenant_id: only useful for logs. If provided, logs will use this tenant_id
            add_uuid: if True, it will create an uuid key entry at INSERT if not provided
        It checks presence of uuid and add one automatically otherwise
        Return: (result, uuid) where result can be 0 if error, or 1 if ok
        '''
        if table in self.tables_with_created_field and created_time==0:
            created_time=time.time()
        tries = 2
        while tries:
            try:
                with self.con:
                    self.cur = self.con.cursor()
                    return self._new_row_internal(table, INSERT, add_uuid, None, created_time)
                    
            except (mdb.Error, AttributeError) as e:
                self._format_error(e, tries)
            tries -= 1

    def update_rows(self, table, UPDATE, WHERE, modified_time=0):
        ''' Update one or several rows into a table.
        Atributes
            UPDATE: dictionary with the key: value to change
            table: table where to update
            WHERE: dictionary of elements to update
        Return: (result, descriptive text) where result indicates the number of updated files
        '''
        if table in self.tables_with_created_field and modified_time==0:
            modified_time=time.time()
        tries = 2
        while tries:
            try:
                with self.con:
                    self.cur = self.con.cursor()
                    return self._update_rows(table, UPDATE, WHERE)
                    
            except (mdb.Error, AttributeError) as e:
                self._format_error(e, tries)
            tries -= 1

    def delete_row_by_id(self, table, uuid):
        tries = 2
        while tries:
            try:
                with self.con:
                    #delete host
                    self.cur = self.con.cursor()
                    cmd = "DELETE FROM {} WHERE uuid = '{}'".format(table, uuid)
                    self.logger.debug(cmd)
                    self.cur.execute(cmd)
                    deleted = self.cur.rowcount
                    if deleted:
                        #delete uuid
                        self.cur = self.con.cursor()
                        cmd = "DELETE FROM uuids WHERE root_uuid = '{}'".format(uuid)
                        self.logger.debug(cmd)
                        self.cur.execute(cmd)
                return deleted
            except (mdb.Error, AttributeError) as e:
                self._format_error(e, tries, "delete", "dependencies")
            tries -= 1

    def delete_row(self, **sql_dict):
        ''' Deletes rows from a table.
        Attribute sql_dir: dictionary with the following key: value
            'FROM': string of table name (Mandatory)
            'WHERE': dict of key:values, translated to key=value AND ... (Optional)
            'WHERE_NOT': dict of key:values, translated to key<>value AND ... (Optional) 
                if value is None, it is translated to key is not null
            'LIMIT': limit of number of rows (Optional)
        Return: the number of deleted or exception if error
        '''
        #print sql_dict
        from_  = "FROM " + str(sql_dict['FROM'])
        #print 'from_', from_
        if 'WHERE' in sql_dict and len(sql_dict['WHERE']) > 0:
            w=sql_dict['WHERE']
            where_ = "WHERE " + " AND ".join(map(self.__tuple2db_format_where, w.iteritems())) 
        else: where_ = ""
        if 'WHERE_NOT' in sql_dict and len(sql_dict['WHERE_NOT']) > 0: 
            w=sql_dict['WHERE_NOT']
            where_2 = " AND ".join(map(self.__tuple2db_format_where_not, w.iteritems()))
            if len(where_)==0:   where_ = "WHERE " + where_2
            else:                where_ = where_ + " AND " + where_2
        #print 'where_', where_
        limit_ = "LIMIT " + str(sql_dict['LIMIT']) if 'LIMIT' in sql_dict else ""
        #print 'limit_', limit_
        cmd =  " ".join( ("DELETE", from_, where_, limit_) )
        tries = 2
        while tries:
            try:
                with self.con:
                    self.cur = self.con.cursor()
                    self.logger.debug(cmd)
                    self.cur.execute(cmd)
                    deleted = self.cur.rowcount
                return deleted
            except (mdb.Error, AttributeError) as e:
                self._format_error(e, tries)
            tries -= 1

    def get_rows_by_id(self, table, uuid):
        '''get row from a table based on uuid'''
        tries = 2
        while tries:
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    cmd="SELECT * FROM {} where uuid='{}'".format(str(table), str(uuid))
                    self.logger.debug(cmd)
                    self.cur.execute(cmd)
                    rows = self.cur.fetchall()
                    return rows
            except (mdb.Error, AttributeError) as e:
                self._format_error(e, tries)
            tries -= 1
    
    def get_rows(self, **sql_dict):
        ''' Obtain rows from a table.
        Attribute sql_dir: dictionary with the following key: value
            'SELECT':    list or tuple of fields to retrieve) (by default all)
            'FROM':      string of table name (Mandatory)
            'WHERE':     dict of key:values, translated to key=value (key is null) AND ... (Optional)
            'WHERE_NOT': dict of key:values, translated to key<>value (key is not null) AND ... (Optional)
            'WHERE_OR': dict of key:values, translated to key=value OR ... (Optional)
            'WHERE_AND_OR: str 'AND' or 'OR'(by default) mark the priority to 'WHERE AND (WHERE_OR)' or (WHERE) OR WHERE_OR' (Optional)
            'LIMIT':     limit of number of rows (Optional)
            'ORDER_BY':  list or tuple of fields to order
        Return: a list with dictionaries at each row
        '''
        #print sql_dict
        select_= "SELECT " + ("*" if 'SELECT' not in sql_dict else ",".join(map(str,sql_dict['SELECT'])) )
        #print 'select_', select_
        from_  = "FROM " + str(sql_dict['FROM'])
        #print 'from_', from_
        where_and = ""
        where_or = ""
        w=sql_dict.get('WHERE')
        if w:
            where_and = " AND ".join(map(self.__tuple2db_format_where, w.iteritems() ))
        w=sql_dict.get('WHERE_NOT')
        if w: 
            if where_and: where_and += " AND "
            where_and += " AND ".join(map(self.__tuple2db_format_where_not, w.iteritems() ) )
        w=sql_dict.get('WHERE_OR')
        if w:
            where_or =  " OR ".join(map(self.__tuple2db_format_where, w.iteritems() ))
        if where_and and where_or:
            if sql_dict.get("WHERE_AND_OR") == "AND":
                where_ = "WHERE " + where_and + " AND (" + where_or + ")"
            else:
                where_ = "WHERE (" + where_and + ") OR " + where_or
        elif where_and and not where_or:
            where_ = "WHERE " + where_and
        elif not where_and and where_or:
            where_ = "WHERE " + where_or
        else:
            where_ = ""
        #print 'where_', where_
        limit_ = "LIMIT " + str(sql_dict['LIMIT']) if 'LIMIT' in sql_dict else ""
        order_ = "ORDER BY " + ",".join(map(str,sql_dict['SELECT'])) if 'ORDER_BY' in sql_dict else ""
        
        #print 'limit_', limit_
        cmd =  " ".join( (select_, from_, where_, limit_, order_) )
        tries = 2
        while tries:
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    self.logger.debug(cmd)
                    self.cur.execute(cmd)
                    rows = self.cur.fetchall()
                    return rows
            except (mdb.Error, AttributeError) as e:
                self._format_error(e, tries)
            tries -= 1

    def get_table_by_uuid_name(self, table, uuid_name, error_item_text=None, allow_serveral=False, WHERE_OR={}, WHERE_AND_OR="OR"):
        ''' Obtain One row from a table based on name or uuid.
        Attribute:
            table: string of table name
            uuid_name: name or uuid. If not uuid format is found, it is considered a name
            allow_severeral: if False return ERROR if more than one row are founded 
            error_item_text: in case of error it identifies the 'item' name for a proper output text 
            'WHERE_OR': dict of key:values, translated to key=value OR ... (Optional)
            'WHERE_AND_OR: str 'AND' or 'OR'(by default) mark the priority to 'WHERE AND (WHERE_OR)' or (WHERE) OR WHERE_OR' (Optional  
        Return: if allow_several==False, a dictionary with this row, or error if no item is found or more than one is found
                if allow_several==True, a list of dictionaries with the row or rows, error if no item is found
        '''

        if error_item_text==None:
            error_item_text = table
        what = 'uuid' if af.check_valid_uuid(uuid_name) else 'name'
        cmd =  " SELECT * FROM {} WHERE {}='{}'".format(table, what, uuid_name)
        if WHERE_OR:
            where_or =  " OR ".join(map(self.__tuple2db_format_where, WHERE_OR.iteritems() ))
            if WHERE_AND_OR == "AND":
                cmd += " AND (" + where_or + ")"
            else:
                cmd += " OR " + where_or

        
        tries = 2
        while tries:
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    self.logger.debug(cmd)
                    self.cur.execute(cmd)
                    number = self.cur.rowcount
                    if number==0:
                        return -HTTP_Not_Found, "No %s found with %s '%s'" %(error_item_text, what, uuid_name)
                    elif number>1 and not allow_serveral: 
                        return -HTTP_Bad_Request, "More than one %s found with %s '%s'" %(error_item_text, what, uuid_name)
                    if allow_serveral:
                        rows = self.cur.fetchall()
                    else:
                        rows = self.cur.fetchone()
                    return rows
            except (mdb.Error, AttributeError) as e:
                self._format_error(e, tries)
            tries -= 1

    def get_uuid(self, uuid):
        '''check in the database if this uuid is already present'''
        for retry_ in range(0,2):
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    self.cur.execute("SELECT * FROM uuids where uuid='" + str(uuid) + "'")
                    rows = self.cur.fetchall()
                    return self.cur.rowcount, rows
            except (mdb.Error, AttributeError) as e:
                print "nfvo_db.get_uuid DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self._format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def get_uuid_from_name(self, table, name):
        '''Searchs in table the name and returns the uuid
        ''' 
        tries = 2
        while tries:
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    where_text = "name='" + name +"'"
                    self.cur.execute("SELECT * FROM " + table + " WHERE "+ where_text)
                    rows = self.cur.fetchall()
                    if self.cur.rowcount==0:
                        return 0, "Name %s not found in table %s" %(name, table)
                    elif self.cur.rowcount>1:
                        return self.cur.rowcount, "More than one VNF with name %s found in table %s" %(name, table)
                    return self.cur.rowcount, rows[0]["uuid"]
            except (mdb.Error, AttributeError) as e:
                self._format_error(e, tries)
            tries -= 1

