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
utils is a module that implements functions that are used by all openmano modules,
dealing with aspects such as reading/writing files, formatting inputs/outputs for quick translation
from dictionaries to appropriate database dictionaries, etc.
'''
__author__="Alfonso Tierno, Gerardo Garcia"
__date__ ="$08-sep-2014 12:21:22$"

import datetime
import time
import warnings
from functools import reduce
from itertools import tee

from six.moves import filter, filterfalse

from jsonschema import exceptions as js_e
from jsonschema import validate as js_v

#from bs4 import BeautifulSoup

def read_file(file_to_read):
    """Reads a file specified by 'file_to_read' and returns (True,<its content as a string>) in case of success or (False, <error message>) in case of failure"""
    try:
        f = open(file_to_read, 'r')
        read_data = f.read()
        f.close()
    except Exception as e:
        return (False, str(e))

    return (True, read_data)

def write_file(file_to_write, text):
    """Write a file specified by 'file_to_write' and returns (True,NOne) in case of success or (False, <error message>) in case of failure"""
    try:
        f = open(file_to_write, 'w')
        f.write(text)
        f.close()
    except Exception as e:
        return (False, str(e))

    return (True, None)

def format_in(http_response, schema):
    try:
        client_data = http_response.json()
        js_v(client_data, schema)
        #print "Input data: ", str(client_data)
        return True, client_data
    except js_e.ValidationError as exc:
        print "validate_in error, jsonschema exception ", exc.message, "at", exc.path
        return False, ("validate_in error, jsonschema exception ", exc.message, "at", exc.path)

def remove_extra_items(data, schema):
    deleted=[]
    if type(data) is tuple or type(data) is list:
        for d in data:
            a= remove_extra_items(d, schema['items'])
            if a is not None: deleted.append(a)
    elif type(data) is dict:
        #TODO deal with patternProperties
        if 'properties' not in schema:
            return None
        for k in data.keys():
            if k not in schema['properties'].keys():
                del data[k]
                deleted.append(k)
            else:
                a = remove_extra_items(data[k], schema['properties'][k])
                if a is not None:  deleted.append({k:a})
    if len(deleted) == 0: return None
    elif len(deleted) == 1: return deleted[0]
    else: return deleted

#def format_html2text(http_content):
#    soup=BeautifulSoup(http_content)
#    text = soup.p.get_text() + " " + soup.pre.get_text()
#    return text


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


def convert_bandwidth(data, reverse=False):
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
                convert_bandwidth(data[k], reverse)
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
                print "convert_bandwidth exception for type", type(data["bandwidth"]), " data", data["bandwidth"]
                return
    if type(data) is tuple or type(data) is list:
        for k in data:
            if type(k) is dict or type(k) is tuple or type(k) is list:
                convert_bandwidth(k, reverse)

def convert_float_timestamp2str(var):
    '''Converts timestamps (created_at, modified_at fields) represented as float
    to a string with the format '%Y-%m-%dT%H:%i:%s'
    It enters recursively in the dict var finding this kind of variables
    '''
    if type(var) is dict:
        for k,v in var.items():
            if type(v) is float and k in ("created_at", "modified_at"):
                var[k] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(v) )
            elif type(v) is dict or type(v) is list or type(v) is tuple:
                convert_float_timestamp2str(v)
        if len(var) == 0: return True
    elif type(var) is list or type(var) is tuple:
        for v in var:
            convert_float_timestamp2str(v)

def convert_datetime2str(var):
    '''Converts a datetime variable to a string with the format '%Y-%m-%dT%H:%i:%s'
    It enters recursively in the dict var finding this kind of variables
    '''
    if type(var) is dict:
        for k,v in var.items():
            if type(v) is datetime.datetime:
                var[k]= v.strftime('%Y-%m-%dT%H:%M:%S')
            elif type(v) is dict or type(v) is list or type(v) is tuple:
                convert_datetime2str(v)
        if len(var) == 0: return True
    elif type(var) is list or type(var) is tuple:
        for v in var:
            convert_datetime2str(v)

def convert_str2boolean(data, items):
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
                convert_str2boolean(data[k], items)
            if k in items:
                if type(data[k]) is str:
                    if   data[k]=="false" or data[k]=="False": data[k]=False
                    elif data[k]=="true"  or data[k]=="True":  data[k]=True
    if type(data) is tuple or type(data) is list:
        for k in data:
            if type(k) is dict or type(k) is tuple or type(k) is list:
                convert_str2boolean(k, items)

def check_valid_uuid(uuid):
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


def expand_brackets(text):
    """
    Change a text with TEXT[ABC..] into a list with [TEXTA, TEXTB, TEXC, ...
    if no bracket is used it just return the a list with the single text
    It uses recursivity to allow several [] in the text
    :param text:
    :return:
    """
    start = text.find("[")
    end = text.find("]")
    if start < 0 or end < 0:
        return [text]
    text_list = []
    for char in text[start+1:end]:
        text_list += expand_brackets(text[:start] + char + text[end+1:])
    return text_list

def deprecated(message):
  def deprecated_decorator(func):
      def deprecated_func(*args, **kwargs):
          warnings.warn("{} is a deprecated function. {}".format(func.__name__, message),
                        category=DeprecationWarning,
                        stacklevel=2)
          warnings.simplefilter('default', DeprecationWarning)
          return func(*args, **kwargs)
      return deprecated_func
  return deprecated_decorator


def truncate(text, max_length=1024):
    """Limit huge texts in number of characters"""
    text = str(text)
    if text and len(text) >= max_length:
        return text[:max_length//2-3] + " ... " + text[-max_length//2+3:]
    return text


def merge_dicts(*dicts, **kwargs):
    """Creates a new dict merging N others and keyword arguments.
    Right-most dicts take precedence.
    Keyword args take precedence.
    """
    return reduce(
        lambda acc, x: acc.update(x) or acc,
        list(dicts) + [kwargs], {})


def remove_none_items(adict):
    """Return a similar dict without keys associated to None values"""
    return {k: v for k, v in adict.items() if v is not None}


def filter_dict_keys(adict, allow):
    """Return a similar dict, but just containing the explicitly allowed keys

    Arguments:
        adict (dict): Simple python dict data struct
        allow (list): Explicits allowed keys
    """
    return {k: v for k, v in adict.items() if k in allow}


def filter_out_dict_keys(adict, deny):
    """Return a similar dict, but not containing the explicitly denied keys

    Arguments:
        adict (dict): Simple python dict data struct
        deny (list): Explicits denied keys
    """
    return {k: v for k, v in adict.items() if k not in deny}


def expand_joined_fields(record):
    """Given a db query result, explode the fields that contains `.` (join
    operations).

    Example
        >> expand_joined_fiels({'wim.id': 2})
        # {'wim': {'id': 2}}
    """
    result = {}
    for field, value in record.items():
        keys = field.split('.')
        target = result
        target = reduce(lambda target, key: target.setdefault(key, {}),
                        keys[:-1], result)
        target[keys[-1]] = value

    return result


def ensure(condition, exception):
    """Raise an exception if condition is not met"""
    if not condition:
        raise exception


def partition(predicate, iterable):
    """Create two derived iterators from a single one
    The first iterator created will loop thought the values where the function
    predicate is True, the second one will iterate over the values where it is
    false.
    """
    iterable1, iterable2 = tee(iterable)
    return filter(predicate, iterable2), filterfalse(predicate, iterable1)


def pipe(*functions):
    """Compose functions of one argument in the opposite order,
    So pipe(f, g)(x) = g(f(x))
    """
    return lambda x: reduce(lambda acc, f: f(acc), functions, x)


def compose(*functions):
    """Compose functions of one argument,
    So compose(f, g)(x) = f(g(x))
    """
    return lambda x: reduce(lambda acc, f: f(acc), functions[::-1], x)


def safe_get(target, key_path, default=None):
    """Given a path of keys (eg.: "key1.key2.key3"), return a nested value in
    a nested dict if present, or the default value
    """
    keys = key_path.split('.')
    target = reduce(lambda acc, key: acc.get(key) or {}, keys[:-1], target)
    return target.get(keys[-1], default)
