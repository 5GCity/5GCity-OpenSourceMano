#!/bin/bash

##
# Copyright 2015 Telefonica Investigacion y Desarrollo, S.A.U.
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
##

# author: Alfonso Tierno

# It uses following env, if not provided filling by default
[ -z "$GIT_OSMIM_URL" ] && GIT_OSMIM_URL=https://osm.etsi.org/gerrit/osm/IM.git
[ -z "$DEVELOP" ] && DEVELOP=""
# folder where RO is installed
[ -z "$BASEFOLDER" ] && HERE=$(dirname $(readlink -f ${BASH_SOURCE[0]})) && BASEFOLDER=$(dirname $HERE)
[ -z "$SUDO_USER" ] && SUDO_USER="$USER"
[ -z "$NO_PACKAGES" ] && NO_PACKAGES=""
[ -z "$_DISTRO" ] && _DISTRO="Ubuntu"

function usage(){
    echo -e "usage: sudo -E $0 [OPTIONS]"
    echo -e "Install last stable source code of osm-im and the needed packages"
    echo -e "  OPTIONS"
    echo -e "     -h --help:  show this help"
    echo -e "     -b REFSPEC: install from source code using a specific branch (master, v2.0, ...) or tag"
    echo -e "                    -b master          (main branch)"
    echo -e "                    -b v2.0            (v2.0 branch)"
    echo -e "                    -b tags/v1.1.0     (a specific tag)"
    echo -e "                    ..."
    echo -e "     --develop:  install last master version for developers"
    echo -e "     --no-install-packages: use this option to skip updating and installing the requires packages. This" \
            "avoid wasting time if you are sure requires packages are present e.g. because of a previous installation"
}
while getopts ":b:h-:" o; do
    case "${o}" in
        b)
            export COMMIT_ID=${OPTARG}
            ;;
        h)
            usage && exit 0
            ;;
        -)
            [ "${OPTARG}" == "help" ] && usage && exit 0
            [ "${OPTARG}" == "develop" ] && export DEVELOP="y" && continue
            [ "${OPTARG}" == "quiet" ] && export QUIET_MODE=yes && export DEBIAN_FRONTEND=noninteractive && continue
            [ "${OPTARG}" == "no-install-packages" ] && export NO_PACKAGES=yes && continue
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
            exit 1
            ;;
    esac
done

su $SUDO_USER -c "git -C ${BASEFOLDER} clone ${GIT_OSMIM_URL} IM" ||
    ! echo "Error cannot clone from '${GIT_OSMIM_URL}'" >&2 || exit 1
if [[ -n $COMMIT_ID ]] ; then
    echo -e "Installing osm-IM from refspec: $COMMIT_ID"
    su $SUDO_USER -c "git -C ${BASEFOLDER}/IM checkout $COMMIT_ID" ||
        ! echo "Error cannot checkout '$COMMIT_ID' from '${GIT_OSMIM_URL}'" >&2 || exit 1
elif [[ -z $DEVELOP ]]; then
    LATEST_STABLE_TAG=`git -C "${BASEFOLDER}/IM" tag -l "v[0-9]*" | sort -V | tail -n1`
    echo -e "Installing osm-IM from refspec: tags/${LATEST_STABLE_TAG}"
    su $SUDO_USER -c "git -C ${BASEFOLDER}/IM checkout tags/${LATEST_STABLE_TAG}" ||
        ! echo "Error cannot checkout 'tags/${LATEST_STABLE_TAG}' from '${GIT_OSMIM_URL}'" >&2 || exit 1
else
    echo -e "Installing osm-IM from refspec: master"
fi

# Install debian dependencies before setup.py
if [[ -z "$NO_PACKAGES" ]]
then
    # apt-get update
    # apt-get install -y git python-pip
    # pip2 install pip==9.0.3
    pip2 install pyangbind || exit 1
fi

PYBINDPLUGIN=$(python2 -c 'import pyangbind; import os; print "%s/plugin" % os.path.dirname(pyangbind.__file__)')
su $SUDO_USER -c 'mkdir -p "'${BASEFOLDER}/IM/osm_im'"'
su $SUDO_USER -c 'touch "'${BASEFOLDER}/IM/osm_im/__init__.py'"'
# wget -q https://raw.githubusercontent.com/RIFTIO/RIFT.ware/RIFT.ware-4.4.1/modules/core/util/yangtools/yang/rw-pb-ext.yang -O "${BASEFOLDER}/IM/models/yang/rw-pb-ext.yang"
for target in vnfd nsd ; do
    pyang -Werror --path "${BASEFOLDER}/IM/models/yang" --plugindir "${PYBINDPLUGIN}" -f pybind \
        -o "${BASEFOLDER}/IM/osm_im/${target}.py" "${BASEFOLDER}/IM/models/yang/${target}.yang"
done

pip2 install -e "${BASEFOLDER}/IM" || ! echo "ERROR installing python-osm-im library!!!" >&2  || exit 1
