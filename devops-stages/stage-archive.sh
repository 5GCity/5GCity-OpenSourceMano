#!/bin/sh

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

MDG=NBI
rm -rf pool
rm -rf dists
mkdir -p pool/$MDG
mv deb_dist/*.deb pool/$MDG/
mkdir -p dists/unstable/$MDG/binary-amd64/
apt-ftparchive packages pool/$MDG > dists/unstable/$MDG/binary-amd64/Packages
gzip -9fk dists/unstable/$MDG/binary-amd64/Packages
echo "dists/**,pool/$MDG/*.deb"
