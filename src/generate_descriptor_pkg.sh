#!/bin/bash

############################################################################
# Copyright 2016 RIFT.io Inc                                               #
#                                                                          #
# Licensed under the Apache License, Version 2.0 (the "License");          #
# you may not use this file except in compliance with the License.         #
# You may obtain a copy of the License at                                  #
#                                                                          #
#     http://www.apache.org/licenses/LICENSE-2.0                           #
#                                                                          #
# Unless required by applicable law or agreed to in writing, software      #
# distributed under the License is distributed on an "AS IS" BASIS,        #
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. #
# See the License for the specific language governing permissions and      #
# limitations under the License.                                           #
############################################################################

#
# This shell script is used to create a descriptor package
# The main functions of this script include:
# - Generate checksums.txt file
# - Generate a tar.gz file
# This script can be used to create the required folders for
# a descriptor package and a template descriptor

# Usage: generate_descriptor_pkg.sh <base-directory> <package-directory>

# Descriptor names should be
#   - (nsd|vnfd).(yaml|yml|json|xml)
#   - *_(nsd|vnfd).(yaml|yml|json|xml)
#   - *_(nsd|vnfd)_*.(yaml|yml|json|xml)
#   - (nsd|vnfd)/*.(yaml|yml|json|xml)
#

SCRIPTNAME=`basename $0`

# From https://osm.etsi.org/wikipub/index.php/Release_0_Data_Model_Details
# Supported folders for VNFD
# cloud_init - Rel 4.3, not yet part of OSM
VNFD_FOLDERS=(images scripts icons charms cloud_init)

# Supported folders for NSD
# OSM document specifies (ns|vnf)-config folder, while Rel 4.3
# is using (ns|vnf)_config.
NSD_FOLDERS=(scripts icons ns_config vnf_config)

# Other files allowed in the descriptor base directory
ALLOWED_FILES=(README)

DESC_TYPES=(vnfd nsd)
DESC_EXTN=(yml yaml json xml)
CHKSUM='checksums.txt'

VERBOSE=false
DRY_RUN=false
CREATE=false
RM="--remove-files"
DEBUG=false

function usage() {
    cat <<EOF
Usage:
     $SCRIPTNAME [-t <type>] [-N] [-c] [base-directory] <package-dir>

        -h|--help : show this message

        -t|--package-type <nsd|vnfd> : Descriptor package type
                                       is NSD or VNFD. Script will try to
                                       determine the type if not provided.
                                       Default is vnfd for create-folders.

        -d|--destination-dir <destination directory>: Directory to create the
                                                      archived file.

        -N|--no-remove-files : Do not remove the package files after creating
                               archive

        -c|--create-folder : Create folder with the structure for the
                             package type using the base-dir and package-dir
                             and a descriptor template

        -v| --verbose : Generate logs

        -n| --dry-run : Validate the package dir

        base-dir : Directory where the archive file or folders are created,
                   if destination directory is not specified.
                   Default is current directory

        package-dir : The descriptor name and directory
EOF
}

function write_vnfd_tmpl() {
    name=$(basename $1)
    desc_file="${name}_vnfd.yaml"

    cat >$desc_file <<EOF
# Only one VNFD per descriptor package is supported
# Update the <update> tag with correct values
# Update or remove <update, optional> tags
vnfd:vnfd-catalog:
    vnfd:
    -   id: ${name}
        name: ${name}
        short-name: ${name}
        description: ${name}

        # Place the logo as png in icons directory and provide the name here
        logo: <update, optional>

        # This is an optional section and can be removed
        vnf-configuration:
            config-attributes:
                config-delay: '0'
                config-priority: '1'

            # Specify the config method
            # Remove this section if the VNF does not use a config method
            juju:
                charm: <update>

            # config-primitive specifies the config and actions for the VNF/charm
            # This is an optional section
            config-primitive:
                # If there are no config to be set, remove this section
            -   name: config
                # There can be multiple parameter sections
                # The name and type should be same as VNF/charm specification
                parameter:
                -   name: <update>
                    data-type: STRING
                    mandatory: <true|false>
                    default-value: <update>

                # If there are no actions specified at VNF level, remove this section
                # Multiple action sections can be specified
                # The name should be the name of the action
            -   name: <update, optional>
                # There can be multiple parameter sections
                # The name and type should be same as charm specification
                parameter:
                -   name: <update, optional>
                    data-type: STRING
                    mandatory: <true|false>

            # Any config or action that need to be executed when VNF comes up
            # This is an optional section
            initial-config-primitive:
            -   name: config
                # Any config to be set when VNF comes up
                # For charm normally the VNF management IP need to be set
                # in one of the config parameters
                # Sepcifying the value a <rw_mgmt_ip> will cause the MANO
                # to replace this with the management ip of VNF when it is
                # instantiated
                parameter:
                -   name: <update>
                    value: <rw_mgmt_ip>
                seq: '1'

        mgmt-interface:
            # This should be id of one of the VDUs specified for this VNF
            vdu-id: ${name}-VM
            port: <update, optional>

        connection-point:
        # Specify the connection points from VDU
        # Can specify multiple connection points here
        -   name: eth0
            type: VPORT
        -   name: eth1
            type: VPORT

        # Atleast one VDU need to be specified
        vdu:
        -   id: ${name}-VM
            name: ${name}-VM
            description: ${name}-VM

            # Image including the full path
            image: <update>

            # Flavour of the VM to be instantiated for the VDU
            vm-flavor:
                memory-mb: '4096'
                storage-gb: '10'
                vcpu-count: '2'

            external-interface:
            # Specify the external interfaces
            # There can be multiple interfaces defined
            -   name: eth0
                virtual-interface:
                    bandwidth: '0'
                    type: VIRTIO
                    vpci: 0000:00:0a.0
                vnfd-connection-point-ref: eth0
            -   name: eth1
                virtual-interface:
                    bandwidth: '0'
                    type: OM-MGMT
                    vpci: 0000:00:0b.0
                vnfd-connection-point-ref: eth1

            # Mgmt vpci, match with the specification in the
            # external interface for mgmt
            mgmt-vpci: 0000:00:0a.0

            # Specify EPA parameters
            # This section is optional
            guest-epa:
                cpu-pinning-policy: DEDICATED
                cpu-thread-pinning-policy: PREFER
                mempage-size: LARGE
                numa-node-policy:
                    mem-policy: STRICT
                    node:
                    -   id: '0'
                        paired-threads:
                            num-paired-threads: '1'
                    node-cnt: '1'

EOF

    if [ $VERBOSE == true ]; then
        echo "INFO: Created $desc_file"
    fi
}

function write_nsd_tmpl() {
    name=$(basename $1)
    desc_file="${name}_nsd.yaml"

    cat >$desc_file <<EOF
# Only one NSD per descriptor package is supported
# Update the <update> tag with correct values
# Update or remove <update, optional> tags
nsd:nsd-catalog:
    nsd:
    -   id: ${name}
        name: ${name}
        short-name: ${name}
        description: ${name}

        # Place the logo as png in icons directory and provide the name here
        logo: <update, optional>

        # Specify the VNFDs that are part of this NSD
        constituent-vnfd:
            # The member-vnf-index needs to be unique, starting from 1
            # vnfd-id-ref is the id of the VNFD
            # Multiple constituent VNFDs can be specified
        -   member-vnf-index: <update>
            vnfd-id-ref: <update>

        vld:
        # Management network for the VNFs
        -   id: management
            name: management
            provider-network:
                overlay-type: VLAN
                physical-network: <update>
            type: ELAN
            vnfd-connection-point-ref:
            # Specify all the constituent VNFs
            # member-vnf-index-ref - entry from constituent vnf
            # vnfd-id-ref - VNFD id
            # vnfd-connection-point-ref - connection point name in the VNFD
            -   member-vnf-index-ref: '1'
                vnfd-connection-point-ref: <update>
                vnfd-id-ref: <update>
            -   member-vnf-index-ref: '2'
                vnfd-connection-point-ref: <update>
                vnfd-id-ref: <update>

        # Addtional netowrk can be specified for data, etc
        -   id: <update>
            name: <update>
            type: ELAN
            provider-network:
                overlay-type: VLAN
                physical-network: <update>
            vnfd-connection-point-ref:
            -   member-vnf-index-ref: <update>
                vnfd-connection-point-ref: <update>
                vnfd-id-ref: <update>

        # NS level configuration primitive
        # This section is optional
        config-primitive:
        -   name: <update>
            # List of parameters, optional
            parameter:
            -   name: <update>
                data-type: string
                default-value: <update>
                mandatory: <true|false>

            # List of parameters grouped by name
            # optional section
            parameter-group:
            -   mandatory: <true|false>
                name: <update>
                parameter:
                -   name: <update>
                    data-type: integer
                    default-value: <update>
                    hidden: <true|false>
                    mandatory: <true|false>

            # Script based NS level configuration
            user-defined-script: <update>
EOF

    if [ $VERBOSE == true ]; then
        echo "INFO: Created $desc_file"
    fi
}

function write_nsd_config_tmpl() {
    name=$(basename $1)
    cfg_file="ns_config/$name.yaml"

    cat >$cfg_file <<EOF

EOF

    if [ $VERBOSE == true ]; then
        echo "INFO: Created $cfg_file"
    fi
}

OPTS=`getopt -o vhnt:d:cN --long verbose,dry-run,help,package-type:,destination-dir,create-folder,no-remove-files,debug -n $SCRIPTNAME -- "$@"`

if [ $? != 0 ] ; then
    echo "ERROR: Failed parsing options ($?)." >&2
    usage
    exit 1
fi

echo "$OPTS"
eval set -- "$OPTS"

cur_dir=`pwd`

# Check if the array contains a specific value
# Taken from
# http://stackoverflow.com/questions/3685970/check-if-an-array-contains-a-value
function contains() {
    local n=$#
    local value=${!n}
    for ((i=1;i < $#;i++)); do
        if [ "${!i}" == "${value}" ]; then
            echo "y"
            return 0
        fi
    done
    echo "n"
    return 1
}

function check_type() {
    type=$1
    if [ $(contains "${DESC_TYPES[@]}" $type) == "y" ]; then
        TYPE=$type
    else
        echo "ERROR: Unknown descriptor type $type!" >&2
        exit 1
    fi
}

function get_expr(){
    # First argument is to specify if this is a negative match or match
    # Rest are filename expressions without extension
    #

    local regex=" "
    local n=$1
    local neg="${1}"
    for ((i=2;i <= $#;i++)); do
        if [ $i -eq 2 ]; then
            if [ $neg == true ]; then
                subexpr='! -name'
            else
                subexpr='-name'
            fi
        else
            if [ $neg == true ]; then
                subexpr=' -a ! -name'
            else
                subexpr=' -o -name'
            fi
        fi

        for extn in ${DESC_EXTN[$@]}; do
            regex="$regex $subexpr ${!i}.$extn"
        done
    done

    if [ $VERBOSE == true ]; then
        echo "INFO: Generate expression: $expr"
    fi

    echo "$expr"
}

function get_expr(){
    # First argument is to specify if this is a negative match or not
    # Rest are filename expressions without extension

    local regex=" "
    local n=$#
    local neg="${1}"
    local first="true"
    for ((i=2;i <= $#;i++)); do
        for extn in "${DESC_EXTN[@]}"; do
            if [ $first == true ]; then
                if [ $neg == true ]; then
                    subexpr='! -name'
                else
                    subexpr='-name'
                fi
                first=false
            else
                if [ $neg == true ]; then
                    subexpr=' -a ! -name'
                else
                    subexpr=' -o -name'
                fi
            fi

            regex="$regex $subexpr ${!i}.$extn"
        done
    done

    echo "$regex"
}

while true; do
    case "$1" in
        -v | --verbose ) VERBOSE=true; shift ;;
        -h | --help )    usage; exit 0; shift ;;
        -n | --dry-run ) DRY_RUN=true; shift ;;
        -t | --package-type ) check_type "$2"; shift; shift ;;
        -d | --destination-dir ) DEST_DIR=$2; shift; shift;;
        -c | --create-folder ) CREATE=true; shift;;
        -N | --no-remove-files ) RM=''; shift;;
        --debug ) DEBUG=true; shift;;
        -- ) shift; break ;;
        * ) break ;;
    esac
done

if [ $DEBUG == true ]; then
    echo "INFO: Debugging ON"
    set -x
fi

if [ $VERBOSE == true ]; then
    echo "INFO: Descriptor type: $TYPE"
fi

# Dry run is to validate existing descriptor folders
if [ $DRY_RUN == true ] && [ $CREATE == true ]; then
    echo "ERROR: Option dry-run with create-folders not supported!" >&2
    exit 1
fi

if [ $# -gt 1 ]; then
    BASE_DIR=$1
    PKG=$(basename $2)
else
    BASE_DIR=$(dirname $1)
    PKG=$(basename $1)
fi

if [ $VERBOSE == true ]; then
    echo "INFO: Using base dir: $BASE_DIR"
fi

if [ $VERBOSE == true ]; then
    echo "INFO: Using package: $PKG"
fi

if [ -z "$PKG" ]; then
    echo "ERROR: Need to specify the package-dir" >&2
    usage >&2
    exit 1
fi

cd $BASE_DIR
if [ $? -ne 0 ]; then
    echo "ERROR: Unable to change to base directory $BASE_DIR!" >&2
    exit 1
fi

# Get full base dir path
BASE_DIR=`pwd`
cd $cur_dir

if [ -z $DEST_DIR ]; then
    DEST_DIR=$BASE_DIR # Default to base directory
fi

mkdir -p $DEST_DIR

cd $DEST_DIR
if [ $? -ne 0 ]; then
    echo "ERROR: Not able to access destination directory $DEST_DIR!" >&2
    exit 1
fi

# Get the full destination dir path
DEST_DIR=`pwd`
cd $cur_dir

dir=${BASE_DIR}/${PKG}

function add_chksum() {
    if [ $VERBOSE == true ]; then
        echo "INFO: Add file $1 to $CHKSUM"
    fi

    md5sum $1 >> $CHKSUM
}

if [ $CREATE == false ]; then
    if [ ! -d $dir ]; then
        echo "INFO: Package folder $dir not found!" >&2
        exit 1
    fi

    cd $dir
    if [ $? -ne 0 ]; then
        rc=$?
        echo "ERROR: changing directory to $dir ($rc)" >&2
        exit $rc
    fi

    # Remove checksum file, if present
    rm -f $CHKSUM

    # Check if the descriptor file is present
    if [ -z $TYPE ]; then
        # Desc type not specified, look for the desc file and guess the type
        # Required for backward compatibility
        for ty in ${DESC_TYPES[@]}; do
            re=$(get_expr false "$ty" "*_$ty" "*_${ty}_*")
            desc=$(find * -maxdepth 0 -type f $re 2>/dev/null)

            if [ -z $desc ] || [ ${#desc[@]} -eq 0 ]; then
                # Check the vnfd|nsd folder
                if [ ! -d $ty ]; then
                    continue
                fi
                re=$(get_expr false "*")
                desc=$(find $ty/* -maxdepth 0 -type f $re 2>/dev/null)
                if [ -z $desc ] || [ ${#desc[@]} -eq 0 ]; then
                    continue
                elif [ ${#desc[@]} -gt 1 ]; then
                    echo "ERROR: Found multiple descriptor files: ${desc[@]}" >&2
                    exit 1
                fi
                # Descriptor sub directory
                desc_sub_dir=$ty
            fi

            TYPE=$ty
            if [ $TYPE == 'nsd' ]; then
                folders=("${NSD_FOLDERS[@]}")
            else
                folders=("${VNFD_FOLDERS[@]}")
            fi

            if [ $VERBOSE == true ]; then
                echo "INFO: Determined descriptor is of type $TYPE"
            fi
            break
        done

        if [ -z $TYPE ]; then
            echo "ERROR: Unable to determine the descriptor type!" >&2
            exit 1
        fi
    else
        if [ $TYPE == 'nsd' ]; then
            folders=("${NSD_FOLDERS[@]}")
        else
            folders=("${VNFD_FOLDERS[@]}")
        fi

        # Check for descriptor of type provided on command line
        re=$(get_expr false "$TYPE" "*_${TYPE}" "*_${TYPE}_*")
        desc=$(find * -maxdepth 0 -type f $re 2>/dev/null)

        if [ -z $desc ] || [ ${#desc[@]} -eq 0 ]; then
            # Check if it is under vnfd/nsd subdirectory
            # Backward compatibility support
            re=$(get_expr false "*")
            desc=$(find $TYPE/* -maxdepth 0 -type f $re 2>/dev/null)
            if [ -z $desc ] || [ ${#desc[@]} -eq 0 ]; then
                echo "ERROR: Did not find descriptor file of type $TYPE" \
                     " in $dir" >&2
                exit 1
            fi
            desc_sub_dir=$ty
        fi
    fi

    if [ ${#desc[@]} -gt 1 ]; then
        echo "ERROR: Found multiple files of type $TYPE in $dir: $desc" >&2
        exit 1
    fi

    descriptor=${desc[0]}

    # Check if there are files not supported
    files=$(find * -maxdepth 0 -type f ! -name $descriptor 2>/dev/null)

    for f in ${files[@]}; do
        if [ $(contains "${ALLOWED_FILES[@]}" $f)  == "n" ]; then
            echo "WARN: Unsupported file $f found"
        fi
    done

    if [ $VERBOSE == true ]; then
        echo "INFO: Found descriptor package: ${desc_sub_dir} ${descriptor}"
    fi

    if [ $DRY_RUN == false ]; then
        add_chksum ${descriptor}
    fi

    # Check the folders are supported ones
    dirs=$( find * -maxdepth 0 -type d )

    for d in ${dirs[@]}; do
        if [ $(contains "${folders[@]}" $d) == "y" ]; then
            if [ $DRY_RUN == false ]; then
                find $d/* -type f  2>/dev/null|
                    while read file; do
                        add_chksum $file
                    done
            fi
        elif [ -z $desc_sub_dir ] || [ $d != $desc_sub_dir ]; then
            echo "WARN: $d is not part of standard folders " \
                 "for descriptor type $TYPE in $PKG"
        fi
    done

    if [ $VERBOSE == true ]; then
        echo "INFO: Creating archive for $PKG"
    fi

    cd $BASE_DIR
    if [ $DRY_RUN == false ]; then
        tar zcvf "$DEST_DIR/$PKG.tar.gz" "${PKG}" ${RM}
        if [ $? -ne 0 ]; then
            rc=$?
            echo "ERROR: creating archive for $PKG ($rc)" >&2
            exit $rc
        fi
    fi
else
    # Create the folders for the descriptor
    if [ $VERBOSE == true ]; then
        echo "INFO: Creating folders for $PKG in $dir"
    fi

    # Create, default to VNFD if no type is defined
    if [ -z $TYPE ]; then
        TYPE=vnfd
        echo "WARNING: Defaulting to descriptor type $TYPE"
    fi

    mkdir -p $dir && cd $dir
    if [ $? -ne 0 ]; then
        rc=$?
        echo "ERROR: creating directory $dir ($rc)" >&2
        exit $rc
    fi

    if [ $TYPE == 'nsd' ]; then
        folders=("${NSD_FOLDERS[@]}")
    else
        folders=("${VNFD_FOLDERS[@]}")
    fi

    for d in ${folders[@]}; do
        mkdir -p $dir/$d
        if [ $? -ne 0 ]; then
            rc=$?
            echo "ERROR: creating directory $dir/$d ($rc)" >&2
            exit $rc
        fi
        if [ $VERBOSE == true ]; then
            echo "Created folder $d in $dir"
        fi
    done

    if [ $VERBOSE == true ]; then
        echo "INFO: Created folders for in $dir"
    fi

    # Write a descriptor template file
    if [ $TYPE == 'vnfd' ]; then
        write_vnfd_tmpl $dir
    else
        write_nsd_tmpl $dir
        # write_nsd_config_tmpl $dir
    fi

fi

cd $cur_dir
