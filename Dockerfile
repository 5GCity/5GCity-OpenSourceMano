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
# Use docker/Dockerfile-local for running osm/RO in a docker container from source

FROM ubuntu:16.04

RUN  apt-get update && \
  DEBIAN_FRONTEND=noninteractive apt-get -y install git make python python-pip debhelper python3 python3-all python3-pip python3-setuptools && \
  DEBIAN_FRONTEND=noninteractive apt-get -y install wget tox apt-utils flake8 python-nose python-mock && \
  DEBIAN_FRONTEND=noninteractive pip install pip==9.0.3 && \
  DEBIAN_FRONTEND=noninteractive pip3 install pip==9.0.3 && \
  DEBIAN_FRONTEND=noninteractive pip install -U setuptools setuptools-version-command stdeb && \
  DEBIAN_FRONTEND=noninteractive pip install -U pyang pyangbind && \
  DEBIAN_FRONTEND=noninteractive pip3 install -U pyang pyangbind && \
  DEBIAN_FRONTEND=noninteractive apt-get -y install python-yaml python-netaddr python-boto && \
  DEBIAN_FRONTEND=noninteractive apt-get -y install software-properties-common && \
  DEBIAN_FRONTEND=noninteractive add-apt-repository -y cloud-archive:queens && \
  DEBIAN_FRONTEND=noninteractive apt-get update && \
  DEBIAN_FRONTEND=noninteractive apt-get -y install python-novaclient python-keystoneclient python-glanceclient python-cinderclient python-neutronclient python-networking-l2gw && \
  DEBIAN_FRONTEND=noninteractive pip install -U progressbar pyvmomi pyvcloud==19.1.1 && \
  DEBIAN_FRONTEND=noninteractive pip install -U fog05rest && \
  DEBIAN_FRONTEND=noninteractive apt-get -y install python-argcomplete python-bottle python-cffi python-packaging python-paramiko python-pkgconfig libmysqlclient-dev libssl-dev libffi-dev python-mysqldb && \
  DEBIAN_FRONTEND=noninteractive apt-get -y install python-logutils python-openstackclient python-openstacksdk && \
  DEBIAN_FRONTEND=noninteractive pip install untangle && \
  DEBIAN_FRONTEND=noninteractive pip install -e git+https://github.com/python-oca/python-oca#egg=oca


# Uncomment this block to generate automatically a debian package and show info
# # Set the working directory to /app
# WORKDIR /app
# # Copy the current directory contents into the container at /app
# ADD . /app
# CMD /app/devops-stages/stage-build.sh && find -name "*.deb" -exec dpkg -I  {} ";"

