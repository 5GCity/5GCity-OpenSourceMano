FROM ubuntu:16.04

RUN apt-get update && apt-get -y install git make python python3 \
    virtualenv libcurl4-gnutls-dev libgnutls-dev python-pip  python3-pip \
    debhelper python-stdeb apt-utils
