FROM ubuntu:16.04

RUN add-apt-repository -y 'deb https://osm-download.etsi.org/repository/osm/debian ReleaseONE unstable' && \
  apt-get update && \
  DEBIAN_FRONTEND=noninteractive apt-get -y install python python-pip libmysqlclient-dev libssl-dev libffi-dev libvirt-dev && \
  DEBIAN_FRONTEND=noninteractive pip install --upgrade pip && \
  DEBIAN_FRONTEND=noninteractive apt-get -y install python-argcomplete python-jsonschema python-mysqldb python-paramiko python-requests python-yaml python-bottle python-libvirt

