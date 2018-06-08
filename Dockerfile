# Copyright 2017 Telefonica Investigacion y Desarrollo, S.A.U.
#
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

FROM ubuntu:16.04

RUN  apt-get update && \
  DEBIAN_FRONTEND=noninteractive apt-get -y install git make wget python python-pip debhelper tox && \
  DEBIAN_FRONTEND=noninteractive pip install pip==9.0.3 && \
  DEBIAN_FRONTEND=noninteractive pip install -U pyang pyangbind && \
  DEBIAN_FRONTEND=noninteractive pip install -U stdeb

