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
    echo -e "     -u USER_OWNER  user owner of the service, 'root' by default"
    echo -e "     -f PATH  path where openmano source is located. If missing it is downloaded from git"
    #echo -e "     -q:  install in an unattended mode"
    echo -e "     -h:  show this help"
    echo -e "     --uninstall: remove created service and files"
}

function uninstall(){
    service openmano stop
    for file in /opt/openmano /etc/default/openmanod.cfg /var/log/openmano /etc/systemd/system/openmano.service /usr/sbin/openmano
    do
        rm -rf $file || ! echo "Can not delete '$file'. Needed root privileges?" >&2 || exit 1
    done
    echo "Done"
}

BAD_PATH_ERROR="Path '$FILE' does not contain a valid openmano distribution"
GIT_URL=https://osm.etsi.org/gerrit/osm/RO.git
USER_OWNER="root"
QUIET_MODE=""
FILE=""
DELETE=""
while getopts ":u:f:hq-:" o; do
    case "${o}" in
        u)
            export USER_OWNER="$OPTARG"
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
            [ "${OPTARG}" == "uninstall" ] && uninstall && exit 0
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

#check root privileges
[ "$USER" != "root" ] && echo "Needed root privileges" >&2 && exit 1

#Discover Linux distribution
#try redhat type
if [[ -f /etc/redhat-release ]]
then 
    _DISTRO=$(cat /etc/redhat-release 2>/dev/null | cut  -d" " -f1)
else 
    #if not assuming ubuntu type
    _DISTRO=$(lsb_release -is  2>/dev/null)
fi            
if [[ "$_DISTRO" == "Ubuntu" ]]
then
    _RELEASE=$(lsb_release -rs)
    if [[ ${_RELEASE%%.*} != 16 ]] 
    then 
        echo "Only tested in Ubuntu Server 16.04" >&2 && exit 1
    fi
else
    echo "Only tested in Ubuntu Server 16.04" >&2 && exit 1
fi


if [[ -z $FILE ]]
then
    git clone $GIT_URL __temp__ || ! echo "Cannot get openmano source code from $GIT_URL" >&2 || exit 1
    #git checkout <tag version>
    FILE=./__temp__
    DELETE=y
fi

#make idempotent
rm -rf /opt/openmano
rm -f /etc/default/openmanod.cfg
rm -f /var/log/openmano
cp -r $FILE /opt/openmano         || ! echo $BAD_PATH_ERROR >&2 || exit 1
mkdir -p /opt/openmano/logs
rm -rf /usr/sbin/openmano
#cp ${FILE}/openmano /usr/sbin/    || ! echo $BAD_PATH_ERROR >&2 || exit 1
ln -s /opt/openmano/openmanod.cfg /etc/default/openmanod.cfg  || echo "warning cannot create link '/etc/default/openmanod.cfg'"
ln -s /opt/openmano/logs /var/log/openmano  || echo "warning cannot create link '/var/log/openmano'"
ln -s /opt/openmano/openmano /usr/sbin/openmano

chown $USER_OWNER /opt/openmano/openmanod.cfg
chown -R $USER_OWNER /opt/openmano

mkdir -p /etc/systemd/system/
cat  > /etc/systemd/system/openmano.service  << EOF 
[Unit]
Description=openmano server

[Service]
User=${USER_OWNER}
ExecStart=/opt/openmano/openmanod.py -c /opt/openmano/openmanod.cfg --log-file=/opt/openmano/logs/openmano.log
Restart=always

[Install]
WantedBy=multi-user.target
EOF

[[ -n $DELETE ]] && rm -rf $FILE

service openmano start

echo Done
exit
