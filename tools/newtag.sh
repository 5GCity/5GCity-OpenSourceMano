#!/bin/bash
if [ $# -ne 2 ]; then
    echo "Usage $0 <repo> <tag>"
    exit 1
fi

CURRENT_BRANCH="v2.0"
TAG="$2"
tag_header="OSM Release TWO:"
tag_message="$tag_header version $TAG"

modules="juju-charms devops descriptor-packages openvim RO SO UI osmclient"
list=""
for i in $modules; do
    if [ "$1" == "$i" -o "$1" == "all" ]; then
        list="$1"
        break
    fi
done

[ "$1" == "all" ] && list=$modules

if [ -z "$list" ]; then
    echo "Repo must be one of these: $modules all"
    exit 1
fi

for i in $list; do
    echo
    echo $i
    if [ "$i" == "juju-charms" ] && [ "$1" == "all" ] ; then
        #This is to allow "./newtag.sh all v2.0.0", and still checkout master in "juju-charms" before tagging
        git -C $i checkout master
    else
        git -C $i checkout $CURRENT_BRANCH
    fi
    git -C $i pull --rebase
    git -C $i tag -a $TAG -m"$tag_message"
    git -C $i push origin $TAG --follow-tags
    sleep 2
done

exit 0

