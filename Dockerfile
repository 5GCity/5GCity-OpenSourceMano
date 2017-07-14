FROM ubuntu:16.04

RUN  apt-get update && \
  DEBIAN_FRONTEND=noninteractive apt-get -y install git build-essential apt-utils && \
  DEBIAN_FRONTEND=noninteractive apt-get -y install python python-dev python-all python-stdeb fakeroot pypi2deb && \
  DEBIAN_FRONTEND=noninteractive apt-get -y install python-pip libmysqlclient-dev libssl-dev libffi-dev && \
  DEBIAN_FRONTEND=noninteractive pip install --upgrade pip && \
  DEBIAN_FRONTEND=noninteractive pip install --upgrade setuptools && \
  DEBIAN_FRONTEND=noninteractive apt-get -y install python-argcomplete python-boto python-bottle python-jsonschema python-logutils python-cinderclient python-glanceclient python-keystoneclient python-neutronclient python-novaclient python-openstackclient python-mysqldb

