#!/bin/sh
MDG=common
rm -rf pool
rm -rf dists
mkdir -p pool/$MDG
mv deb_dist/*.deb pool/$MDG/
mkdir -p dists/unstable/$MDG/binary-amd64/
apt-ftparchive packages pool/$MDG > dists/unstable/$MDG/binary-amd64/Packages
gzip -9fk dists/unstable/$MDG/binary-amd64/Packages
echo "dists/**,pool/$MDG/*.deb"
