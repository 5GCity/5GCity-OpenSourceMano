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

# author: Alfonso Tierno
# Script that uses the test NBI URL to clean database. See usage


function usage(){
    echo -e "usage: $0 [OPTIONS]"
    echo -e "TEST NBI API is used to clean database content, except user admin. Useful for testing."
    echo -e "NOTE: database is cleaned but not the content of other modules as RO or VCA that must be cleaned manually."
    echo -e "  OPTIONS"
    echo -e "     -h --help:   show this help"
    echo -e "     -f --force:  Do not ask for confirmation"
    echo -e "     --completely:  It cleans also user admin. NBI will need to be restarted to init database"
    echo -e "     --clean-RO:  clean RO content. RO client (openmano) must be installed and configured"
    echo -e "     --clean-VCA: clean VCA content. juju  must be installed and configured"
    echo -e "  ENV variable 'OSMNBI_URL' is used for the URL of the NBI server. If missing, it uses" \
            "'https://\$OSM_HOSTNAME:9999/osm'. If 'OSM_HOSTNAME' is missing, localhost is used"
}


function ask_user(){
    # ask to the user and parse a response among 'y', 'yes', 'n' or 'no'. Case insensitive.
    # Params: $1 text to ask;   $2 Action by default, can be 'y' for yes, 'n' for no, other or empty for not allowed.
    # Return: true(0) if user type 'yes'; false (1) if user type 'no'
    read -e -p "$1" USER_CONFIRMATION
    while true ; do
        [ -z "$USER_CONFIRMATION" ] && [ "$2" == 'y' ] && return 0
        [ -z "$USER_CONFIRMATION" ] && [ "$2" == 'n' ] && return 1
        [ "${USER_CONFIRMATION,,}" == "yes" ] || [ "${USER_CONFIRMATION,,}" == "y" ] && return 0
        [ "${USER_CONFIRMATION,,}" == "no" ]  || [ "${USER_CONFIRMATION,,}" == "n" ] && return 1
        read -e -p "Please type 'yes' or 'no': " USER_CONFIRMATION
    done
}


while [ -n "$1" ]
do
    option="$1"
    shift
    ( [ "$option" == -h ] || [ "$option" == --help ] ) && usage && exit
    ( [ "$option" == -f ] || [ "$option" == --force ] ) && OSMNBI_CLEAN_FORCE=yes && continue
    [ "$option" == --completely ] && OSMNBI_COMPLETELY=yes && continue
    [ "$option" == --clean-RO ] && OSMNBI_CLEAN_RO=yes && continue
    [ "$option" == --clean-VCA ] && OSMNBI_CLEAN_VCA=yes && continue
    echo "Unknown option '$option'. Type $0 --help" 2>&1 && exit 1
done


[ -n "$OSMNBI_CLEAN_FORCE" ] || ask_user "Clean database content (y/N)?" n || exit
[ -z "$OSM_HOSTNAME" ] && OSM_HOSTNAME=localhost
[ -z "$OSMNBI_URL" ] && OSMNBI_URL="https://${OSM_HOSTNAME}:9999/osm"

if [ -n "$OSMNBI_CLEAN_RO" ]
then
    export OPENMANO_TENANT=osm
    for dc in `openmano datacenter-list | awk '{print $1}'`
    do
        export OPENMANO_DATACENTER=$dc
        for i in instance-scenario scenario vnf
        do
            for f in `openmano $i-list | awk '{print $1}'`
            do
                [[ -n "$f" ]] && [[ "$f" != No ]] && openmano ${i}-delete -f ${f}
            done
        done
    done
fi

for item in vim_accounts wim_accounts sdns nsrs vnfrs nslcmops nsds vnfds projects pdus nsts nsis nsilcmops # vims
do
    curl --insecure ${OSMNBI_URL}/test/db-clear/${item}
done
    curl --insecure ${OSMNBI_URL}/test/fs-clear
if [ -n "$OSMNBI_COMPLETELY" ] ; then
    curl --insecure ${OSMNBI_URL}/test/db-clear/users
    curl --insecure ${OSMNBI_URL}/test/db-clear/admin
else
    # delete all users except admin
    curl --insecure ${OSMNBI_URL}/test/db-clear/users?username.ne=admin
fi

if [ -n "$OSMNBI_CLEAN_RO" ]
then
    for dc in `openmano datacenter-list | awk '{print $1}'` ; do openmano datacenter-detach $dc ; done
    for dc in `openmano datacenter-list --all | awk '{print $1}'` ; do openmano datacenter-delete -f  $dc ; done
    for dc in `openmano sdn-controller-list | awk '{print $1}'` ; do openmano sdn-controller-delete -f $dc ; done
    for dc in `openmano wim-list | awk '{print $1}'` ; do openmano wim-detach $dc ; done
    for dc in `openmano wim-list --all | awk '{print $1}'` ; do openmano wim-delete -f  $dc ; done
fi

if [ -n "$OSMNBI_CLEAN_VCA" ]
then
    juju destroy-model -y default
    juju add-model default
fi
