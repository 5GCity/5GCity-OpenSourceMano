sudo lxd init --auto --storage-backend zfs --storage-pool lxdpool --storage-create-loop 20

sudo systemctl stop lxd-bridge
sudo systemctl --system daemon-reload

sudo cp -f /tmp/lxd-bridge /etc/default/lxd-bridge
sudo systemctl enable lxd-bridge
sudo systemctl start lxd-bridge

sudo usermod -a -G lxd $(whoami) 
