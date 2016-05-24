BUILD_DIR = build

NSDS := gw_corpa_ns ims_allin1_corpa mwc16_gen_ns mwc16_pe_ns
NSD_SRC_DIR := src/nsd
NSD_BUILD_DIR := $(BUILD_DIR)/nsd

NSD_SRC_DIRS := $(addprefix $(NSD_SRC_DIR)/, $(NSDS))
NSD_BUILD_DIRS := $(addprefix $(NSD_BUILD_DIR)/, $(NSDS))
NSD_PKGS := $(addsuffix .tar.gz, $(NSDS))
NSD_BUILD_PKGS := $(addprefix $(NSD_BUILD_DIR)_pkgs/, $(NSD_PKGS))

VNFDS := 6wind_vnf gw_corpa_pe1_vnf gw_corpa_pe2_vnf ims_allin1_2p_vnf tidgen_mwc16_vnf
VNFD_SRC_DIR := src/vnfd
VNFD_BUILD_DIR := $(BUILD_DIR)/vnfd

VNFD_SRC_DIRS := $(addprefix $(VNFD_SRC_DIR)/, $(VNFDS))
VNFD_BUILD_DIRS := $(addprefix $(VNFD_BUILD_DIR)/, $(VNFDS))
VNFD_PKGS := $(addsuffix .tar.gz, $(VNFDS))
VNFD_BUILD_PKGS := $(addprefix $(VNFD_BUILD_DIR)_pkgs/, $(VNFD_PKGS))

IMS_GITHUB="https://github.com/Metaswitch/clearwater-juju.git"

all: $(VNFD_BUILD_PKGS) ${NSD_BUILD_PKGS}
	echo $@

clean:
	-@ $(RM) -rf $(BUILD_DIR)

$(VNFD_BUILD_DIR)/%: $(VNFD_SRC_DIR)/%
	mkdir -p $(VNFD_BUILD_DIR)
	cp -rf $< $(VNFD_BUILD_DIR)

	src/gen_vnfd_pkg.sh $< $@

$(BUILD_DIR)/clearwater-juju: $(VNFD_BUILD_DIR)/ims_allin1_2p_vnf
	-cd $(BUILD_DIR) && (test -e clearwater-juju || git clone $(IMS_GITHUB))

$(NSD_BUILD_DIR)/%: $(NSD_SRC_DIR)/%
	mkdir -p $(NSD_BUILD_DIR)
	cp -rf $< $(NSD_BUILD_DIR)

	src/gen_nsd_pkg.sh $< $@

$(BUILD_DIR)/nsd_pkgs/%.tar.gz: $(NSD_BUILD_DIR)/%
	src/generate_descriptor_pkg.sh $(BUILD_DIR)/nsd_pkgs $<

$(VNFD_BUILD_DIR)/ims_allin1_2p_vnf/charms/clearwater-aio-proxy: $(BUILD_DIR)/clearwater-juju
	# Copy the IMS Charm into the IMS vnf package directory before
	cp -rf $(BUILD_DIR)/clearwater-juju/charms/trusty/clearwater-aio-proxy $(VNFD_BUILD_DIR)/ims_allin1_2p_vnf/charms

$(BUILD_DIR)/vnfd_pkgs/%.tar.gz: $(VNFD_BUILD_DIR)/% $(VNFD_BUILD_DIR)/ims_allin1_2p_vnf/charms/clearwater-aio-proxy
	src/generate_descriptor_pkg.sh $(BUILD_DIR)/vnfd_pkgs $<
