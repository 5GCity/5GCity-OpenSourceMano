#!/bin/bash
export PATH=$PATH:/snap/bin
echo "PATH=$PATH"
juju status

wget "$1"
chmod +x install_osm.sh
./install_osm.sh --nolxd -y --vimemu
