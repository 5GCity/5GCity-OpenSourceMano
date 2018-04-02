# Dockerfile to launch MON module in a docker
# Kafka bus must be launched in a different container

FROM ubuntu:16.04

LABEL authors="Guillermo Calvino"

# These ENV must be provided
# ENV BROKER_URI=kafka:9092
# ENV OS_AUTH_URL=http://IP-ADDR:PORT/
# ENV OS_PASSWORD=****
# ENV OS_TENANT_NAME=****
# ENV OS_USERNAME=****
# ENV OS_IDENTITY_API_VERSION=v2 or 3

ENV BROKER_URI=""
ENV OS_AUTH_URL=""
ENV OS_PASSWORD=""
ENV OS_TENANT_NAME=""
ENV OS_USERNAME=""
ENV OS_IDENTITY_API_VERSION=""

EXPOSE 8662

RUN apt-get --yes update \
 && apt-get --yes install software-properties-common python-software-properties \
 && apt-get --yes update \
 && apt-get --yes install git python python-pip sudo libmysqlclient-dev libxext-dev libxrender-dev libxtst-dev \
 && cd /root/ \
 && git clone https://osm.etsi.org/gerrit/osm/MON MON \
 && pip install /root/MON \
 && pip install --upgrade pip \
 && pip install -r /root/MON/requirements.txt

CMD /bin/bash /root/MON/docker/scripts/runInstall.sh