#!/bin/bash

REPO_NAME=$(basename $(git config --get remote.origin.url) | cut -d'.' -f1)
# get the latest tag
TAG_END="HEAD"
TAG_START=$(git tag | sort -Vr | head -1)
git pull --tags origin master &> /dev/null
echo "<h1>$REPO_NAME Changelog</h1>"
echo "<h2>tag: ${TAG_START} -> ${TAG_END}</h2>"
git log --pretty=format:"<li> <a href=https://osm.etsi.org/gitweb/?p=osm/$i.git;a=commitdiff;h=%H>%h &bull;</a> %s</li> " --reverse  ${TAG_START}..${TAG_END}
