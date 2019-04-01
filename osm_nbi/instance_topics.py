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

# import logging
from uuid import uuid4
from http import HTTPStatus
from time import time
from copy import copy, deepcopy
from validation import validate_input, ValidationError, ns_instantiate, ns_action, ns_scale, nsi_instantiate
from base_topic import BaseTopic, EngineException, get_iterable
from descriptor_topics import DescriptorTopic
from yaml import safe_dump

__author__ = "Alfonso Tierno <alfonso.tiernosepulveda@telefonica.com>"


class NsrTopic(BaseTopic):
    topic = "nsrs"
    topic_msg = "ns"

    def __init__(self, db, fs, msg):
        BaseTopic.__init__(self, db, fs, msg)

    def _check_descriptor_dependencies(self, session, descriptor):
        """
        Check that the dependent descriptors exist on a new descriptor or edition
        :param session: client session information
        :param descriptor: descriptor to be inserted or edit
        :return: None or raises exception
        """
        if not descriptor.get("nsdId"):
            return
        nsd_id = descriptor["nsdId"]
        if not self.get_item_list(session, "nsds", {"id": nsd_id}):
            raise EngineException("Descriptor error at nsdId='{}' references a non exist nsd".format(nsd_id),
                                  http_code=HTTPStatus.CONFLICT)

    @staticmethod
    def format_on_new(content, project_id=None, make_public=False):
        BaseTopic.format_on_new(content, project_id=project_id, make_public=make_public)
        content["_admin"]["nsState"] = "NOT_INSTANTIATED"

    def check_conflict_on_del(self, session, _id, force=False):
        if force:
            return
        nsr = self.db.get_one("nsrs", {"_id": _id})
        if nsr["_admin"].get("nsState") == "INSTANTIATED":
            raise EngineException("nsr '{}' cannot be deleted because it is in 'INSTANTIATED' state. "
                                  "Launch 'terminate' operation first; or force deletion".format(_id),
                                  http_code=HTTPStatus.CONFLICT)

    def delete(self, session, _id, force=False, dry_run=False):
        """
        Delete item by its internal _id
        :param session: contains the used login username, working project, and admin rights
        :param _id: server internal id
        :param force: indicates if deletion must be forced in case of conflict
        :param dry_run: make checking but do not delete
        :return: dictionary with deleted item _id. It raises EngineException on error: not found, conflict, ...
        """
        # TODO add admin to filter, validate rights
        BaseTopic.delete(self, session, _id, force, dry_run=True)
        if dry_run:
            return

        self.fs.file_delete(_id, ignore_non_exist=True)
        v = self.db.del_one("nsrs", {"_id": _id})
        self.db.del_list("nslcmops", {"nsInstanceId": _id})
        self.db.del_list("vnfrs", {"nsr-id-ref": _id})
        # set all used pdus as free
        self.db.set_list("pdus", {"_admin.usage.nsr_id": _id},
                         {"_admin.usageState": "NOT_IN_USE", "_admin.usage": None})
        self._send_msg("deleted", {"_id": _id})
        return v

    @staticmethod
    def _format_ns_request(ns_request):
        formated_request = copy(ns_request)
        formated_request.pop("additionalParamsForNs", None)
        formated_request.pop("additionalParamsForVnf", None)
        return formated_request

    @staticmethod
    def _format_addional_params(ns_request, member_vnf_index=None, descriptor=None):
        """
        Get and format user additional params for NS or VNF
        :param ns_request: User instantiation additional parameters
        :param member_vnf_index: None for extract NS params, or member_vnf_index to extract VNF params
        :param descriptor: If not None it check that needed parameters of descriptor are supplied
        :return: a formated copy of additional params or None if not supplied
        """
        additional_params = None
        if not member_vnf_index:
            additional_params = copy(ns_request.get("additionalParamsForNs"))
            where_ = "additionalParamsForNs"
        elif ns_request.get("additionalParamsForVnf"):
            for additionalParamsForVnf in get_iterable(ns_request.get("additionalParamsForVnf")):
                if additionalParamsForVnf["member-vnf-index"] == member_vnf_index:
                    additional_params = copy(additionalParamsForVnf.get("additionalParams"))
                    where_ = "additionalParamsForVnf[member-vnf-index={}]".format(
                        additionalParamsForVnf["member-vnf-index"])
                    break
        if additional_params:
            for k, v in additional_params.items():
                if not isinstance(k, str):
                    raise EngineException("Invalid param at {}:{}. Only string keys are allowed".format(where_, k))
                if "." in k or "$" in k:
                    raise EngineException("Invalid param at {}:{}. Keys must not contain dots or $".format(where_, k))
                if isinstance(v, (dict, tuple, list)):
                    additional_params[k] = "!!yaml " + safe_dump(v)

        if descriptor:
            # check that enough parameters are supplied for the initial-config-primitive
            # TODO: check for cloud-init
            if member_vnf_index:
                if descriptor.get("vnf-configuration"):
                    for initial_primitive in get_iterable(
                            descriptor["vnf-configuration"].get("initial-config-primitive")):
                        for param in get_iterable(initial_primitive.get("parameter")):
                            if param["value"].startswith("<") and param["value"].endswith(">"):
                                if param["value"] in ("<rw_mgmt_ip>", "<VDU_SCALE_INFO>"):
                                    continue
                                if not additional_params or param["value"][1:-1] not in additional_params:
                                    raise EngineException("Parameter '{}' needed for vnfd[id={}]:vnf-configuration:"
                                                          "initial-config-primitive[name={}] not supplied".
                                                          format(param["value"], descriptor["id"],
                                                                 initial_primitive["name"]))

        return additional_params

    def new(self, rollback, session, indata=None, kwargs=None, headers=None, force=False, make_public=False):
        """
        Creates a new nsr into database. It also creates needed vnfrs
        :param rollback: list to append the created items at database in case a rollback must be done
        :param session: contains the used login username and working project
        :param indata: params to be used for the nsr
        :param kwargs: used to override the indata descriptor
        :param headers: http request headers
        :param force: If True avoid some dependence checks
        :param make_public: Make the created item public to all projects
        :return: the _id of nsr descriptor created at database
        """

        try:
            ns_request = self._remove_envelop(indata)
            # Override descriptor with query string kwargs
            self._update_input_with_kwargs(ns_request, kwargs)
            self._validate_input_new(ns_request, force)

            step = ""
            # look for nsr
            step = "getting nsd id='{}' from database".format(ns_request.get("nsdId"))
            _filter = {"_id": ns_request["nsdId"]}
            _filter.update(BaseTopic._get_project_filter(session, write=False, show_all=True))
            nsd = self.db.get_one("nsds", _filter)

            nsr_id = str(uuid4())

            now = time()
            step = "filling nsr from input data"
            nsr_descriptor = {
                "name": ns_request["nsName"],
                "name-ref": ns_request["nsName"],
                "short-name": ns_request["nsName"],
                "admin-status": "ENABLED",
                "nsd": nsd,
                "datacenter": ns_request["vimAccountId"],
                "resource-orchestrator": "osmopenmano",
                "description": ns_request.get("nsDescription", ""),
                "constituent-vnfr-ref": [],

                "operational-status": "init",    # typedef ns-operational-
                "config-status": "init",         # typedef config-states
                "detailed-status": "scheduled",

                "orchestration-progress": {},
                # {"networks": {"active": 0, "total": 0}, "vms": {"active": 0, "total": 0}},

                "crete-time": now,
                "nsd-name-ref": nsd["name"],
                "operational-events": [],   # "id", "timestamp", "description", "event",
                "nsd-ref": nsd["id"],
                "instantiate_params": self._format_ns_request(ns_request),
                "additionalParamsForNs": self._format_addional_params(ns_request),
                "ns-instance-config-ref": nsr_id,
                "id": nsr_id,
                "_id": nsr_id,
                # "input-parameter": xpath, value,
                "ssh-authorized-key": ns_request.get("key-pair-ref"),  # TODO remove
            }
            ns_request["nsr_id"] = nsr_id
            # Create vld
            if nsd.get("vld"):
                nsr_descriptor["vld"] = []
                for nsd_vld in nsd.get("vld"):
                    nsr_descriptor["vld"].append(
                        {key: nsd_vld[key] for key in ("id", "vim-network-name", "vim-network-id") if key in nsd_vld})

            # Create VNFR
            needed_vnfds = {}
            for member_vnf in nsd.get("constituent-vnfd", ()):
                vnfd_id = member_vnf["vnfd-id-ref"]
                step = "getting vnfd id='{}' constituent-vnfd='{}' from database".format(
                    member_vnf["vnfd-id-ref"], member_vnf["member-vnf-index"])
                if vnfd_id not in needed_vnfds:
                    # Obtain vnfd
                    vnfd = DescriptorTopic.get_one_by_id(self.db, session, "vnfds", vnfd_id)
                    vnfd.pop("_admin")
                    needed_vnfds[vnfd_id] = vnfd
                else:
                    vnfd = needed_vnfds[vnfd_id]
                step = "filling vnfr  vnfd-id='{}' constituent-vnfd='{}'".format(
                    member_vnf["vnfd-id-ref"], member_vnf["member-vnf-index"])
                vnfr_id = str(uuid4())
                vnfr_descriptor = {
                    "id": vnfr_id,
                    "_id": vnfr_id,
                    "nsr-id-ref": nsr_id,
                    "member-vnf-index-ref": member_vnf["member-vnf-index"],
                    "additionalParamsForVnf": self._format_addional_params(ns_request, member_vnf["member-vnf-index"],
                                                                           vnfd),
                    "created-time": now,
                    # "vnfd": vnfd,        # at OSM model.but removed to avoid data duplication TODO: revise
                    "vnfd-ref": vnfd_id,
                    "vnfd-id": vnfd["_id"],    # not at OSM model, but useful
                    "vim-account-id": None,
                    "vdur": [],
                    "connection-point": [],
                    "ip-address": None,  # mgmt-interface filled by LCM
                }

                # Create vld
                if vnfd.get("internal-vld"):
                    vnfr_descriptor["vld"] = []
                    for vnfd_vld in vnfd.get("internal-vld"):
                        vnfr_descriptor["vld"].append(
                            {key: vnfd_vld[key] for key in ("id", "vim-network-name", "vim-network-id") if key in
                             vnfd_vld})

                vnfd_mgmt_cp = vnfd["mgmt-interface"].get("cp")
                for cp in vnfd.get("connection-point", ()):
                    vnf_cp = {
                        "name": cp["name"],
                        "connection-point-id": cp.get("id"),
                        "id": cp.get("id"),
                        # "ip-address", "mac-address" # filled by LCM
                        # vim-id  # TODO it would be nice having a vim port id
                    }
                    vnfr_descriptor["connection-point"].append(vnf_cp)
                for vdu in vnfd.get("vdu", ()):
                    vdur = {
                        "vdu-id-ref": vdu["id"],
                        # TODO      "name": ""     Name of the VDU in the VIM
                        "ip-address": None,  # mgmt-interface filled by LCM
                        # "vim-id", "flavor-id", "image-id", "management-ip" # filled by LCM
                        "internal-connection-point": [],
                        "interfaces": [],
                    }
                    if vdu.get("pdu-type"):
                        vdur["pdu-type"] = vdu["pdu-type"]
                    # TODO volumes: name, volume-id
                    for icp in vdu.get("internal-connection-point", ()):
                        vdu_icp = {
                            "id": icp["id"],
                            "connection-point-id": icp["id"],
                            "name": icp.get("name"),
                            # "ip-address", "mac-address" # filled by LCM
                            # vim-id  # TODO it would be nice having a vim port id
                        }
                        vdur["internal-connection-point"].append(vdu_icp)
                    for iface in vdu.get("interface", ()):
                        vdu_iface = {
                            "name": iface.get("name"),
                            # "ip-address", "mac-address" # filled by LCM
                            # vim-id  # TODO it would be nice having a vim port id
                        }
                        if vnfd_mgmt_cp and iface.get("external-connection-point-ref") == vnfd_mgmt_cp:
                            vdu_iface["mgmt-vnf"] = True
                        if iface.get("mgmt-interface"):
                            vdu_iface["mgmt-interface"] = True  # TODO change to mgmt-vdu

                        # look for network where this interface is connected
                        if iface.get("external-connection-point-ref"):
                            for nsd_vld in get_iterable(nsd.get("vld")):
                                for nsd_vld_cp in get_iterable(nsd_vld.get("vnfd-connection-point-ref")):
                                    if nsd_vld_cp.get("vnfd-connection-point-ref") == \
                                            iface["external-connection-point-ref"] and \
                                            nsd_vld_cp.get("member-vnf-index-ref") == member_vnf["member-vnf-index"]:
                                        vdu_iface["ns-vld-id"] = nsd_vld["id"]
                                        break
                                else:
                                    continue
                                break
                        elif iface.get("internal-connection-point-ref"):
                            for vnfd_ivld in get_iterable(vnfd.get("internal-vld")):
                                for vnfd_ivld_icp in get_iterable(vnfd_ivld.get("internal-connection-point")):
                                    if vnfd_ivld_icp.get("id-ref") == iface["internal-connection-point-ref"]:
                                        vdu_iface["vnf-vld-id"] = vnfd_ivld["id"]
                                        break
                                else:
                                    continue
                                break

                        vdur["interfaces"].append(vdu_iface)
                    count = vdu.get("count", 1)
                    if count is None:
                        count = 1
                    count = int(count)    # TODO remove when descriptor serialized with payngbind
                    for index in range(0, count):
                        if index:
                            vdur = deepcopy(vdur)
                        vdur["_id"] = str(uuid4())
                        vdur["count-index"] = index
                        vnfr_descriptor["vdur"].append(vdur)

                step = "creating vnfr vnfd-id='{}' constituent-vnfd='{}' at database".format(
                    member_vnf["vnfd-id-ref"], member_vnf["member-vnf-index"])

                # add at database
                BaseTopic.format_on_new(vnfr_descriptor, session["project_id"], make_public=make_public)
                self.db.create("vnfrs", vnfr_descriptor)
                rollback.append({"topic": "vnfrs", "_id": vnfr_id})
                nsr_descriptor["constituent-vnfr-ref"].append(vnfr_id)

            step = "creating nsr at database"
            self.format_on_new(nsr_descriptor, session["project_id"], make_public=make_public)
            self.db.create("nsrs", nsr_descriptor)
            rollback.append({"topic": "nsrs", "_id": nsr_id})

            step = "creating nsr temporal folder"
            self.fs.mkdir(nsr_id)

            return nsr_id
        except Exception as e:
            self.logger.exception("Exception {} at NsrTopic.new()".format(e), exc_info=True)
            raise EngineException("Error {}: {}".format(step, e))
        except ValidationError as e:
            raise EngineException(e, HTTPStatus.UNPROCESSABLE_ENTITY)

    def edit(self, session, _id, indata=None, kwargs=None, force=False, content=None):
        raise EngineException("Method edit called directly", HTTPStatus.INTERNAL_SERVER_ERROR)


class VnfrTopic(BaseTopic):
    topic = "vnfrs"
    topic_msg = None

    def __init__(self, db, fs, msg):
        BaseTopic.__init__(self, db, fs, msg)

    def delete(self, session, _id, force=False, dry_run=False):
        raise EngineException("Method delete called directly", HTTPStatus.INTERNAL_SERVER_ERROR)

    def edit(self, session, _id, indata=None, kwargs=None, force=False, content=None):
        raise EngineException("Method edit called directly", HTTPStatus.INTERNAL_SERVER_ERROR)

    def new(self, rollback, session, indata=None, kwargs=None, headers=None, force=False, make_public=False):
        # Not used because vnfrs are created and deleted by NsrTopic class directly
        raise EngineException("Method new called directly", HTTPStatus.INTERNAL_SERVER_ERROR)


class NsLcmOpTopic(BaseTopic):
    topic = "nslcmops"
    topic_msg = "ns"
    operation_schema = {    # mapping between operation and jsonschema to validate
        "instantiate": ns_instantiate,
        "action": ns_action,
        "scale": ns_scale,
        "terminate": None,
    }

    def __init__(self, db, fs, msg):
        BaseTopic.__init__(self, db, fs, msg)

    def _check_ns_operation(self, session, nsr, operation, indata):
        """
        Check that user has enter right parameters for the operation
        :param session:
        :param operation: it can be: instantiate, terminate, action, TODO: update, heal
        :param indata: descriptor with the parameters of the operation
        :return: None
        """
        vnfds = {}
        vim_accounts = []
        nsd = nsr["nsd"]

        def check_valid_vnf_member_index(member_vnf_index):
            # TODO change to vnfR
            for vnf in nsd["constituent-vnfd"]:
                if member_vnf_index == vnf["member-vnf-index"]:
                    vnfd_id = vnf["vnfd-id-ref"]
                    if vnfd_id not in vnfds:
                        vnfds[vnfd_id] = self.db.get_one("vnfds", {"id": vnfd_id})
                    return vnfds[vnfd_id]
            else:
                raise EngineException("Invalid parameter member_vnf_index='{}' is not one of the "
                                      "nsd:constituent-vnfd".format(member_vnf_index))

        def _check_vnf_instantiation_params(in_vnfd, vnfd):

            for in_vdu in get_iterable(in_vnfd.get("vdu")):
                for vdu in get_iterable(vnfd.get("vdu")):
                    if in_vdu["id"] == vdu["id"]:
                        for volume in get_iterable(in_vdu.get("volume")):
                            for volumed in get_iterable(vdu.get("volumes")):
                                if volumed["name"] == volume["name"]:
                                    break
                            else:
                                raise EngineException("Invalid parameter vnf[member-vnf-index='{}']:vdu[id='{}']:"
                                                      "volume:name='{}' is not present at vnfd:vdu:volumes list".
                                                      format(in_vnf["member-vnf-index"], in_vdu["id"],
                                                             volume["name"]))
                        for in_iface in get_iterable(in_vdu["interface"]):
                            for iface in get_iterable(vdu.get("interface")):
                                if in_iface["name"] == iface["name"]:
                                    break
                            else:
                                raise EngineException("Invalid parameter vnf[member-vnf-index='{}']:vdu[id='{}']:"
                                                      "interface[name='{}'] is not present at vnfd:vdu:interface"
                                                      .format(in_vnf["member-vnf-index"], in_vdu["id"],
                                                              in_iface["name"]))
                        break
                else:
                    raise EngineException("Invalid parameter vnf[member-vnf-index='{}']:vdu[id='{}'] is is not present "
                                          "at vnfd:vdu".format(in_vnf["member-vnf-index"], in_vdu["id"]))

            for in_ivld in get_iterable(in_vnfd.get("internal-vld")):
                for ivld in get_iterable(vnfd.get("internal-vld")):
                    if in_ivld["name"] == ivld["name"] or in_ivld["name"] == ivld["id"]:
                        for in_icp in get_iterable(in_ivld["internal-connection-point"]):
                            for icp in ivld["internal-connection-point"]:
                                if in_icp["id-ref"] == icp["id-ref"]:
                                    break
                            else:
                                raise EngineException("Invalid parameter vnf[member-vnf-index='{}']:internal-vld[name"
                                                      "='{}']:internal-connection-point[id-ref:'{}'] is not present at "
                                                      "vnfd:internal-vld:name/id:internal-connection-point"
                                                      .format(in_vnf["member-vnf-index"], in_ivld["name"],
                                                              in_icp["id-ref"], vnfd["id"]))
                        break
                else:
                    raise EngineException("Invalid parameter vnf[member-vnf-index='{}']:internal-vld:name='{}'"
                                          " is not present at vnfd '{}'".format(in_vnf["member-vnf-index"],
                                                                                in_ivld["name"], vnfd["id"]))

        def check_valid_vim_account(vim_account):
            if vim_account in vim_accounts:
                return
            try:
                db_filter = self._get_project_filter(session, write=False, show_all=True)
                db_filter["_id"] = vim_account
                self.db.get_one("vim_accounts", db_filter)
            except Exception:
                raise EngineException("Invalid vimAccountId='{}' not present for the project".format(vim_account))
            vim_accounts.append(vim_account)

        if operation == "action":
            # check vnf_member_index
            if indata.get("vnf_member_index"):
                indata["member_vnf_index"] = indata.pop("vnf_member_index")    # for backward compatibility
            if not indata.get("member_vnf_index"):
                raise EngineException("Missing 'member_vnf_index' parameter")
            vnfd = check_valid_vnf_member_index(indata["member_vnf_index"])
            # check primitive
            for config_primitive in get_iterable(vnfd.get("vnf-configuration", {}).get("config-primitive")):
                if indata["primitive"] == config_primitive["name"]:
                    # check needed primitive_params are provided
                    if indata.get("primitive_params"):
                        in_primitive_params_copy = copy(indata["primitive_params"])
                    else:
                        in_primitive_params_copy = {}
                    for paramd in get_iterable(config_primitive.get("parameter")):
                        if paramd["name"] in in_primitive_params_copy:
                            del in_primitive_params_copy[paramd["name"]]
                        elif not paramd.get("default-value"):
                            raise EngineException("Needed parameter {} not provided for primitive '{}'".format(
                                paramd["name"], indata["primitive"]))
                    # check no extra primitive params are provided
                    if in_primitive_params_copy:
                        raise EngineException("parameter/s '{}' not present at vnfd for primitive '{}'".format(
                            list(in_primitive_params_copy.keys()), indata["primitive"]))
                    break
            else:
                raise EngineException("Invalid primitive '{}' is not present at vnfd".format(indata["primitive"]))
        if operation == "scale":
            vnfd = check_valid_vnf_member_index(indata["scaleVnfData"]["scaleByStepData"]["member-vnf-index"])
            for scaling_group in get_iterable(vnfd.get("scaling-group-descriptor")):
                if indata["scaleVnfData"]["scaleByStepData"]["scaling-group-descriptor"] == scaling_group["name"]:
                    break
            else:
                raise EngineException("Invalid scaleVnfData:scaleByStepData:scaling-group-descriptor '{}' is not "
                                      "present at vnfd:scaling-group-descriptor".format(
                                          indata["scaleVnfData"]["scaleByStepData"]["scaling-group-descriptor"]))
        if operation == "instantiate":
            # check vim_account
            check_valid_vim_account(indata["vimAccountId"])
            for in_vnf in get_iterable(indata.get("vnf")):
                vnfd = check_valid_vnf_member_index(in_vnf["member-vnf-index"])
                _check_vnf_instantiation_params(in_vnf, vnfd)
                if in_vnf.get("vimAccountId"):
                    check_valid_vim_account(in_vnf["vimAccountId"])

            for in_vld in get_iterable(indata.get("vld")):
                for vldd in get_iterable(nsd.get("vld")):
                    if in_vld["name"] == vldd["name"] or in_vld["name"] == vldd["id"]:
                        break
                else:
                    raise EngineException("Invalid parameter vld:name='{}' is not present at nsd:vld".format(
                        in_vld["name"]))

    def _look_for_pdu(self, session, rollback, vnfr, vim_account, vnfr_update, vnfr_update_rollback):
        """
        Look for a free PDU in the catalog matching vdur type and interfaces. Fills vnfr.vdur with the interface
        (ip_address, ...) information.
        Modifies PDU _admin.usageState to 'IN_USE'
        
        :param session: client session information
        :param rollback: list with the database modifications to rollback if needed
        :param vnfr: vnfr to be updated. It is modified with pdu interface info if pdu is found
        :param vim_account: vim_account where this vnfr should be deployed
        :param vnfr_update: dictionary filled by this method with changes to be done at database vnfr
        :param vnfr_update_rollback: dictionary filled by this method with original content of vnfr in case a rollback
                                     of the changed vnfr is needed

        :return: List of PDU interfaces that are connected to an existing VIM network. Each item contains:
                 "vim-network-name": used at VIM
                  "name": interface name
                  "vnf-vld-id": internal VNFD vld where this interface is connected, or
                  "ns-vld-id": NSD vld where this interface is connected.
                  NOTE: One, and only one between 'vnf-vld-id' and 'ns-vld-id' contains a value. The other will be None
        """

        ifaces_forcing_vim_network = []
        for vdur_index, vdur in enumerate(get_iterable(vnfr.get("vdur"))):
            if not vdur.get("pdu-type"):
                continue
            pdu_type = vdur.get("pdu-type")
            pdu_filter = self._get_project_filter(session, write=True, show_all=True)
            pdu_filter["vim_accounts"] = vim_account
            pdu_filter["type"] = pdu_type
            pdu_filter["_admin.operationalState"] = "ENABLED"
            pdu_filter["_admin.usageState"] = "NOT_IN_USE"
            # TODO feature 1417: "shared": True,

            available_pdus = self.db.get_list("pdus", pdu_filter)
            for pdu in available_pdus:
                # step 1 check if this pdu contains needed interfaces:
                match_interfaces = True
                for vdur_interface in vdur["interfaces"]:
                    for pdu_interface in pdu["interfaces"]:
                        if pdu_interface["name"] == vdur_interface["name"]:
                            # TODO feature 1417: match per mgmt type
                            break
                    else:  # no interface found for name
                        match_interfaces = False
                        break
                if match_interfaces:
                    break
            else:
                raise EngineException(
                    "No PDU of type={} at vim_account={} found for member_vnf_index={}, vdu={} matching interface "
                    "names".format(pdu_type, vim_account, vnfr["member-vnf-index-ref"], vdur["vdu-id-ref"]))

            # step 2. Update pdu
            rollback_pdu = {
                "_admin.usageState": pdu["_admin"]["usageState"],
                "_admin.usage.vnfr_id": None,
                "_admin.usage.nsr_id": None,
                "_admin.usage.vdur": None,
            }
            self.db.set_one("pdus", {"_id": pdu["_id"]},
                            {"_admin.usageState": "IN_USE",
                             "_admin.usage": {"vnfr_id": vnfr["_id"],
                                              "nsr_id": vnfr["nsr-id-ref"],
                                              "vdur": vdur["vdu-id-ref"]}
                             })
            rollback.append({"topic": "pdus", "_id": pdu["_id"], "operation": "set", "content": rollback_pdu})

            # step 3. Fill vnfr info by filling vdur
            vdu_text = "vdur.{}".format(vdur_index)
            vnfr_update_rollback[vdu_text + ".pdu-id"] = None
            vnfr_update[vdu_text + ".pdu-id"] = pdu["_id"]
            for iface_index, vdur_interface in enumerate(vdur["interfaces"]):
                for pdu_interface in pdu["interfaces"]:
                    if pdu_interface["name"] == vdur_interface["name"]:
                        iface_text = vdu_text + ".interfaces.{}".format(iface_index)
                        for k, v in pdu_interface.items():
                            if k in ("ip-address", "mac-address"):  # TODO: switch-xxxxx must be inserted
                                vnfr_update[iface_text + ".{}".format(k)] = v
                                vnfr_update_rollback[iface_text + ".{}".format(k)] = vdur_interface.get(v)
                        if pdu_interface.get("ip-address"):
                            if vdur_interface.get("mgmt-interface"):
                                vnfr_update_rollback[vdu_text + ".ip-address"] = vdur.get("ip-address")
                                vnfr_update[vdu_text + ".ip-address"] = pdu_interface["ip-address"]
                            if vdur_interface.get("mgmt-vnf"):
                                vnfr_update_rollback["ip-address"] = vnfr.get("ip-address")
                                vnfr_update["ip-address"] = pdu_interface["ip-address"]
                        if pdu_interface.get("vim-network-name") or pdu_interface.get("vim-network-id"):
                            ifaces_forcing_vim_network.append({
                                "name": vdur_interface.get("vnf-vld-id") or vdur_interface.get("ns-vld-id"),
                                "vnf-vld-id": vdur_interface.get("vnf-vld-id"),
                                "ns-vld-id": vdur_interface.get("ns-vld-id")})
                            if pdu_interface.get("vim-network-id"):
                                ifaces_forcing_vim_network.append({
                                    "vim-network-id": pdu_interface.get("vim-network-id")})
                            if pdu_interface.get("vim-network-name"):
                                ifaces_forcing_vim_network.append({
                                    "vim-network-name": pdu_interface.get("vim-network-name")})
                        break

        return ifaces_forcing_vim_network

    def _update_vnfrs(self, session, rollback, nsr, indata):
        vnfrs = None
        # get vnfr
        nsr_id = nsr["_id"]
        vnfrs = self.db.get_list("vnfrs", {"nsr-id-ref": nsr_id})

        for vnfr in vnfrs:
            vnfr_update = {}
            vnfr_update_rollback = {}
            member_vnf_index = vnfr["member-vnf-index-ref"]
            # update vim-account-id

            vim_account = indata["vimAccountId"]
            # check instantiate parameters
            for vnf_inst_params in get_iterable(indata.get("vnf")):
                if vnf_inst_params["member-vnf-index"] != member_vnf_index:
                    continue
                if vnf_inst_params.get("vimAccountId"):
                    vim_account = vnf_inst_params.get("vimAccountId")

            vnfr_update["vim-account-id"] = vim_account
            vnfr_update_rollback["vim-account-id"] = vnfr.get("vim-account-id")

            # get pdu
            ifaces_forcing_vim_network = self._look_for_pdu(session, rollback, vnfr, vim_account, vnfr_update,
                                                            vnfr_update_rollback)

            # updata database vnfr
            self.db.set_one("vnfrs", {"_id": vnfr["_id"]}, vnfr_update)
            rollback.append({"topic": "vnfrs", "_id": vnfr["_id"], "operation": "set", "content": vnfr_update_rollback})

            # Update indada in case pdu forces to use a concrete vim-network-name
            # TODO check if user has already insert a vim-network-name and raises an error
            if not ifaces_forcing_vim_network:
                continue
            for iface_info in ifaces_forcing_vim_network:
                if iface_info.get("ns-vld-id"):
                    if "vld" not in indata:
                        indata["vld"] = []
                    indata["vld"].append({key: iface_info[key] for key in
                                          ("name", "vim-network-name", "vim-network-id") if iface_info.get(key)})

                elif iface_info.get("vnf-vld-id"):
                    if "vnf" not in indata:
                        indata["vnf"] = []
                    indata["vnf"].append({
                        "member-vnf-index": member_vnf_index,
                        "internal-vld": [{key: iface_info[key] for key in
                                          ("name", "vim-network-name", "vim-network-id") if iface_info.get(key)}]
                    })

    @staticmethod
    def _create_nslcmop(nsr_id, operation, params):
        """
        Creates a ns-lcm-opp content to be stored at database.
        :param nsr_id: internal id of the instance
        :param operation: instantiate, terminate, scale, action, ...
        :param params: user parameters for the operation
        :return: dictionary following SOL005 format
        """
        now = time()
        _id = str(uuid4())
        nslcmop = {
            "id": _id,
            "_id": _id,
            "operationState": "PROCESSING",  # COMPLETED,PARTIALLY_COMPLETED,FAILED_TEMP,FAILED,ROLLING_BACK,ROLLED_BACK
            "statusEnteredTime": now,
            "nsInstanceId": nsr_id,
            "lcmOperationType": operation,
            "startTime": now,
            "isAutomaticInvocation": False,
            "operationParams": params,
            "isCancelPending": False,
            "links": {
                "self": "/osm/nslcm/v1/ns_lcm_op_occs/" + _id,
                "nsInstance": "/osm/nslcm/v1/ns_instances/" + nsr_id,
            }
        }
        return nslcmop

    def new(self, rollback, session, indata=None, kwargs=None, headers=None, force=False, make_public=False,
            slice_object=False):
        """
        Performs a new operation over a ns
        :param rollback: list to append created items at database in case a rollback must to be done
        :param session: contains the used login username and working project
        :param indata: descriptor with the parameters of the operation. It must contains among others
            nsInstanceId: _id of the nsr to perform the operation
            operation: it can be: instantiate, terminate, action, TODO: update, heal
        :param kwargs: used to override the indata descriptor
        :param headers: http request headers
        :param force: If True avoid some dependence checks
        :param make_public: Make the created item public to all projects
        :return: id of the nslcmops
        """
        try:
            # Override descriptor with query string kwargs
            self._update_input_with_kwargs(indata, kwargs)
            operation = indata["lcmOperationType"]
            nsInstanceId = indata["nsInstanceId"]

            validate_input(indata, self.operation_schema[operation])
            # get ns from nsr_id
            _filter = BaseTopic._get_project_filter(session, write=True, show_all=False)
            _filter["_id"] = nsInstanceId
            nsr = self.db.get_one("nsrs", _filter)

            # initial checking
            if not nsr["_admin"].get("nsState") or nsr["_admin"]["nsState"] == "NOT_INSTANTIATED":
                if operation == "terminate" and indata.get("autoremove"):
                    # NSR must be deleted
                    return None    # a none in this case is used to indicate not instantiated. It can be removed
                if operation != "instantiate":
                    raise EngineException("ns_instance '{}' cannot be '{}' because it is not instantiated".format(
                        nsInstanceId, operation), HTTPStatus.CONFLICT)
            else:
                if operation == "instantiate" and not indata.get("force"):
                    raise EngineException("ns_instance '{}' cannot be '{}' because it is already instantiated".format(
                        nsInstanceId, operation), HTTPStatus.CONFLICT)
            self._check_ns_operation(session, nsr, operation, indata)

            if operation == "instantiate":
                self._update_vnfrs(session, rollback, nsr, indata)

            nslcmop_desc = self._create_nslcmop(nsInstanceId, operation, indata)
            self.format_on_new(nslcmop_desc, session["project_id"], make_public=make_public)
            _id = self.db.create("nslcmops", nslcmop_desc)
            rollback.append({"topic": "nslcmops", "_id": _id})
            if not slice_object:
                self.msg.write("ns", operation, nslcmop_desc)
            return _id
        except ValidationError as e:
            raise EngineException(e, HTTPStatus.UNPROCESSABLE_ENTITY)
        # except DbException as e:
        #     raise EngineException("Cannot get ns_instance '{}': {}".format(e), HTTPStatus.NOT_FOUND)

    def delete(self, session, _id, force=False, dry_run=False):
        raise EngineException("Method delete called directly", HTTPStatus.INTERNAL_SERVER_ERROR)

    def edit(self, session, _id, indata=None, kwargs=None, force=False, content=None):
        raise EngineException("Method edit called directly", HTTPStatus.INTERNAL_SERVER_ERROR)


class NsiTopic(BaseTopic):
    topic = "nsis"
    topic_msg = "nsi"

    def __init__(self, db, fs, msg):
        BaseTopic.__init__(self, db, fs, msg)
        self.nsrTopic = NsrTopic(db, fs, msg)

    @staticmethod
    def _format_ns_request(ns_request):
        formated_request = copy(ns_request)
        # TODO: Add request params
        return formated_request

    @staticmethod
    def _format_addional_params(slice_request):
        """
        Get and format user additional params for NS or VNF
        :param slice_request: User instantiation additional parameters
        :return: a formatted copy of additional params or None if not supplied
        """
        additional_params = copy(slice_request.get("additionalParamsForNsi"))
        if additional_params:
            for k, v in additional_params.items():
                if not isinstance(k, str):
                    raise EngineException("Invalid param at additionalParamsForNsi:{}. Only string keys are allowed".
                                          format(k))
                if "." in k or "$" in k:
                    raise EngineException("Invalid param at additionalParamsForNsi:{}. Keys must not contain dots or $".
                                          format(k))
                if isinstance(v, (dict, tuple, list)):
                    additional_params[k] = "!!yaml " + safe_dump(v)
        return additional_params

    def _check_descriptor_dependencies(self, session, descriptor):
        """
        Check that the dependent descriptors exist on a new descriptor or edition
        :param session: client session information
        :param descriptor: descriptor to be inserted or edit
        :return: None or raises exception
        """
        if not descriptor.get("nst-ref"):
            return
        nstd_id = descriptor["nst-ref"]
        if not self.get_item_list(session, "nsts", {"id": nstd_id}):
            raise EngineException("Descriptor error at nst-ref='{}' references a non exist nstd".format(nstd_id),
                                  http_code=HTTPStatus.CONFLICT)

    @staticmethod
    def format_on_new(content, project_id=None, make_public=False):
        BaseTopic.format_on_new(content, project_id=project_id, make_public=make_public)

    def check_conflict_on_del(self, session, _id, force=False):
        if force:
            return
        nsi = self.db.get_one("nsis", {"_id": _id})
        if nsi["_admin"].get("nsiState") == "INSTANTIATED":
            raise EngineException("nsi '{}' cannot be deleted because it is in 'INSTANTIATED' state. "
                                  "Launch 'terminate' operation first; or force deletion".format(_id),
                                  http_code=HTTPStatus.CONFLICT)

    def delete(self, session, _id, force=False, dry_run=False):
        """
        Delete item by its internal _id
        :param session: contains the used login username, working project, and admin rights
        :param _id: server internal id
        :param force: indicates if deletion must be forced in case of conflict
        :param dry_run: make checking but do not delete
        :return: dictionary with deleted item _id. It raises EngineException on error: not found, conflict, ...
        """
        # TODO add admin to filter, validate rights
        BaseTopic.delete(self, session, _id, force, dry_run=True)
        if dry_run:
            return

        # deletes NetSlice instance object
        v = self.db.del_one("nsis", {"_id": _id})

        # makes a temporal list of nsilcmops objects related to the _id given and deletes them from db
        _filter = {"netsliceInstanceId": _id} 
        self.db.del_list("nsilcmops", _filter)

        _filter = {"operationParams.netsliceInstanceId": _id}
        nslcmops_list = self.db.get_list("nslcmops", _filter)

        for id_item in nslcmops_list:
            _filter = {"_id": id_item}
            nslcmop = self.db.get_one("nslcmops", _filter)
            nsr_id = nslcmop["operationParams"]["nsr_id"]
            self.nsrTopic.delete(session, nsr_id, force=False, dry_run=False)
        self._send_msg("deleted", {"_id": _id})
        return v

    def new(self, rollback, session, indata=None, kwargs=None, headers=None, force=False, make_public=False):
        """
        Creates a new netslice instance record into database. It also creates needed nsrs and vnfrs
        :param rollback: list to append the created items at database in case a rollback must be done
        :param session: contains the used login username and working project
        :param indata: params to be used for the nsir
        :param kwargs: used to override the indata descriptor
        :param headers: http request headers
        :param force: If True avoid some dependence checks
        :param make_public: Make the created item public to all projects
        :return: the _id of nsi descriptor created at database
        """

        try:
            slice_request = self._remove_envelop(indata)
            # Override descriptor with query string kwargs
            self._update_input_with_kwargs(slice_request, kwargs)
            self._validate_input_new(slice_request, force)

            step = ""
            # look for nstd
            step = "getting nstd id='{}' from database".format(slice_request.get("nstId"))
            _filter = {"_id": slice_request["nstId"]}
            _filter.update(BaseTopic._get_project_filter(session, write=False, show_all=True))
            nstd = self.db.get_one("nsts", _filter)
            nstd.pop("_admin", None)
            nstd.pop("_id", None)
            nsi_id = str(uuid4())
            step = "filling nsi_descriptor with input data"

            # Creating the NSIR
            nsi_descriptor = {
                "id": nsi_id,
                "name": slice_request["nsiName"],
                "description": slice_request.get("nsiDescription", ""),
                "datacenter": slice_request["vimAccountId"],
                "nst-ref": nstd["id"],
                "instantiation_parameters": slice_request,
                "network-slice-template": nstd,
                "nsr-ref-list": [],
                "vlr-list": [],
                "_id": nsi_id,
                "additionalParamsForNsi": self._format_addional_params(slice_request)
            }

            step = "creating nsi at database"
            self.format_on_new(nsi_descriptor, session["project_id"], make_public=make_public)
            nsi_descriptor["_admin"]["nsiState"] = "NOT_INSTANTIATED"
            nsi_descriptor["_admin"]["netslice-subnet"] = None
            
            # Creating netslice-vld for the RO.
            step = "creating netslice-vld at database"
            instantiation_parameters = slice_request

            # Building the vlds list to be deployed
            # From netslice descriptors, creating the initial list
            nsi_vlds = []           
            if nstd.get("netslice-vld"):
                # Building VLDs from NST
                for netslice_vlds in nstd["netslice-vld"]:
                    nsi_vld = {}
                    # Adding nst vld name and global vimAccountId for netslice vld creation
                    nsi_vld["name"] = netslice_vlds["name"]
                    nsi_vld["vimAccountId"] = slice_request["vimAccountId"]
                    # Getting template Instantiation parameters from NST
                    for netslice_vld in netslice_vlds["nss-connection-point-ref"]:
                        for netslice_subnet in nstd["netslice-subnet"]:
                            nsi_vld["nsd-ref"] = netslice_subnet["nsd-ref"]
                            nsi_vld["nsd-connection-point-ref"] = netslice_vld["nsd-connection-point-ref"]
                            # Obtaining the vimAccountId from template instantiation parameter            
                            if netslice_subnet.get("instantiation-parameters"):
                                # Taking the vimAccountId from NST netslice-subnet instantiation parameters
                                if netslice_subnet["instantiation-parameters"].get("vimAccountId"):
                                    netsn = netslice_subnet["instantiation-parameters"]["vimAccountId"]
                                    nsi_vld["vimAccountId"] = netsn
                            # Obtaining the vimAccountId from user instantiation parameter
                            if instantiation_parameters.get("netslice-subnet"):
                                for ins_param in instantiation_parameters["netslice-subnet"]:
                                    if ins_param.get("id") == netslice_vld["nss-ref"]:
                                        if ins_param.get("vimAccountId"):
                                            nsi_vld["vimAccountId"] = ins_param["vimAccountId"]
                    # Adding vim-network-name / vim-network-id defined by the user to vld
                    if instantiation_parameters.get("netslice-vld"):
                        for ins_param in instantiation_parameters["netslice-vld"]:
                            if ins_param["name"] == netslice_vlds["name"]:
                                if ins_param.get("vim-network-name"):
                                    nsi_vld["vim-network-name"] = ins_param.get("vim-network-name")
                                if ins_param.get("vim-network-id"):
                                    nsi_vld["vim-network-id"] = ins_param.get("vim-network-id")
                    if netslice_vlds.get("mgmt-network"):
                        nsi_vld["mgmt-network"] = netslice_vlds.get("mgmt-network")
                    nsi_vlds.append(nsi_vld)

            nsi_descriptor["_admin"]["netslice-vld"] = nsi_vlds
            # Creating netslice-subnet_record. 
            needed_nsds = {}
            services = []

            for member_ns in nstd["netslice-subnet"]:
                nsd_id = member_ns["nsd-ref"]
                step = "getting nstd id='{}' constituent-nsd='{}' from database".format(
                    member_ns["nsd-ref"], member_ns["id"])
                if nsd_id not in needed_nsds:
                    # Obtain nsd
                    nsd = DescriptorTopic.get_one_by_id(self.db, session, "nsds", nsd_id)
                    nsd.pop("_admin")
                    needed_nsds[nsd_id] = nsd
                    member_ns["_id"] = needed_nsds[nsd_id].get("_id")
                    services.append(member_ns)
                else:
                    nsd = needed_nsds[nsd_id]
                    member_ns["_id"] = needed_nsds[nsd_id].get("_id")
                    services.append(member_ns)

                step = "filling nsir nsd-id='{}' constituent-nsd='{}' from database".format(
                    member_ns["nsd-ref"], member_ns["id"])

            # check additionalParamsForSubnet contains a valid id
            if slice_request.get("additionalParamsForSubnet"):
                for additional_params_subnet in get_iterable(slice_request.get("additionalParamsForSubnet")):
                    for service in services:
                        if additional_params_subnet["id"] == service["id"]:
                            break
                    else:
                        raise EngineException("Error at additionalParamsForSubnet:id='{}' not match any "
                                              "netslice-subnet:id".format(additional_params_subnet["id"]))

            # creates Network Services records (NSRs)
            step = "creating nsrs at database using NsrTopic.new()"
            ns_params = slice_request.get("netslice-subnet")

            nsrs_list = []
            nsi_netslice_subnet = []
            for service in services:
                indata_ns = {}
                indata_ns["nsdId"] = service["_id"]
                indata_ns["nsName"] = slice_request.get("nsiName") + "." + service["id"]
                indata_ns["vimAccountId"] = slice_request.get("vimAccountId")
                indata_ns["nsDescription"] = service["description"]
                indata_ns["key-pair-ref"] = None
                for additional_params_subnet in get_iterable(slice_request.get("additionalParamsForSubnet")):
                    if additional_params_subnet["id"] == service["id"]:
                        if additional_params_subnet.get("additionalParamsForNs"):
                            indata_ns["additionalParamsForNs"] = additional_params_subnet["additionalParamsForNs"]
                        if additional_params_subnet.get("additionalParamsForVnf"):
                            indata_ns["additionalParamsForVnf"] = additional_params_subnet["additionalParamsForVnf"]
                        break

                # NsrTopic(rollback, session, indata_ns, kwargs, headers, force)
                # Overwriting ns_params filtering by nsName == netslice-subnet.id

                if ns_params:
                    for ns_param in ns_params:
                        if ns_param.get("id") == service["id"]:
                            copy_ns_param = deepcopy(ns_param)
                            del copy_ns_param["id"]
                            indata_ns.update(copy_ns_param)
                # TODO: Improve network selection via networkID
                # Override the instantiation parameters for netslice-vld provided by user
                if nsi_vlds:
                    indata_ns_list = []
                    for nsi_vld in nsi_vlds:
                        nsd = self.db.get_one("nsds", {"id": nsi_vld["nsd-ref"]})
                        if nsd["connection-point"]:
                            for cp_item in nsd["connection-point"]:
                                if cp_item["name"] == nsi_vld["nsd-connection-point-ref"]:
                                    vld_id_ref = cp_item["vld-id-ref"]
                                    # Mapping the vim-network-name or vim-network-id instantiation parameters
                                    if nsi_vld.get("vim-network-id"):
                                        vnid = nsi_vld.get("vim-network-id")
                                        if type(vnid) is not dict:
                                            vim_network_id = {slice_request.get("vimAccountId"): vnid}
                                        else:  # is string
                                            vim_network_id = vnid
                                        indata_ns_list.append({"name": vld_id_ref, "vim-network-id": vim_network_id})
                                    # Case not vim-network-name instantiation parameter
                                    elif nsi_vld.get("vim-network-name"):
                                        vnm = nsi_vld.get("vim-network-name")
                                        if type(vnm) is not dict:
                                            vim_network_name = {slice_request.get("vimAccountId"): vnm}
                                        else:  # is string
                                            vim_network_name = vnm
                                        indata_ns_list.append({"name": vld_id_ref,
                                                              "vim-network-name": vim_network_name})
                                    # Case neither vim-network-name nor vim-network-id provided
                                    else:
                                        indata_ns_list.append({"name": vld_id_ref})
                    if indata_ns_list:
                        indata_ns["vld"] = indata_ns_list

                # Creates Nsr objects
                _id_nsr = self.nsrTopic.new(rollback, session, indata_ns, kwargs, headers, force)
                nsrs_item = {"nsrId": _id_nsr}
                nsrs_list.append(nsrs_item)
                nsi_netslice_subnet.append(indata_ns)
                nsr_ref = {"nsr-ref": _id_nsr}
                nsi_descriptor["nsr-ref-list"].append(nsr_ref)

            # Adding the nsrs list to the nsi
            nsi_descriptor["_admin"]["nsrs-detailed-list"] = nsrs_list
            nsi_descriptor["_admin"]["netslice-subnet"] = nsi_netslice_subnet
            # Creating the entry in the database
            self.db.create("nsis", nsi_descriptor)
            rollback.append({"topic": "nsis", "_id": nsi_id})
            return nsi_id
        except Exception as e:
            self.logger.exception("Exception {} at NsiTopic.new()".format(e), exc_info=True)
            raise EngineException("Error {}: {}".format(step, e))
        except ValidationError as e:
            raise EngineException(e, HTTPStatus.UNPROCESSABLE_ENTITY)

    def edit(self, session, _id, indata=None, kwargs=None, force=False, content=None):
        raise EngineException("Method edit called directly", HTTPStatus.INTERNAL_SERVER_ERROR)


class NsiLcmOpTopic(BaseTopic):
    topic = "nsilcmops"
    topic_msg = "nsi"
    operation_schema = {  # mapping between operation and jsonschema to validate
        "instantiate": nsi_instantiate,
        "terminate": None
    }

    def __init__(self, db, fs, msg):
        BaseTopic.__init__(self, db, fs, msg)

    def _check_nsi_operation(self, session, nsir, operation, indata):
        """
        Check that user has enter right parameters for the operation
        :param session:
        :param operation: it can be: instantiate, terminate, action, TODO: update, heal
        :param indata: descriptor with the parameters of the operation
        :return: None
        """
        nsds = {}
        nstd = nsir["network-slice-template"]

        def check_valid_netslice_subnet_id(nstId):
            # TODO change to vnfR (??)
            for netslice_subnet in nstd["netslice-subnet"]:
                if nstId == netslice_subnet["id"]:
                    nsd_id = netslice_subnet["nsd-ref"]
                    if nsd_id not in nsds:
                        nsds[nsd_id] = self.db.get_one("nsds", {"id": nsd_id})
                    return nsds[nsd_id]
            else:
                raise EngineException("Invalid parameter nstId='{}' is not one of the "
                                      "nst:netslice-subnet".format(nstId))
        if operation == "instantiate":
            # check the existance of netslice-subnet items
            for in_nst in get_iterable(indata.get("netslice-subnet")):   
                check_valid_netslice_subnet_id(in_nst["id"])

    def _create_nsilcmop(self, session, netsliceInstanceId, operation, params):
        now = time()
        _id = str(uuid4())
        nsilcmop = {
            "id": _id,
            "_id": _id,
            "operationState": "PROCESSING",  # COMPLETED,PARTIALLY_COMPLETED,FAILED_TEMP,FAILED,ROLLING_BACK,ROLLED_BACK
            "statusEnteredTime": now,
            "netsliceInstanceId": netsliceInstanceId,
            "lcmOperationType": operation,
            "startTime": now,
            "isAutomaticInvocation": False,
            "operationParams": params,
            "isCancelPending": False,
            "links": {
                "self": "/osm/nsilcm/v1/nsi_lcm_op_occs/" + _id,
                "nsInstance": "/osm/nsilcm/v1/netslice_instances/" + netsliceInstanceId,
            }
        }
        return nsilcmop

    def new(self, rollback, session, indata=None, kwargs=None, headers=None, force=False, make_public=False):
        """
        Performs a new operation over a ns
        :param rollback: list to append created items at database in case a rollback must to be done
        :param session: contains the used login username and working project
        :param indata: descriptor with the parameters of the operation. It must contains among others
            nsiInstanceId: _id of the nsir to perform the operation
            operation: it can be: instantiate, terminate, action, TODO: update, heal
        :param kwargs: used to override the indata descriptor
        :param headers: http request headers
        :param force: If True avoid some dependence checks
        :param make_public: Make the created item public to all projects
        :return: id of the nslcmops
        """
        try:
            # Override descriptor with query string kwargs
            self._update_input_with_kwargs(indata, kwargs)
            operation = indata["lcmOperationType"]
            nsiInstanceId = indata["nsiInstanceId"]
            validate_input(indata, self.operation_schema[operation])

            # get nsi from nsiInstanceId
            _filter = BaseTopic._get_project_filter(session, write=True, show_all=False)
            _filter["_id"] = nsiInstanceId
            nsir = self.db.get_one("nsis", _filter)

            # initial checking
            if not nsir["_admin"].get("nsiState") or nsir["_admin"]["nsiState"] == "NOT_INSTANTIATED":
                if operation == "terminate" and indata.get("autoremove"):
                    # NSIR must be deleted
                    return None    # a none in this case is used to indicate not instantiated. It can be removed
                if operation != "instantiate":
                    raise EngineException("netslice_instance '{}' cannot be '{}' because it is not instantiated".format(
                        nsiInstanceId, operation), HTTPStatus.CONFLICT)
            else:
                if operation == "instantiate" and not indata.get("force"):
                    raise EngineException("netslice_instance '{}' cannot be '{}' because it is already instantiated".
                                          format(nsiInstanceId, operation), HTTPStatus.CONFLICT)
            
            # Creating all the NS_operation (nslcmop)
            # Get service list from db
            nsrs_list = nsir["_admin"]["nsrs-detailed-list"]
            nslcmops = []
            for nsr_item in nsrs_list:
                service = self.db.get_one("nsrs", {"_id": nsr_item["nsrId"]})
                indata_ns = {}
                indata_ns = service["instantiate_params"]
                indata_ns["lcmOperationType"] = operation
                indata_ns["nsInstanceId"] = service["_id"]
                # Including netslice_id in the ns instantiate Operation
                indata_ns["netsliceInstanceId"] = nsiInstanceId
                del indata_ns["key-pair-ref"]
                nsi_NsLcmOpTopic = NsLcmOpTopic(self.db, self.fs, self.msg)
                # Creating NS_LCM_OP with the flag slice_object=True to not trigger the service instantiation 
                # message via kafka bus
                nslcmop = nsi_NsLcmOpTopic.new(rollback, session, indata_ns, kwargs, headers, force, slice_object=True)
                nslcmops.append(nslcmop)

            # Creates nsilcmop
            indata["nslcmops_ids"] = nslcmops
            self._check_nsi_operation(session, nsir, operation, indata)
            nsilcmop_desc = self._create_nsilcmop(session, nsiInstanceId, operation, indata)
            self.format_on_new(nsilcmop_desc, session["project_id"], make_public=make_public)
            _id = self.db.create("nsilcmops", nsilcmop_desc)
            rollback.append({"topic": "nsilcmops", "_id": _id})
            self.msg.write("nsi", operation, nsilcmop_desc)
            return _id
        except ValidationError as e:
            raise EngineException(e, HTTPStatus.UNPROCESSABLE_ENTITY)
        # except DbException as e:
        #     raise EngineException("Cannot get nsi_instance '{}': {}".format(e), HTTPStatus.NOT_FOUND)

    def delete(self, session, _id, force=False, dry_run=False):
        raise EngineException("Method delete called directly", HTTPStatus.INTERNAL_SERVER_ERROR)

    def edit(self, session, _id, indata=None, kwargs=None, force=False, content=None):
        raise EngineException("Method edit called directly", HTTPStatus.INTERNAL_SERVER_ERROR)
