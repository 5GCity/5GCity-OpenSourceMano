# -*- coding: utf-8 -*-

#
# Util functions previously in `httpserver`
#

__author__ = "Alfonso Tierno, Gerardo Garcia"

import json
import logging

import bottle
import yaml
from jsonschema import exceptions as js_e
from jsonschema import validate as js_v

from . import errors as httperrors

logger = logging.getLogger('openmano.http')


def remove_clear_passwd(data):
    """
    Removes clear passwords from the data received
    :param data: data with clear password
    :return: data without the password information
    """

    passw = ['password: ', 'passwd: ']

    for pattern in passw:
        init = data.find(pattern)
        while init != -1:
            end = data.find('\n', init)
            data = data[:init] + '{}******'.format(pattern) + data[end:]
            init += 1
            init = data.find(pattern, init)
    return data


def change_keys_http2db(data, http_db, reverse=False):
    '''Change keys of dictionary data acording to the key_dict values
    This allow change from http interface names to database names.
    When reverse is True, the change is otherwise
    Attributes:
        data: can be a dictionary or a list
        http_db: is a dictionary with hhtp names as keys and database names as value
        reverse: by default change is done from http api to database.
            If True change is done otherwise.
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
    '''Return string of dictionary data according to requested json, yaml, xml.
    By default json
    '''
    logger.debug("OUT: " + yaml.safe_dump(data, explicit_start=True, indent=4, default_flow_style=False, tags=False, encoding='utf-8', allow_unicode=True) )
    accept = bottle.request.headers.get('Accept')
    if accept and 'application/yaml' in accept:
        bottle.response.content_type='application/yaml'
        return yaml.safe_dump(
                data, explicit_start=True, indent=4, default_flow_style=False,
                tags=False, encoding='utf-8', allow_unicode=True) #, canonical=True, default_style='"'
    else: #by default json
        bottle.response.content_type='application/json'
        #return data #json no style
        return json.dumps(data, indent=4) + "\n"


def format_in(default_schema, version_fields=None, version_dict_schema=None, confidential_data=False):
    """
    Parse the content of HTTP request against a json_schema

    :param default_schema: The schema to be parsed by default
        if no version field is found in the client data.
        In None no validation is done
    :param version_fields: If provided it contains a tuple or list with the
        fields to iterate across the client data to obtain the version
    :param version_dict_schema: It contains a dictionary with the version as key,
        and json schema to apply as value.
        It can contain a None as key, and this is apply
        if the client data version does not match any key
    :return:  user_data, used_schema: if the data is successfully decoded and
        matches the schema.

    Launch a bottle abort if fails
    """
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
            logger.warning('Content-Type ' + str(format_type) + ' not supported.')
            bottle.abort(httperrors.Not_Acceptable, 'Content-Type ' + str(format_type) + ' not supported.')
            return
        # if client_data == None:
        #    bottle.abort(httperrors.Bad_Request, "Content error, empty")
        #    return
        if confidential_data:
            logger.debug('IN: %s', remove_clear_passwd (yaml.safe_dump(client_data, explicit_start=True, indent=4, default_flow_style=False,
                                              tags=False, encoding='utf-8', allow_unicode=True)))
        else:
            logger.debug('IN: %s', yaml.safe_dump(client_data, explicit_start=True, indent=4, default_flow_style=False,
                                              tags=False, encoding='utf-8', allow_unicode=True) )
        # look for the client provider version
        error_text = "Invalid content "
        if not default_schema and not version_fields:
            return client_data, None
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
        if client_version == None:
            used_schema = default_schema
        elif version_dict_schema != None:
            if client_version in version_dict_schema:
                used_schema = version_dict_schema[client_version]
            elif None in version_dict_schema:
                used_schema = version_dict_schema[None]
        if used_schema==None:
            bottle.abort(httperrors.Bad_Request, "Invalid schema version or missing version field")

        js_v(client_data, used_schema)
        return client_data, used_schema
    except (TypeError, ValueError, yaml.YAMLError) as exc:
        error_text += str(exc)
        logger.error(error_text, exc_info=True)
        bottle.abort(httperrors.Bad_Request, error_text)
    except js_e.ValidationError as exc:
        logger.error(
            "validate_in error, jsonschema exception", exc_info=True)
        error_pos = ""
        if len(exc.path)>0: error_pos=" at " + ":".join(map(json.dumps, exc.path))
        bottle.abort(httperrors.Bad_Request, error_text + exc.message + error_pos)
    #except:
    #    bottle.abort(httperrors.Bad_Request, "Content error: Failed to parse Content-Type",  error_pos)
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
    #if type(qs) is not bottle.FormsDict:
    #    bottle.abort(httperrors.Internal_Server_Error, '!!!!!!!!!!!!!!invalid query string not a dictionary')
    #    #bottle.abort(httperrors.Internal_Server_Error, "call programmer")
    for k in qs:
        if k=='field':
            select += qs.getall(k)
            for v in select:
                if v not in allowed:
                    bottle.abort(httperrors.Bad_Request, "Invalid query string at 'field="+v+"'")
        elif k=='limit':
            try:
                limit=int(qs[k])
            except:
                bottle.abort(httperrors.Bad_Request, "Invalid query string at 'limit="+qs[k]+"'")
        else:
            if k not in allowed:
                bottle.abort(httperrors.Bad_Request, "Invalid query string at '"+k+"="+qs[k]+"'")
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
    #print "filter_query_string", select,where,limit

    return select,where,limit
