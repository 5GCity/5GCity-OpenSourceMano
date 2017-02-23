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
LAYER_BASIC="gcc build-essential python3-pip python3-setuptools python3-yaml"

# the basic layer also installs virtualenv, but the name changed in xenial.
TRUSTY_PACKAGES="python-virtualenv"
XENIAL_PACKAGES="virtualenv"

# Predownload common packages used by your charms in development
DOWNLOAD_PACKAGES=""

PACKAGES="$LAYER_BASIC $DOWNLOAD_PACKAGES"

function cache() {
    series=$1
    container=juju-${series}-base
    alias=juju/$series/amd64

    lxc delete $container -f || true
    lxc launch ubuntu:$series $container
    sleep 5  # wait for network

    lxc exec $container -- apt-get update -y
    lxc exec $container -- apt-get upgrade -y
    lxc exec $container -- apt-get install -y $PACKAGES $2
    lxc stop $container

    lxc image delete $alias || true
    lxc publish $container --alias $alias description="$series juju dev image ($(date +%Y%m%d))"

    lxc delete $container -f || true
}

cache trusty "$TRUSTY_PACKAGES"
cache xenial "$XENIAL_PACKAGES"
