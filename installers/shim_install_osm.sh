#!/bin/bash
#   Copyright 2017 Telefónica Investigación y Desarrollo S.A.U.
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
    echo -e "Install OSM from binaries or source code (by default, from binaries)"
    echo -e "  OPTIONS"
    echo -e "     --uninstall:    uninstall OSM: remove the containers and delete NAT rules"
    echo -e "     --source:       install OSM from source code using the latest stable tag"
    echo -e "     -r <repo>:      use specified repository name for osm packages"
    echo -e "     -R <release>:   use specified release for osm binaries (deb packages, lxd images, ...)"
    echo -e "     -u <repo base>: use specified repository url for osm packages"
    echo -e "     -k <repo key>:  use specified repository public key url"
    echo -e "     -b <refspec>:   install OSM from source code using a specific branch (master, v2.0, ...) or tag"
    echo -e "                     -b master          (main dev branch)"
    echo -e "                     -b v2.0            (v2.0 branch)"
    echo -e "                     -b tags/v1.1.0     (a specific tag)"
    echo -e "                     ..."
    echo -e "     --lxdimages:    download lxd images from OSM repository instead of creating them from scratch"
    echo -e "     -l <lxd_repo>:  use specified repository url for lxd images"
    echo -e "     --develop:      (deprecated, use '-b master') install OSM from source code using the master branch"
#    echo -e "     --reconfigure:  reconfigure the modules (DO NOT change NAT rules)"
    echo -e "     --nat:          install only NAT rules"
    echo -e "     --noconfigure:  DO NOT install osmclient, DO NOT install NAT rules, DO NOT configure modules"
#    echo -e "     --update:       update to the latest stable release or to the latest commit if using a specific branch"
    echo -e "     --showopts:     print chosen options and exit (only for debugging)"
    echo -e "     -y:             do not prompt for confirmation, assumes yes"
    echo -e "     -h / --help:    print this help"
}

function FATAL() {
    echo -e $1
    exit 1
}

TEST_INSTALLER=""
LATEST_STABLE_DEVOPS=""

while getopts ":h" o; do
    case "${o}" in
        h)
            usage && exit 0
            ;;
        -)
            [ "${OPTARG}" == "help" ] && usage && exit 0
            [ "${OPTARG}" == "test" ] && TEST_INSTALLER="y" && continue
            ;;
    esac
done

if [ -n "$TEST_INSTALLER" ]; then
    echo -e "\nUsing local devops repo for OSM installation"
    TEMPDIR="$(dirname $(realpath $(dirname $0)))"
else
    echo -e "\nCreating temporary dir for OSM installation"
    TEMPDIR="$(mktemp -d -q --tmpdir "installosm.XXXXXX")"
    trap 'rm -rf "$TEMPDIR"' EXIT
fi

if [ -z "$TEST_INSTALLER" ]; then
    need_packages="git"
    for package in $need_packages; do
        echo -e "Checking required packages: $package"
        dpkg -l $package &>/dev/null \
            || ! echo -e "     $package not installed.\nInstalling $package requires root privileges" \
            || sudo apt-get install -y $package \
            || FATAL "failed to install $package"
    done
    echo -e "\nCloning devops repo temporarily"
    git clone https://osm.etsi.org/gerrit/osm/devops.git $TEMPDIR
    echo -e "\nGuessing the current stable release"
    LATEST_STABLE_DEVOPS=`git -C $TEMPDIR tag -l v[0-9].* | sort -V | tail -n1`
    [ -z "$LATEST_STABLE_DEVOPS" ] && FATAL "Could not find the current latest stable release"
    echo "Using latest tag in devops repo: $LATEST_STABLE_DEVOPS"
    git -C $TEMPDIR checkout tags/$LATEST_STABLE_DEVOPS || FATAL "Could not checkout latest tag"
fi

$TEMPDIR/installers/install_osm.sh --test $*

