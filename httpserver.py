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
HTTP server implementing the openmano API. It will answer to POST, PUT, GET methods in the appropriate URLs
and will use the nfvo.py module to run the appropriate method.
Every YAML/JSON file is checked against a schema in openmano_schemas.py module.  
'''
__author__="Alfonso Tierno, Gerardo Garcia"
__date__ ="$17-sep-2014 09:07:15$"

import bottle
import yaml
import json
import threading
import time

from jsonschema import validate as js_v, exceptions as js_e
from openmano_schemas import vnfd_schema_v01, vnfd_schema_v02, \
                            nsd_schema_v01, nsd_schema_v02, scenario_edit_schema, \
                            scenario_action_schema, instance_scenario_action_schema, instance_scenario_create_schema, \
                            tenant_schema, tenant_edit_schema,\
                            datacenter_schema, datacenter_edit_schema, datacenter_action_schema, datacenter_associate_schema,\
                            object_schema, netmap_new_schema, netmap_edit_schema
import nfvo
import utils

global mydb
global url_base
url_base="/openmano"

HTTP_Bad_Request =          400
HTTP_Unauthorized =         401 
HTTP_Not_Found =            404 
HTTP_Forbidden =            403
HTTP_Method_Not_Allowed =   405 
HTTP_Not_Acceptable =       406
HTTP_Service_Unavailable =  503 
HTTP_Internal_Server_Error= 500 

def delete_nulls(var):
    if type(var) is dict:
        for k in var.keys():
            if var[k] is None: del var[k]
            elif type(var[k]) is dict or type(var[k]) is list or type(var[k]) is tuple: 
                if delete_nulls(var[k]): del var[k]
        if len(var) == 0: return True
    elif type(var) is list or type(var) is tuple:
        for k in var:
            if type(k) is dict: delete_nulls(k)
        if len(var) == 0: return True
    return False

def convert_datetime2str(var):
    '''Converts a datetime variable to a string with the format '%Y-%m-%dT%H:%i:%s'
    It enters recursively in the dict var finding this kind of variables
    '''
    if type(var) is dict:
        for k,v in var.items():
            if type(v) is float and k in ("created_at", "modified_at"):
                var[k] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(v) )
            elif type(v) is dict or type(v) is list or type(v) is tuple: 
                convert_datetime2str(v)
        if len(var) == 0: return True
    elif type(var) is list or type(var) is tuple:
        for v in var:
            convert_datetime2str(v)


class httpserver(threading.Thread):
    def __init__(self, db, admin=False, host='localhost', port=9090):
        #global url_base
        global mydb
        #initialization
        threading.Thread.__init__(self)
        self.host = host
        self.port = port   #Port where the listen service must be started
        if admin==True:
            self.name = "http_admin"
        else:
            self.name = "http"
            #self.url_preffix = 'http://' + host + ':' + str(port) + url_base
            mydb = db
        #self.first_usable_connection_index = 10
        #self.next_connection_index = self.first_usable_connection_index #The next connection index to be used 
        #Ensure that when the main program exits the thread will also exit
        self.daemon = True
        self.setDaemon(True)
         
    def run(self):
        bottle.run(host=self.host, port=self.port, debug=True) #quiet=True
           
def run_bottle(db, host_='localhost', port_=9090):
    '''used for launching in main thread, so that it can be debugged'''
    global mydb
    mydb = db
    bottle.run(host=host_, port=port_, debug=True) #quiet=True
    

@bottle.route(url_base + '/', method='GET')
def http_get():
    print 
    return 'works' #TODO: to be completed

#
# Util functions
#

def change_keys_http2db(data, http_db, reverse=False):
    '''Change keys of dictionary data acording to the key_dict values
    This allow change from http interface names to database names.
    When reverse is True, the change is otherwise
    Attributes:
        data: can be a dictionary or a list
        http_db: is a dictionary with hhtp names as keys and database names as value
        reverse: by default change is done from http api to database. If True change is done otherwise
    Return: None, but data is modified'''
    if type(data) is tuple or type(data) is list:
        for d in data:
            change_keys_http2db(d, http_db, reverse)
    elif type(data) is dict or type(data) is bottle.FormsDict:
        if reverse:
            for k,v in http_db.items():
                if v in data: data[k]=data.pop(v)
        else:
            for k,v in http_db.items():
                if k in data: data[v]=data.pop(k)

def format_out(data):
    '''return string of dictionary data according to requested json, yaml, xml. By default json'''
    if 'application/yaml' in bottle.request.headers.get('Accept'):
        bottle.response.content_type='application/yaml'
        print yaml.safe_dump(data, explicit_start=True, indent=4, default_flow_style=False, tags=False, encoding='utf-8', allow_unicode=True) 
        return yaml.safe_dump(data, explicit_start=True, indent=4, default_flow_style=False, tags=False, encoding='utf-8', allow_unicode=True) #, canonical=True, default_style='"'
    else: #by default json
        bottle.response.content_type='application/json'
        #return data #json no style
        return json.dumps(data, indent=4) + "\n"

def format_in(default_schema, version_fields=None, version_dict_schema=None):
    ''' Parse the content of HTTP request against a json_schema
        Parameters
            default_schema: The schema to be parsed by default if no version field is found in the client data
            version_fields: If provided it contains a tuple or list with the fields to iterate across the client data to obtain the version
            version_dict_schema: It contains a dictionary with the version as key, and json schema to apply as value
                It can contain a None as key, and this is apply if the client data version does not match any key 
        Return:
            user_data, used_schema: if the data is successfully decoded and matches the schema
            launch a bottle abort if fails
    '''
    #print "HEADERS :" + str(bottle.request.headers.items())
    try:
        error_text = "Invalid header format "
        format_type = bottle.request.headers.get('Content-Type', 'application/json')
        if 'application/json' in format_type:
            error_text = "Invalid json format "
            #Use the json decoder instead of bottle decoder because it informs about the location of error formats with a ValueError exception
            client_data = json.load(bottle.request.body)
            #client_data = bottle.request.json()
        elif 'application/yaml' in format_type:
            error_text = "Invalid yaml format "
            client_data = yaml.load(bottle.request.body)
        elif 'application/xml' in format_type:
            bottle.abort(501, "Content-Type: application/xml not supported yet.")
        else:
            print 'Content-Type ' + str(format_type) + ' not supported.'
            bottle.abort(HTTP_Not_Acceptable, 'Content-Type ' + str(format_type) + ' not supported.')
            return
        #if client_data == None:
        #    bottle.abort(HTTP_Bad_Request, "Content error, empty")
        #    return

        #look for the client provider version
        error_text = "Invalid content "
        client_version = None
        used_schema = None
        if version_fields != None:
            client_version = client_data
            for field in version_fields:
                if field in client_version:
                    client_version = client_version[field]
                else:
                    client_version=None
                    break
        if client_version==None:
            used_schema=default_schema
        elif version_dict_schema!=None:
            if client_version in version_dict_schema:
                used_schema = version_dict_schema[client_version]
            elif None in version_dict_schema:
                used_schema = version_dict_schema[None]
        if used_schema==None:
            bottle.abort(HTTP_Bad_Request, "Invalid schema version or missing version field")
            
        js_v(client_data, used_schema)
        return client_data, used_schema
    except (ValueError, yaml.YAMLError) as exc:
        error_text += str(exc)
        print error_text 
        bottle.abort(HTTP_Bad_Request, error_text)
    except js_e.ValidationError as exc:
        print "validate_in error, jsonschema exception ", exc.message, "at", exc.path
        error_pos = ""
        if len(exc.path)>0: error_pos=" at " + ":".join(map(json.dumps, exc.path))
        bottle.abort(HTTP_Bad_Request, error_text + exc.message + error_pos)
    #except:
    #    bottle.abort(HTTP_Bad_Request, "Content error: Failed to parse Content-Type",  error_pos)
    #    raise

def filter_query_string(qs, http2db, allowed):
    '''Process query string (qs) checking that contains only valid tokens for avoiding SQL injection
    Attributes:
        'qs': bottle.FormsDict variable to be processed. None or empty is considered valid
        'http2db': dictionary with change from http API naming (dictionary key) to database naming(dictionary value)
        'allowed': list of allowed string tokens (API http naming). All the keys of 'qs' must be one of 'allowed'
    Return: A tuple with the (select,where,limit) to be use in a database query. All of then transformed to the database naming
        select: list of items to retrieve, filtered by query string 'field=token'. If no 'field' is present, allowed list is returned
        where: dictionary with key, value, taken from the query string token=value. Empty if nothing is provided
        limit: limit dictated by user with the query string 'limit'. 100 by default
    abort if not permited, using bottel.abort
    '''
    where={}
    limit=100
    select=[]
    if type(qs) is not bottle.FormsDict:
        print '!!!!!!!!!!!!!!invalid query string not a dictionary'
        #bottle.abort(HTTP_Internal_Server_Error, "call programmer")
    else:
        for k in qs:
            if k=='field':
                select += qs.getall(k)
                for v in select:
                    if v not in allowed:
                        bottle.abort(HTTP_Bad_Request, "Invalid query string at 'field="+v+"'")
            elif k=='limit':
                try:
                    limit=int(qs[k])
                except:
                    bottle.abort(HTTP_Bad_Request, "Invalid query string at 'limit="+qs[k]+"'")
            else:
                if k not in allowed:
                    bottle.abort(HTTP_Bad_Request, "Invalid query string at '"+k+"="+qs[k]+"'")
                if qs[k]!="null":  where[k]=qs[k]
                else: where[k]=None 
    if len(select)==0: select += allowed
    #change from http api to database naming
    for i in range(0,len(select)):
        k=select[i]
        if http2db and k in http2db: 
            select[i] = http2db[k]
    if http2db:
        change_keys_http2db(where, http2db)
    print "filter_query_string", select,where,limit
    
    return select,where,limit

@bottle.hook('after_request')
def enable_cors():
    '''Don't know yet if really needed. Keep it just in case'''
    bottle.response.headers['Access-Control-Allow-Origin'] = '*'

#
# VNFs
#

@bottle.route(url_base + '/tenants', method='GET')
def http_get_tenants():
    select_,where_,limit_ = filter_query_string(bottle.request.query, None,
            ('uuid','name','description','created_at') )
    result, content = mydb.get_table(FROM='nfvo_tenants', SELECT=select_,WHERE=where_,LIMIT=limit_)
    if result < 0:
        print "http_get_tenants Error", content
        bottle.abort(-result, content)
    else:
        #change_keys_http2db(content, http2db_tenant, reverse=True)
        convert_datetime2str(content)
        data={'tenants' : content}
        return format_out(data)

@bottle.route(url_base + '/tenants/<tenant_id>', method='GET')
def http_get_tenant_id(tenant_id):
    '''get tenant details, can use both uuid or name'''
    #obtain data
    result, content = mydb.get_table_by_uuid_name('nfvo_tenants', tenant_id, "tenant") 
    if result < 0:
        print "http_get_tenant_id error %d %s" % (result, content)
        bottle.abort(-result, content)
    #change_keys_http2db(content, http2db_tenant, reverse=True)
    convert_datetime2str(content)
    print content
    data={'tenant' : content}
    return format_out(data)

@bottle.route(url_base + '/tenants', method='POST')
def http_post_tenants():
    '''insert a tenant into the catalogue. '''
    #parse input data
    http_content,_ = format_in( tenant_schema )
    r = utils.remove_extra_items(http_content, tenant_schema)
    if r is not None: print "http_post_tenants: Warning: remove extra items ", r
    result, data = nfvo.new_tenant(mydb, http_content['tenant'])
    if result < 0:
        print "http_post_tenants error %d %s" % (-result, data)
        bottle.abort(-result, data)
    else:
        return http_get_tenant_id(data)

@bottle.route(url_base + '/tenants/<tenant_id>', method='PUT')
def http_edit_tenant_id(tenant_id):
    '''edit tenant details, can use both uuid or name'''
    #parse input data
    http_content,_ = format_in( tenant_edit_schema )
    r = utils.remove_extra_items(http_content, tenant_edit_schema)
    if r is not None: print "http_edit_tenant_id: Warning: remove extra items ", r
    
    #obtain data, check that only one exist
    result, content = mydb.get_table_by_uuid_name('nfvo_tenants', tenant_id)
    if result < 0:
        print "http_edit_tenant_id error %d %s" % (result, content)
        bottle.abort(-result, content)
    
    #edit data 
    tenant_id = content['uuid']
    where={'uuid': content['uuid']}
    result, content = mydb.update_rows('nfvo_tenants', http_content['tenant'], where)
    if result < 0:
        print "http_edit_tenant_id error %d %s" % (result, content)
        bottle.abort(-result, content)

    return http_get_tenant_id(tenant_id)

@bottle.route(url_base + '/tenants/<tenant_id>', method='DELETE')
def http_delete_tenant_id(tenant_id):
    '''delete a tenant from database, can use both uuid or name'''
    
    result, data = nfvo.delete_tenant(mydb, tenant_id)
    if result < 0:
        print "http_delete_tenant_id error %d %s" % (-result, data)
        bottle.abort(-result, data)
    else:
        #print json.dumps(data, indent=4)
        return format_out({"result":"tenant " + data + " deleted"})
    

@bottle.route(url_base + '/<tenant_id>/datacenters', method='GET')
def http_get_datacenters(tenant_id):
    #check valid tenant_id
    if tenant_id != 'any':
        if not nfvo.check_tenant(mydb, tenant_id): 
            print 'httpserver.http_get_datacenters () tenant %s not found' % tenant_id
            bottle.abort(HTTP_Not_Found, 'Tenant %s not found' % tenant_id)
            return
    select_,where_,limit_ = filter_query_string(bottle.request.query, None,
            ('uuid','name','vim_url','type','created_at') )
    if tenant_id != 'any':
        where_['nfvo_tenant_id'] = tenant_id
        if 'created_at' in select_:
            select_[ select_.index('created_at') ] = 'd.created_at as created_at'
        if 'created_at' in where_:
            where_['d.created_at'] = where_.pop('created_at')
        result, content = mydb.get_table(FROM='datacenters as d join tenants_datacenters as td on d.uuid=td.datacenter_id',
                                      SELECT=select_,WHERE=where_,LIMIT=limit_)
    else:
        result, content = mydb.get_table(FROM='datacenters',
                                      SELECT=select_,WHERE=where_,LIMIT=limit_)
    if result < 0:
        print "http_get_datacenters Error", content
        bottle.abort(-result, content)
    else:
        #change_keys_http2db(content, http2db_tenant, reverse=True)
        convert_datetime2str(content)
        data={'datacenters' : content}
        return format_out(data)

@bottle.route(url_base + '/<tenant_id>/datacenters/<datacenter_id>', method='GET')
def http_get_datacenter_id(tenant_id, datacenter_id):
    '''get datacenter details, can use both uuid or name'''
    #check valid tenant_id
    if tenant_id != 'any':
        if not nfvo.check_tenant(mydb, tenant_id): 
            print 'httpserver.http_get_datacenter_id () tenant %s not found' % tenant_id
            bottle.abort(HTTP_Not_Found, 'Tenant %s not found' % tenant_id)
            return
    #obtain data
    what = 'uuid' if utils.check_valid_uuid(datacenter_id) else 'name'
    where_={}
    where_[what] = datacenter_id
    select_=['uuid', 'name','vim_url', 'vim_url_admin', 'type', 'config', 'description', 'd.created_at as created_at']
    if tenant_id != 'any':
        select_.append("datacenter_tenant_id")
        where_['td.nfvo_tenant_id']= tenant_id
        from_='datacenters as d join tenants_datacenters as td on d.uuid=td.datacenter_id'
    else:
        from_='datacenters as d'
    result, content = mydb.get_table(
                SELECT=select_,
                FROM=from_,
                WHERE=where_)

    if result < 0:
        print "http_get_datacenter_id error %d %s" % (result, content)
        bottle.abort(-result, content)
    elif result==0:
        bottle.abort( HTTP_Not_Found, "No datacenter found for tenant with %s '%s'" %(what, datacenter_id) )
    elif result>1: 
        bottle.abort( HTTP_Bad_Request, "More than one datacenter found for tenant with %s '%s'" %(what, datacenter_id) )

    if tenant_id != 'any':
        #get vim tenant info
        result, content2 = mydb.get_table(
                SELECT=("vim_tenant_name", "vim_tenant_id", "user"),
                FROM="datacenter_tenants",
                WHERE={"uuid": content[0]["datacenter_tenant_id"]},
                ORDER_BY=("created", ) )
        del content[0]["datacenter_tenant_id"]
        if result < 0:
            print "http_get_datacenter_id vim_tenant_info error %d %s" % (result, content2)
            bottle.abort(-result, content2)
        content[0]["vim_tenants"] = content2

    print content
    if content[0]['config'] != None:
        try:
            config_dict = yaml.load(content[0]['config'])
            content[0]['config'] = config_dict
        except Exception, e:
            print "Exception '%s' while trying to load config information" % str(e)
    #change_keys_http2db(content, http2db_datacenter, reverse=True)
    convert_datetime2str(content[0])
    data={'datacenter' : content[0]}
    return format_out(data)

@bottle.route(url_base + '/datacenters', method='POST')
def http_post_datacenters():
    '''insert a tenant into the catalogue. '''
    #parse input data
    http_content,_ = format_in( datacenter_schema )
    r = utils.remove_extra_items(http_content, datacenter_schema)
    if r is not None: print "http_post_tenants: Warning: remove extra items ", r
    result, data = nfvo.new_datacenter(mydb, http_content['datacenter'])
    if result < 0:
        print "http_post_datacenters error %d %s" % (-result, data)
        bottle.abort(-result, data)
    else:
        return http_get_datacenter_id('any', data)

@bottle.route(url_base + '/datacenters/<datacenter_id_name>', method='PUT')
def http_edit_datacenter_id(datacenter_id_name):
    '''edit datacenter details, can use both uuid or name'''
    #parse input data
    http_content,_ = format_in( datacenter_edit_schema )
    r = utils.remove_extra_items(http_content, datacenter_edit_schema)
    if r is not None: print "http_edit_datacenter_id: Warning: remove extra items ", r
    
    
    result, datacenter_id = nfvo.edit_datacenter(mydb, datacenter_id_name, http_content['datacenter'])
    if result < 0:
        print "http_edit_datacenter_id error %d %s" % (-result, datacenter_id)
        bottle.abort(-result, datacenter_id)
    else:
        return http_get_datacenter_id('any', datacenter_id)

@bottle.route(url_base + '/<tenant_id>/datacenters/<datacenter_id>/networks', method='GET')  #deprecated
@bottle.route(url_base + '/<tenant_id>/datacenters/<datacenter_id>/netmaps', method='GET')
@bottle.route(url_base + '/<tenant_id>/datacenters/<datacenter_id>/netmaps/<netmap_id>', method='GET')
def http_getnetmap_datacenter_id(tenant_id, datacenter_id, netmap_id=None):
    '''get datacenter networks, can use both uuid or name'''
    #obtain data
    result, datacenter_dict = mydb.get_table_by_uuid_name('datacenters', datacenter_id, "datacenter") 
    if result < 0:
        print "http_getnetwork_datacenter_id error %d %s" % (result, datacenter_dict)
        bottle.abort(-result, datacenter_dict)
    where_= {"datacenter_id":datacenter_dict['uuid']}
    if netmap_id:
        if utils.check_valid_uuid(netmap_id):
            where_["uuid"] = netmap_id
        else:
            where_["name"] = netmap_id
    result, content =mydb.get_table(FROM='datacenter_nets',
                                    SELECT=('name','vim_net_id as vim_id', 'uuid', 'type','multipoint','shared','description', 'created_at'),
                                    WHERE=where_ ) 
    if result < 0:
        print "http_getnetwork_datacenter_id error %d %s" % (result, content)
        bottle.abort(-result, content)

    convert_datetime2str(content)
    utils.convert_str2boolean(content, ('shared', 'multipoint') )
    if netmap_id and len(content)==1:
        data={'netmap' : content[0]}
    elif netmap_id and len(content)==0:
        bottle.abort(HTTP_Not_Found, "No netmap found with " + " and ".join(map(lambda x: str(x[0])+": "+str(x[1]), where_.iteritems())) )
        return 
    else:
        data={'netmaps' : content}
    return format_out(data)

@bottle.route(url_base + '/<tenant_id>/datacenters/<datacenter_id>/netmaps', method='DELETE')
@bottle.route(url_base + '/<tenant_id>/datacenters/<datacenter_id>/netmaps/<netmap_id>', method='DELETE')
def http_delnetmap_datacenter_id(tenant_id, datacenter_id, netmap_id=None):
    '''get datacenter networks, can use both uuid or name'''
    #obtain data
    result, datacenter_dict = mydb.get_table_by_uuid_name('datacenters', datacenter_id, "datacenter") 
    if result < 0:
        print "http_delnetmap_datacenter_id error %d %s" % (result, datacenter_dict)
        bottle.abort(-result, datacenter_dict)
    where_= {"datacenter_id":datacenter_dict['uuid']}
    if netmap_id:
        if utils.check_valid_uuid(netmap_id):
            where_["uuid"] = netmap_id
        else:
            where_["name"] = netmap_id
    #change_keys_http2db(content, http2db_tenant, reverse=True)
    result, content =mydb.delete_row_by_dict(FROM='datacenter_nets', WHERE= where_) 
    if result < 0:
        print "http_delnetmap_datacenter_id error %d %s" % (result, content)
        bottle.abort(-result, content)
    elif result == 0 and netmap_id :
        bottle.abort(HTTP_Not_Found, "No netmap found with " + " and ".join(map(lambda x: str(x[0])+": "+str(x[1]), where_.iteritems())) )
    if netmap_id:
        return format_out({"result": "netmap %s deleted" % netmap_id})
    else:
        return format_out({"result": "%d netmap deleted" % result})


@bottle.route(url_base + '/<tenant_id>/datacenters/<datacenter_id>/netmaps/upload', method='POST')
def http_uploadnetmap_datacenter_id(tenant_id, datacenter_id):
    result, content = nfvo.datacenter_new_netmap(mydb, tenant_id, datacenter_id, None)
    if result < 0:
        print "http_postnetmap_datacenter_id error %d %s" % (result, content)
        bottle.abort(-result, content)
    convert_datetime2str(content)
    utils.convert_str2boolean(content, ('shared', 'multipoint') )
    print content
    data={'netmaps' : content}
    return format_out(data)

@bottle.route(url_base + '/<tenant_id>/datacenters/<datacenter_id>/netmaps', method='POST')
def http_postnetmap_datacenter_id(tenant_id, datacenter_id):
    '''creates a new netmap'''
    #parse input data
    http_content,_ = format_in( netmap_new_schema )
    r = utils.remove_extra_items(http_content, netmap_new_schema)
    if r is not None: print "http_action_datacenter_id: Warning: remove extra items ", r
    
    #obtain data, check that only one exist
    result, content = nfvo.datacenter_new_netmap(mydb, tenant_id, datacenter_id, http_content)
    if result < 0:
        print "http_postnetmap_datacenter_id error %d %s" % (result, content)
        bottle.abort(-result, content)
    convert_datetime2str(content)
    utils.convert_str2boolean(content, ('shared', 'multipoint') )
    print content
    data={'netmaps' : content}
    return format_out(data)

@bottle.route(url_base + '/<tenant_id>/datacenters/<datacenter_id>/netmaps/<netmap_id>', method='PUT')
def http_putnettmap_datacenter_id(tenant_id, datacenter_id, netmap_id):
    '''edit a  netmap'''
    #parse input data
    http_content,_ = format_in( netmap_edit_schema )
    r = utils.remove_extra_items(http_content, netmap_edit_schema)
    if r is not None: print "http_putnettmap_datacenter_id: Warning: remove extra items ", r
    
    #obtain data, check that only one exist
    result, content = nfvo.datacenter_edit_netmap(mydb, tenant_id, datacenter_id, netmap_id, http_content)
    if result < 0:
        print "http_putnettmap_datacenter_id error %d %s" % (result, content)
        bottle.abort(-result, content)
    else:
        return http_getnetmap_datacenter_id(tenant_id, datacenter_id, netmap_id)
    

@bottle.route(url_base + '/<tenant_id>/datacenters/<datacenter_id>/action', method='POST')
def http_action_datacenter_id(tenant_id, datacenter_id):
    '''perform an action over datacenter, can use both uuid or name'''
    #parse input data
    http_content,_ = format_in( datacenter_action_schema )
    r = utils.remove_extra_items(http_content, datacenter_action_schema)
    if r is not None: print "http_action_datacenter_id: Warning: remove extra items ", r
    
    #obtain data, check that only one exist
    result, content = nfvo.datacenter_action(mydb, tenant_id, datacenter_id, http_content)
    if result < 0:
        print "http_action_datacenter_id error %d %s" % (result, content)
        bottle.abort(-result, content)
    if 'net-update' in http_content:
        return http_getnetmap_datacenter_id(datacenter_id)
    else:
        return format_out(content)


@bottle.route(url_base + '/datacenters/<datacenter_id>', method='DELETE')
def http_delete_datacenter_id( datacenter_id):
    '''delete a tenant from database, can use both uuid or name'''
    
    result, data = nfvo.delete_datacenter(mydb, datacenter_id)
    if result < 0:
        print "http_delete_datacenter_id error %d %s" % (-result, data)
        bottle.abort(-result, data)
    else:
        #print json.dumps(data, indent=4)
        return format_out({"result":"datacenter " + data + " deleted"})

@bottle.route(url_base + '/<tenant_id>/datacenters/<datacenter_id>', method='POST')
def http_associate_datacenters(tenant_id, datacenter_id):
    '''associate an existing datacenter to a this tenant. '''
    #parse input data
    http_content,_ = format_in( datacenter_associate_schema )
    r = utils.remove_extra_items(http_content, datacenter_associate_schema)
    if r != None: print "http_associate_datacenters: Warning: remove extra items ", r
    result, data = nfvo.associate_datacenter_to_tenant(mydb, tenant_id, datacenter_id, 
                                http_content['datacenter'].get('vim_tenant'),
                                http_content['datacenter'].get('vim_tenant_name'),
                                http_content['datacenter'].get('vim_username'),
                                http_content['datacenter'].get('vim_password')
                     )
    if result < 0:
        print "http_associate_datacenters error %d %s" % (-result, data)
        bottle.abort(-result, data)
    else:
        print "http_associate_datacenters data" , data 
        return http_get_datacenter_id(tenant_id, data)

@bottle.route(url_base + '/<tenant_id>/datacenters/<datacenter_id>', method='DELETE')
def http_deassociate_datacenters(tenant_id, datacenter_id):
    '''deassociate an existing datacenter to a this tenant. '''
    result, data = nfvo.deassociate_datacenter_to_tenant(mydb, tenant_id, datacenter_id)
    if result < 0:
        print "http_deassociate_datacenters error %d %s" % (-result, data)
        bottle.abort(-result, data)
    else:
        return format_out({"result":data})
       


@bottle.route(url_base + '/<tenant_id>/vim/<datacenter_id>/<item>', method='GET')
@bottle.route(url_base + '/<tenant_id>/vim/<datacenter_id>/<item>/<name>', method='GET')
def http_get_vim_items(tenant_id, datacenter_id, item, name=None):
    result, data = nfvo.vim_action_get(mydb, tenant_id, datacenter_id, item, name)
    if result < 0:
        print "http_get_vim_items error %d %s" % (-result, data)
        bottle.abort(-result, data)
    else:
        return format_out(data)

@bottle.route(url_base + '/<tenant_id>/vim/<datacenter_id>/<item>/<name>', method='DELETE')
def http_del_vim_items(tenant_id, datacenter_id, item, name):
    result, data = nfvo.vim_action_delete(mydb, tenant_id, datacenter_id, item, name)
    if result < 0:
        print "http_get_vim_items error %d %s" % (-result, data)
        bottle.abort(-result, data)
    else:
        return format_out({"result":data})

@bottle.route(url_base + '/<tenant_id>/vim/<datacenter_id>/<item>', method='POST')
def http_post_vim_items(tenant_id, datacenter_id, item):
    http_content,_ = format_in( object_schema )
    result, data = nfvo.vim_action_create(mydb, tenant_id, datacenter_id, item, http_content)
    if result < 0:
        print "http_post_vim_items error %d %s" % (-result, data)
        bottle.abort(-result, data)
    else:
        return format_out(data)

@bottle.route(url_base + '/<tenant_id>/vnfs', method='GET')
def http_get_vnfs(tenant_id):
    #check valid tenant_id
    if tenant_id != "any" and not nfvo.check_tenant(mydb, tenant_id): 
        print 'httpserver.http_get_vnf_id() tenant %s not found' % tenant_id
        bottle.abort(HTTP_Not_Found, 'Tenant %s not found' % tenant_id)
        return
    select_,where_,limit_ = filter_query_string(bottle.request.query, None,
            ('uuid','name','description','public', "tenant_id", "created_at") )
    where_or = {}
    if tenant_id != "any":
        where_or["tenant_id"] = tenant_id
        where_or["public"] = True
    result, content = mydb.get_table(FROM='vnfs', SELECT=select_,WHERE=where_,WHERE_OR=where_or, WHERE_AND_OR="AND",LIMIT=limit_)
    if result < 0:
        print "http_get_vnfs Error", content
        bottle.abort(-result, content)
    else:
        #change_keys_http2db(content, http2db_vnf, reverse=True)
        utils.convert_str2boolean(content, ('public',))
        convert_datetime2str(content)
        data={'vnfs' : content}
        return format_out(data)

@bottle.route(url_base + '/<tenant_id>/vnfs/<vnf_id>', method='GET')
def http_get_vnf_id(tenant_id,vnf_id):
    '''get vnf details, can use both uuid or name'''
    result, data = nfvo.get_vnf_id(mydb,tenant_id,vnf_id)
    if result < 0:
        print "http_post_vnfs error %d %s" % (-result, data)
        bottle.abort(-result, data)

    utils.convert_str2boolean(data, ('public',))
    convert_datetime2str(data)
    return format_out(data)

@bottle.route(url_base + '/<tenant_id>/vnfs', method='POST')
def http_post_vnfs(tenant_id):
    '''insert a vnf into the catalogue. Creates the flavor and images in the VIM, and creates the VNF and its internal structure in the OPENMANO DB'''
    print "Parsing the YAML file of the VNF"
    #parse input data
    http_content, used_schema = format_in( vnfd_schema_v01, ("version",), {"v0.2": vnfd_schema_v02})
    r = utils.remove_extra_items(http_content, used_schema)
    if r is not None: print "http_post_vnfs: Warning: remove extra items ", r
    result, data = nfvo.new_vnf(mydb,tenant_id,http_content)
    if result < 0:
        print "http_post_vnfs error %d %s" % (-result, data)
        bottle.abort(-result, data)
    else:
        return http_get_vnf_id(tenant_id,data)
            
@bottle.route(url_base + '/<tenant_id>/vnfs/<vnf_id>', method='DELETE')
def http_delete_vnf_id(tenant_id,vnf_id):
    '''delete a vnf from database, and images and flavors in VIM when appropriate, can use both uuid or name'''
    #check valid tenant_id and deletes the vnf, including images, 
    result, data = nfvo.delete_vnf(mydb,tenant_id,vnf_id)
    if result < 0:
        print "http_delete_vnf_id error %d %s" % (-result, data)
        bottle.abort(-result, data)
    else:
        #print json.dumps(data, indent=4)
        return format_out({"result":"VNF " + data + " deleted"})

#@bottle.route(url_base + '/<tenant_id>/hosts/topology', method='GET')
#@bottle.route(url_base + '/<tenant_id>/physicalview/Madrid-Alcantara', method='GET')
@bottle.route(url_base + '/<tenant_id>/physicalview/<datacenter>', method='GET')
def http_get_hosts(tenant_id, datacenter):
    '''get the tidvim host hopology from the vim.'''
    global mydb
    print "http_get_hosts received by tenant " + tenant_id + ' datacenter ' + datacenter
    if datacenter == 'treeview':
        result, data = nfvo.get_hosts(mydb, tenant_id)
    else:
        #openmano-gui is using a hardcoded value for the datacenter
        result, data = nfvo.get_hosts_info(mydb, tenant_id) #, datacenter)
    
    if result < 0:
        print "http_post_vnfs error %d %s" % (-result, data)
        bottle.abort(-result, data)
    else:
        convert_datetime2str(data)
        print json.dumps(data, indent=4)
        return format_out(data)


@bottle.route(url_base + '/<path:path>', method='OPTIONS')
def http_options_deploy(path):
    '''For some reason GUI web ask for OPTIONS that must be responded'''
    #TODO: check correct path, and correct headers request
    bottle.response.set_header('Access-Control-Allow-Methods','POST, GET, PUT, DELETE, OPTIONS')
    bottle.response.set_header('Accept','application/yaml,application/json')
    bottle.response.set_header('Content-Type','application/yaml,application/json')
    bottle.response.set_header('Access-Control-Allow-Headers','content-type')
    bottle.response.set_header('Access-Control-Allow-Origin','*')
    return

@bottle.route(url_base + '/<tenant_id>/topology/deploy', method='POST')
def http_post_deploy(tenant_id):
    '''post topology deploy.'''
    print "http_post_deploy by tenant " + tenant_id 

    http_content, used_schema = format_in( nsd_schema_v01, ("version",), {"v0.2": nsd_schema_v02})
    #r = utils.remove_extra_items(http_content, used_schema)
    #if r is not None: print "http_post_deploy: Warning: remove extra items ", r
    print "http_post_deploy input: ",  http_content
    
    result, scenario_uuid = nfvo.new_scenario(mydb, tenant_id, http_content)
    if result < 0:
        print "http_post_deploy error creating the scenario %d %s" % (-result, scenario_uuid)
        bottle.abort(-result, scenario_uuid)

    result, data = nfvo.start_scenario(mydb, tenant_id, scenario_uuid, http_content['name'], http_content['name'])
    if result < 0:
        print "http_post_deploy error launching the scenario %d %s" % (-result, data)
        bottle.abort(-result, data)
    else:
        print json.dumps(data, indent=4)
        return format_out(data)

@bottle.route(url_base + '/<tenant_id>/topology/verify', method='POST')
def http_post_verify(tenant_id):
    #TODO:
#    '''post topology verify'''
#    print "http_post_verify by tenant " + tenant_id + ' datacenter ' + datacenter
    return 

#
# SCENARIOS
#

@bottle.route(url_base + '/<tenant_id>/scenarios', method='POST')
def http_post_scenarios(tenant_id):
    '''add a scenario into the catalogue. Creates the scenario and its internal structure in the OPENMANO DB'''
    print "http_post_scenarios by tenant " + tenant_id 
    http_content, used_schema = format_in( nsd_schema_v01, ("schema_version",), {"0.2": nsd_schema_v02})
    #r = utils.remove_extra_items(http_content, used_schema)
    #if r is not None: print "http_post_scenarios: Warning: remove extra items ", r
    print "http_post_scenarios input: ",  http_content
    if http_content.get("schema_version") == None:
        result, data = nfvo.new_scenario(mydb, tenant_id, http_content)
    else:
        result, data = nfvo.new_scenario_v02(mydb, tenant_id, http_content)
    if result < 0:
        print "http_post_scenarios error %d %s" % (-result, data)
        bottle.abort(-result, data)
    else:
        #print json.dumps(data, indent=4)
        #return format_out(data)
        return http_get_scenario_id(tenant_id,data)

@bottle.route(url_base + '/<tenant_id>/scenarios/<scenario_id>/action', method='POST')
def http_post_scenario_action(tenant_id, scenario_id):
    '''take an action over a scenario'''
    #check valid tenant_id
    if not nfvo.check_tenant(mydb, tenant_id): 
        print 'httpserver.http_post_scenario_action() tenant %s not found' % tenant_id
        bottle.abort(HTTP_Not_Found, 'Tenant %s not found' % tenant_id)
        return
    #parse input data
    http_content,_ = format_in( scenario_action_schema )
    r = utils.remove_extra_items(http_content, scenario_action_schema)
    if r is not None: print "http_post_scenario_action: Warning: remove extra items ", r
    if "start" in http_content:
        result, data = nfvo.start_scenario(mydb, tenant_id, scenario_id, http_content['start']['instance_name'], \
                    http_content['start'].get('description',http_content['start']['instance_name']),
                    http_content['start'].get('datacenter') )
        if result < 0:
            print "http_post_scenario_action start error %d: %s" % (-result, data)
            bottle.abort(-result, data)
        else:
            return format_out(data)
    elif "deploy" in http_content:   #Equivalent to start
        result, data = nfvo.start_scenario(mydb, tenant_id, scenario_id, http_content['deploy']['instance_name'],
                    http_content['deploy'].get('description',http_content['deploy']['instance_name']),
                    http_content['deploy'].get('datacenter') )
        if result < 0:
            print "http_post_scenario_action deploy error %d: %s" % (-result, data)
            bottle.abort(-result, data)
        else:
            return format_out(data)
    elif "reserve" in http_content:   #Reserve resources
        result, data = nfvo.start_scenario(mydb, tenant_id, scenario_id, http_content['reserve']['instance_name'],
                    http_content['reserve'].get('description',http_content['reserve']['instance_name']),
                    http_content['reserve'].get('datacenter'),  startvms=False )
        if result < 0:
            print "http_post_scenario_action reserve error %d: %s" % (-result, data)
            bottle.abort(-result, data)
        else:
            return format_out(data)
    elif "verify" in http_content:   #Equivalent to start and then delete
        result, data = nfvo.start_scenario(mydb, tenant_id, scenario_id, http_content['verify']['instance_name'],
                    http_content['verify'].get('description',http_content['verify']['instance_name']),
                    http_content['verify'].get('datacenter'), startvms=False )
        if result < 0 or result!=1:
            print "http_post_scenario_action verify error during start %d: %s" % (-result, data)
            bottle.abort(-result, data)
        instance_id = data['uuid']
        result, message = nfvo.delete_instance(mydb, tenant_id,instance_id)
        if result < 0:
            print "http_post_scenario_action verify error during start delete_instance_id %d %s" % (-result, message)
            bottle.abort(-result, message)
        else:
            #print json.dumps(data, indent=4)
            return format_out({"result":"Verify OK"})

@bottle.route(url_base + '/<tenant_id>/scenarios', method='GET')
def http_get_scenarios(tenant_id):
    '''get scenarios list'''
    #check valid tenant_id
    if tenant_id != "any" and not nfvo.check_tenant(mydb, tenant_id): 
        print "httpserver.http_get_scenarios() tenant '%s' not found" % tenant_id
        bottle.abort(HTTP_Not_Found, "Tenant '%s' not found" % tenant_id)
        return
    #obtain data
    s,w,l=filter_query_string(bottle.request.query, None, ('uuid', 'name', 'description', 'tenant_id', 'created_at', 'public'))
    where_or={}
    if tenant_id != "any":
        where_or["tenant_id"] = tenant_id
        where_or["public"] = True
    result, data = mydb.get_table(SELECT=s, WHERE=w, WHERE_OR=where_or, WHERE_AND_OR="AND", LIMIT=l, FROM='scenarios')
    if result < 0:
        print "http_get_scenarios error %d %s" % (-result, data)
        bottle.abort(-result, data)
    else:
        convert_datetime2str(data)
        utils.convert_str2boolean(data, ('public',) )
        scenarios={'scenarios':data}
        #print json.dumps(scenarios, indent=4)
        return format_out(scenarios)

@bottle.route(url_base + '/<tenant_id>/scenarios/<scenario_id>', method='GET')
def http_get_scenario_id(tenant_id, scenario_id):
    '''get scenario details, can use both uuid or name'''
    #check valid tenant_id
    if tenant_id != "any" and not nfvo.check_tenant(mydb, tenant_id): 
        print "httpserver.http_get_scenario_id() tenant '%s' not found" % tenant_id
        bottle.abort(HTTP_Not_Found, "Tenant '%s' not found" % tenant_id)
        return
    #obtain data
    result, content = mydb.get_scenario(scenario_id, tenant_id)
    if result < 0:
        print "http_get_scenario_id error %d %s" % (-result, content)
        bottle.abort(-result, content)
    else:
        #print json.dumps(content, indent=4)
        convert_datetime2str(content)
        data={'scenario' : content}
        return format_out(data)

@bottle.route(url_base + '/<tenant_id>/scenarios/<scenario_id>', method='DELETE')
def http_delete_scenario_id(tenant_id, scenario_id):
    '''delete a scenario from database, can use both uuid or name'''
    #check valid tenant_id
    if tenant_id != "any" and not nfvo.check_tenant(mydb, tenant_id): 
        print "httpserver.http_delete_scenario_id() tenant '%s' not found" % tenant_id
        bottle.abort(HTTP_Not_Found, "Tenant '%s' not found" % tenant_id)
        return
    #obtain data
    result, data = mydb.delete_scenario(scenario_id, tenant_id)
    if result < 0:
        print "http_delete_scenario_id error %d %s" % (-result, data)
        bottle.abort(-result, data)
    else:
        #print json.dumps(data, indent=4)
        return format_out({"result":"scenario " + data + " deleted"})


@bottle.route(url_base + '/<tenant_id>/scenarios/<scenario_id>', method='PUT')
def http_put_scenario_id(tenant_id, scenario_id):
    '''edit an existing scenario id'''
    print "http_put_scenarios by tenant " + tenant_id 
    http_content,_ = format_in( scenario_edit_schema )
    #r = utils.remove_extra_items(http_content, scenario_edit_schema)
    #if r is not None: print "http_put_scenario_id: Warning: remove extra items ", r
    print "http_put_scenario_id input: ",  http_content
    
    result, data = nfvo.edit_scenario(mydb, tenant_id, scenario_id, http_content)
    if result < 0:
        print "http_put_scenarios error %d %s" % (-result, data)
        bottle.abort(-result, data)
    else:
        #print json.dumps(data, indent=4)
        #return format_out(data)
        return http_get_scenario_id(tenant_id,data)

@bottle.route(url_base + '/<tenant_id>/instances', method='POST')
def http_post_instances(tenant_id):
    '''take an action over a scenario'''
    #check valid tenant_id
    if not nfvo.check_tenant(mydb, tenant_id): 
        print 'httpserver.http_post_scenario_action() tenant %s not found' % tenant_id
        bottle.abort(HTTP_Not_Found, 'Tenant %s not found' % tenant_id)
        return
    #parse input data
    http_content,used_schema = format_in( instance_scenario_create_schema)
    r = utils.remove_extra_items(http_content, used_schema)
    if r is not None: print "http_post_instances: Warning: remove extra items ", r
    result, data = nfvo.create_instance(mydb, tenant_id, http_content["instance"])
    if result < 0:
        print "http_post_instances start error %d: %s" % (-result, data)
        bottle.abort(-result, data)
    else:
        return format_out(data)

#
# INSTANCES
#
@bottle.route(url_base + '/<tenant_id>/instances', method='GET')
def http_get_instances(tenant_id):
    '''get instance list'''
    #check valid tenant_id
    if tenant_id != "any" and not nfvo.check_tenant(mydb, tenant_id): 
        print 'httpserver.http_get_instances() tenant %s not found' % tenant_id
        bottle.abort(HTTP_Not_Found, 'Tenant %s not found' % tenant_id)
        return
    #obtain data
    s,w,l=filter_query_string(bottle.request.query, None, ('uuid', 'name', 'scenario_id', 'tenant_id', 'description', 'created_at'))
    where_or={}
    if tenant_id != "any":
        w['tenant_id'] = tenant_id
    result, data = mydb.get_table(SELECT=s, WHERE=w, LIMIT=l, FROM='instance_scenarios')
    if result < 0:
        print "http_get_instances error %d %s" % (-result, data)
        bottle.abort(-result, data)
    else:
        convert_datetime2str(data)
        utils.convert_str2boolean(data, ('public',) )
        instances={'instances':data}
        print json.dumps(instances, indent=4)
        return format_out(instances)

@bottle.route(url_base + '/<tenant_id>/instances/<instance_id>', method='GET')
def http_get_instance_id(tenant_id, instance_id):
    '''get instances details, can use both uuid or name'''
    #check valid tenant_id
    if tenant_id != "any" and not nfvo.check_tenant(mydb, tenant_id): 
        print 'httpserver.http_get_instance_id() tenant %s not found' % tenant_id
        bottle.abort(HTTP_Not_Found, 'Tenant %s not found' % tenant_id)
        return
    if tenant_id == "any":
        tenant_id = None
  
    #obtain data (first time is only to check that the instance exists)
    result, data = mydb.get_instance_scenario(instance_id, tenant_id, verbose=True)
    if result < 0:
        print "http_get_instance_id error %d %s" % (-result, data)
        bottle.abort(-result, data)
        return
    
    r,c = nfvo.refresh_instance(mydb, tenant_id, data)
    if r<0:
        print "WARNING: nfvo.refresh_instance couldn't refresh the status of the instance: %s" %c
    #obtain data with results upated
    result, data = mydb.get_instance_scenario(instance_id, tenant_id)
    if result < 0:
        print "http_get_instance_id error %d %s" % (-result, data)
        bottle.abort(-result, data)
        return
    convert_datetime2str(data)
    print json.dumps(data, indent=4)
    return format_out(data)

@bottle.route(url_base + '/<tenant_id>/instances/<instance_id>', method='DELETE')
def http_delete_instance_id(tenant_id, instance_id):
    '''delete instance from VIM and from database, can use both uuid or name'''
    #check valid tenant_id
    if tenant_id != "any" and not nfvo.check_tenant(mydb, tenant_id): 
        print 'httpserver.http_delete_instance_id() tenant %s not found' % tenant_id
        bottle.abort(HTTP_Not_Found, 'Tenant %s not found' % tenant_id)
        return
    if tenant_id == "any":
        tenant_id = None
    #obtain data
    result, message = nfvo.delete_instance(mydb, tenant_id,instance_id)
    if result < 0:
        print "http_delete_instance_id error %d %s" % (-result, message)
        bottle.abort(-result, message)
    else:
        #print json.dumps(data, indent=4)
        return format_out({"result":message})

@bottle.route(url_base + '/<tenant_id>/instances/<instance_id>/action', method='POST')
def http_post_instance_scenario_action(tenant_id, instance_id):
    '''take an action over a scenario instance'''
    #check valid tenant_id
    if not nfvo.check_tenant(mydb, tenant_id): 
        print 'httpserver.http_post_instance_scenario_action() tenant %s not found' % tenant_id
        bottle.abort(HTTP_Not_Found, 'Tenant %s not found' % tenant_id)
        return
    #parse input data
    http_content,_ = format_in( instance_scenario_action_schema )
    r = utils.remove_extra_items(http_content, instance_scenario_action_schema)
    if r is not None: print "http_post_instance_scenario_action: Warning: remove extra items ", r
    print "http_post_instance_scenario_action input: ", http_content
    #obtain data
    result, data = mydb.get_instance_scenario(instance_id, tenant_id)
    if result < 0:
        print "http_get_instance_id error %d %s" % (-result, data)
        bottle.abort(-result, data)
    instance_id = data["uuid"]
    
    result, data = nfvo.instance_action(mydb, tenant_id, instance_id, http_content)
    if result < 0:
        print "http_post_scenario_action error %d: %s" % (-result, data)
        bottle.abort(-result, data)
    else:
        return format_out(data)


@bottle.error(400)
@bottle.error(401) 
@bottle.error(404) 
@bottle.error(403)
@bottle.error(405) 
@bottle.error(406)
@bottle.error(409)
@bottle.error(503) 
@bottle.error(500)
def error400(error):
    e={"error":{"code":error.status_code, "type":error.status, "description":error.body}}
    bottle.response.headers['Access-Control-Allow-Origin'] = '*'
    return format_out(e)

