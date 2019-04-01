# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from jsonschema import validate as js_v, exceptions as js_e
from http import HTTPStatus
from copy import deepcopy

__author__ = "Alfonso Tierno <alfonso.tiernosepulveda@telefonica.com>"
__version__ = "0.1"
version_date = "Mar 2018"

"""
Validator of input data using JSON schemas for those items that not contains an  OSM yang information model
"""

# Basis schemas
patern_name = "^[ -~]+$"
shortname_schema = {"type": "string", "minLength": 1, "maxLength": 60, "pattern": "^[^,;()\\.\\$'\"]+$"}
passwd_schema = {"type": "string", "minLength": 1, "maxLength": 60}
name_schema = {"type": "string", "minLength": 1, "maxLength": 255, "pattern": "^[^,;()'\"]+$"}
string_schema = {"type": "string", "minLength": 1, "maxLength": 255}
xml_text_schema = {"type": "string", "minLength": 1, "maxLength": 1000, "pattern": "^[^']+$"}
description_schema = {"type": ["string", "null"], "maxLength": 255, "pattern": "^[^'\"]+$"}
id_schema_fake = {"type": "string", "minLength": 2, "maxLength": 36}
bool_schema = {"type": "boolean"}
null_schema = {"type": "null"}
# "pattern": "^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$"
id_schema = {"type": "string", "pattern": "^[a-fA-F0-9]{8}(-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}$"}
time_schema = {"type": "string", "pattern": "^[0-9]{4}-[0-1][0-9]-[0-3][0-9]T[0-2][0-9]([0-5]:){2}"}
pci_schema = {"type": "string", "pattern": "^[0-9a-fA-F]{4}(:[0-9a-fA-F]{2}){2}\\.[0-9a-fA-F]$"}
# allows [] for wildcards. For that reason huge length limit is set
pci_extended_schema = {"type": "string", "pattern": "^[0-9a-fA-F.:-\\[\\]]{12,40}$"}
http_schema = {"type": "string", "pattern": "^https?://[^'\"=]+$"}
bandwidth_schema = {"type": "string", "pattern": "^[0-9]+ *([MG]bps)?$"}
memory_schema = {"type": "string", "pattern": "^[0-9]+ *([MG]i?[Bb])?$"}
integer0_schema = {"type": "integer", "minimum": 0}
integer1_schema = {"type": "integer", "minimum": 1}
path_schema = {"type": "string", "pattern": "^(\\.){0,2}(/[^/\"':{}\\(\\)]+)+$"}
vlan_schema = {"type": "integer", "minimum": 1, "maximum": 4095}
vlan1000_schema = {"type": "integer", "minimum": 1000, "maximum": 4095}
mac_schema = {"type": "string",
              "pattern": "^[0-9a-fA-F][02468aceACE](:[0-9a-fA-F]{2}){5}$"}  # must be unicast: LSB bit of MSB byte ==0
dpid_Schema = {"type": "string", "pattern": "^[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){7}$"}
# mac_schema={"type":"string", "pattern":"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$"}
ip_schema = {"type": "string",
             "pattern": "^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"}
ip_prefix_schema = {"type": "string",
                    "pattern": "^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}"
                               "(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)/(30|[12]?[0-9])$"}
port_schema = {"type": "integer", "minimum": 1, "maximum": 65534}
object_schema = {"type": "object"}
schema_version_2 = {"type": "integer", "minimum": 2, "maximum": 2}
# schema_version_string={"type":"string","enum": ["0.1", "2", "0.2", "3", "0.3"]}
log_level_schema = {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]}
checksum_schema = {"type": "string", "pattern": "^[0-9a-fA-F]{32}$"}
size_schema = {"type": "integer", "minimum": 1, "maximum": 100}
array_edition_schema = {
    "type": "object",
    "patternProperties": {
        "^\\$": {}
    },
    "additionalProperties": False,
    "minProperties": 1,
}
nameshort_list_schema = {
    "type": "array",
    "minItems": 1,
    "items": shortname_schema,
}


ns_instantiate_vdu = {
    "title": "ns action instantiate input schema for vdu",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "id": name_schema,
        "volume": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "name": name_schema,
                    "vim-volume-id": name_schema,
                },
                "required": ["name", "vim-volume-id"],
                "additionalProperties": False
            }
        },
        "interface": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "name": name_schema,
                    "ip-address": ip_schema,
                    "mac-address": mac_schema,
                    "floating-ip-required": bool_schema,
                },
                "required": ["name"],
                "additionalProperties": False
            }
        }
    },
    "required": ["id"],
    "additionalProperties": False
}

ip_profile_dns_schema = {
    "type": "array",
    "minItems": 1,
    "items": {
        "type": "object",
        "properties": {
            "address": ip_schema,
        },
        "required": ["address"],
        "additionalProperties": False
    }
}

ip_profile_dhcp_schema = {
    "type": "object",
    "properties": {
        "enabled": {"type": "boolean"},
        "count": integer1_schema,
        "start-address": ip_schema
    },
    "additionalProperties": False,
}

ip_profile_schema = {
    "title": "ip profile validation schame",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "ip-version": {"enum": ["ipv4", "ipv6"]},
        "subnet-address": ip_prefix_schema,
        "gateway-address": ip_schema,
        "dns-server": ip_profile_dns_schema,
        "dhcp-params": ip_profile_dhcp_schema,
    }
}

ip_profile_update_schema = {
    "title": "ip profile validation schame",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "ip-version": {"enum": ["ipv4", "ipv6"]},
        "subnet-address": {"oneOf": [null_schema, ip_prefix_schema]},
        "gateway-address": {"oneOf": [null_schema, ip_schema]},
        "dns-server": {"oneOf": [null_schema, ip_profile_dns_schema]},

        "dhcp-params": {"oneOf": [null_schema, ip_profile_dhcp_schema]},
    },
    "additionalProperties": False
}

ns_instantiate_internal_vld = {
    "title": "ns action instantiate input schema for vdu",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "name": name_schema,
        "vim-network-name": name_schema,
        "vim-network-id": name_schema,
        "ip-profile": ip_profile_update_schema,
        "internal-connection-point": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "id-ref": name_schema,
                    "ip-address": ip_schema,
                    # "mac-address": mac_schema,
                },
                "required": ["id-ref"],
                "minProperties": 2,
                "additionalProperties": False
            },
        }
    },
    "required": ["name"],
    "minProperties": 2,
    "additionalProperties": False
}

additional_params_for_vnf = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "member-vnf-index": name_schema,
            "additionalParams": object_schema,
        },
        "required": ["member-vnf-index", "additionalParams"],
        "additionalProperties": False
    }

}

ns_instantiate = {
    "title": "ns action instantiate input schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "lcmOperationType": string_schema,
        "nsInstanceId": id_schema,
        "netsliceInstanceId": id_schema,
        "nsName": name_schema,
        "nsDescription": {"oneOf": [description_schema, {"type": "null"}]},
        "nsdId": id_schema,
        "vimAccountId": id_schema,
        "additionalParamsForNs": object_schema,
        "additionalParamsForVnf": additional_params_for_vnf,
        "ssh_keys": {"type": "array", "items": {"type": "string"}},
        "nsr_id": id_schema,
        "vduImage": name_schema,
        "vnf": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "member-vnf-index": name_schema,
                    "vimAccountId": id_schema,
                    "vdu": {
                        "type": "array",
                        "minItems": 1,
                        "items": ns_instantiate_vdu,
                    },
                    "internal-vld": {
                        "type": "array",
                        "minItems": 1,
                        "items": ns_instantiate_internal_vld
                    }
                },
                "required": ["member-vnf-index"],
                "minProperties": 2,
                "additionalProperties": False
            }
        },
        "vld": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "name": string_schema,
                    "vim-network-name": {"OneOf": [string_schema, object_schema]},
                    "vim-network-id": {"OneOf": [string_schema, object_schema]},
                    "ip-profile": object_schema,
                    "vnfd-connection-point-ref": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "member-vnf-index-ref": name_schema,
                                "vnfd-connection-point-ref": name_schema,
                                "ip-address": ip_schema,
                                # "mac-address": mac_schema,
                            },
                            "required": ["member-vnf-index-ref", "vnfd-connection-point-ref"],
                            "minProperties": 3,
                            "additionalProperties": False
                        },
                    }
                },
                "required": ["name"],
                "additionalProperties": False
            }
        },
    },
    "required": ["nsName", "nsdId", "vimAccountId"],
    "additionalProperties": False
}

ns_action = {   # TODO for the moment it is only contemplated the vnfd primitive execution
    "title": "ns action input schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "lcmOperationType": string_schema,
        "nsInstanceId": id_schema,
        "member_vnf_index": name_schema,
        "vnf_member_index": name_schema,  # TODO for backward compatibility. To remove in future
        "vdu_id": name_schema,
        "primitive": name_schema,
        "primitive_params": {"type": "object"},
    },
    "required": ["primitive", "primitive_params"],   # TODO add member_vnf_index
    "additionalProperties": False
}
ns_scale = {   # TODO for the moment it is only VDU-scaling
    "title": "ns scale input schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "lcmOperationType": string_schema,
        "nsInstanceId": id_schema,
        "scaleType": {"enum": ["SCALE_VNF"]},
        "scaleVnfData": {
            "type": "object",
            "properties": {
                "vnfInstanceId": name_schema,
                "scaleVnfType": {"enum": ["SCALE_OUT", 'SCALE_IN']},
                "scaleByStepData": {
                    "type": "object",
                    "properties": {
                        "scaling-group-descriptor": name_schema,
                        "member-vnf-index": name_schema,
                        "scaling-policy": name_schema,
                    },
                    "required": ["scaling-group-descriptor", "member-vnf-index"],
                    "additionalProperties": False
                },
            },
            "required": ["scaleVnfType", "scaleByStepData"],  # vnfInstanceId
            "additionalProperties": False
        },
        "scaleTime": time_schema,
    },
    "required": ["scaleType", "scaleVnfData"],
    "additionalProperties": False
}


schema_version = {"type": "string", "enum": ["1.0"]}
schema_type = {"type": "string"}
vim_account_edit_schema = {
    "title": "vim_account edit input schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "name": name_schema,
        "description": description_schema,
        "type": shortname_schema,
        "vim": name_schema,
        "datacenter": name_schema,
        "vim_url": description_schema,
        "vim_url_admin": description_schema,
        "vim_tenant": name_schema,
        "vim_tenant_name": name_schema,
        "vim_username": shortname_schema,
        "vim_password": passwd_schema,
        "config": {"type": "object"}
    },
    "additionalProperties": False
}

vim_account_new_schema = {
    "title": "vim_account creation input schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "schema_version": schema_version,
        "schema_type": schema_type,
        "name": name_schema,
        "description": description_schema,
        "vim": name_schema,
        "datacenter": name_schema,
        "vim_type": {"enum": ["openstack", "openvim", "vmware", "opennebula", "aws", "fos"]},
        "vim_url": description_schema,
        # "vim_url_admin": description_schema,
        # "vim_tenant": name_schema,
        "vim_tenant_name": name_schema,
        "vim_user": shortname_schema,
        "vim_password": passwd_schema,
        "config": {"type": "object"}
    },
    "required": ["name", "vim_url", "vim_type", "vim_user", "vim_password", "vim_tenant_name"],
    "additionalProperties": False
}

wim_account_edit_schema = {
    "title": "wim_account edit input schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "name": name_schema,
        "description": description_schema,
        "type": shortname_schema,
        "wim": name_schema,
        "wim_url": description_schema,
        "user": shortname_schema,
        "password": passwd_schema,
        "config": {"type": "object"}
    },
    "additionalProperties": False
}

wim_account_new_schema = {
    "title": "wim_account creation input schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "schema_version": schema_version,
        "schema_type": schema_type,
        "name": name_schema,
        "description": description_schema,
        "wim": name_schema,
        "wim_type": {"enum": ["tapi", "onos", "odl", "dynpac"]},
        "wim_url": description_schema,
        "user": shortname_schema,
        "password": passwd_schema,
        "config": {"type": "object"}
    },
    "required": ["name", "wim_url", "wim_type"],
    "additionalProperties": False
}

sdn_properties = {
    "name": name_schema,
    "description": description_schema,
    "dpid": dpid_Schema,
    "ip": ip_schema,
    "port": port_schema,
    "type": {"type": "string", "enum": ["opendaylight", "floodlight", "onos"]},
    "version": {"type": "string", "minLength": 1, "maxLength": 12},
    "user": shortname_schema,
    "password": passwd_schema
}
sdn_new_schema = {
    "title": "sdn controller information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": sdn_properties,
    "required": ["name", "port", 'ip', 'dpid', 'type'],
    "additionalProperties": False
}
sdn_edit_schema = {
    "title": "sdn controller update information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": sdn_properties,
    # "required": ["name", "port", 'ip', 'dpid', 'type'],
    "additionalProperties": False
}
sdn_port_mapping_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "sdn port mapping information schema",
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "compute_node": shortname_schema,
            "ports": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "pci": pci_extended_schema,
                        "switch_port": shortname_schema,
                        "switch_mac": mac_schema
                    },
                    "required": ["pci"]
                }
            }
        },
        "required": ["compute_node", "ports"]
    }
}
sdn_external_port_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "External port information",
    "type": "object",
    "properties": {
        "port": {"type": "string", "minLength": 1, "maxLength": 60},
        "vlan": vlan_schema,
        "mac": mac_schema
    },
    "required": ["port"]
}

# PDUs
pdu_interface = {
    "type": "object",
    "properties": {
        "name": shortname_schema,
        "mgmt": bool_schema,
        "type": {"enum": ["overlay", 'underlay']},
        "ip-address": ip_schema,
        # TODO, add user, password, ssh-key
        "mac-address": mac_schema,
        "vim-network-name": shortname_schema,  # interface is connected to one vim network, or switch port
        "vim-network-id": shortname_schema,
        # # provide this in case SDN assist must deal with this interface
        # "switch-dpid": dpid_Schema,
        # "switch-port": shortname_schema,
        # "switch-mac": shortname_schema,
        # "switch-vlan": vlan_schema,
    },
    "required": ["name", "mgmt", "ip-address"],
    "additionalProperties": False
}
pdu_new_schema = {
    "title": "pdu creation input schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "name": shortname_schema,
        "type": shortname_schema,
        "description": description_schema,
        "shared": bool_schema,
        "vims": nameshort_list_schema,
        "vim_accounts": nameshort_list_schema,
        "interfaces": {
            "type": "array",
            "items": pdu_interface,
            "minItems": 1
        }
    },
    "required": ["name", "type", "interfaces"],
    "additionalProperties": False
}

pdu_edit_schema = {
    "title": "pdu edit input schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "name": shortname_schema,
        "type": shortname_schema,
        "description": description_schema,
        "shared": bool_schema,
        "vims": {"oneOf": [array_edition_schema, nameshort_list_schema]},
        "vim_accounts": {"oneOf": [array_edition_schema, nameshort_list_schema]},
        "interfaces": {"oneOf": [
            array_edition_schema,
            {
                "type": "array",
                "items": pdu_interface,
                "minItems": 1
            }
        ]}
    },
    "additionalProperties": False,
    "minProperties": 1
}

# USERS
user_new_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "New user schema",
    "type": "object",
    "properties": {
        "username": shortname_schema,
        "password": passwd_schema,
        "projects": nameshort_list_schema,
    },
    "required": ["username", "password", "projects"],
    "additionalProperties": False
}
user_edit_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "User edit schema for administrators",
    "type": "object",
    "properties": {
        "password": passwd_schema,
        "projects": {
            "oneOf": [
                nameshort_list_schema,
                array_edition_schema
            ]
        },
    },
    "minProperties": 1,
    "additionalProperties": False
}

# PROJECTS
project_new_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "New project schema for administrators",
    "type": "object",
    "properties": {
        "name": shortname_schema,
        "admin": bool_schema,
    },
    "required": ["name"],
    "additionalProperties": False
}
project_edit_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Project edit schema for administrators",
    "type": "object",
    "properties": {
        "admin": bool_schema,
    },
    "additionalProperties": False,
    "minProperties": 1
}

# GLOBAL SCHEMAS

nbi_new_input_schemas = {
    "users": user_new_schema,
    "projects": project_new_schema,
    "vim_accounts": vim_account_new_schema,
    "sdns": sdn_new_schema,
    "ns_instantiate": ns_instantiate,
    "ns_action": ns_action,
    "ns_scale": ns_scale,
    "pdus": pdu_new_schema,
}

nbi_edit_input_schemas = {
    "users": user_edit_schema,
    "projects": project_edit_schema,
    "vim_accounts": vim_account_edit_schema,
    "sdns": sdn_edit_schema,
    "pdus": pdu_edit_schema,
}

# NETSLICE SCHEMAS
nsi_slice_instantiate = deepcopy(ns_instantiate)
nsi_slice_instantiate["title"] = "netslice subnet instantiation params input schema"
nsi_slice_instantiate["properties"]["id"] = name_schema
nsi_slice_instantiate["properties"]["additionalParamsForNsi"] = object_schema
nsi_slice_instantiate["properties"]["additionalParamsForSubnet"] = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": name_schema,
            "additionalParamsForNs": object_schema,
            "additionalParamsForVnf": additional_params_for_vnf
        },
        "required": ["id"],
        "additionalProperties": False
    }
}
del nsi_slice_instantiate["required"]
del nsi_slice_instantiate["properties"]["additionalParamsForNs"]
del nsi_slice_instantiate["properties"]["additionalParamsForVnf"]

nsi_vld_instantiate = {
    "title": "netslice vld instantiation params input schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "name": string_schema,
        "vim-network-name": {"OneOf": [string_schema, object_schema]},
        "vim-network-id": {"OneOf": [string_schema, object_schema]},
        "ip-profile": object_schema,
    },
    "required": ["name"],
    "additionalProperties": False
}

nsi_instantiate = {
    "title": "netslice action instantiate input schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "lcmOperationType": string_schema,
        "nsiInstanceId": id_schema,
        "nsiName": name_schema,
        "nsiDescription": {"oneOf": [description_schema, {"type": "null"}]},
        "nstId": string_schema,
        "vimAccountId": id_schema,
        "ssh_keys": {"type": "string"},
        "nsi_id": id_schema,
        "netslice-subnet": {
            "type": "array",
            "minItems": 1,
            "items": nsi_slice_instantiate
        },
        "netslice-vld": {
            "type": "array",
            "minItems": 1,
            "items": nsi_vld_instantiate
        },
    },
    "required": ["nsiName", "nstId", "vimAccountId"],
    "additionalProperties": False
}

nsi_action = {

}

nsi_terminate = {

}


class ValidationError(Exception):
    def __init__(self, message, http_code=HTTPStatus.UNPROCESSABLE_ENTITY):
        self.http_code = http_code
        Exception.__init__(self, message)


def validate_input(indata, schema_to_use):
    """
    Validates input data against json schema
    :param indata: user input data. Should be a dictionary
    :param schema_to_use: jsonschema to test
    :return: None if ok, raises ValidationError exception on error
    """
    try:
        if schema_to_use:
            js_v(indata, schema_to_use)
        return None
    except js_e.ValidationError as e:
        if e.path:
            error_pos = "at '" + ":".join(map(str, e.path)) + "'"
        else:
            error_pos = ""
        raise ValidationError("Format error {} '{}' ".format(error_pos, e.message))
    except js_e.SchemaError:
        raise ValidationError("Bad json schema {}".format(schema_to_use), http_code=HTTPStatus.INTERNAL_SERVER_ERROR)
