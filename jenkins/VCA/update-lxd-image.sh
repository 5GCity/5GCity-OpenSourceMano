#!/bin/bash
#
# This script will create xenial and trusty lxd images that will be used by the
# lxd provider in juju 2.1+ It is for use with the lxd provider for local
# development and preinstalls a common set of production packages.
#
# This dramatically speeds up the install hooks for lxd deploys by
# pre-installing common packages. It is intended to run daily as part of
# a cron job.
set -eux

# The basic charm layer also installs all the things. 47 packages.
LAYER_BASIC="gcc build-essential python3-pip python3-setuptools libyaml-dev python3-yaml python3-dev"

# the basic layer also installs virtualenv, but the name changed in xenial.
TRUSTY_PACKAGES="python-virtualenv"
XENIAL_PACKAGES="virtualenv"

# Predownload common packages used by your charms in development
DOWNLOAD_PACKAGES=""

PACKAGES="$LAYER_BASIC $DOWNLOAD_PACKAGES"

# Packages from pypi to pre-install
PYPI="charms.reactive charmhelpers paramiko>=1.16.0,<1.17"

function cache() {
    series=$1
    container=juju-${series}-base
    alias=juju/$series/amd64

    lxc delete $container -f || true
    lxc launch ubuntu:$series $container

    # Wait for the container to get an IP address
    lxc exec $container -- bash -c "for i in {1..60}; do sleep 1; ping -c1 10.44.127.1 &> /dev/null && break; done"

    # Wait for cloud-init to finish
    lxc exec $container -- bash -c "while [ ! -f /var/lib/cloud/instance/boot-finished ]; do sleep 1; done"

    lxc exec $container -- apt-get update -y
    lxc exec $container -- apt-get upgrade -y -o Dpkg::Options::='--force-confold'
    lxc exec $container -- apt-get install -y $PACKAGES $2
    lxc exec $container -- pip3 install --upgrade pip
    lxc exec $container -- pip3 install --upgrade $PYPI
    lxc stop $container

    lxc image delete $alias || true
    lxc publish $container --alias $alias description="$series juju dev image ($(date +%Y%m%d))"

    lxc delete $container -f || true
}

# Cache the image for the Ubuntu series or series to support
# cache trusty "$TRUSTY_PACKAGES"
cache xenial "$XENIAL_PACKAGES"
