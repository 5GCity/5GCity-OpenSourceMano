#!/bin/bash

REPO_NAME=$(basename $(git config --get remote.origin.url) | cut -d'.' -f1)
# get the latest tag
TAG_START=$(git tag | sort -Vr | head -1)

head_tag_diff=$(git rev-list $TAG_START ^HEAD |wc -l)
if  [ $head_tag_diff -eq 0 ]; then
    # HEAD and latest tag intersect. Instead try and find a previous tag and use that as the start diff
    TAG_END=$TAG_START
    TAG_START=$(git tag | sort -Vr | head -2 | sort -V | head -1)
else
    TAG_END="HEAD"
fi

git pull --tags origin master &> /dev/null
echo "<h1>$REPO_NAME Changelog</h1>"
echo "<h2>tag: ${TAG_START} -> ${TAG_END}</h2>"
git log --pretty=format:"<li> <a href=https://osm.etsi.org/gitweb/?p=osm/$REPO_NAME.git;a=commitdiff;h=%H>%h &bull;</a> %s</li> " --reverse  ${TAG_START}..${TAG_END}
