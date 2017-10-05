#
#   Copyright 2017 Sandvine
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

TOPDIR=$(shell readlink -f .|sed -e 's/\/descriptor-packages\/.*//')

BUILD_DIR := build
TOOLS_DIR := $(TOPDIR)/descriptor-packages/tools
PKG_BASE_NAME := $(shell basename $(shell pwd))
PKG_NAME      := $(addsuffix .tar.gz, $(PKG_BASE_NAME))

CHARM_DIR        := $(TOPDIR)/juju-charms
CHARM_SRC_DIR    := $(CHARM_DIR)/layers
CHARM_DOCKER_TAG := charm-tools
CHARM_BUILD_DIR  := $(CHARM_DIR)/builds
DOCKER_BUILD     ?= $(shell which docker)

Q=@

GEN_VNFD_PKG := $(TOOLS_DIR)/gen_vnfd_pkg.sh
GEN_NSD_PKG  := $(TOOLS_DIR)/gen_nsd_pkg.sh
GEN_PKG      := $(TOOLS_DIR)/generate_descriptor_pkg.sh
BUILD_VNFD   := $(shell readlink -f .|sed -e 's/\/.*descriptor-packages//' | grep vnfd)

DEP_FILES = $(wildcard src/*)

ifdef BUILD_VNFD
$(BUILD_DIR)/$(PKG_BASE_NAME): src $(DEP_FILES)
	$(Q)mkdir -p $@
	$(Q)cp -rf $</. $@
	$(Q)$(GEN_VNFD_PKG) $< $@
else
$(BUILD_DIR)/$(PKG_BASE_NAME): src $(DEP_FILES)
	$(Q)mkdir -p $@
	$(Q)cp -rf $</. $@
	$(Q)$(GEN_NSD_PKG) $< $@
endif

ifdef VNFD_CHARM
$(BUILD_DIR)/$(PKG_NAME): $(BUILD_DIR)/$(PKG_BASE_NAME) $(CHARM_BUILD_DIR)/$(VNFD_CHARM)
	$(Q)echo "building $(PKG_BASE_NAME) with charm $(VNFD_CHARM)"
	$(Q)cp -rf $(CHARM_BUILD_DIR)/$(VNFD_CHARM) $(BUILD_DIR)/$(PKG_BASE_NAME)/charms
	$(Q)$(GEN_PKG) --no-remove-files -d $(BUILD_DIR) $(BUILD_DIR)/$(PKG_BASE_NAME)
else
$(BUILD_DIR)/$(PKG_NAME): $(BUILD_DIR)/$(PKG_BASE_NAME)
	$(Q)echo "building $(PKG_BASE_NAME)"
	$(Q)$(GEN_PKG) --no-remove-files -d $(BUILD_DIR) $(BUILD_DIR)/$(PKG_BASE_NAME)
endif

ifdef DOCKER_BUILD
$(CHARM_BUILD_DIR)/%: $(CHARM_SRC_DIR)/%
	$(Q)docker build -q -t $(CHARM_DOCKER_TAG) $(CHARM_DIR)/.
	$(CHARM_DIR) $(CHARM_DOCKER_TAG) charm-build -o $(CHARM_DIR) $<
else
$(CHARM_BUILD_DIR)/%: $(CHARM_SRC_DIR)/%
	$(Q)charm-build -o $(CHARM_DIR) $<
endif
 
clean:
	$(Q)rm -rf $(BUILD_DIR)
	$(Q)rm -rf $(CHARM_BUILD_DIR)

.DEFAULT_GOAL := all
