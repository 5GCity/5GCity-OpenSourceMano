# Copyright 2017 Intel Research and Development Ireland Limited
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Intel Corporation

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at

#         http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# For those usages not covered by the Apache License, Version 2.0 please
# contact: prithiv.mohan@intel.com or adrian.hoban@intel.com

#__author__ = "Prithiv Mohan"
#__date__   = "14/Sep/2017"

SHELL := /bin/bash
all: package install

clean_deb:
	rm -rf .build

clean:
	rm -rf build

prepare:
	pip install --upgrade setuptools
	mkdir -p build/
	cp MANIFEST.in build/
	cp requirements.txt build/
	cp README.rst build/
	cp stdeb.cfg build/
	cp kafkad build/
	cp -r core build/
	cp -r plugins build/
	cp -r devops_stages build/
	cp -r test build/
	cp -r scripts build/
	cp setup.py build/

build: clean openstack_plugins prepare
	python -m py_compile build/plugins/OpenStack/*.py

build: clean vrops_plugins prepare
	python -m py_compile build/plugins/vRealiseOps/*.py

build: clean cloudwatch_plugins prepare
	python -m py_compile build/plugins/CloudWatch/*.py

build: clean core prepare
	python -m py_compile build/core/message_bus/*.py

pip: prepare
	cd build ./setup.py sdist
	cd build ./plugin_setup.py sdist

package: clean clean_deb prepare
	cd build && python setup.py --command-packages=stdeb.command sdist_dsc --with-python2=True
	cd build/deb_dist/* && dpkg-buildpackage -rfakeroot -uc -us
	mkdir -p .build
	cp build/deb_dist/python-*.deb .build/

install:
	DEBIAN_FRONTEND=noninteractive apt-get update && \
	DEBIAN_FRONTEND=noninteractive apt-get install --yes python-pip && \
	pip install --upgrade pip
        #dpkg -i build/deb_dist/*.deb

develop: prepare
	pip install -r requirements.txt
	cd build && ./setup.py develop

build-docker-from-source:
	docker build -t osm:MON -f docker/Dockerfile