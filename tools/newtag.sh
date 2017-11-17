#!/bin/bash
if [ $# -ne 3 ]; then
    echo "Usage $0 <repo> <tag> <user>"
    exit 1
fi

USER=$3
TAG="$2"
tag_header="OSM Release THREE:" tag_message="$tag_header version $TAG"

modules="devops openvim RO SO UI IM osmclient"
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
    echo $i
    if [ ! -d $i ]; then
        git clone ssh://$USER@osm.etsi.org:29418/osm/$i
    fi
    git -C $i checkout master
    git -C $i pull --rebase
    git -C $i tag -a $TAG -m"$tag_message"
    git -C $i push origin $TAG --follow-tags
    sleep 2
done

exit 0
