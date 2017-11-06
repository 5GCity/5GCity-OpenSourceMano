#!/bin/bash
if [ $# -ne 2 ]; then
    echo "Usage $0 <repo> <outfile>"
    exit 1
fi

REPO="$1"
OUTFILE=$2

modules="devops openvim RO SO UI IM osmclient"
list=""
for i in $modules; do
    if [ $REPO == "$i" -o $REPO == "all" ]; then
        list=$REPO
        break
    fi
done

[ $REPO == "all" ] && list=$modules

if [ -z "$list" ]; then
    echo "Repo must be one of these: $modules all"
    exit 1
fi

echo "<h1>OSM Changelog</h1>" >> $OUTFILE
for i in $list; do
    echo
    echo $i
    if [ ! -d $i ]; then
        git clone https://osm.etsi.org/gerrit/osm/$i
    fi
    git -C $i checkout master
    git -C $i pull --rebase
    git -C $i fetch --tags
    TAG_START=$(git -C $i tag | sort -Vr | head -2 | sort -V | head -1)
    TAG_END=$(git -C $i tag | sort -Vr | head -1)
    echo "<h2>Changes for $i tag: ${TAG_START}..${TAG_END}</h2>" >> $OUTFILE
    #git -C $i log --pretty=format:"* %h; author: %cn; date: %ci; subject:%s" ${TAG_START}..${TAG_END} >> $OUTFILE
    git -C $i log --pretty=format:"<li> <a href=https://osm.etsi.org/gitweb/?p=osm/$i.git;a=commitdiff;h=%H>%h &bull;</a> %s</li> " --reverse  ${TAG_START}..${TAG_END} >> $OUTFILE
    echo "" >> $OUTFILE
done

exit 0
