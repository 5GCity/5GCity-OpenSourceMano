#!/usr/bin/env python2
# -*- coding: utf-8 -*-

##
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
##
from __future__ import print_function
import json
import yaml
# import logging
import sys
import getopt

"""
Converts OSM VNFD, NSD descriptor from release TWO to release THREE format
"""
__author__ = "Alfonso Tierno, Guillermo Calvino"
__date__ = "2017-10-14"
__version__ = "0.0.2"
version_date = "Nov 2017"


class ArgumentParserError(Exception):
    pass


def usage():
    print("Usage: {} [options] FILE".format(sys.argv[0]))
    print(" EXPERIMENTAL: Upgrade vnfd, nsd descriptor from old versions to release THREE version")
    print(" FILE: a yaml or json vnfd-catalog or nsd-catalog descriptor")
    print(" OPTIONS:")
    print("      -v|--version: prints current version")
    print("      -h|--help: shows this help")
    print("      -i|--input FILE: (same as param FILE) descriptor file to be upgraded")
    print("      -o|--output FILE: where to write generated descriptor. By default stdout")
    print("      --test: Content is tested to check wrong format or unknown keys")
    return


def remove_prefix(desc, prefix):
    """
    Recursively removes prefix from keys
    :param desc: dictionary or list to change
    :param prefix: prefix to remove. Must
    :return: None, param desc is changed
    """
    prefix_len = len(prefix)
    if isinstance(desc, dict):
        prefixed_list=[]
        for k,v in desc.items():
            if isinstance(v, (list, tuple, dict)):
                remove_prefix(v, prefix)
            if isinstance(k, str) and k.startswith(prefix) and k != prefix:
                prefixed_list.append(k)
        for k in prefixed_list:
            desc[k[prefix_len:]] = desc.pop(k)
    elif isinstance(desc, (list, tuple)):
        for i in desc:
            if isinstance(desc, (list, tuple, dict)):
                remove_prefix(i, prefix)


if __name__=="__main__":
    error_position = []
    format_output_yaml = True
    input_file_name = None
    output_file_name = None
    test_file = None
    file_name = None
    try:
        # load parameters and configuration
        opts, args = getopt.getopt(sys.argv[1:], "hvi:o:", ["input=", "help", "version", "output=", "test",])

        for o, a in opts:
            if o in ("-v", "--version"):
                print ("upgrade descriptor version " + __version__ + ' ' + version_date)
                sys.exit()
            elif o in ("-h", "--help"):
                usage()
                sys.exit()
            elif o in ("-i", "--input"):
                input_file_name = a
            elif o in ("-o", "--output"):
                output_file_name = a
            elif o == "--test":
                test_file = True
            else:
                assert False, "Unhandled option"
        if not input_file_name:
            if not args:
                raise ArgumentParserError("missing DESCRIPTOR_FILE parameter. Type --help for more info")
            input_file_name = args[0]

        # Open files
        file_name = input_file_name
        with open(file_name, 'r') as f:
            descriptor_str = f.read()
        if output_file_name:
            file_name = output_file_name
            output = open(file_name, 'w')
        else:
            output = sys.stdout
        file_name = None

        if input_file_name.endswith('.yaml') or input_file_name.endswith('.yml') or not \
            (input_file_name.endswith('.json') or '\t' in descriptor_str):
            data = yaml.load(descriptor_str)
        else:   # json
            data = json.loads(descriptor_str)
            format_output_yaml = False

        if test_file:
            import osm_im.vnfd as vnfd_catalog
            import osm_im.nsd as nsd_catalog
            from pyangbind.lib.serialise import pybindJSONDecoder

            if "vnfd:vnfd-catalog" in data or "vnfd-catalog" in data:
                descriptor = "VNF"
                myvnfd = vnfd_catalog.vnfd()
                pybindJSONDecoder.load_ietf_json(data, None, None, obj=myvnfd)
            elif "nsd:nsd-catalog" in data or "nsd-catalog" in data:
                descriptor = "NS"
                mynsd = nsd_catalog.nsd()
                pybindJSONDecoder.load_ietf_json(data, None, None, obj=mynsd)
            else:
                descriptor = None
                raise KeyError("This is not neither nsd-catalog nor vnfd-catalog descriptor")
            exit(0)

        # Convert version
        if "vnfd:vnfd-catalog" in data or "vnfd-catalog" in data:
            remove_prefix(data, "vnfd:")
            error_position.append("vnfd-catalog")
            vnfd_descriptor = data["vnfd-catalog"]
            vnfd_list = vnfd_descriptor["vnfd"]
            error_position.append("vnfd")
            for vnfd in vnfd_list:
                error_position[-1] = "vnfd[{}]".format(vnfd["id"])
                # Remove vnf-configuration:config-attributes
                if "vnf-configuration" in vnfd and "config-attributes" in vnfd["vnf-configuration"]:
                    del vnfd["vnf-configuration"]["config-attributes"]
                # Remove interval-vld:vendor
                if "internal-vld" in vnfd:
                    internal_vld_list = vnfd.get("internal-vld", ())
                    for internal_vld in internal_vld_list:
                        if "vendor" in internal_vld:
                            del internal_vld["vendor"]
                # Remove "rw-nsd:meta"
                if "rw-vnfd:meta" in vnfd:
                    del vnfd["rw-vnfd:meta"]
                # Change vnf-configuration:service-primitive into vnf-configuration:config-primitive
                if "vnf-configuration" in vnfd and "service-primitive" in vnfd["vnf-configuration"]:
                    vnfd["vnf-configuration"]["config-primitive"] = vnfd["vnf-configuration"].pop("service-primitive")

                # Convert to capital letters vnf-configuration:service-primitive:parameter:data-type
                if "vnf-configuration" in vnfd and "config-primitive" in vnfd["vnf-configuration"]:
                    error_position.append("vnf-configuration")
                    error_position.append("config-primitive")
                    primitive_list = vnfd["vnf-configuration"].get("config-primitive", ())

                    for primitive in primitive_list:
                        if "parameter" in primitive:
                            parameter_list = primitive.get("parameter", ())
                            for parameter in parameter_list:
                                parameter["data-type"] = str(parameter["data-type"]).upper()

                    vnfd["vnf-configuration"]["config-primitive"] = primitive_list
                    error_position.pop()
                    error_position.pop()
                # Iterate with vdu:interfaces
                vdu_list = vnfd["vdu"]
                error_position.append("vdu")
                vdu2mgmt_cp = {}  # internal dict to indicate management interface for each vdu
                for vdu in vdu_list:
                    error_position[-1] = "vdu[{}]".format(vdu["id"])
                    # Change external/internal interface
                    interface_list = []
                    external_interface_list = vdu.pop("external-interface", ())
                    error_position.append("external-interface")
                    for external_interface in external_interface_list:
                        error_position[-1] = "external-interface[{}]".format(external_interface["name"])
                        external_interface["type"] = "EXTERNAL"
                        external_interface["external-connection-point-ref"] = \
                            external_interface.pop("vnfd-connection-point-ref")
                        if external_interface.get("virtual-interface", {}).get("type") == "OM-MGMT":
                            external_interface["virtual-interface"]["type"] = "VIRTIO"
                            if vdu["id"] not in vdu2mgmt_cp:
                                vdu2mgmt_cp[vdu["id"]] = external_interface["external-connection-point-ref"]
                        interface_list.append(external_interface)
                    error_position.pop()
                    internal_interface_list = vdu.pop("internal-interface", ())
                    error_position.append("internal-interface")
                    for internal_interface in internal_interface_list:
                        error_position[-1] = "internal-interface[{}]".format(internal_interface["name"])
                        internal_interface["type"] = "INTERNAL"
                        internal_interface["internal-connection-point-ref"] = \
                            internal_interface.pop("vdu-internal-connection-point-ref")
                        interface_list.append(internal_interface)
                    error_position.pop()
                    # order interface alphabetically and set position
                    if interface_list:
                        interface_list = sorted(interface_list,
                                                key=lambda k: k.get('external-connection-point-ref',
                                                                    k.get('internal-connection-point-ref')))
                        index = 1
                        for i in interface_list:
                            i["position"] = str(index)
                            index += 1

                        vdu["interface"] = interface_list
                error_position.pop()
                # change mgmt-interface
                if vnfd.get("mgmt-interface"):
                    error_position.append("mgmt-interface")
                    vdu_id = vnfd["mgmt-interface"].pop("vdu-id", None)
                    if vdu_id:
                        error_position.append("vdu-id")
                        vnfd["mgmt-interface"]["cp"] = vdu2mgmt_cp[vdu_id]
                        error_position.pop()
                    error_position.pop()
            error_position = []
        elif "nsd:nsd-catalog" in data or "nsd-catalog" in data:
            remove_prefix(data, "nsd:")
            error_position.append("nsd-catalog")
            nsd_descriptor = data["nsd-catalog"]
            nsd_list = nsd_descriptor["nsd"]
            error_position.append("nsd")
            for nsd in nsd_list:
                error_position[-1] = "nsd[{}]".format(nsd["id"])
                # set mgmt-network to true
                error_position.append("vld")
                vld_list = nsd.get("vld", ())
                for vld in vld_list:
                    error_position[-1] = "vld[{}]".format(vld["id"])
                    if "mgmt" in vld["name"].lower() or "management" in vld["name"].lower():
                        vld['mgmt-network'] = 'true'
                        break
                error_position.pop()
                # Change initial-config-primitive into initial-service-primitive
                if "initial-config-primitive" in nsd:
                    nsd['initial-service-primitive'] = nsd.pop("initial-config-primitive")
                # Remove "rw-nsd:meta"
                if "rw-nsd:meta" in nsd:
                    del nsd["rw-nsd:meta"]
                # Remove "rw-meta"
                if "rw-meta" in nsd:
                    del nsd["rw-meta"]
                # Iterate with vld:id
                error_position.append("vld")
                vld_list = nsd.get("vld",())
                for vld in vld_list:
                    error_position[-1] = "vld[{}]".format(vld["id"])
                    if "provider-network" in vld and "overlay-type" in vld["provider-network"]:
                        del vld["provider-network"]["overlay-type"]
                error_position.pop()
                if vld_list:
                    nsd["vld"] = vld_list
            error_position = []
        else:
            error_position = ["global"]
            raise KeyError("This is not neither nsd-catalog nor vnfd-catalog descriptor")

        if format_output_yaml:
            yaml.dump(data, output, indent=4, default_flow_style=False)
        else:
            json.dump(data, output)
        exit(0)

    except yaml.YAMLError as exc:
        error_pos = ""
        if hasattr(exc, 'problem_mark'):
            mark = exc.problem_mark
            error_pos = "at line:%s column:%s" % (mark.line + 1, mark.column + 1)
        print("Error loading file '{}'. yaml format error {}".format(input_file_name, error_pos), file=sys.stderr)

#    except json.decoder.JSONDecodeError as e:
#        print("Invalid field at configuration file '{file}' {message}".format(file=input_file_name, message=str(e)),
#              file=sys.stderr)
    except ArgumentParserError as e:
        print(str(e), file=sys.stderr)
    except IOError as e:
            print("Error loading file '{}': {}".format(file_name, e), file=sys.stderr)
    except ImportError as e:
        print ("Package python-osm-im not installed: {}".format(e), file=sys.stderr)
    except Exception as e:
        if test_file:
            if descriptor:
                print("Error. Invalid {} descriptor format in '{}': {}".format(descriptor, input_file_name, str(e)), file=sys.stderr)
            else:
                print("Error. Invalid descriptor format in '{}': {}".format(input_file_name, str(e)),
                      file=sys.stderr)
        elif error_position:
            print("Descriptor error at '{}': {}".format(":".join(error_position), e), file=sys.stderr)
        elif file_name:
            print ("Error loading file '{}': {}".format(file_name, str(e)), file=sys.stderr)
        else:
            raise
            # print("Unexpected exception {}".format(e), file=sys.stderr)
    exit(1)
