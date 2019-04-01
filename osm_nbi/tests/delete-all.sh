#! /bin/bash

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

export NBI_URL=https://localhost:9999/osm
USERNAME=admin
PASSWORD=admin
PROJECT=admin

#get token
TOKEN=`curl --insecure -H "Content-Type: application/yaml" -H "Accept: application/yaml"  --data "{username: $USERNAME, password: $PASSWORD, project_id: $PROJECT}" ${NBI_URL}/admin/v1/tokens 2>/dev/null | awk '($1=="id:"){print $2}' ` ; echo $TOKEN

echo  deleting all
#DELETE ALL

for url_item in nslcm/v1/ns_instances nsd/v1/ns_descriptors_content vnfpkgm/v1/vnf_packages_content
do
    for ITEM_ID in `curl --insecure -w "%{http_code}\n" -H "Content-Type: application/yaml" -H "Accept: application/yaml" -H "Authorization: Bearer $TOKEN"  ${NBI_URL}/${url_item} 2>/dev/null | awk '($1=="_id:") {print $2}'` ;
    do
        curl --insecure -w "%{http_code}\n" -H "Content-Type: application/yaml" -H "Accept: application/yaml" -H "Authorization: Bearer $TOKEN"  ${NBI_URL}/${url_item}/$ITEM_ID -X DELETE
    done
done

# curl --insecure  ${NBI_URL}/test/prune

