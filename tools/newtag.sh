#!/bin/bash
if [ $# -ne 4 ]; then
    echo "Usage $0 <repo> <tag> <user> <release_name>"
    echo "Example: $0 all v4.0.2 garciadeblas FOUR"
    echo "Example: $0 devops v4.0.3 marchettim FIVE"
    exit 1
fi

TAG="$2"
USER="$3"
RELEASE_NAME="$4"
tag_header="OSM Release $RELEASE_NAME:"
tag_message="$tag_header version $TAG"

modules="common devops IM LCM LW-UI MON N2VC NBI openvim osmclient RO vim-emu"
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
