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
import sys
import getopt

"""
Tests the format of OSM VNFD and NSD descriptors
"""
__author__ = "Alfonso Tierno, Guillermo Calvino"
__date__ = "2018-04-16"
__version__ = "0.0.1"
version_date = "Apr 2018"


class ArgumentParserError(Exception):
    pass


def usage():
    print("Usage: {} [options] FILE".format(sys.argv[0]))
    print(" EXPERIMENTAL: Validates vnfd, nsd descriptors format")
    print(" FILE: a yaml or json vnfd-catalog or nsd-catalog descriptor")
    print(" OPTIONS:")
    print("      -v|--version: prints current version")
    print("      -h|--help: shows this help")
    print("      -i|--input FILE: (same as param FILE) descriptor file to be upgraded")
    return

if __name__=="__main__":
    error_position = []
    format_output_yaml = True
    input_file_name = None
    test_file = None
    file_name = None
    try:
        # load parameters and configuration
        opts, args = getopt.getopt(sys.argv[1:], "hvi:o:", ["input=", "help", "version",])

        for o, a in opts:
            if o in ("-v", "--version"):
                print ("test descriptor version THREE " + __version__ + ' ' + version_date)
                sys.exit()
            elif o in ("-h", "--help"):
                usage()
                sys.exit()
            elif o in ("-i", "--input"):
                input_file_name = a
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
        file_name = None

        if input_file_name.endswith('.yaml') or input_file_name.endswith('.yml') or not \
            (input_file_name.endswith('.json') or '\t' in descriptor_str):
            data = yaml.load(descriptor_str)
        else:   # json
            data = json.loads(descriptor_str)
            format_output_yaml = False

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

    except yaml.YAMLError as exc:
        error_pos = ""
        if hasattr(exc, 'problem_mark'):
            mark = exc.problem_mark
            error_pos = "at line:%s column:%s" % (mark.line + 1, mark.column + 1)
        print("Error loading file '{}'. yaml format error {}".format(input_file_name, error_pos), file=sys.stderr)
    except ArgumentParserError as e:
        print(str(e), file=sys.stderr)
    except IOError as e:
            print("Error loading file '{}': {}".format(file_name, e), file=sys.stderr)
    except ImportError as e:
        print ("Package python-osm-im not installed: {}".format(e), file=sys.stderr)
    except Exception as e:
        if file_name:
            print("Error loading file '{}': {}".format(file_name, str(e)), file=sys.stderr)
        else:
            if descriptor:
                print("Error. Invalid {} descriptor format in '{}': {}".format(descriptor, input_file_name, str(e)), file=sys.stderr)
            else:
                print("Error. Invalid descriptor format in '{}': {}".format(input_file_name, str(e)), file=sys.stderr)
    exit(1)
