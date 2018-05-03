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

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, JsonResponse
from lib.osm.osmclient.client import Client
import json
import logging

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('helper.py')

@login_required
def list(request):
    client = Client()
    result = client.vim_list()
    print result
    result = {
        "datacenters": result
    }
    return __response_handler(request, result, 'vim_list.html')

@login_required
def create(request):
    result = {}
    if request.method == 'GET':
        return __response_handler(request, result, 'vim_create.html')
    else:
        new_vim_dict = request.POST.dict()
        client = Client()
        keys = ["schema_version",
                "schema_type",
                "name",
                "vim_url",
                "vim_type",
                "vim_user",
                "vim_password",
                "vim_tenant_name",
                "description"]
        vim_data = dict(filter(lambda i: i[0] in keys and len(i[1]) > 0, new_vim_dict.items()))
        vim_data['config']={}
        for k,v in new_vim_dict.items():
            if str(k).startswith('config_') and len(v) > 0:
                config_key = k[7:]
                vim_data['config'][config_key] = v
        print vim_data
        result = client.vim_create(vim_data)
        # TODO  'vim:show', to_redirect=True, vim_id=vim_id
        return __response_handler(request, result, 'vim:list', to_redirect=True)

@login_required
def delete(request, vim_id=None):
    try:
        client = Client()
        del_res = client.vim_delete(vim_id)
    except Exception as e:
        log.exception(e)
    return __response_handler(request, {}, 'vim:list', to_redirect=True)

@login_required
def show(request, vim_id=None):
    client = Client()
    datacenter = client.vim_get(vim_id)
    print datacenter
    return __response_handler(request, {
        "datacenter": datacenter
    }, 'vim_show.html')


def __response_handler(request, data_res, url=None, to_redirect=None, *args, **kwargs):
    raw_content_types = request.META.get('HTTP_ACCEPT', '*/*').split(',')
    if 'application/json' in raw_content_types:
        return JsonResponse(data_res)
    elif to_redirect:
        return redirect(url, *args, **kwargs)
    else:
        return render(request, url, data_res)
