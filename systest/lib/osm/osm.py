# Copyright 2017 Sandvine
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


from osmclient.client import client

class Osm():
    def __init__(self,osmhost,ro_host=None,descriptors_dir=None,vnfd_descriptors_list=None,nsd_descriptors_list=None,ns_name_prefix=None):
        self._OsmApi=client.Client(host=osmhost,ro_host=ro_host)
        self._descriptors_dir = descriptors_dir
        self.vnfd_descriptors_list = vnfd_descriptors_list
        self.nsd_descriptors_list  = nsd_descriptors_list 
        self.ns_name_prefix = ns_name_prefix

    def get_api(self):
        return self._OsmApi

    def get_descriptors_dir(self):
        return self._descriptors_dir
