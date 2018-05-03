#
#   Copyright 2018 CNIT - Consorzio Nazionale Interuniversitario per le Telecomunicazioni
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an  BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

from django import template
register = template.Library()

'''
    Custom template filter 
'''
@register.filter
def get(mapping, key):
    result = mapping.get(key, '')
    return result

'''
    Custom template filter 
'''
@register.filter
def get_sub(mapping, args):
    splitted = args.split(',')
    sub_dict = mapping.get(splitted[0], '')
    if isinstance(sub_dict, dict):
        return sub_dict.get(splitted[1], '')
    return ''
