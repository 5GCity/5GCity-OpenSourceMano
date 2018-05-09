/*
   Copyright 2018 CNIT - Consorzio Nazionale Interuniversitario per le Telecomunicazioni

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an  BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/


function openModalCreateNS(args) {

    // load vim account list
    select2_groups = $('#vimAccountId').select2({
        placeholder: 'Select VIM',
        ajax: {
            url: args.vim_list_url,
            dataType: 'json',
            processResults: function (data) {
                vims = [];
                if (data['datacenters']) {
                    for (d in data['datacenters']) {
                        var datacenter = data['datacenters'][d];
                        vims.push({id: datacenter['_id'], text: datacenter['name']})
                    }
                }

                return {
                    results: vims
                };
            }
        }
    });
    /*
    // load nsd list
    select2_groups = $('#nsdId').select2({
        placeholder: 'Select NSD',
        ajax: {
            url: args.nsd_list_url,
            dataType: 'json',
            processResults: function (data) {
                nsd_list = [];
                if (data['nsd_list']) {
                    for (d in data['nsd_list']) {
                        var nsd = data['nsd_list'][d];
                        nsd_list.push({id: nsd['_id'], text: nsd['name']})
                    }
                }

                return {
                    results: nsd_list
                };
            }
        }
    });
    */
    $('#nsdId').val(args.descriptor_id);
    $('#modal_new_instance').modal('show');
}