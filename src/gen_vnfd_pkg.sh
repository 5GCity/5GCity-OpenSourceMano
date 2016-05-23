#!/bin/bash

# Generates a NSD descriptor package from a source directory
# Usage:
# gen_vnfd_pkg.sh <pkg_src_dir> <pkg_dest_dir>

set -o nounset

if [ $# -ne 2 ]; then
	echo "Error: Must provide 2 parameters" >@2
	exit 1
fi

pkg_src_dir="$1"
pkg_dest_dir="$2"

if [ ! -e ${pkg_src_dir} ]; then
    echo "Error: ${pkg_src_dir} does not exist"
    exit 1
fi

if [ ! -e ${pkg_dest_dir} ]; then
    echo "Error: ${pkg_src_dir} does not exist"
    exit 1
fi

echo "Generating package in directory: ${pkg_dest_dir}"

# Create any missing directories/files so each package has
# a complete hierachy
vnfd_dirs=( charms icons scripts images )
vnfd_files=( README )

vnfd_dir="${pkg_src_dir}"
echo $(pwd)

mkdir -p "${pkg_dest_dir}"
cp -rf ${vnfd_dir}/* "${pkg_dest_dir}"
for sub_dir in ${vnfd_dirs[@]}; do
    dir_path=${pkg_dest_dir}/${sub_dir}
    mkdir -p ${dir_path}
done

for file in ${vnfd_files[@]}; do
    file_path=${pkg_dest_dir}/${file}
    touch ${file_path}
done
