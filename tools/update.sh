#!/bin/bash
if [ $# -lt 1 -o $# -gt 2 ]; then
    echo "Usage $0 <repo> [<branch>]"
    exit 1
fi

BRANCH="master"
if [ $# -ge 2 ]; then
    BRANCH=$2
fi

modules="juju-charms devops descriptor-packages openvim RO SO UI osmclient IM N2VC MON vim-emu"
list=""
for i in $modules; do
    if [ "$1" == "$i" -o "$1" == "all" ]; then
        list="$1"
        break
    fi
done

[ "$1" == "all" ] && list=$modules

if [ "$1" == "juju-charms" ] && [ "$BRANCH" != "master" ]; then
    echo "Repo $1 does not have branch $BRANCH"
    exit 1
fi

if [ -z "$list" ]; then
    echo "Repo must be one of these: $modules all"
    exit 1
fi

for i in $list; do
    echo
    echo $i
    git -C $i fetch
    if [ "$i" == "juju-charms" ] && [ "$1" == "all" ] ; then
        #This is to allow "./update.sh all v2.0", and still update "juju-charms" with master
        git -C $i checkout master
    else
        git -C $i checkout $BRANCH
    fi
    git -C $i pull --rebase
done

exit 0

