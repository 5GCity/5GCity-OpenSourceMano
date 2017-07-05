FROM ubuntu:16.04

RUN apt-get update && apt-get -y install python \
    libcurl4-gnutls-dev libgnutls-dev \
    python-setuptools python-pip git python-pytest \
    charm-tools sudo

# allow users to sudo.  This will allow packages to be installed
# inside the container
RUN echo "ALL ALL = NOPASSWD: ALL" > /etc/sudoers.d/user && \
    chmod 0440 /etc/sudoers.d/user
