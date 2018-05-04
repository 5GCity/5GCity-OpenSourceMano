#!/bin/sh

# moved to a Makefile in order to add post install. Needed for "pip3 install aiokafka", 
# that is not available with a package
make clean package

#rm -rf deb_dist
#tox -e build
