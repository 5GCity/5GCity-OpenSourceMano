#! /usr/bin/bash
#
#   Copyright 2016 RIFT.IO Inc
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
# Author(s): Austin Cormier
# Creation Date: 2016/05/23
#
#
# This shell script is used to create a descriptor package
# The main functions of this script include:
# - Generate checksums.txt file
# - Generate a tar.gz file

# Usage: generate_descriptor_pkg.sh <package-directory> <dest_package_dir>

mkdir -p $1
mkdir -p $2

dest_dir=$(cd $1 && pwd)
pkg_dir=$(cd $2 && pwd)

echo $(pwd)
cd ${pkg_dir}
rm -rf checksums.txt
find * -type f |
    while read file; do
        md5sum $file >> checksums.txt
    done
cd ..
tar -zcvf ${dest_dir}/$(basename $pkg_dir).tar.gz $(basename $pkg_dir)
