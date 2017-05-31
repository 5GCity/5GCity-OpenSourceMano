#!/bin/bash
#   Copyright 2017 Sandvine
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# A helper routine that cleans up old container images based
# on an input prefix to check. Jenkins builds will add an incrementing
# build suffix  (build number) to the prefix
#
#$1 container prefix name

keep_number=1
prefix=$1

# keep the first build
keep=$(lxc list | grep $prefix | awk '{print $2}' | sort -rn | head -n$keep_number)
for container in $(lxc list | grep $prefix | awk '{print $2}' | sort -rn); do
    if [ "$container" != "$keep" ]; then
        echo "deleting old container $container"
        lxc delete $container --force
    fi
done
