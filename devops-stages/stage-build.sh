#!/bin/sh
rm -rf deb_dist
tox -e build
#make clean package
