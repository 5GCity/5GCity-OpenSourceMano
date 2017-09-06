# Copyright 2017 Sandvine
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

# NOTE: pyang and pyangbind are required for build

PYANG:= pyang
PYBINDPLUGIN:=$(shell /usr/bin/env python -c \
	            'import pyangbind; import os; print "%s/plugin" % os.path.dirname(pyangbind.__file__)')

YANG_MODELS := vnfd nsd
PYTHON_MODELS := $(addsuffix .py, $(YANG_MODELS))
PYTHON_JSONSCHEMAS := $(addsuffix .jsonschema, $(YANG_MODELS))

OUT_DIR := osm_im
MODEL_DIR := models/yang
RW_PB_EXT := build/yang/rw-pb-ext.yang
Q?=@

PYANG_OPTIONS := -Werror

all: $(PYTHON_MODELS) pyangbind
	$(MAKE) package

$(OUT_DIR):
	$(Q)mkdir -p $(OUT_DIR)
	$(Q)touch $(OUT_DIR)/__init__.py

%.py: $(OUT_DIR) $(RW_PB_EXT)
	$(Q)echo generating $@ from $*.yang
	$(Q)pyang $(PYANG_OPTIONS) --path build/yang --path $(MODEL_DIR) --plugindir $(PYBINDPLUGIN) -f pybind -o $(OUT_DIR)/$@ $(MODEL_DIR)/$*.yang

%.jsonschema: $(OUT_DIR) $(RW_PB_EXT) pyang-json-schema-plugin
	$(Q)echo generating $@ from $*.yang
	$(Q)pyang $(PYANG_OPTIONS) --path build/yang --path $(MODEL_DIR) --plugindir pyang-json-schema-plugin -f json-schema -o $(OUT_DIR)/$@ $(MODEL_DIR)/$*.yang

$(RW_PB_EXT):
	$(Q)mkdir -p $$(dirname $@)
	$(Q)wget -q https://raw.githubusercontent.com/RIFTIO/RIFT.ware/RIFT.ware-4.4.1/modules/core/util/yangtools/yang/rw-pb-ext.yang -O $@

package:
	tox -e build

pyangbind:
	git clone https://github.com/robshakir/pyangbind
	cd pyangbind; python setup.py --command-packages=stdeb.command bdist_deb; cd ..

pyang-json-schema-plugin:
	git clone https://github.com/cmoberg/pyang-json-schema-plugin

clean:
	$(Q)rm -rf build dist osm_im.egg-info deb deb_dist *.gz pyangbind pyang-json-schema-plugin $(OUT_DIR)
