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

#This script can be used as a basic test of openmano.
#WARNING: It destroy the database content


function usage(){
    echo -e "usage: ${BASH_SOURCE[0]} [OPTIONS] <action>\n  test openmano using openvim as a VIM"
    echo -e "           the OPENVIM_HOST, OPENVIM_PORT shell variables indicate openvim location"
    echo -e "           by default localhost:9080"
    echo -e "  <action> is a list of the following items (by default 'reset create delete')"
    echo -e "    reset     reset the openmano database content"
    echo -e "    create    creates items"
    echo -e "    delete    delete created items"
    echo -e "  OPTIONS:"
    echo -e "    -f --force       does not prompt for confirmation"
    echo -e "    -h --help        shows this help"
    echo -e "    --insert-bashrc  insert the created tenant,datacenter variables at"
    echo -e "                     ~/.bashrc to be available by openmano CLI"
    echo -e "    --init-openvim   if openvim runs locally, an init is called to clean openvim"
    echo -e "                      database and add fake hosts"
}

function is_valid_uuid(){
    echo "$1" | grep -q -E '^[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}$' && return 0
    return 1
}

#detect if is called with a source to use the 'exit'/'return' command for exiting
[[ ${BASH_SOURCE[0]} != $0 ]] && _exit="return" || _exit="exit"


#check correct arguments
force=""
action_list=""
insert_bashrc=""
init_openvim=""
for param in $*
do
    if [[ $param == reset ]] || [[ $param == create ]] || [[ $param == delete ]]
    then
        action_list="$action_list $param"
    elif [[ $param == -h ]] || [[ $param == --help ]]
    then
        usage
        $_exit 0
    elif [[ $param == -f ]] || [[ $param == --force ]]
    then
        force="-f"
    elif [[ $param == --insert-bashrc ]]
    then
        insert_bashrc=y
    elif [[ $param == --init-openvim ]]
    then
        init_openvim=y
    else
        echo "invalid argument '$param'?  Type -h for help" >&2 && $_exit 1
    fi
done

DIRNAME=$(dirname $(readlink -f ${BASH_SOURCE[0]}))
DIRmano=$(dirname $DIRNAME)
DIRscript=${DIRmano}/scripts
export OPENMANO_HOST=localhost
export OPENMANO_PORT=9090
[[ $insert_bashrc == y ]] && echo -e "\nexport OPENMANO_HOST=localhost"  >> ~/.bashrc
[[ $insert_bashrc == y ]] && echo -e "\nexport OPENMANO_PORT=9090"  >> ~/.bashrc


#by default action should be reset and create
[[ -z $action_list ]]  && action_list="reset create delete"
[[ -z $init_openvim ]] || initopenvim $force || echo "WARNING openvim cannot be initialized. The rest of test can fail!"

#check openvim client variables are set
#fail=""
#[[ -z $OPENVIM_HOST ]] && echo "OPENVIM_HOST variable not defined" >&2 && fail=1
#[[ -z $OPENVIM_PORT ]] && echo "OPENVIM_PORT variable not defined" >&2 && fail=1
#[[ -n $fail ]] && $_exit 1


for action in $action_list
do
#if [[ $action == "install-openvim" ]]
    #echo "Installing and starting openvim"
    #mkdir -p temp
    #pushd temp
    #wget https://github.com/nfvlabs/openvim/raw/v0.4/scripts/install-openvim.sh
    #chmod -x install-openvim.sh
#fi

if [[ $action == "reset" ]]
then

    #ask for confirmation if argument is not -f --force
    force_=y
    [[ -z $force ]] && read -e -p "WARNING: reset openmano database, content will be lost!!! Continue(y/N) " force_
    [[ $force_ != y ]] && [[ $force_ != yes ]] && echo "aborted!" && $_exit

    echo "Stopping openmano"
    $DIRscript/service-openmano.sh mano stop
    echo "Initializing openmano database"
    $DIRmano/database_utils/init_mano_db.sh -u mano -p manopw
    echo "Starting openmano"
    $DIRscript/service-openmano.sh mano start
    echo

elif [[ $action == "delete" ]]
then
    result=`openmano tenant-list TEST-tenant`
    nfvotenant=`echo $result |gawk '{print $1}'`
    #check a valid uuid is obtained
    is_valid_uuid $nfvotenant || ! echo "Tenant TEST-tenant not found. Already delete?" >&2 || $_exit 1
    export OPENMANO_TENANT=$nfvotenant
    ${DIRmano}/openmano instance-scenario-delete -f simple-instance     || echo "fail"
    ${DIRmano}/openmano instance-scenario-delete -f complex-instance    || echo "fail"
    ${DIRmano}/openmano instance-scenario-delete -f complex2-instance   || echo "fail"
    ${DIRmano}/openmano scenario-delete -f simple       || echo "fail"
    ${DIRmano}/openmano scenario-delete -f complex      || echo "fail"
    ${DIRmano}/openmano scenario-delete -f complex2     || echo "fail"
    ${DIRmano}/openmano vnf-delete -f linux             || echo "fail"
    ${DIRmano}/openmano vnf-delete -f dataplaneVNF_2VMs || echo "fail"
    ${DIRmano}/openmano vnf-delete -f dataplaneVNF2     || echo "fail"
    ${DIRmano}/openmano vnf-delete -f dataplaneVNF3     || echo "fail"
    ${DIRmano}/openmano datacenter-detach TEST-dc        || echo "fail"
    ${DIRmano}/openmano datacenter-delete -f TEST-dc     || echo "fail"
    ${DIRmano}/openmano tenant-delete -f TEST-tenant     || echo "fail"
    echo

elif [[ $action == "create" ]]
then
    printf "%-50s" "Creating openmano tenant 'TEST-tenant': "
    result=`${DIRmano}/openmano tenant-create TEST-tenant --description="created by basictest.sh"`
    nfvotenant=`echo $result |gawk '{print $1}'`
    #check a valid uuid is obtained
    ! is_valid_uuid $nfvotenant && echo "FAIL" && echo "    $result" && $_exit 1
    export OPENMANO_TENANT=$nfvotenant
    [[ $insert_bashrc == y ]] && echo -e "\nexport OPENMANO_TENANT=$nfvotenant"  >> ~/.bashrc
    echo $nfvotenant

    printf "%-50s" "Creating datacenter 'TEST-dc' in openmano:"
    [[ -z $OPENVIM_HOST ]] && OPENVIM_HOST=localhost
    [[ -z $OPENVIM_PORT ]] && OPENVIM_PORT=9080
    URL_ADMIN_PARAM=""
    [[ -n $OPENVIM_ADMIN_PORT ]] && URL_ADMIN_PARAM="--url_admin=http://${$OPENVIM_HOST}:${OPENVIM_ADMIN_PORT}/openvim"
    result=`${DIRmano}/openmano datacenter-create TEST-dc "http://${OPENVIM_HOST}:${OPENVIM_PORT}/openvim" --type=openvim $URL_ADMIN_PARAM`
    datacenter=`echo $result |gawk '{print $1}'`
    #check a valid uuid is obtained
    ! is_valid_uuid $datacenter && echo "FAIL" && echo "    $result" && $_exit 1
    echo $datacenter
    export OPENMANO_DATACENTER=$datacenter
    [[ $insert_bashrc == y ]] && echo -e "\nexport OPENMANO_DATACENTER=$datacenter"  >> ~/.bashrc

    printf "%-50s" "Attaching openmano tenant to the datacenter:"
    result=`${DIRmano}/openmano datacenter-attach TEST-dc`
    [[ $? != 0 ]] && echo  "FAIL" && echo "    $result" && $_exit 1
    echo OK

    printf "%-50s" "Updating external nets in openmano: "
    result=`${DIRmano}/openmano datacenter-netmap-delete -f --all`
    [[ $? != 0 ]] && echo  "FAIL" && echo "    $result"  && $_exit 1
    result=`${DIRmano}/openmano datacenter-netmap-upload -f`
    [[ $? != 0 ]] && echo  "FAIL" && echo "    $result"  && $_exit 1
    echo OK

    for VNF in linux dataplaneVNF1 dataplaneVNF2 dataplaneVNF_2VMs dataplaneVNF3
    do    
        printf "%-50s" "Creating VNF '${VNF}': "
        result=`$DIRmano/openmano vnf-create $DIRmano/vnfs/examples/${VNF}.yaml`
        vnf=`echo $result |gawk '{print $1}'`
        #check a valid uuid is obtained
        ! is_valid_uuid $vnf && echo FAIL && echo "    $result" &&  $_exit 1
        echo $vnf
    done
    for NS in simple complex complex2
    do
        printf "%-50s" "Creating scenario '${NS}':"
        result=`$DIRmano/openmano scenario-create $DIRmano/scenarios/examples/${NS}.yaml`
        scenario=`echo $result |gawk '{print $1}'`
        ! is_valid_uuid $scenario && echo FAIL && echo "    $result" &&  $_exit 1
        echo $scenario
    done

    for IS in simple complex complex2
    do
        printf "%-50s" "Creating instance-scenario '${IS}':"
        result=`$DIRmano/openmano instance-scenario-create  --scenario ${IS} --name ${IS}-instance`
        instance=`echo $result |gawk '{print $1}'`
        ! is_valid_uuid $instance && echo FAIL && echo "    $result" &&  $_exit 1
        echo $instance
    done

    echo
    #echo "Check virtual machines are deployed"
    #vms_error=`openvim vm-list | grep ERROR | wc -l`
    #vms=`openvim vm-list | wc -l`
    #[[ $vms -ne 8 ]]       &&  echo "WARNING: $vms VMs created, must be 8 VMs" >&2 && $_exit 1
    #[[ $vms_error -gt 0 ]] &&  echo "WARNING: $vms_error VMs with ERROR" >&2       && $_exit 1
fi
done

echo
echo DONE


