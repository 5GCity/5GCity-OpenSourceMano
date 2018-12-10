# -*- coding: utf-8 -*-
##
# Copyright 2018 University of Bristol - High Performance Networks Research
# Group
# All Rights Reserved.
#
# Contributors: Anderson Bravalheri, Dimitrios Gkounis, Abubakar Siddique
# Muqaddas, Navdeep Uniyal, Reza Nejabati and Dimitra Simeonidou
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
# For those usages not covered by the Apache License, Version 2.0 please
# contact with: <highperformance-networks@bristol.ac.uk>
#
# Neither the name of the University of Bristol nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# This work has been performed in the context of DCMS UK 5G Testbeds
# & Trials Programme and in the framework of the Metro-Haul project -
# funded by the European Commission under Grant number 761727 through the
# Horizon 2020 and 5G-PPP programmes.
##

from ..openmano_schemas import (
    description_schema,
    name_schema,
    nameshort_schema
)

# WIM -------------------------------------------------------------------------
wim_types = ["tapi", "onos", "odl", "dynpac"]

wim_schema_properties = {
    "name": name_schema,
    "description": description_schema,
    "type": {
        "type": "string",
        "enum": ["tapi", "onos", "odl", "dynpac"]
    },
    "wim_url": description_schema,
    "config": {"type": "object"}
}

wim_schema = {
    "title": "wim information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "wim": {
            "type": "object",
            "properties": wim_schema_properties,
            "required": ["name", "type", "wim_url"],
            "additionalProperties": True
        }
    },
    "required": ["wim"],
    "additionalProperties": False
}

wim_edit_schema = {
    "title": "wim edit information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "wim": {
            "type": "object",
            "properties": wim_schema_properties,
            "additionalProperties": False
        }
    },
    "required": ["wim"],
    "additionalProperties": False
}

wim_account_schema = {
    "title": "wim account information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "wim_account": {
            "type": "object",
            "properties": {
                "name": name_schema,
                "user": nameshort_schema,
                "password": nameshort_schema,
                "config": {"type": "object"}
            },
            "additionalProperties": True
        }
    },
    "required": ["wim_account"],
    "additionalProperties": False
}

dpid_type = {
    "type": "string",
    "pattern":
        "^[0-9a-zA-Z]+(:[0-9a-zA-Z]+)*$"
}

port_type = {
    "oneOf": [
        {"type": "string",
         "minLength": 1,
         "maxLength": 5},
        {"type": "integer",
         "minimum": 1,
         "maximum": 65534}
    ]
}

wim_port_mapping_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "wim mapping information schema",
    "type": "object",
    "properties": {
        "wim_port_mapping": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "datacenter_name": nameshort_schema,
                    "pop_wan_mappings": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "pop_switch_dpid": dpid_type,
                                "pop_switch_port": port_type,
                                "wan_service_endpoint_id": name_schema,
                                "wan_service_mapping_info": {
                                    "type": "object",
                                    "properties": {
                                        "mapping_type": name_schema,
                                        "wan_switch_dpid": dpid_type,
                                        "wan_switch_port": port_type
                                    },
                                    "additionalProperties": True,
                                    "required": ["mapping_type"]
                                }
                            },
                            "oneOf": [
                                {
                                    "required": [
                                        "pop_switch_dpid",
                                        "pop_switch_port",
                                        "wan_service_endpoint_id"
                                    ]
                                },
                                {
                                    "required": [
                                        "pop_switch_dpid",
                                        "pop_switch_port",
                                        "wan_service_mapping_info"
                                    ]
                                }
                            ]
                        }
                    }
                },
                "required": ["datacenter_name", "pop_wan_mappings"]
            }
        }
    },
    "required": ["wim_port_mapping"]
}
