#!/usr/bin/python3
# -*- coding: utf-8 -*-

import asyncio
import yaml
import ROclient
import dbmemory
import dbmongo
import fslocal
import msglocal
from dbbase import DbException
from fsbase import FsException
from msgbase import MsgException
import logging

#streamformat = "%(asctime)s %(name)s %(levelname)s: %(message)s"
streamformat = "%(name)s %(levelname)s: %(message)s"
logging.basicConfig(format=streamformat, level=logging.DEBUG)


class LcmException(Exception):
    pass


class Lcm:

    def __init__(self, config):
        """
        Init, Connect to database, filesystem storage, and messaging
        :param config: two level dictionary with configuration. Top level should contain 'database', 'storage',
        :return: None
        """
        # contains created tasks/futures to be able to cancel
        self.lcm_tasks = {}

        self.config = config
        # logging
        self.logger = logging.getLogger('lcm')
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
            else:
                raise LcmException("Invalid configuration param '{}' at '[message]':'driver'".format(
                    config["storage"]["driver"]))
        except (DbException, FsException, MsgException) as e:
            self.self.logger.critical(str(e), exc_info=True)
            raise LcmException(str(e))

    async def create_ns(self, nsr_id):
        self.logger.debug("create_ns task nsr_id={} Enter".format(nsr_id))
        nsr_lcm = {
            "id": nsr_id,
            "RO": {"vnfd_id": {}, "nsd_id": None, "nsr_id": None, "nsr_status": "SCHEDULED"},
            "nsr_ip": {},
            "VCA": {"TODO"},
            "status": "BUILD",
            "status_detailed": "",
        }

        deloyment_timeout = 120
        try:
            ns_request = self.db.get_one("ns_request", {"id": nsr_id})
            nsd = self.db.get_one("nsd", {"id": ns_request["nsd_id"]})
            RO = ROclient.ROClient(self.loop, endpoint_url=self.ro_url, tenant=self.ro_tenant,
                                   datacenter=ns_request["vim"])
            nsr_lcm["status_detailed"] = "Creating vnfd at RO"
            # ns_request["constituent-vnfr-ref"] = []

            self.db.create("nsr_lcm", nsr_lcm)

            # get vnfds, instantiate at RO
            self.logger.debug("create_ns task nsr_id={} RO VNFD".format(nsr_id))
            for c_vnf in nsd["constituent-vnfd"]:
                vnfd_id = c_vnf["vnfd-id-ref"]
                vnfd = self.db.get_one("vnfd", {"id": vnfd_id})
                vnfd.pop("_admin", None)
                vnfd.pop("_id", None)
                # vnfr = deepcopy(vnfd)
                # vnfr["member-vnf-index"] = c_vnf["member-vnf-index"]
                # vnfr["nsr-id"] = nsr_id
                # vnfr["id"] = uuid4()
                # vnfr["vnf-id"] = vnfd["id"]
                # ns_request["constituent-vnfr-ref"],append(vnfd_id)

                # TODO change id for RO in case it is present
                try:
                    desc = await RO.create("vnfd", descriptor=vnfd)
                    nsr_lcm["RO"]["vnfd_id"][vnfd_id] = desc["uuid"]
                    self.db.replace("nsr_lcm", {"id": nsr_id}, nsr_lcm)
                except ROclient.ROClientException as e:
                    if e.http_code == 409:  # conflict, vnfd already present
                        print("debug", e)
                    else:
                        raise

                # db_new("vnfr", vnfr)
                # db_update("ns_request", nsr_id, ns_request)

            # create nsd at RO
            self.logger.debug("create_ns task nsr_id={} RO NSD".format(nsr_id))
            nsr_lcm["status_detailed"] = "Creating nsd at RO"
            nsd_id = ns_request["nsd_id"]
            nsd = self.db.get_one("nsd", {"id": nsd_id})
            nsd.pop("_admin", None)
            nsd.pop("_id", None)
            try:
                desc = await RO.create("nsd", descriptor=nsd)
                nsr_lcm["RO"]["nsd_id"] = desc["uuid"]
                self.db.replace("nsr_lcm", {"id": nsr_id}, nsr_lcm)
            except ROclient.ROClientException as e:
                if e.http_code == 409:  # conflict, nsd already present
                    print("debug", e)
                else:
                    raise

            # Crate ns at RO
            self.logger.debug("create_ns task nsr_id={} RO NS".format(nsr_id))
            nsr_lcm["status_detailed"] = "Creating ns at RO"
            desc = await RO.create("ns", name=ns_request["name"], datacenter=ns_request["vim"], scenario=nsr_lcm["RO"]["nsd_id"])
            RO_nsr_id = desc["uuid"]
            nsr_lcm["RO"]["nsr_id"] = RO_nsr_id
            nsr_lcm["RO"]["nsr_status"] = "BUILD"
            self.db.replace("nsr_lcm", {"id": nsr_id}, nsr_lcm)

            # wait until NS is ready
            deloyment_timeout = 600
            while deloyment_timeout > 0:
                ns_status_detailed = "Waiting ns ready at RO"
                nsr_lcm["status_detailed"] = ns_status_detailed
                desc = await RO.show("ns", RO_nsr_id)
                ns_status, ns_status_info = RO.check_ns_status(desc)
                nsr_lcm["RO"]["nsr_status"] = ns_status
                if ns_status == "ERROR":
                    raise ROclient.ROClientException(ns_status_info)
                elif ns_status == "BUILD":
                    nsr_lcm["status_detailed"] = ns_status_detailed + "; nsr_id: '{}', {}".format(nsr_id, ns_status_info)
                elif ns_status == "ACTIVE":
                    nsr_lcm["nsr_ip"] = RO.get_ns_vnf_ip(desc)
                    break
                else:
                    assert False, "ROclient.check_ns_status returns unknown {}".format(ns_status)

                await asyncio.sleep(5, loop=self.loop)
                deloyment_timeout -= 5
            if deloyment_timeout <= 0:
                raise ROclient.ROClientException("Timeot wating ns to be ready")
            nsr_lcm["status_detailed"] = "Configuring vnfr"
            self.db.replace("nsr_lcm", {"id": nsr_id}, nsr_lcm)

            #for nsd in nsr_lcm["descriptors"]["nsd"]:

            self.logger.debug("create_ns task nsr_id={} VCA look for".format(nsr_id))
            for c_vnf in nsd["constituent-vnfd"]:
                vnfd_id = c_vnf["vnfd-id-ref"]
                vnfd_index = int(c_vnf["member-vnf-index"])
                vnfd = self.db.get_one("vnfd", {"id": vnfd_id})
                if vnfd.get("vnf-configuration") and vnfd["vnf-configuration"].get("juju"):
                    proxy_charm = vnfd["vnf-configuration"]["juju"]["charm"]
                    config_primitive = vnfd["vnf-configuration"].get("config-primitive")
                    # get parameters for juju charm
                    base_folder = vnfd["_admin"]["storage"]
                    path = base_folder + "/charms/" + proxy_charm
                    mgmt_ip = nsr_lcm['nsr_ip'][vnfd_index]
                    # TODO launch VCA charm
                    # task = asyncio.ensure_future(DeployCharm(self.loop, path, mgmt_ip, config_primitive))
            nsr_lcm["status"] = "DONE"
            self.db.replace("nsr_lcm", {"id": nsr_id}, nsr_lcm)

            return nsr_lcm

        except (ROclient.ROClientException, Exception) as e:
            self.logger.debug("create_ns nsr_id={} Exception {}".format(nsr_id, e), exc_info=True)
            nsr_lcm["status"] = "ERROR"
            nsr_lcm["status_detailed"] += ": ERROR {}".format(e)
        finally:
            self.logger.debug("create_ns task nsr_id={} Exit".format(nsr_id))


    async def delete_ns(self, nsr_id):
        self.logger.debug("delete_ns task nsr_id={} Enter".format(nsr_id))
        nsr_lcm = self.db.get_one("nsr_lcm", {"id": nsr_id})
        ns_request = self.db.get_one("ns_request", {"id": nsr_id})

        nsr_lcm["status"] = "DELETING"
        nsr_lcm["status_detailed"] = "Deleting charms"
        self.db.replace("nsr_lcm", {"id": nsr_id}, nsr_lcm)
        # TODO destroy VCA charm

        # remove from RO
        RO = ROclient.ROClient(self.loop, endpoint_url=self.ro_url, tenant=self.ro_tenant,
                               datacenter=ns_request["vim"])
        # Delete ns
        try:
            RO_nsr_id = nsr_lcm["RO"]["nsr_id"]
            if RO_nsr_id:
                nsr_lcm["status_detailed"] = "Deleting ns at RO"
                desc = await RO.delete("ns", RO_nsr_id)
                print("debug", "deleted RO ns {}".format(RO_nsr_id))
                nsr_lcm["RO"]["nsr_id"] = None
                nsr_lcm["RO"]["nsr_status"] = "DELETED"
                self.db.replace("nsr_lcm", {"id": nsr_id}, nsr_lcm)
        except ROclient.ROClientException as e:
            if e.http_code == 404:
                nsr_lcm["RO"]["nsr_id"] = None
                nsr_lcm["RO"]["nsr_status"] = "DELETED"
                self.db.replace("nsr_lcm", {"id": nsr_id}, nsr_lcm)
                print("warning", e)
            else:
                print("error", e)

        # Delete nsd
        try:
            RO_nsd_id = nsr_lcm["RO"]["nsd_id"]
            if RO_nsd_id:
                nsr_lcm["status_detailed"] = "Deleting nsd at RO"
                desc = await RO.delete("nsd", RO_nsd_id)
                print("debug", "deleted RO nsd {}".format(RO_nsd_id))
                nsr_lcm["RO"]["nsd_id"] = None
                self.db.replace("nsr_lcm", {"id": nsr_id}, nsr_lcm)
        except ROclient.ROClientException as e:
            if e.http_code == 404:
                nsr_lcm["RO"]["nsd_id"] = None
                print("warning", e)
            else:
                print("error", e)

        for vnf_id, RO_vnfd_id in nsr_lcm["RO"]["vnfd_id"].items():
            try:
                if RO_vnfd_id:
                    nsr_lcm["status_detailed"] = "Deleting vnfd at RO"
                    desc = await RO.delete("vnfd", RO_vnfd_id)
                    print("debug", "deleted RO vnfd {}".format(RO_vnfd_id))
                    nsr_lcm["RO"]["vnfd_id"][vnf_id] = None
                    self.db.replace("nsr_lcm", {"id": nsr_id}, nsr_lcm)
            except ROclient.ROClientException as e:
                if e.http_code == 404:
                    nsr_lcm["RO"]["vnfd_id"][vnf_id] = None
                    print("warning", e)
                else:
                    print("error", e)
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
            command, params = await self.msg.aioread(self.loop, "ns")
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


def read_config_file(config_file):
    # TODO make a [ini] + yaml inside parser
    # the configparser library is not suitable, because it does not admit comments at the end of line,
    # and not parse integer or boolean
    try:
        with open(config_file) as f:
            conf = yaml.load(f)
        # TODO insert envioronment
        # for k, v in environ.items():
        #    if k.startswith("OSMLCM_"):
        # split _ lower add to config
        return conf
    except Exception as e:
        self.logger.critical("At config file '{}': {}".format(config_file, e))



if __name__ == '__main__':

    config_file = "lcm.cfg"
    conf = read_config_file(config_file)
    lcm = Lcm(conf)

    # FOR TEST
    RO_VIM = "OST2_MRT"

    #FILL DATABASE
    with open("/home/atierno/OSM/osm/devops/descriptor-packages/vnfd/ping_vnf/src/ping_vnfd.yaml") as f:
        vnfd = yaml.load(f)
        vnfd_clean, _ = ROclient.remove_envelop("vnfd", vnfd)
        vnfd_clean["_admin"] = {"storage": "/home/atierno/OSM/osm/devops/descriptor-packages/vnfd/ping_vnf"}
        lcm.db.create("vnfd", vnfd_clean)
    with open("/home/atierno/OSM/osm/devops/descriptor-packages/vnfd/pong_vnf/src/pong_vnfd.yaml") as f:
        vnfd = yaml.load(f)
        vnfd_clean, _ = ROclient.remove_envelop("vnfd", vnfd)
        vnfd_clean["_admin"] = {"storage": "/home/atierno/OSM/osm/devops/descriptor-packages/vnfd/pong_vnf"}
        lcm.db.create("vnfd", vnfd_clean)
    with open("/home/atierno/OSM/osm/devops/descriptor-packages/nsd/ping_pong_ns/src/ping_pong_nsd.yaml") as f:
        nsd = yaml.load(f)
        nsd_clean, _ = ROclient.remove_envelop("nsd", nsd)
        nsd_clean["_admin"] = {"storage": "/home/atierno/OSM/osm/devops/descriptor-packages/nsd/ping_pong_ns"}
        lcm.db.create("nsd", nsd_clean)

    ns_request = {
        "id": "ns1",
        "nsr_id": "ns1",
        "name": "pingpongOne",
        "vim": RO_VIM,
        "nsd_id": nsd_clean["id"],  # nsd_ping_pong
    }
    lcm.db.create("ns_request", ns_request)
    ns_request = {
        "id": "ns2",
        "nsr_id": "ns2",
        "name": "pingpongTwo",
        "vim": RO_VIM,
        "nsd_id": nsd_clean["id"],  # nsd_ping_pong
    }
    lcm.db.create("ns_request", ns_request)

    lcm.start()



