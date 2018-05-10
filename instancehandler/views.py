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
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
import yaml
import logging
from lib.osm.osmclient.client import Client


@login_required
def list(request, project_id=None, type=None):
    client = Client()
    if type == 'ns':
        result = client.ns_list()

    return __response_handler(request, {'instances': result, 'type': 'ns', 'project_id': project_id}, 'instance_list.html')


@login_required
def create(request, project_id=None):
    result = {}
    ns_data = {
        "nsName": request.POST.get('nsName', 'WithoutName'),
        "nsDescription": request.POST.get('nsDescription', ''),
        "nsdId": request.POST.get('nsdId', ''),
        "vimAccountId": request.POST.get('vimAccountId', ''),
    }
    if 'ssh_key' in request.POST and request.POST.get('ssh_key') != '':
        ns_data["ssh-authorized-key"] = [request.POST.get('ssh_key')]

    if 'config' in request.POST:
        ns_config = yaml.load(request.POST.get('config'))
        if isinstance(ns_config, dict):
            if "vim-network-name" in ns_config:
                ns_config["vld"] = ns_config.pop("vim-network-name")
            if "vld" in ns_config:
                for vld in ns_config["vld"]:
                    if vld.get("vim-network-name"):
                        if isinstance(vld["vim-network-name"], dict):
                            vim_network_name_dict = {}
                            for vim_account, vim_net in vld["vim-network-name"].items():
                                vim_network_name_dict[ns_data["vimAccountId"]] = vim_net
                            vld["vim-network-name"] = vim_network_name_dict
                ns_data["vld"] = ns_config["vld"]
            if "vnf" in ns_config:
                for vnf in ns_config["vnf"]:
                    if vnf.get("vim_account"):
                        vnf["vimAccountId"] = ns_data["vimAccountId"]

                ns_data["vnf"] = ns_config["vnf"]
    print ns_data
    client = Client()
    result = client.ns_create(ns_data)
    return __response_handler(request, result, 'projects:instances:list', to_redirect=True, type='ns', project_id=project_id)


@login_required
def action(request, project_id=None, instance_id=None, type=None):

    client = Client()

    # result = client.ns_action(instance_id, action_payload)
    primitive_param_keys = request.POST.getlist('primitive_params_name')
    primitive_param_value = request.POST.getlist('primitive_params_value')
    action_payload = {
        "vnf_member_index": request.POST.get('vnf_member_index'),
        "primitive": request.POST.get('primitive'),
        "primitive_params": {k: v for k, v in zip(primitive_param_keys, primitive_param_value) if len(k) > 0}
    }

    result = client.ns_action(instance_id, action_payload)
    return __response_handler(request, result, None, to_redirect=False, status=result['status'] )


@login_required
def delete(request, project_id=None, instance_id=None, type=None):
    result = {}
    client = Client()
    result = client.ns_delete(instance_id)
    print result
    return __response_handler(request, result, 'projects:instances:list', to_redirect=True, type='ns', project_id=project_id)


@login_required
def show(request, project_id=None, instance_id=None, type=None):
    # result = {}
    client = Client()
    result = client.ns_get(instance_id)
    print result
    return __response_handler(request, result)


def __response_handler(request, data_res, url=None, to_redirect=None, *args, **kwargs):
    raw_content_types = request.META.get('HTTP_ACCEPT', '*/*').split(',')
    if 'application/json' in raw_content_types or url is None:
        return JsonResponse(data_res, *args, **kwargs)
    elif to_redirect:
        return redirect(url, *args, **kwargs)
    else:
        return render(request, url, data_res)
