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
from dbbase import DbException
from fsbase import FsException
from msgbase import MsgException
from os import environ
import logging

#streamformat = "%(asctime)s %(name)s %(levelname)s: %(message)s"
streamformat = "%(name)s %(levelname)s: %(message)s"
logging.basicConfig(format=streamformat, level=logging.DEBUG)


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
        self.config = config
        self.ro_url = "http://{}:{}/openmano".format(config["RO"]["host"], config["RO"]["port"])
        self.ro_tenant = config["RO"]["tenant"]
        self.vca = config["VCA"]  # TODO VCA
        self.loop = None
        try:
            if config["database"]["driver"] == "mongo":
                self.db = dbmongo.dbmongo()
                self.db.db_connect(config["database"])
            elif config["database"]["driver"] == "memory":
                self.db = dbmemory.dbmemory()
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
                self.msg = msglocal.msgLocal()
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

    # def update_nsr_db(self, nsr_id, nsr_desc):
    #    self.db.replace("nsrs", nsr_id, nsr_desc)

    async def create_ns(self, nsr_id):
        self.logger.debug("create_ns task nsr_id={} Enter".format(nsr_id))
        db_nsr = self.db.get_one("nsrs", {"_id": nsr_id})
        nsr_lcm = {
            "id": nsr_id,
            "RO": {"vnfd_id": {}, "nsd_id": None, "nsr_id": None, "nsr_status": "SCHEDULED"},
            "nsr_ip": {},
            "VCA": {}, # "TODO"
        }
        db_nsr["_admin"]["deploy"] = nsr_lcm
        db_nsr["detailed-status"] = "creating"
        db_nsr["operational-status"] = "init"

        deloyment_timeout = 120
        try:
            nsd = db_nsr["nsd"]
            RO = ROclient.ROClient(self.loop, endpoint_url=self.ro_url, tenant=self.ro_tenant,
                                   datacenter=db_nsr["datacenter"])

            # get vnfds, instantiate at RO
            for c_vnf in nsd["constituent-vnfd"]:
                vnfd_id = c_vnf["vnfd-id-ref"]
                self.logger.debug("create_ns task nsr_id={} RO vnfd={} creating".format(nsr_id, vnfd_id))
                db_nsr["detailed-status"] = "Creating vnfd {} at RO".format(vnfd_id)
                vnfd = self.db.get_one("vnfds", {"id": vnfd_id})
                vnfd.pop("_admin", None)
                vnfd.pop("_id", None)

                # look if present
                vnfd_list = await RO.get_list("vnfd", filter_by={"osm_id": vnfd_id})
                if vnfd_list:
                    nsr_lcm["RO"]["vnfd_id"][vnfd_id] = vnfd_list[0]["uuid"]
                    self.logger.debug("create_ns task nsr_id={} RO vnfd={} exist. Using RO_id={}".format(
                        nsr_id, vnfd_id, vnfd_list[0]["uuid"]))
                else:
                    desc = await RO.create("vnfd", descriptor=vnfd)
                    nsr_lcm["RO"]["vnfd_id"][vnfd_id] = desc["uuid"]
                self.db.replace("nsrs", nsr_id, db_nsr)

                # db_new("vnfr", vnfr)
                # db_update("ns_request", nsr_id, ns_request)

            # create nsd at RO
            nsd_id = db_nsr["nsd"]["id"]
            self.logger.debug("create_ns task nsr_id={} RO nsd={} creating".format(nsr_id, nsd_id))
            db_nsr["detailed-status"] = "Creating nsd {} at RO".format(nsd_id)
            nsd = self.db.get_one("nsds", {"id": nsd_id})
            nsd.pop("_admin", None)
            nsd.pop("_id", None)

            nsd_list = await RO.get_list("nsd", filter_by={"osm_id": nsd_id})
            if nsd_list:
                nsr_lcm["RO"]["nsd_id"] = nsd_list[0]["uuid"]
                self.logger.debug("create_ns task nsr_id={} RO nsd={} exist. Using RO_id={}".format(
                    nsr_id, nsd_id, nsd_list[0]["uuid"]))
            else:
                desc = await RO.create("nsd", descriptor=nsd)
                nsr_lcm["RO"]["nsd_id"] = desc["uuid"]
            self.db.replace("nsrs", nsr_id, db_nsr)

            # Crate ns at RO
            self.logger.debug("create_ns task nsr_id={} RO ns creating".format(nsr_id))
            db_nsr["detailed-status"] = "Creating ns at RO"
            desc = await RO.create("ns", name=db_nsr["name"], datacenter=db_nsr["datacenter"],
                                   scenario=nsr_lcm["RO"]["nsd_id"])
            RO_nsr_id = desc["uuid"]
            nsr_lcm["RO"]["nsr_id"] = RO_nsr_id
            nsr_lcm["RO"]["nsr_status"] = "BUILD"
            self.db.replace("nsrs", nsr_id, db_nsr)

            # wait until NS is ready
            self.logger.debug("create_ns task nsr_id={} RO ns_id={} waiting to be ready".format(nsr_id, RO_nsr_id))
            deloyment_timeout = 600
            while deloyment_timeout > 0:
                ns_status_detailed = "Waiting ns ready at RO"
                db_nsr["detailed-status"] = ns_status_detailed
                desc = await RO.show("ns", RO_nsr_id)
                ns_status, ns_status_info = RO.check_ns_status(desc)
                nsr_lcm["RO"]["nsr_status"] = ns_status
                if ns_status == "ERROR":
                    raise ROclient.ROClientException(ns_status_info)
                elif ns_status == "BUILD":
                    db_nsr["detailed-status"] = ns_status_detailed + "; nsr_id: '{}', {}".format(nsr_id, ns_status_info)
                elif ns_status == "ACTIVE":
                    nsr_lcm["nsr_ip"] = RO.get_ns_vnf_ip(desc)
                    break
                else:
                    assert False, "ROclient.check_ns_status returns unknown {}".format(ns_status)

                await asyncio.sleep(5, loop=self.loop)
                deloyment_timeout -= 5
            if deloyment_timeout <= 0:
                raise ROclient.ROClientException("Timeot wating ns to be ready")
            db_nsr["detailed-status"] = "Configuring vnfr"
            self.db.replace("nsrs", nsr_id, db_nsr)

            #for nsd in nsr_lcm["descriptors"]["nsd"]:

            self.logger.debug("create_ns task nsr_id={} VCA look for".format(nsr_id))
            for c_vnf in nsd["constituent-vnfd"]:
                vnfd_id = c_vnf["vnfd-id-ref"]
                vnfd_index = str(c_vnf["member-vnf-index"])
                vnfd = self.db.get_one("vnfds", {"id": vnfd_id})
                db_nsr["config-status"] = "config_not_needed"
                if vnfd.get("vnf-configuration") and vnfd["vnf-configuration"].get("juju"):
                    db_nsr["config-status"] = "configuring"
                    proxy_charm = vnfd["vnf-configuration"]["juju"]["charm"]
                    config_primitive = vnfd["vnf-configuration"].get("config-primitive")
                    # get parameters for juju charm
                    base_folder = vnfd["_admin"]["storage"]
                    path = "{}{}/{}/charms".format(base_folder["path"], base_folder["folder"], base_folder["file"],
                                                   proxy_charm)
                    mgmt_ip = nsr_lcm['nsr_ip'][vnfd_index]
                    # TODO launch VCA charm
                    # task = asyncio.ensure_future(DeployCharm(self.loop, path, mgmt_ip, config_primitive))
            db_nsr["detailed-status"] = "Done"
            db_nsr["operational-status"] = "running"
            self.db.replace("nsrs", nsr_id, db_nsr)

            self.logger.debug("create_ns task nsr_id={} Exit Ok".format(nsr_id))
            return nsr_lcm

        except (ROclient.ROClientException, Exception) as e:
            db_nsr["operational-status"] = "failed"
            db_nsr["detailed-status"] += ": ERROR {}".format(e)
            self.db.replace("nsrs", nsr_id, db_nsr)
            self.logger.debug(
                "create_ns nsr_id={} Exit Exception on '{}': {}".format(nsr_id, db_nsr["detailed-status"], e),
                exc_info=True)

    async def delete_ns(self, nsr_id):
        self.logger.debug("delete_ns task nsr_id={}, Delete_ns task nsr_id={} Enter".format(nsr_id, nsr_id))
        db_nsr = self.db.get_one("nsrs", {"_id": nsr_id})
        nsr_lcm = db_nsr["_admin"]["deploy"]

        db_nsr["operational-status"] = "terminate"
        db_nsr["config-status"] = "terminate"
        db_nsr["detailed-status"] = "Deleting charms"
        self.db.replace("nsrs", nsr_id, db_nsr)
        # TODO destroy VCA charm

        # remove from RO
        RO = ROclient.ROClient(self.loop, endpoint_url=self.ro_url, tenant=self.ro_tenant,
                               datacenter=db_nsr["datacenter"])
        # Delete ns
        RO_nsr_id = nsr_lcm["RO"]["nsr_id"]
        if RO_nsr_id:
            try:
                db_nsr["detailed-status"] = "Deleting ns at RO"
                desc = await RO.delete("ns", RO_nsr_id)
                self.logger.debug("delete_ns task nsr_id={} RO ns={} deleted".format(nsr_id, RO_nsr_id))
                nsr_lcm["RO"]["nsr_id"] = None
                nsr_lcm["RO"]["nsr_status"] = "DELETED"
            except ROclient.ROClientException as e:
                if e.http_code == 404:  # not found
                    nsr_lcm["RO"]["nsr_id"] = None
                    nsr_lcm["RO"]["nsr_status"] = "DELETED"
                    self.logger.debug("delete_ns task nsr_id={} RO ns={} already deleted".format(nsr_id, RO_nsr_id))
                elif e.http_code == 409:   #conflict
                    self.logger.debug("delete_ns task nsr_id={} RO ns={} delete conflict: {}".format(nsr_id, RO_nsr_id,
                                                                                                     e))
                else:
                    self.logger.error("delete_ns task nsr_id={} RO ns={} delete error: {}".format(nsr_id, RO_nsr_id, e))
            self.db.replace("nsrs", nsr_id, db_nsr)

        # Delete nsd
        RO_nsd_id = nsr_lcm["RO"]["nsd_id"]
        if RO_nsd_id:
            try:
                db_nsr["detailed-status"] = "Deleting nsd at RO"
                desc = await RO.delete("nsd", RO_nsd_id)
                self.logger.debug("delete_ns task nsr_id={} RO nsd={} deleted".format(nsr_id, RO_nsd_id))
                nsr_lcm["RO"]["nsd_id"] = None
            except ROclient.ROClientException as e:
                if e.http_code == 404:  # not found
                    nsr_lcm["RO"]["nsd_id"] = None
                    self.logger.debug("delete_ns task nsr_id={} RO nsd={} already deleted".format(nsr_id, RO_nsd_id))
                elif e.http_code == 409:   #conflict
                    self.logger.debug("delete_ns task nsr_id={} RO nsd={} delete conflict: {}".format(nsr_id, RO_nsd_id,
                                                                                                      e))
                else:
                    self.logger.error("delete_ns task nsr_id={} RO nsd={} delete error: {}".format(nsr_id, RO_nsd_id,
                                                                                                   e))
            self.db.replace("nsrs", nsr_id, db_nsr)

        for vnf_id, RO_vnfd_id in nsr_lcm["RO"]["vnfd_id"].items():
            if not RO_vnfd_id:
                continue
            try:
                db_nsr["detailed-status"] = "Deleting vnfd {} at RO".format(vnf_id)
                desc = await RO.delete("vnfd", RO_vnfd_id)
                self.logger.debug("delete_ns task nsr_id={} RO vnfd={} deleted".format(nsr_id, RO_vnfd_id))
                nsr_lcm["RO"]["vnfd_id"][vnf_id] = None
            except ROclient.ROClientException as e:
                if e.http_code == 404:  # not found
                    nsr_lcm["RO"]["vnfd_id"][vnf_id] = None
                    self.logger.debug("delete_ns task nsr_id={} RO vnfd={} already deleted ".format(nsr_id, RO_vnfd_id))
                elif e.http_code == 409:   #conflict
                    self.logger.debug("delete_ns task nsr_id={} RO vnfd={} delete conflict: {}".format(
                        nsr_id, RO_vnfd_id, e))
                else:
                    self.logger.error("delete_ns task nsr_id={} RO vnfd={} delete error: {}".format(
                        nsr_id, RO_vnfd_id, e))
            self.db.replace("nsrs", nsr_id, db_nsr)


        # TODO delete from database or mark as deleted???
        db_nsr["operational-status"] = "terminated"
        self.db.del_one("nsrs", {"_id": nsr_id})
        self.logger.debug("delete_ns task nsr_id={} Exit".format(nsr_id))

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
                print(params)
            elif command == "test":
                asyncio.Task(self.test(params), loop=self.loop)
            elif command == "break":
                print("put a break in this line of code")
            elif command == "create":
                nsr_id = params.strip()
                self.logger.debug("Deploying NS {}".format(nsr_id))
                task = asyncio.ensure_future(self.create_ns(nsr_id))
                if nsr_id not in self.lcm_tasks:
                    self.lcm_tasks[nsr_id] = {}
                self.lcm_tasks[nsr_id][order_id] = {"create_ns": task}
            elif command == "delete":
                nsr_id = params.strip()
                self.logger.debug("Deleting NS {}".format(nsr_id))
                self.cancel_tasks(nsr_id)
                task = asyncio.ensure_future(self.delete_ns(nsr_id))
                if nsr_id not in self.lcm_tasks:
                    self.lcm_tasks[nsr_id] = {}
                self.lcm_tasks[nsr_id][order_id] = {"delete_ns": task}
            elif command == "show":
                nsr_id = params.strip()
                nsr_lcm = self.db.get_one("nsr_lcm", {"id": nsr_id})
                print("nsr_lcm", nsr_lcm)
                print("self.lcm_tasks", self.lcm_tasks.get(nsr_id))
            else:
                self.logger.debug("unknown command '{}'".format(command))
                print("Usage:\n  echo: <>\n  create: <ns1|ns2>\n  delete: <ns1|ns2>\n  show: <ns1|ns2>")
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

    # # FOR TEST
    # RO_VIM = "OST2_MRT"
    #
    # #FILL DATABASE
    # with open("/home/atierno/OSM/osm/devops/descriptor-packages/vnfd/ping_vnf/src/ping_vnfd.yaml") as f:
    #     vnfd = yaml.load(f)
    #     vnfd_clean, _ = ROclient.remove_envelop("vnfd", vnfd)
    #     vnfd_clean["_admin"] = {"storage": "/home/atierno/OSM/osm/devops/descriptor-packages/vnfd/ping_vnf"}
    #     lcm.db.create("vnfd", vnfd_clean)
    # with open("/home/atierno/OSM/osm/devops/descriptor-packages/vnfd/pong_vnf/src/pong_vnfd.yaml") as f:
    #     vnfd = yaml.load(f)
    #     vnfd_clean, _ = ROclient.remove_envelop("vnfd", vnfd)
    #     vnfd_clean["_admin"] = {"storage": "/home/atierno/OSM/osm/devops/descriptor-packages/vnfd/pong_vnf"}
    #     lcm.db.create("vnfd", vnfd_clean)
    # with open("/home/atierno/OSM/osm/devops/descriptor-packages/nsd/ping_pong_ns/src/ping_pong_nsd.yaml") as f:
    #     nsd = yaml.load(f)
    #     nsd_clean, _ = ROclient.remove_envelop("nsd", nsd)
    #     nsd_clean["_admin"] = {"storage": "/home/atierno/OSM/osm/devops/descriptor-packages/nsd/ping_pong_ns"}
    #     lcm.db.create("nsd", nsd_clean)
    #
    # ns_request = {
    #     "id": "ns1",
    #     "nsr_id": "ns1",
    #     "name": "pingpongOne",
    #     "vim": RO_VIM,
    #     "nsd_id": nsd_clean["id"],  # nsd_ping_pong
    # }
    # lcm.db.create("ns_request", ns_request)
    # ns_request = {
    #     "id": "ns2",
    #     "nsr_id": "ns2",
    #     "name": "pingpongTwo",
    #     "vim": RO_VIM,
    #     "nsd_id": nsd_clean["id"],  # nsd_ping_pong
    # }
    # lcm.db.create("ns_request", ns_request)

    lcm.start()



