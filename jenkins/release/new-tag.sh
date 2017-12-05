#!/bin/bash
HERE=$(realpath $(dirname $0))
OSM_JENKINS=$(dirname $HERE)
echo $OSM_JENKINS
. $OSM_JENKINS/common/all_funcs

[ $# -ne 2 ] && FATAL "arg1 is branch, arg2 is new tag"

#CURRENT_BRANCH="v1.1"
#TAG="v1.1.0"
CURRENT_BRANCH="$1"
TAG="$2"

#tag_header="OSM Release ONE:"
tag_header="OSM"
tag_message="$tag_header version $TAG"

TEMPDIR="$(mktemp -q -d --tmpdir "tagosm.XXXXXX")"
trap 'rm -rf "$TEMPDIR"' EXIT
#chmod 0600 "$TEMPDIR"

#juju-charms and devops repos have no vx.y branch yet
list="juju-charms devops"
for i in $list; do
    REPO_FOLDER="$TEMPDIR/$i"
    echo
    echo "Cloning and tagging $i"
    #git -C $TEMPDIR clone ssh://garciadeblas@osm.etsi.org:29418/osm/$i
    git -C $REPO_FOLDER checkout master
    git -C $REPO_FOLDER tag -a $TAG -m"$tag_message"
    git -C $REPO_FOLDER push origin $TAG --follow-tags
    sleep 2
    rm -rf $REPO_FOLDER
done

list="descriptor-packages openvim RO MON SO UI"
for i in $list; do
    REPO_FOLDER="$TEMPDIR/$i"
    echo
    echo "Cloning and tagging $i"
    #git -C $TEMPDIR clone ssh://garciadeblas@osm.etsi.org:29418/osm/$i
    git -C $REPO_FOLDER checkout $CURRENT_BRANCH
    git -C $REPO_FOLDER tag -a $TAG -m"$tag_message"
    git -C $REPO_FOLDER push origin $TAG --follow-tags
    sleep 2
    rm -rf $REPO_FOLDER
done

