#!/bin/bash
if [ $# -ne 2 ]; then
    echo "Usage $0 <repo> <tag>"
    exit 1
fi

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
    git -C $i fetch
    echo "Deleting tag $tag in repo $i"
    git -C $i tag -d $tag
    git -C $i push origin :refs/tags/$tag
    sleep 2
done

exit 0

