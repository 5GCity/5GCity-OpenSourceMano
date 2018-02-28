#!/bin/sh
# Copyright 2018 Sandvine
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

PKG_DIRECTORIES="jenkins installers systest juju-charms descriptor-packages tools"
MDG_NAME=osm-devops
DEB_INSTALL=debian/$MDG_NAME.install
export DEBEMAIL="mmarchetti@sandvine.com"
export DEBFULLNAME="Michael Marchetti"

PKG_VERSION=$(git describe --tags --abbrev=0)
PKG_VERSION_PREFIX=$(echo $PKG_VERSION | sed -e 's/v//g')
PKG_VERSION_POST=$(git rev-list $PKG_VERSION..HEAD | wc -l)
if [ "$PKG_VERSION_POST" -eq 0 ]; then
    PKG_DIR="${MDG_NAME}-${PKG_VERSION_PREFIX}"
else
    PKG_DIR="${MDG_NAME}-$PKG_VERSION_PREFIX.post${PKG_VERSION_POST}"
fi

rm -rf $PKG_DIR
rm -f *.orig.tar.xz
rm -f *.deb
rm $DEB_INSTALL
mkdir -p $PKG_DIR

for dir in $PKG_DIRECTORIES; do
    ln -s $PWD/$dir $PKG_DIR/.
    echo "$dir/* usr/share/$MDG_NAME/$dir" >> $DEB_INSTALL
done
cp -R debian $PKG_DIR/.

cd $PKG_DIR
dh_make -y --indep --createorig --a -c apache
dpkg-buildpackage -uc -us -tc -rfakeroot 
cd -

rm -rf pool
rm -rf dists
mkdir -p pool/$MDG_NAME
mv *.deb pool/$MDG_NAME/
