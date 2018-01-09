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

YANG_DESC_MODELS := vnfd nsd
YANG_RECORD_MODELS := vnfr nsr
PYTHON_MODELS := $(addsuffix .py, $(YANG_DESC_MODELS))
PYTHON_JSONSCHEMAS := $(addsuffix .jsonschema, $(YANG_DESC_MODELS))
YANG_DESC_TREES := $(addsuffix .tree.txt, $(YANG_DESC_MODELS))
YANG_DESC_JSTREES := $(addsuffix .html, $(YANG_DESC_MODELS))
YANG_RECORD_TREES := $(addsuffix .rec.tree.txt, $(YANG_RECORD_MODELS))
YANG_RECORD_JSTREES := $(addsuffix .rec.html, $(YANG_RECORD_MODELS))

OUT_DIR := osm_im
TREES_DIR := osm_im_trees
MODEL_DIR := models/yang
RW_PB_EXT := build/yang/rw-pb-ext.yang
Q?=@

PYANG_OPTIONS := -Werror

all: $(PYTHON_MODELS) pyangbind
	$(MAKE) package

trees: $(YANG_DESC_TREES) $(YANG_DESC_JSTREES) $(YANG_RECORD_TREES) $(YANG_RECORD_JSTREES)

$(OUT_DIR):
	$(Q)mkdir -p $(OUT_DIR)
	$(Q)touch $(OUT_DIR)/__init__.py

$(TREES_DIR):
	$(Q)mkdir -p $(TREES_DIR)

%.py: $(OUT_DIR) $(RW_PB_EXT)
	$(Q)echo generating $@ from $*.yang
	$(Q)pyang $(PYANG_OPTIONS) --path build/yang --path $(MODEL_DIR) --plugindir $(PYBINDPLUGIN) -f pybind -o $(OUT_DIR)/$@ $(MODEL_DIR)/$*.yang

%.jsonschema: $(OUT_DIR) $(RW_PB_EXT) pyang-json-schema-plugin
	$(Q)echo generating $@ from $*.yang
	$(Q)pyang $(PYANG_OPTIONS) --path build/yang --path $(MODEL_DIR) --plugindir pyang-json-schema-plugin -f json-schema -o $(OUT_DIR)/$@ $(MODEL_DIR)/$*.yang

%.tree.txt: $(TREES_DIR)
	$(Q)echo generating $@ from $*.yang
	$(Q)pyang $(PYANG_OPTIONS) --path build/yang --path $(MODEL_DIR) -f tree -o $(TREES_DIR)/$@ $(MODEL_DIR)/$*.yang

%.html: $(TREES_DIR)
	$(Q)echo generating $@ from $*.yang
	$(Q)pyang $(PYANG_OPTIONS) --path build/yang --path $(MODEL_DIR) -f jstree -o $(TREES_DIR)/$@ $(MODEL_DIR)/$*.yang

%.rec.tree.txt: $(TREES_DIR)
	$(Q)echo generating $@ from $*.yang
	$(Q)pyang $(PYANG_OPTIONS) --path build/yang --path $(MODEL_DIR) -f tree -o $(TREES_DIR)/$@ $(MODEL_DIR)/$*.yang
	$(Q)mv $(TREES_DIR)/$@ $(TREES_DIR)/$*.tree.txt

%.rec.html: $(TREES_DIR)
	$(Q)echo generating $@ from $*.yang
	$(Q)pyang $(PYANG_OPTIONS) --path build/yang --path $(MODEL_DIR) -f jstree -o $(TREES_DIR)/$@ $(MODEL_DIR)/rw-project.yang $(MODEL_DIR)/$*.yang
	$(Q)mv $(TREES_DIR)/$@ $(TREES_DIR)/$*.html

$(RW_PB_EXT):
	$(Q)mkdir -p $$(dirname $@)
	$(Q)wget -q https://raw.githubusercontent.com/RIFTIO/RIFT.ware/RIFT.ware-4.4.1/modules/core/util/yangtools/yang/rw-pb-ext.yang -O $@

package:
	tox -e build

pyangbind: pyang
	git clone https://github.com/alf-tierno/pyangbind
	cd pyangbind; git checkout issue151; python setup.py --command-packages=stdeb.command bdist_deb; cd ..
	mkdir -p deb_dist
	cp pyangbind/deb_dist/*.deb deb_dist

pyang:
	git clone https://github.com/mbj4668/pyang
	cd pyang; python setup.py --command-packages=stdeb.command bdist_deb; cd ..
	mkdir -p deb_dist
	cp pyang/deb_dist/*.deb deb_dist

pyang-json-schema-plugin:
	git clone https://github.com/cmoberg/pyang-json-schema-plugin

clean:
	$(Q)rm -rf build dist osm_im.egg-info deb deb_dist *.gz pyang pyangbind pyang-json-schema-plugin $(OUT_DIR) $(TREES_DIR)
