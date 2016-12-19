#!/bin/bash
#   Copyright 2016 Telefónica Investigación y Desarrollo S.A.U.
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

function usage(){
    echo -e "usage: $0 [OPTIONS]"
    echo -e "Install OSM from source code"
    echo -e "  OPTIONS"
    echo -e "     --uninstall:   uninstall OSM: remove the containers and delete NAT rules"
    echo -e "     -b <branch>:   install OSM from source code using a specific branch (master, v1.0, ...)"
    echo -e "     --develop:     (deprecated, use '-b master') install OSM from source code using the master branch"
    echo -e "     --nat:         install only NAT rules"
    echo -e "     -h / --help:   print this help"
}

#Uninstall OSM: remove containers
function uninstall(){
    if [ $RC_CLONE ] || [ -n "$TEST_INSTALLER" ]; then
        $OSM_DEVOPS/jenkins/host/clean_container RO
        $OSM_DEVOPS/jenkins/host/clean_container VCA
        $OSM_DEVOPS/jenkins/host/clean_container SO
        #$OSM_DEVOPS/jenkins/host/clean_container UI
    else
        lxc stop RO && lxc delete RO
        lxc stop VCA && lxc delete VCA
        lxc stop SO-ub && lxc delete SO-ub
    fi
}

#Configure NAT rules, based on the current IP addresses of containers
function nat(){
    echo -e "\nChecking required packages: iptables-persistent"
    dpkg -l iptables-persistent &>/dev/null || ! echo -e "    Not installed.\nInstalling iptables-persistent requires root privileges" || \
    sudo DEBIAN_FRONTEND=noninteractive apt-get -yq install iptables-persistent
    echo -e "\nConfiguring NAT rules"
    echo -e "   Required root privileges"
    sudo $OSM_DEVOPS/installers/nat_osm
}

#Configure VCA, SO and RO with the initial configuration:
#  RO -> tenant:osm, logs to be sent to SO
#  VCA -> juju-password
#  SO -> route to Juju Controller, add RO account, add VCA account
function configure(){
    #Configure components
    echo -e "\nConfiguring components"
    . $OSM_DEVOPS/installers/export_ips

    echo -e "       Configuring RO"
    lxc exec RO -- sed -i -e "s/^\#\?log_socket_host:.*/log_socket_host: $SO_CONTAINER_IP/g" /opt/openmano/openmanod.cfg
    lxc exec RO -- service openmano restart
    time=0; step=2; timelength=20; while [ $time -le $timelength ]; do sleep $step; echo -n "."; time=$((time+step)); done; echo
    lxc exec RO -- openmano tenant-delete -f osm >/dev/null
    RO_TENANT_ID=`lxc exec RO -- openmano tenant-create osm |awk '{print $1}'`

    echo -e "       Configuring VCA"
    JUJU_PASSWD=`date +%s | sha256sum | base64 | head -c 32`
    echo -e "$JUJU_PASSWD\n$JUJU_PASSWD" | lxc exec VCA -- juju change-user-password
    JUJU_CONTROLLER_IP=`lxc exec VCA -- lxc list -c 4 |grep eth0 |awk '{print $2}'`

    echo -e "       Configuring SO"
    sudo route add -host $JUJU_CONTROLLER_IP gw $VCA_CONTAINER_IP
    lxc exec SO-ub -- nohup sudo -b -H /usr/rift/rift-shell -r -i /usr/rift -a /usr/rift/.artifacts -- ./demos/launchpad.py --use-xml-mode &
    time=0; step=30; timelength=300; while [ $time -le $timelength ]; do sleep $step; echo -n "."; time=$((time+step)); done; echo

    curl -k --request POST \
      --url https://$SO_CONTAINER_IP:8008/api/config/config-agent \
      --header 'accept: application/vnd.yang.data+json' \
      --header 'authorization: Basic YWRtaW46YWRtaW4=' \
      --header 'cache-control: no-cache' \
      --header 'content-type: application/vnd.yang.data+json' \
      --data '{"account": [ { "name": "osmjuju", "account-type": "juju", "juju": { "ip-address": "'$JUJU_CONTROLLER_IP'", "port": "17070", "user": "admin", "secret": "'$JUJU_PASSWD'" }  }  ]}'

    curl -k --request PUT \
      --url https://$SO_CONTAINER_IP:8008/api/config/resource-orchestrator \
      --header 'accept: application/vnd.yang.data+json' \
      --header 'authorization: Basic YWRtaW46YWRtaW4=' \
      --header 'cache-control: no-cache' \
      --header 'content-type: application/vnd.yang.data+json' \
      --data '{ "openmano": { "host": "'$RO_CONTAINER_IP'", "port": "9090", "tenant-id": "'$RO_TENANT_ID'" }, "name": "osmopenmano", "account-type": "openmano" }'

}

function install_lxd() {
    lxd init --auto
    lxd waitready
    systemctl stop lxd-bridge
    systemctl --system daemon-reload
    systemctl enable lxd-bridge
    systemctl start lxd-bridge
}


UNINSTALL=""
DEVELOP=""
NAT=""
RECONFIGURE=""
TEST_INSTALLER=""
LXD=""
SHOWOPTS=""
COMMIT_ID=""
while getopts ":h-:b:" o; do
    case "${o}" in
        h)
            usage && exit 0
            ;;
        b)
            COMMIT_ID=${OPTARG}
            ;;
        -)
            [ "${OPTARG}" == "help" ] && usage && exit 0
            [ "${OPTARG}" == "develop" ] && DEVELOP="y" && continue
            [ "${OPTARG}" == "uninstall" ] && UNINSTALL="y" && continue
            [ "${OPTARG}" == "nat" ] && NAT="y" && continue
            [ "${OPTARG}" == "reconfigure" ] && RECONFIGURE="y" && continue
            [ "${OPTARG}" == "test" ] && TEST_INSTALLER="y" && continue
            [ "${OPTARG}" == "lxd" ] && LXD="y" && continue
            [ "${OPTARG}" == "showopts" ] && SHOWOPTS="y" && continue
            echo -e "Invalid option: '--$OPTARG'\n" >&2
            usage && exit 1
            ;;
        \?)
            echo -e "Invalid option: '-$OPTARG'\n" >&2
            usage && exit 1
            ;;
        *)
            usage && exit 1
            ;;
    esac
done

[ -z "$COMMIT_ID" ] && [ -n "$DEVELOP" ] && COMMIT_ID="master"
[ -z "$COMMIT_ID" ] && COMMIT_ID="tags/v1.0.2"

if [ -n "$SHOWOPTS" ]; then
    echo "UNINSTALL=$UNINSTALL"
    echo "DEVELOP=$DEVELOP"
    echo "NAT=$NAT"
    echo "RECONFIGURE=$RECONFIGURE"
    echo "TEST_INSTALLER=$TEST_INSTALLER"
    echo "LXD=$LXD"
    echo "Commit: $COMMIT_ID"
    exit 0
fi

if [ -n "$TEST_INSTALLER" ]; then
    echo -e "\nUsing local devops repo for OSM installation"
    TEMPDIR="$(dirname $(realpath $(dirname $0)))"
else
    echo -e "\nCreating temporary dir for OSM installation"
    TEMPDIR="$(mktemp -d -q --tmpdir "installosm.XXXXXX")"
    trap 'rm -rf "$TEMPDIR"' EXIT
fi

echo -e "Checking required packages: git"
dpkg -l git &>/dev/null || ! echo -e "     git not installed.\nInstalling git requires root privileges" || sudo apt install -y git
if [ -z "$TEST_INSTALLER" ]; then
    echo -e "\nCloning devops repo temporarily"
    git clone https://osm.etsi.org/gerrit/osm/devops.git $TEMPDIR
    RC_CLONE=$?
    DEVOPS_COMMITID="tags/v1.0.2"
    git -C $TEMPDIR checkout $DEVOPS_COMMITID
fi
OSM_DEVOPS=$TEMPDIR
OSM_JENKINS="$TEMPDIR/jenkins"
. $OSM_JENKINS/common/all_funcs

[ -n "$UNINSTALL" ] && uninstall && echo -e "\nDONE" && exit 0
[ -n "$NAT" ] && nat && echo -e "\nDONE" && exit 0
[ -n "$RECONFIGURE" ] && configure && echo -e "\nDONE" && exit 0

#Installation starts here
wget -q -O- https://osm-download.etsi.org/ftp/osm-1.0-one/README.txt &> /dev/null

[ -n "$LXD" ] && echo -e "\nConfiguring lxd" && install_lxd

echo -e "\nChecking required packages: wget, curl, tar"
dpkg -l wget curl tar &>/dev/null || ! echo -e "    One or several packages are not installed.\nInstalling required packages\n     Root privileges are required" || sudo apt install -y wget curl tar

echo -e "\nCreating the containers and building ..."
$OSM_DEVOPS/jenkins/host/start_build RO checkout $COMMIT_ID
$OSM_DEVOPS/jenkins/host/start_build VCA
$OSM_DEVOPS/jenkins/host/start_build SO checkout $COMMIT_ID
$OSM_DEVOPS/jenkins/host/start_build UI checkout $COMMIT_ID

#Install iptables-persistent and configure NAT rules
nat

#Configure components
configure

echo -e "\nDONE"


