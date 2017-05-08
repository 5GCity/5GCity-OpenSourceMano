# Copyright 2017 Sandvine
# 
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

all: build_tools
	$(MAKE) test
	$(MAKE) package

BUILD_TOOLS=python python3 virtualenv \
            libcurl4-gnutls-dev python-pip \
            python3-pip libgnutls-dev debhelper

VENV=osmclient-venv
VENV3=osmclient-venv3
VENV_BIN=$(VENV)/bin/python
VENV3_BIN=$(VENV3)/bin/python

venv: $(VENV)/bin/activate
venv3: $(VENV3)/bin/activate

$(VENV)/bin/activate: test_requirements.txt
	test -d $(VENV) || virtualenv $(VENV)
	$(VENV)/bin/pip install -Ur test_requirements.txt
	touch $(VENV)/bin/activate

$(VENV3)/bin/activate: test_requirements.txt
	test -d $(VENV3) || virtualenv -p python3 $(VENV3)
	$(VENV3)/bin/pip3 install -Ur test_requirements.txt
	touch $(VENV3)/bin/activate

build_tools:
	sudo apt-get -y install $(BUILD_TOOLS)

package: build_tools
	$(VENV_BIN) setup.py --command-packages=stdeb.command bdist_deb

test_flake8: venv
	$(VENV_BIN) setup.py flake8

test_nose: venv
	$(VENV_BIN) setup.py test

test_nose3: venv3
	$(VENV3_BIN) setup.py test

test: test_flake8 test_nose test_nose3

.PHONY: package build_tools test test_flake8 test_nose test_nose3

clean:
	rm -rf $(VENV) $(VENV3) deb_dist dist osmclient.egg-info
