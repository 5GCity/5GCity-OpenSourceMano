from ubuntu:xenial

VOLUME /opt/openmano
VOLUME /var/log/osm

ENV DEBIAN_FRONTEND=noninteractive


RUN apt-get update && \
    apt-get -y install python python-pip mysql-client libmysqlclient-dev && \
    pip install tox

ENTRYPOINT ["tox"]
