#!/usr/bin/env bash

##
# Copyright 2016-2017 VMware Inc.
# This file is part of ETSI OSM
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact:  osslegalrouting@vmware.com
##

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SSL_Cert_Dir="${BASEDIR}/SSL_certificate"
THISHOST=$(hostname)
Domain_Name="${THISHOST}"
#Domain_Name="www.vrops_webservice.com"
WebServiceFile='vrops_webservice.py'

echo '
 #################################################################
 #####             Installing Require Packages             #####
 #################################################################'

#Function to install packages using apt-get
function install_packages(){
      [ -x /usr/bin/apt-get ] && apt-get install -y $*
       
       #check properly installed
       for PACKAGE in $*
       do
           PACKAGE_INSTALLED="no"
           [ -x /usr/bin/apt-get ] && dpkg -l $PACKAGE            &>> /dev/null && PACKAGE_INSTALLED="yes"
           if [ "$PACKAGE_INSTALLED" = "no" ]
           then
               echo "failed to install package '$PACKAGE'. Revise network connectivity and try again" >&2
               exit 1
          fi
       done
   }
  
apt-get update  # To get the latest package lists

[ "$_DISTRO" == "Ubuntu" ] && install_packages "python-yaml python-bottle python-jsonschema python-requests libxml2-dev libxslt-dev python-dev python-pip openssl"
[ "$_DISTRO" == "CentOS" -o "$_DISTRO" == "Red" ] && install_packages "python-jsonschema python-requests libxslt-devel libxml2-devel python-devel python-pip openssl"
#The only way to install python-bottle on Centos7 is with easy_install or pip
[ "$_DISTRO" == "CentOS" -o "$_DISTRO" == "Red" ] && easy_install -U bottle

#required for vmware connector TODO move that to separete opt in install script
sudo pip install --upgrade pip
sudo pip install cherrypy

echo '
 #################################################################
 #####             Genrate SSL Certificate                 #####
 #################################################################'
#Create SSL Certifcate folder and file
mkdir "${SSL_Cert_Dir}"

openssl genrsa -out "${SSL_Cert_Dir}/${Domain_Name}".key 2048
openssl req -new -x509 -key "${SSL_Cert_Dir}/${Domain_Name}".key -out "${SSL_Cert_Dir}/${Domain_Name}".cert -days 3650 -subj /CN="${Domain_Name}"

echo '
 #################################################################
 #####             Start Web Service                      #####
 #################################################################'

nohup python "${WebServiceFile}" &

echo '	
 #################################################################
 #####              Done                                  #####
 #################################################################'

