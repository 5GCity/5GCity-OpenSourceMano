# Copyright 2018 Telefonica S.A.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This Dockerfile is intented for devops and deb package generation
#
# Use Dockerfile.local for running osm/NBI in a docker container from source
# Use Dockerfile.fromdeb for running osm/NBI in a docker container from last stable package


FROM ubuntu:16.04

RUN apt-get update && apt-get -y install wget git make python python3 python-pip \
    libcurl4-gnutls-dev libgnutls-dev tox python-dev python3-dev \
    debhelper python-setuptools python-all python3-all apt-utils python-magic \
    python3-pip python-pip && \
    DEBIAN_FRONTEND=noninteractive pip3 install -U stdeb setuptools-version-command && \
    DEBIAN_FRONTEND=noninteractive pip2 install -U stdeb

# Uncomment this block to generate automatically a debian package and show info
# # Set the working directory to /app
# WORKDIR /app
# # Copy the current directory contents into the container at /app
# ADD . /app
# CMD /app/devops-stages/stage-build.sh && find -name "*.deb" -exec dpkg -I  {} ";"

