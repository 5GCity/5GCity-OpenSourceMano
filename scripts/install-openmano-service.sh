#!/bin/bash

##
# Copyright 2015 Telefónica Investigación y Desarrollo, S.A.U.
# This file is part of openmano
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact with: nfvlabs@tid.es
##

#ONLY TESTED for Ubuntu 16.04
#it configures openmano to run as a service

function usage(){
    echo -e "usage: sudo $0 [OPTIONS]"
    echo -e "Configures openmano to run as a service"
    echo -e "  OPTIONS"
    echo -e "     -u USER  user to run openmano, 'root' by default"
    echo -e "     -f PATH  path where openmano source is located. If missing it download from git"
    echo -e "     -q:  install in an unattended mode"
    echo -e "     -h:  show this help"
}


USER="root"
QUIET_MODE=""
FILE=""
DELETE=""
while getopts ":u:f:hq-:" o; do
    case "${o}" in
        u)
            export USER="$OPTARG"
            ;;
        f)
            export FILE="$OPTARG"
            ;;
        q)
            export QUIET_MODE=yes
            ;;
        h)
            usage && exit 0
            ;;
        -)
            [ "${OPTARG}" == "help" ] && usage && exit 0
            echo -e "Invalid option: '--$OPTARG'\nTry $0 --help for more information" >&2 
            exit 1
            ;; 
        \?)
            echo -e "Invalid option: '-$OPTARG'\nTry $0 --help for more information" >&2
            exit 1
            ;;
        :)
            echo -e "Option '-$OPTARG' requires an argument\nTry $0 --help for more information" >&2
            exit 1
            ;;
        *)
            usage >&2
            exit -1
            ;;
    esac
done

#check root privileges and non a root user behind
[ "$USER" != "root" ] && echo "Needed root privileges" >&2 && exit 1

#Discover Linux distribution
#try redhat type
[ -f /etc/redhat-release ] && _DISTRO=$(cat /etc/redhat-release 2>/dev/null | cut  -d" " -f1) 
#if not assuming ubuntu type
[ -f /etc/redhat-release ] || _DISTRO=$(lsb_release -is  2>/dev/null)            
if [ "$_DISTRO" == "Ubuntu" ]
then
    _RELEASE=`lsb_release -rs`
    if ! lsb_release -rs | grep -q -e "16.04"
    then 
        echo "Only tested in Ubuntu Server 16.04" >&2 && exit 1
    fi
else
    echo "Only tested in Ubuntu Server 16.04" >&2 && exit 1
fi


if [[ -z $FILE ]]
then
    git clone https://osm.etsi.org/gerrit/osm/RO.git openmano
    FILE=./openmano
    DELETE=y
fi
cp -r $FILE /opt/openmano
cp ${FILE}/openmano /usr/sbin/
mv /opt/openmano/openmanod.cfg /etc/default/openmanod.cfg
mkdir -p /var/log/openmano/
mkdir -p etc/systemd/system/


cat  >> /etc/systemd/system/openmano.service  << EOF 
[Unit]
Description=openmano server

[Service]
User=${USER}
ExecStart=/opt/openmano/openmanod.py -c /etc/default/openmanod.cfg --log-file=/var/log/openmano/openmano.log
Restart=always

[Install]
WantedBy=multi-user.target
EOF

[[ -n $DELETE ]] && rm -rf $FILE

service openmano start

echo Done
exit
