# Copyright 2018 Whitestack, LLC
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Whitestack, LLC

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at

#         http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# For those usages not covered by the Apache License, Version 2.0 please
# contact: bdiaz@whitestack.com or glavado@whitestack.com
##

FROM ubuntu:16.04

LABEL authors="Guillermo Calvino"

RUN apt-get --yes update \
 && apt-get --yes install git python python-pip python3 python3-pip libmysqlclient-dev libssl-dev libffi-dev \
 && pip install pip==9.0.3

COPY requirements.txt /mon/requirements.txt

RUN pip3 install -r /mon/requirements.txt

COPY . /mon

RUN pip3 install /mon

# These ENV must be provided
# ENV BROKER_URI=kafka:9092
# ENV OS_NOTIFIER_URI=<IP_ACCESIBLE_FROM_OPENSTACK>:8662

EXPOSE 8662

CMD /bin/bash mon/docker/scripts/runInstall.sh
