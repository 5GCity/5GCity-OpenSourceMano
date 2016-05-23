#! /usr/bin/bash
# STANDARD_RIFT_IO_COPYRIGHT
# Author(s): Anil Gunturu
# Creation Date: 2015/10/09
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
