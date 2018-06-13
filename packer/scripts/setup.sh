#!/bin/sh

echo "vagrant        ALL=(ALL)       NOPASSWD: ALL" >> /etc/sudoers
sed -i "s/^.*requiretty/#Defaults requiretty/" /etc/sudoers
echo 'APT::Periodic::Enable "0";' >> /etc/apt/apt.conf.d/10periodic
