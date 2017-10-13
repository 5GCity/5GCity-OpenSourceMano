#
#   Copyright 2016 RIFT.io Inc
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
#
#

BUILD_DIR = .

CHARMS:= pingpong vyos-proxy netutils
CHARM_SRC_DIR := layers
CHARM_BUILD_DIR := $(BUILD_DIR)/builds

CHARM_SRC_DIRS := $(addprefix $(CHARM_SRC_DIR)/, $(CHARMS))
CHARM_BUILD_DIRS := $(addprefix $(CHARM_BUILD_DIR)/, $(CHARMS))
CHARM_DOCKER_TAG := charm-tools
DOCKER_BUILD     ?=

all: $(CHARM_BUILD_DIRS)

clean:
	-@ $(RM) -rf $(CHARM_BUILD_DIR)


ifdef DOCKER_BUILD
$(CHARM_BUILD_DIR)/%: $(CHARM_SRC_DIR)/%
	docker build -t $(CHARM_DOCKER_TAG) .
	docker run -u $$(id -u):$$(id -g) -v$$(pwd):$$(pwd) -w$$(pwd) $(CHARM_DOCKER_TAG) charm-build -o $(BUILD_DIR) $<
else
$(CHARM_BUILD_DIR)/%: $(CHARM_SRC_DIR)/%
	charm-build -o $(BUILD_DIR) $<
endif
