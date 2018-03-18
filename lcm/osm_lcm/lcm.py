#!/usr/bin/python3
# -*- coding: utf-8 -*-

import asyncio
import yaml
import ROclient
import dbmemory
import dbmongo
import fslocal
import msglocal
import msgkafka
import logging
import functools
from dbbase import DbException
from fsbase import FsException
from msgbase import MsgException
from os import environ
# from vca import DeployApplication, RemoveApplication
from n2vc.vnf import N2VC
import os.path
import time

from copy import deepcopy
from http import HTTPStatus

class LcmException(Exception):
    pass


class Lcm:

    def __init__(self, config_file):
        """
        Init, Connect to database, filesystem storage, and messaging
        :param config: two level dictionary with configuration. Top level should contain 'database', 'storage',
        :return: None
        """
        # contains created tasks/futures to be able to cancel
        self.lcm_tasks = {}
        # logging
        self.logger = logging.getLogger('lcm')
        # load configuration
        config = self.read_config_file(config_file)
        self.config = config
        self.ro_config={
            "endpoint_url": "http://{}:{}/openmano".format(config["RO"]["host"], config["RO"]["port"]),
            "tenant":  config.get("tenant", "osm"),
            "logger_name": "lcm.ROclient",
            "loglevel": "ERROR",
        }

        self.vca = config["VCA"]  # TODO VCA
        self.loop = None

        # logging
        log_format_simple = "%(asctime)s %(levelname)s %(name)s %(filename)s:%(lineno)s %(message)s"
        log_formatter_simple = logging.Formatter(log_format_simple, datefmt='%Y-%m-%dT%H:%M:%S')
        config["database"]["logger_name"] = "lcm.db"
        config["storage"]["logger_name"] = "lcm.fs"
        config["message"]["logger_name"] = "lcm.msg"
        if "logfile" in config["global"]:
            file_handler = logging.handlers.RotatingFileHandler(config["global"]["logfile"],
                                                                maxBytes=100e6, backupCount=9, delay=0)
            file_handler.setFormatter(log_formatter_simple)
            self.logger.addHandler(file_handler)
        else:
            str_handler = logging.StreamHandler()
            str_handler.setFormatter(log_formatter_simple)
            self.logger.addHandler(str_handler)

        if config["global"].get("loglevel"):
            self.logger.setLevel(config["global"]["loglevel"])

        # logging other modules
        for k1, logname in {"message": "lcm.msg", "database": "lcm.db", "storage": "lcm.fs"}.items():
            config[k1]["logger_name"] = logname
            logger_module = logging.getLogger(logname)
            if "logfile" in config[k1]:
                file_handler = logging.handlers.RotatingFileHandler(config[k1]["logfile"],
                                                                    maxBytes=100e6, backupCount=9, delay=0)
                file_handler.setFormatter(log_formatter_simple)
                logger_module.addHandler(file_handler)
            if "loglevel" in config[k1]:
                logger_module.setLevel(config[k1]["loglevel"])

        self.n2vc = N2VC(
            log=self.logger,
            server=config['VCA']['host'],
            port=config['VCA']['port'],
            user=config['VCA']['user'],
            secret=config['VCA']['secret'],
            # TODO: This should point to the base folder where charms are stored,
            # if there is a common one (like object storage). Otherwise, leave
            # it unset and pass it via DeployCharms
            # artifacts=config['VCA'][''],
            artifacts=None,
        )

        try:
            if config["database"]["driver"] == "mongo":
                self.db = dbmongo.DbMongo()
                self.db.db_connect(config["database"])
            elif config["database"]["driver"] == "memory":
                self.db = dbmemory.DbMemory()
                self.db.db_connect(config["database"])
            else:
                raise LcmException("Invalid configuration param '{}' at '[database]':'driver'".format(
                    config["database"]["driver"]))

            if config["storage"]["driver"] == "local":
                self.fs = fslocal.FsLocal()
                self.fs.fs_connect(config["storage"])
            else:
                raise LcmException("Invalid configuration param '{}' at '[storage]':'driver'".format(
                    config["storage"]["driver"]))

            if config["message"]["driver"] == "local":
                self.msg = msglocal.MsgLocal()
                self.msg.connect(config["message"])
            elif config["message"]["driver"] == "kafka":
                self.msg = msgkafka.MsgKafka()
                self.msg.connect(config["message"])
            else:
                raise LcmException("Invalid configuration param '{}' at '[message]':'driver'".format(
                    config["storage"]["driver"]))
        except (DbException, FsException, MsgException) as e:
            self.logger.critical(str(e), exc_info=True)
            raise LcmException(str(e))

    def update_nsr_db(self, nsr_id, nsr_desc):
        try:
            self.db.replace("nsrs", nsr_id, nsr_desc)
        except DbException as e:
            self.logger.error("Updating nsr_id={}: {}".format(nsr_id, e))

    def n2vc_callback(self, nsd, vnfd, vnf_member_index, workload_status, *args):
        """Update the lcm database with the status of the charm.

        Updates the VNF's operational status with the state of the charm:
        - blocked: The unit needs manual intervention
        - maintenance: The unit is actively deploying/configuring
        - waiting: The unit is waiting for another charm to be ready
        - active: The unit is deployed, configured, and ready
        - error: The charm has failed and needs attention.
        - terminated: The charm has been destroyed

        Updates the network service's config-status to reflect the state of all
        charms.
        """
        if workload_status and len(args) == 3:
            # self.logger.debug("[n2vc_callback] Workload status \"{}\"".format(workload_status))
            try:
                (db_nsr, vnf_index, task) = args

                nsr_id = db_nsr["_id"]
                nsr_lcm = db_nsr["_admin"]["deploy"]
                nsr_lcm["VCA"][vnf_index]['operational-status'] = workload_status

                if task:
                    if task.cancelled():
                        return

                    if task.done():
                        exc = task.exception()
                        if exc:
                            nsr_lcm = db_nsr["_admin"]["deploy"]
                            nsr_lcm["VCA"][vnf_index]['operational-status'] = "failed"
                            db_nsr["detailed-status"] = "fail configuring vnf_index={} {}".format(vnf_index, exc)
                            db_nsr["config-status"] = "failed"
                            self.update_nsr_db(nsr_id, db_nsr)
                else:
                    units = len(nsr_lcm["VCA"])
                    active = 0
                    statusmap = {}
                    for vnf_index in nsr_lcm["VCA"]:
                        if 'operational-status' in nsr_lcm["VCA"][vnf_index]:

                            if nsr_lcm["VCA"][vnf_index]['operational-status'] not in statusmap:
                                # Initialize it
                                statusmap[nsr_lcm["VCA"][vnf_index]['operational-status']] = 0

                            statusmap[nsr_lcm["VCA"][vnf_index]['operational-status']] += 1

                            if nsr_lcm["VCA"][vnf_index]['operational-status'] == "active":
                                active += 1
                        else:
                            self.logger.debug("No operational-status")

                    cs = ""
                    for status in statusmap:
                        cs += "{} ({}) ".format(status, statusmap[status])
                    db_nsr["config-status"] = cs
                    self.update_nsr_db(nsr_id, db_nsr)

            except Exception as e:
                # self.logger.critical("Task create_ns={} n2vc_callback Exception {}".format(nsr_id, e), exc_info=True)
                self.logger.critical("Task create_ns n2vc_callback Exception {}".format(e), exc_info=True)
            pass

    def vca_deploy_callback(self, db_nsr, vnf_index, status, task):
        # TODO study using this callback when VCA.DeployApplication success from VCAMonitor
        # By the moment this callback is used only to capture exception conditions from VCA DeployApplication
        nsr_id = db_nsr["_id"]
        self.logger.debug("Task create_ns={} vca_deploy_callback Enter".format(nsr_id))
        try:
            if task.cancelled():
                return
            if task.done():
                exc = task.exception()
                if exc:
                    nsr_lcm = db_nsr["_admin"]["deploy"]
                    nsr_lcm["VCA"][vnf_index]['operational-status'] = "failed"
                    db_nsr["detailed-status"] = "fail configuring vnf_index={} {}".format(vnf_index, exc)
                    db_nsr["config-status"] = "failed"
                    self.update_nsr_db(nsr_id, db_nsr)
            else:
                # TODO may be used to be called when VCA monitor status changes
                pass
        # except DbException as e:
        #     self.logger.error("Task create_ns={} vca_deploy_callback Exception {}".format(nsr_id, e))
        except Exception as e:
            self.logger.critical("Task create_ns={} vca_deploy_callback Exception {}".format(nsr_id, e), exc_info=True)

    async def create_ns(self, nsr_id, order_id):
        logging_text = "Task create_ns={} ".format(nsr_id)
        self.logger.debug(logging_text + "Enter")
        # get all needed from database
        db_nsr = None
        exc = None
        step = "Getting nsr from db"
        try:
            db_nsr = self.db.get_one("nsrs", {"_id": nsr_id})
            nsd = db_nsr["nsd"]
            needed_vnfd = {}
            for c_vnf in nsd["constituent-vnfd"]:
                vnfd_id = c_vnf["vnfd-id-ref"]
                if vnfd_id not in needed_vnfd:
                    step = "Getting vnfd={} from db".format(vnfd_id)
                    needed_vnfd[vnfd_id] = self.db.get_one("vnfds", {"id": vnfd_id})

            nsr_lcm = {
                "id": nsr_id,
                "RO": {"vnfd_id": {}, "nsd_id": None, "nsr_id": None, "nsr_status": "SCHEDULED"},
                "nsr_ip": {},
                "VCA": {},
            }
            db_nsr["_admin"]["deploy"] = nsr_lcm
            db_nsr["detailed-status"] = "creating"
            db_nsr["operational-status"] = "init"

            deloyment_timeout = 120

            RO = ROclient.ROClient(self.loop, datacenter=db_nsr["datacenter"], **self.ro_config)

            # get vnfds, instantiate at RO
            for vnfd_id, vnfd in needed_vnfd.items():
                step = db_nsr["detailed-status"] = "Creating vnfd={} at RO".format(vnfd_id)
                self.logger.debug(logging_text + step)
                vnfd_id_RO = nsr_id + "." + vnfd_id[:200]

                # look if present
                vnfd_list = await RO.get_list("vnfd", filter_by={"osm_id": vnfd_id_RO})
                if vnfd_list:
                    nsr_lcm["RO"]["vnfd_id"][vnfd_id] = vnfd_list[0]["uuid"]
                    self.logger.debug(logging_text + "RO vnfd={} exist. Using RO_id={}".format(
                        vnfd_id, vnfd_list[0]["uuid"]))
                else:
                    vnfd_RO = deepcopy(vnfd)
                    vnfd_RO.pop("_id", None)
                    vnfd_RO.pop("_admin", None)
                    vnfd_RO["id"] = vnfd_id_RO
                    desc = await RO.create("vnfd", descriptor=vnfd_RO)
                    nsr_lcm["RO"]["vnfd_id"][vnfd_id] = desc["uuid"]
                self.update_nsr_db(nsr_id, db_nsr)

            # create nsd at RO
            nsd_id = nsd["id"]
            step = db_nsr["detailed-status"] = "Creating nsd={} at RO".format(nsd_id)
            self.logger.debug(logging_text + step)

            nsd_id_RO = nsd_id + "." + nsd_id[:200]
            nsd_list = await RO.get_list("nsd", filter_by={"osm_id": nsd_id_RO})
            if nsd_list:
                nsr_lcm["RO"]["nsd_id"] = nsd_list[0]["uuid"]
                self.logger.debug(logging_text + "RO nsd={} exist. Using RO_id={}".format(
                    nsd_id, nsd_list[0]["uuid"]))
            else:
                nsd_RO = deepcopy(nsd)
                nsd_RO["id"] = nsd_id_RO
                nsd_RO.pop("_id", None)
                nsd_RO.pop("_admin", None)
                for c_vnf in nsd_RO["constituent-vnfd"]:
                    vnfd_id = c_vnf["vnfd-id-ref"]
                    c_vnf["vnfd-id-ref"] = nsr_id + "." + vnfd_id[:200]
                desc = await RO.create("nsd", descriptor=nsd_RO)
                nsr_lcm["RO"]["nsd_id"] = desc["uuid"]
            self.update_nsr_db(nsr_id, db_nsr)

            # Crate ns at RO
            # if present use it unless in error status
            RO_nsr_id = nsr_lcm["RO"].get("nsr_id")
            if RO_nsr_id:
                try:
                    step = db_nsr["detailed-status"] = "Looking for existing ns at RO"
                    self.logger.debug(logging_text + step + " RO_ns_id={}".format(RO_nsr_id))
                    desc = await RO.show("ns", RO_nsr_id)
                except ROclient.ROClientException as e:
                    if e.http_code != HTTPStatus.NOT_FOUND:
                        raise
                    RO_nsr_id = nsr_lcm["RO"]["nsr_id"] = None
                if RO_nsr_id:
                    ns_status, ns_status_info = RO.check_ns_status(desc)
                    nsr_lcm["RO"]["nsr_status"] = ns_status
                    if ns_status == "ERROR":
                        step = db_nsr["detailed-status"] = "Deleting ns at RO"
                        self.logger.debug(logging_text + step + " RO_ns_id={}".format(RO_nsr_id))
                        await RO.delete("ns", RO_nsr_id)
                        RO_nsr_id = nsr_lcm["RO"]["nsr_id"] = None

            if not RO_nsr_id:
                step = db_nsr["detailed-status"] = "Creating ns at RO"
                self.logger.debug(logging_text + step)

                desc = await RO.create("ns", name=db_nsr["name"], datacenter=db_nsr["datacenter"],
                                       scenario=nsr_lcm["RO"]["nsd_id"])
                RO_nsr_id = nsr_lcm["RO"]["nsr_id"] = desc["uuid"]
                nsr_lcm["RO"]["nsr_status"] = "BUILD"
            self.update_nsr_db(nsr_id, db_nsr)

            # wait until NS is ready
            step = ns_status_detailed = "Waiting ns ready at RO"
            db_nsr["detailed-status"] = ns_status_detailed
            self.logger.debug(logging_text + step + " RO_ns_id={}".format(RO_nsr_id))
            deloyment_timeout = 600
            while deloyment_timeout > 0:
                desc = await RO.show("ns", RO_nsr_id)
                ns_status, ns_status_info = RO.check_ns_status(desc)
                nsr_lcm["RO"]["nsr_status"] = ns_status
                if ns_status == "ERROR":
                    raise ROclient.ROClientException(ns_status_info)
                elif ns_status == "BUILD":
                    db_nsr["detailed-status"] = ns_status_detailed + "; {}".format(ns_status_info)
                    self.update_nsr_db(nsr_id, db_nsr)
                elif ns_status == "ACTIVE":
                    nsr_lcm["nsr_ip"] = RO.get_ns_vnf_ip(desc)
                    break
                else:
                    assert False, "ROclient.check_ns_status returns unknown {}".format(ns_status)

                await asyncio.sleep(5, loop=self.loop)
                deloyment_timeout -= 5
            if deloyment_timeout <= 0:
                raise ROclient.ROClientException("Timeout waiting ns to be ready")
            db_nsr["detailed-status"] = "Configuring vnfr"
            self.update_nsr_db(nsr_id, db_nsr)

            vnfd_to_config = 0
            step = "Looking for needed vnfd to configure"
            self.logger.debug(logging_text + step)
            for c_vnf in nsd["constituent-vnfd"]:
                vnfd_id = c_vnf["vnfd-id-ref"]
                vnf_index = str(c_vnf["member-vnf-index"])
                vnfd = needed_vnfd[vnfd_id]
                if vnfd.get("vnf-configuration") and vnfd["vnf-configuration"].get("juju"):
                    nsr_lcm["VCA"][vnf_index] = {}
                    vnfd_to_config += 1
                    proxy_charm = vnfd["vnf-configuration"]["juju"]["charm"]

                    # Note: The charm needs to exist on disk at the location
                    # specified by charm_path.
                    base_folder = vnfd["_admin"]["storage"]
                    charm_path = "{}{}/{}/charms/{}".format(
                        base_folder["path"],
                        base_folder["folder"],
                        base_folder["file"],
                        proxy_charm
                    )

                    self.logger.debug("Passing artifacts path '{}' for {}".format(charm_path, proxy_charm))
                    task = asyncio.ensure_future(
                        self.n2vc.DeployCharms(nsd, vnfd, vnf_index, charm_path, self.n2vc_callback, db_nsr, vnf_index, None)
                    )
                    task.add_done_callback(functools.partial(self.n2vc_callback, None, None, None, None, None, db_nsr, vnf_index))

                    # task.add_done_callback(functools.partial(self.vca_deploy_callback, db_nsr, vnf_index, None))
                    self.lcm_tasks[nsr_id][order_id]["create_charm:" + vnf_index] = task
            db_nsr["config-status"] = "configuring" if vnfd_to_config else "configured"
            db_nsr["detailed-status"] = "Configuring 1/{}".format(vnfd_to_config) if vnfd_to_config else "done"
            db_nsr["operational-status"] = "running"
            self.update_nsr_db(nsr_id, db_nsr)

            self.logger.debug("create_ns task nsr_id={} Exit Ok".format(nsr_id))
            return nsr_lcm

        except (ROclient.ROClientException, DbException) as e:
            self.logger.error(logging_text + "Exit Exception {}".format(e))
            exc = e
        except Exception as e:
            self.logger.critical(logging_text + "Exit Exception {}".format(e), exc_info=True)
            exc = e
        finally:
            if exc and db_nsr:
                db_nsr["detailed-status"] = "ERROR {}: {}".format(step , exc)
                db_nsr["operational-status"] = "failed"
                self.update_nsr_db(nsr_id, db_nsr)

    async def delete_ns(self, nsr_id, order_id):
        logging_text = "Task delete_ns={} ".format(nsr_id)
        self.logger.debug(logging_text + "Enter")
        db_nsr = None
        exc = None
        step = "Getting nsr from db"
        try:
            db_nsr = self.db.get_one("nsrs", {"_id": nsr_id})
            nsd = db_nsr["nsd"]
            nsr_lcm = db_nsr["_admin"]["deploy"]

            db_nsr["operational-status"] = "terminate"
            db_nsr["config-status"] = "terminate"
            db_nsr["detailed-status"] = "Deleting charms"
            self.update_nsr_db(nsr_id, db_nsr)

            try:
                step = db_nsr["detailed-status"] = "Deleting charms"
                self.logger.debug(logging_text + step)
                for vnf_index, deploy_info in nsr_lcm["VCA"].items():
                    if deploy_info and deploy_info.get("appliation"):

                        task = asyncio.ensure_future(
                            self.n2vc.RemoveCharms(nsd, vnfd, vnf_index, self.n2vc_callback, db_nsr, vnf_index, None)
                        )
                        self.lcm_tasks[nsr_id][order_id]["delete_charm:" + vnf_index] = task
            except Exception as e:
                self.logger.debug(logging_text + "Failed while deleting charms: {}".format(e))
            # remove from RO

            RO = ROclient.ROClient(self.loop, datacenter=db_nsr["datacenter"], **self.ro_config)
            # Delete ns
            RO_nsr_id = nsr_lcm["RO"]["nsr_id"]
            if RO_nsr_id:
                try:
                    step = db_nsr["detailed-status"] = "Deleting ns at RO"
                    self.logger.debug(logging_text + step)
                    desc = await RO.delete("ns", RO_nsr_id)
                    nsr_lcm["RO"]["nsr_id"] = None
                    nsr_lcm["RO"]["nsr_status"] = "DELETED"
                except ROclient.ROClientException as e:
                    if e.http_code == 404:  # not found
                        nsr_lcm["RO"]["nsr_id"] = None
                        nsr_lcm["RO"]["nsr_status"] = "DELETED"
                        self.logger.debug(logging_text + "RO_ns_id={} already deleted".format(RO_nsr_id))
                    elif e.http_code == 409:   #conflict
                        self.logger.debug(logging_text + "RO_ns_id={} delete conflict: {}".format(RO_nsr_id, e))
                    else:
                        self.logger.error(logging_text + "RO_ns_id={} delete error: {}".format(RO_nsr_id, e))
                self.update_nsr_db(nsr_id, db_nsr)

            # Delete nsd
            RO_nsd_id = nsr_lcm["RO"]["nsd_id"]
            if RO_nsd_id:
                try:
                    step = db_nsr["detailed-status"] = "Deleting nsd at RO"
                    desc = await RO.delete("nsd", RO_nsd_id)
                    self.logger.debug(logging_text + "RO_nsd_id={} deleted".format(RO_nsd_id))
                    nsr_lcm["RO"]["nsd_id"] = None
                except ROclient.ROClientException as e:
                    if e.http_code == 404:  # not found
                        nsr_lcm["RO"]["nsd_id"] = None
                        self.logger.debug(logging_text + "RO_nsd_id={} already deleted".format(RO_nsd_id))
                    elif e.http_code == 409:   #conflict
                        self.logger.debug(logging_text + "RO_nsd_id={} delete conflict: {}".format(RO_nsd_id, e))
                    else:
                        self.logger.error(logging_text + "RO_nsd_id={} delete error: {}".format(RO_nsd_id, e))
                self.update_nsr_db(nsr_id, db_nsr)

            for vnf_id, RO_vnfd_id in nsr_lcm["RO"]["vnfd_id"].items():
                if not RO_vnfd_id:
                    continue
                try:
                    step = db_nsr["detailed-status"] = "Deleting vnfd={} at RO".format(vnf_id)
                    desc = await RO.delete("vnfd", RO_vnfd_id)
                    self.logger.debug(logging_text + "RO_vnfd_id={} deleted".format(RO_vnfd_id))
                    nsr_lcm["RO"]["vnfd_id"][vnf_id] = None
                except ROclient.ROClientException as e:
                    if e.http_code == 404:  # not found
                        nsr_lcm["RO"]["vnfd_id"][vnf_id] = None
                        self.logger.debug(logging_text + "RO_vnfd_id={} already deleted ".format(RO_vnfd_id))
                    elif e.http_code == 409:   #conflict
                        self.logger.debug(logging_text + "RO_vnfd_id={} delete conflict: {}".format(RO_vnfd_id, e))
                    else:
                        self.logger.error(logging_text + "RO_vnfd_id={} delete error: {}".format(RO_vnfd_id, e))
                self.update_nsr_db(nsr_id, db_nsr)

            # TODO delete from database or mark as deleted???
            db_nsr["operational-status"] = "terminated"
            self.db.del_one("nsrs", {"_id": nsr_id})
            self.logger.debug(logging_text + "Exit")

        except (ROclient.ROClientException, DbException) as e:
            self.logger.error(logging_text + "Exit Exception {}".format(e))
            exc = e
        except Exception as e:
            self.logger.critical(logging_text + "Exit Exception {}".format(e), exc_info=True)
            exc = e
        finally:
            if exc and db_nsr:
                db_nsr["detailed-status"] = "ERROR {}: {}".format(step , exc)
                db_nsr["operational-status"] = "failed"
                self.update_nsr_db(nsr_id, db_nsr)

    async def test(self, param=None):
        self.logger.debug("Starting/Ending test task: {}".format(param))

    def cancel_tasks(self, nsr_id):
        """
        Cancel all active tasks of a concrete nsr identified for nsr_id
        :param nsr_id:  nsr identity
        :return: None, or raises an exception if not possible
        """
        if not self.lcm_tasks.get(nsr_id):
            return
        for order_id, tasks_set in self.lcm_tasks[nsr_id].items():
            for task_name, task in tasks_set.items():
                result = task.cancel()
                if result:
                    self.logger.debug("nsr_id={} order_id={} task={} cancelled".format(nsr_id, order_id, task_name))
        self.lcm_tasks[nsr_id] = {}

    async def read_kafka(self):
        self.logger.debug("kafka task Enter")
        order_id = 1
        # future = asyncio.Future()

        while True:
            command, params = await self.msg.aioread("ns", self.loop)
            order_id += 1
            if command == "exit":
                print("Bye!")
                break
            elif command.startswith("#"):
                continue
            elif command == "echo":
                # just for test
                print(params)
            elif command == "test":
                asyncio.Task(self.test(params), loop=self.loop)
            elif command == "break":
                print("put a break in this line of code")
            elif command == "create":
                nsr_id = params.strip()
                self.logger.debug("Deploying NS {}".format(nsr_id))
                task = asyncio.ensure_future(self.create_ns(nsr_id, order_id))
                if nsr_id not in self.lcm_tasks:
                    self.lcm_tasks[nsr_id] = {}
                self.lcm_tasks[nsr_id][order_id] = {"create_ns": task}
            elif command == "delete":
                nsr_id = params.strip()
                self.logger.debug("Deleting NS {}".format(nsr_id))
                self.cancel_tasks(nsr_id)
                task = asyncio.ensure_future(self.delete_ns(nsr_id, order_id))
                if nsr_id not in self.lcm_tasks:
                    self.lcm_tasks[nsr_id] = {}
                self.lcm_tasks[nsr_id][order_id] = {"delete_ns": task}
            elif command == "show":
                # just for test
                nsr_id = params.strip()
                try:
                    db_nsr = self.db.get_one("nsrs", {"_id": nsr_id})
                    print("nsr:\n    _id={}\n    operational-status: {}\n    config-status: {}\n    detailed-status: "
                          "{}\n    deploy: {}\n    tasks: {}".format(
                                nsr_id, db_nsr["operational-status"],
                                db_nsr["config-status"], db_nsr["detailed-status"],
                                db_nsr["_admin"]["deploy"], self.lcm_tasks.get(nsr_id)))
                except Exception as e:
                    print("nsr {} not found: {}".format(nsr_id, e))
            else:
                self.logger.critical("unknown command '{}'".format(command))
        self.logger.debug("kafka task Exit")


    def start(self):
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self.read_kafka())
        self.loop.close()
        self.loop = None


    def read_config_file(self, config_file):
        # TODO make a [ini] + yaml inside parser
        # the configparser library is not suitable, because it does not admit comments at the end of line,
        # and not parse integer or boolean
        try:
            with open(config_file) as f:
                conf = yaml.load(f)
            for k, v in environ.items():
                if not k.startswith("OSMLCM_"):
                    continue
                k_items = k.lower().split("_")
                c = conf
                try:
                    for k_item in k_items[1:-1]:
                        if k_item in ("ro", "vca"):
                            # put in capital letter
                            k_item = k_item.upper()
                        c = c[k_item]
                    if k_items[-1] == "port":
                        c[k_items[-1]] = int(v)
                    else:
                        c[k_items[-1]] = v
                except Exception as e:
                    self.logger.warn("skipping environ '{}' on exception '{}'".format(k, e))

            return conf
        except Exception as e:
            self.logger.critical("At config file '{}': {}".format(config_file, e))


if __name__ == '__main__':

    config_file = "lcm.cfg"
    lcm = Lcm(config_file)

    lcm.start()
