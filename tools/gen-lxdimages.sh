#!/bin/bash

function usage() {
    echo -e "usage: $0 [OPTIONS]"
    echo -e "  OPTIONS"
    echo -e "     -c <COMPONENT>:    the component whose lxd image has to be generated. Allowed values: RO, VCA, SOUI, MON"
    echo -e "     -R <RELEASE>:      push images to specific RELEASE folder"
}

GEN_ALL="y"
GEN_RO=""
GEN_VCA=""
GEN_SOUI=""
GEN_MON=""
RELEASE="ReleaseTHREE"

while getopts ":h" o; do
    case "${o}" in
        h)
            usage
            exit 0
            ;;
        R)
            RELEASE="${OPTARG}"
            ;;
        c)
            [ "${OPTARG}" == "RO" ] && GEN_ALL="" && GEN_RO="y" && continue
            [ "${OPTARG}" == "VCA" ] && GEN_ALL="" && GEN_VCA="y" && continue
            [ "${OPTARG}" == "SOUI" ] && GEN_ALL="" && GEN_SOUI="y" && continue
            [ "${OPTARG}" == "MON" ] && GEN_ALL="" && GEN_MON="y" && continue
            echo -e "Invalid option: '--$OPTARG'\n" >&2
            usage && exit 1
            ;;
        *)
            usage && exit 1
            ;;
    esac
done

[ "$GEN_ALL" == "y" ] && GEN_RO="y" && GEN_VCA="y" && GEN_SOUI="y" && GEN_MON="y"

echo "Stopping containers"
lxc stop RO
lxc stop VCA
lxc stop SO-ub
#lxc stop MON

echo "Saving containers as images in local lxd server"
OSM_RO_IMAGE="osm-ro"
OSM_VCA_IMAGE="osm-vca"
OSM_SOUI_IMAGE="osm-soui"
OSM_MON_IMAGE="osm-mon"

[ -n "$GEN_RO" ] && lxc publish --public RO --alias ${OSM_RO_IMAGE}
[ -n "$GEN_VCA" ] && lxc publish --public VCA --alias ${OSM_VCA_IMAGE}
[ -n "$GEN_SOUI" ] && lxc publish --public SO-ub --alias ${OSM_SOUI_IMAGE}
#[ -n "$GEN_MON" ] && lxc publish --public MON --alias ${OSM_MON_IMAGE}
#lxc image list

#echo "Copying images to a remote lxd server"
#[ -n "$GEN_RO" ] && lxc image copy ${OSM_RO_IMAGE} remote:
#[ -n "$GEN_VCA" ] && lxc image copy ${OSM_VCA_IMAGE} remote:
#[ -n "$GEN_SOUI" ] && lxc image copy ${OSM_SOUI_IMAGE} remote:
#[ -n "$GEN_MON" ] && lxc image copy ${OSM_MON_IMAGE} remote:

echo "Exporting images as targz"
mkdir -p "${RELEASE}"
#trap 'rm -rf "$RELEASE"' EXIT

[ -n "$GEN_RO" ] && lxc image export "${OSM_RO_IMAGE}" "${RELEASE}"/"${OSM_RO_IMAGE}" || echo "Failed to export RO"
[ -n "$GEN_VCA" ] && lxc image export "${OSM_VCA_IMAGE}" "${RELEASE}"/"${OSM_VCA_IMAGE}" || echo "Failed to export VCA"
[ -n "$GEN_SOUI" ] && lxc image export "${OSM_SOUI_IMAGE}" "${RELEASE}"/"${OSM_SOUI_IMAGE}" || echo "Failed to export SOUI"
#[ -n "$GEN_MON" ] && lxc image export "${OSM_MON_IMAGE}" "${RELEASE}"/"${OSM_MON_IMAGE}" || echo "Failed to export MON"
chmod 664 "${RELEASE}"/*.tar.gz

echo "Pushing images to ETSI FTP server"
RSYNC_USER_HOST=osmusers@osm-download.etsi.org
RSYNC_OPTIONS="--delete --progress --password-file rsync.pass"
rsync -avR "$RSYNC_OPTIONS" "$RELEASE" rsync://$RSYNC_USER_HOST/repos/osm/lxd


