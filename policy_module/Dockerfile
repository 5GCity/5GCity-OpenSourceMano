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

LABEL authors="Benjamín Díaz"

ADD . /policy_module

RUN apt-get --yes update \
 && apt-get --yes install software-properties-common python-software-properties \
 && apt-get --yes install git python python-pip sudo libmysqlclient-dev libxext-dev libxrender-dev libxtst-dev \
 && pip install /policy_module \
 && pip install --upgrade pip \
 && pip install -r /policy_module/requirements.txt

CMD bash /policy_module/scripts/gen_config_from_env.sh && osm-policy-agent --config osm_policy_agent.cfg