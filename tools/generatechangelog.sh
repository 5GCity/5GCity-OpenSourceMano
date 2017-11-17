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

TEMPDIR=$(mktemp -d)

echo "<h1>OSM Changelog</h1>" >> $OUTFILE
for i in $list; do
    REPODIR=$TEMPDIR/$i
    echo
    echo $i
    if [ ! -d $REPODIR ]; then
        git clone https://osm.etsi.org/gerrit/osm/$i $REPODIR
    fi
    git -C $REPODIR checkout master
    git -C $REPODIR pull --rebase
    git -C $REPODIR fetch --tags
    TAG_START=$(git -C $REPODIR tag | sort -Vr | head -2 | sort -V | head -1)
    TAG_END=$(git -C $REPODIR tag | sort -Vr | head -1)
    echo "<h2>Changes for $i tag: ${TAG_START}..${TAG_END}</h2>" >> $OUTFILE
    #git -C $i log --pretty=format:"* %h; author: %cn; date: %ci; subject:%s" ${TAG_START}..${TAG_END} >> $OUTFILE
    git -C $REPODIR log --pretty=format:"<li> <a href=https://osm.etsi.org/gitweb/?p=osm/$i.git;a=commitdiff;h=%H>%h &bull;</a> %s</li> " --reverse  ${TAG_START}..${TAG_END} >> $OUTFILE
    echo "" >> $OUTFILE
done

exit 0
