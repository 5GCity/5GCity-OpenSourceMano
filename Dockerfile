FROM ubuntu:16.04

RUN apt-get update && apt-get -y install git make python python3 \
    libcurl4-gnutls-dev libgnutls-dev tox python-dev python3-dev \
    debhelper python-setuptools python-all python3-all apt-utils python-magic
