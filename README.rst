===========
osm-ro
===========

osm-ro is the Resource Orchestrator for OSM, dealing with resource operations
against different VIMs such as Openstack, VMware's vCloud Director, openvim
and AWS.

===========
Updated version with support for Eclipse fog05 as VIM for RELEASE FOUR
===========

===========
How to build the image
===========
You need docker in order to build che docker image for the RO

.. code-block:: bash
	$ cd ~
  	$ git clone https://github.com/gabrik/etsi_ro
  	$ git -C etsi_ro checkout v4-city
  	$ sg docker -c "docker build ~/etsi_ro -f ~/etsi_ro/docker/Dockerfile-local -t dockercity/ro --no-cache"


Then if you have a running OSM installation on docker you have to edit the
file `/etc/osm/docker/docker-compose.yaml` and update the image for the RO

.. code-block:: yaml
	ro:
   	  image: dockercity/ro
