#!/bin/sh

apt autoremove
apt update

rm -f /home/vagrant/*.sh

wget --no-check-certificate https://raw.github.com/mitchellh/vagrant/master/keys/vagrant.pub -O /home/vagrant/.ssh/authorized_keys
chmod 0600 /home/vagrant/.ssh/authorized_keys
chown -R vagrant:vagrant /home/vagrant/.ssh

dd if=/dev/zero of=/EMPTY bs=1M
rm -f /EMPTY
sync
