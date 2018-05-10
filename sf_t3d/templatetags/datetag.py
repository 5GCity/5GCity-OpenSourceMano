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
import time
register = template.Library()


'''
    Custom template filter handle timestamp
'''


# TODO add configurable date format
@register.filter
def get_date(timestamp):
    if isinstance(timestamp, float):
        return time.strftime("%d-%m-%Y %H:%M:%S", time.gmtime(timestamp))
    return '-'

