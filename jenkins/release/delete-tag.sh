#!/bin/bash
HERE=$(realpath $(dirname $0))
OSM_JENKINS=$(dirname $HERE)
echo $OSM_JENKINS
. $OSM_JENKINS/common/all_funcs

[ $# -ne 1 ] && FATAL "arg1 is tag to be deleted"

TAG="$1"

TEMPDIR="$(mktemp -q -d --tmpdir "tagosm.XXXXXX")"
trap 'rm -rf "$TEMPDIR"' EXIT

list="juju-charms devops descriptor-packages openvim RO SO UI"
for i in $list; do
    REPO_FOLDER="$TEMPDIR/$i"
    echo
    echo "Cloning $i"
    #git -C $TEMPDIR clone ssh://garciadeblas@osm.etsi.org:29418/osm/$i
    git -C $REPO_FOLDER tag -d $TAG
    git -C $REPO_FOLDER push origin :refs/tags/$TAG
    sleep 2
    rm -rf $REPO_FOLDER
done

