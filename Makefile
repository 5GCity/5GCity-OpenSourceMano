#
#   Copyright 2016 RIFT.IO Inc
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
# Author(s): Austin Cormier
# Creation Date: 2016/05/23
#
BUILD_DIR = build

NSDS := gw_corpa_ns ims_allin1_corpa mwc16_gen_ns mwc16_pe_ns VyOS_ns cirros_ns cirros_2vnf_ns ubuntu_xenial_ns ping_pong_ns knt_flownac_ns knt_flownac-us_ns sandvine_pts_ns
NSD_SRC_DIR := src/nsd
NSD_BUILD_DIR := $(BUILD_DIR)/nsd

NSD_SRC_DIRS := $(addprefix $(NSD_SRC_DIR)/, $(NSDS))
NSD_BUILD_DIRS := $(addprefix $(NSD_BUILD_DIR)/, $(NSDS))
NSD_PKGS := $(addsuffix .tar.gz, $(NSDS))
NSD_BUILD_PKGS := $(addprefix $(NSD_BUILD_DIR)_pkgs/, $(NSD_PKGS))

VNFDS := 6wind_vnf gw_corpa_pe1_vnf gw_corpa_pe2_vnf ims_allin1_2p_vnf tidgen_mwc16_vnf VyOS_vnf cirros_vnf ubuntu_xenial_vnf ping_vnf pong_vnf knt_fnc_vnf knt_fne_vnf knt_fnu_vnf knt_fnd_vnf sandvine_pts_vnf
VNFD_SRC_DIR := src/vnfd
VNFD_BUILD_DIR := $(BUILD_DIR)/vnfd

VNFD_SRC_DIRS := $(addprefix $(VNFD_SRC_DIR)/, $(VNFDS))
VNFD_BUILD_DIRS := $(addprefix $(VNFD_BUILD_DIR)/, $(VNFDS))
VNFD_PKGS := $(addsuffix .tar.gz, $(VNFDS))
VNFD_BUILD_PKGS := $(addprefix $(VNFD_BUILD_DIR)_pkgs/, $(VNFD_PKGS))

IMS_GITHUB="https://github.com/Metaswitch/clearwater-juju.git"
CHARM_REPO="https://osm.etsi.org/gerrit/osm/juju-charms.git"

all: $(VNFD_BUILD_PKGS) ${NSD_BUILD_PKGS}
	echo $@

clean:
	-@ $(RM) -rf $(BUILD_DIR)

$(VNFD_BUILD_DIR)/%: $(VNFD_SRC_DIR)/%
	mkdir -p $(VNFD_BUILD_DIR)
	cp -rf $< $(VNFD_BUILD_DIR)

	src/gen_vnfd_pkg.sh $< $@

$(BUILD_DIR)/clearwater-juju:
	mkdir -p $(BUILD_DIR)
	-cd $(BUILD_DIR) && (test -e clearwater-juju || git clone $(IMS_GITHUB))

$(BUILD_DIR)/juju-charms:
	mkdir -p $(BUILD_DIR)
	-cd $(BUILD_DIR) && (test -e juju-charms || git clone $(CHARM_REPO))
	-cd $(BUILD_DIR)/juju-charms && make

$(NSD_BUILD_DIR)/%: $(NSD_SRC_DIR)/%
	mkdir -p $(NSD_BUILD_DIR)
	cp -rf $< $(NSD_BUILD_DIR)

	src/gen_nsd_pkg.sh $< $@

$(BUILD_DIR)/nsd_pkgs/%.tar.gz: $(NSD_BUILD_DIR)/%
	src/generate_descriptor_pkg.sh -d $(BUILD_DIR)/nsd_pkgs $<

$(VNFD_BUILD_DIR)/ims_allin1_2p_vnf/charms/clearwater-aio-proxy: $(VNFD_BUILD_DIR)/ims_allin1_2p_vnf $(BUILD_DIR)/clearwater-juju
	# Copy the IMS Charm into the IMS vnf package directory before packaging
	cp -rf $(BUILD_DIR)/clearwater-juju/charms/trusty/clearwater-aio-proxy $(VNFD_BUILD_DIR)/ims_allin1_2p_vnf/charms

$(VNFD_BUILD_DIR)/6wind_vnf/charms/vpe-router: $(VNFD_BUILD_DIR)/6wind_vnf $(BUILD_DIR)/juju-charms
	# Copy the PE Charm into the PE vnf package directory before packaging
	cp -rf $(BUILD_DIR)/juju-charms/builds/vpe-router $(VNFD_BUILD_DIR)/6wind_vnf/charms

$(VNFD_BUILD_DIR)/VyOS_vnf/charms/vyos-proxy: $(VNFD_BUILD_DIR)/VyOS_vnf $(BUILD_DIR)/juju-charms
	# Copy the PE Charm into the PE vnf package directory before packaging
	cp -rf $(BUILD_DIR)/juju-charms/builds/vyos-proxy $(VNFD_BUILD_DIR)/VyOS_vnf/charms

$(VNFD_BUILD_DIR)/ping_vnf/charms/pingpong: $(VNFD_BUILD_DIR)/ping_vnf $(BUILD_DIR)/juju-charms
	# Copy the pingpong Charm into the ping vnf package directory before packaging
	cp -rf $(BUILD_DIR)/juju-charms/builds/pingpong $(VNFD_BUILD_DIR)/ping_vnf/charms

$(VNFD_BUILD_DIR)/pong_vnf/charms/pingpong: $(VNFD_BUILD_DIR)/pong_vnf $(BUILD_DIR)/juju-charms
	# Copy the pingpong Charm into the pong vnf package directory before packaging
	cp -rf $(BUILD_DIR)/juju-charms/builds/pingpong $(VNFD_BUILD_DIR)/pong_vnf/charms

$(BUILD_DIR)/vnfd_pkgs/%.tar.gz: $(VNFD_BUILD_DIR)/% $(VNFD_BUILD_DIR)/ims_allin1_2p_vnf/charms/clearwater-aio-proxy $(VNFD_BUILD_DIR)/6wind_vnf/charms/vpe-router $(VNFD_BUILD_DIR)/VyOS_vnf/charms/vyos-proxy $(VNFD_BUILD_DIR)/ping_vnf/charms/pingpong $(VNFD_BUILD_DIR)/pong_vnf/charms/pingpong
	src/generate_descriptor_pkg.sh -d $(BUILD_DIR)/vnfd_pkgs $<
