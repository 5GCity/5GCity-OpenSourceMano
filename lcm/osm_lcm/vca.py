#!/usr/bin/python3
# -*- coding: utf-8 -*-

from juju_api import JujuApi
from juju.model import ModelObserver
import logging
import os
import os.path
import re


class VCAMonitor(ModelObserver):
    """Monitor state changes within the Juju Model."""
    context = None

    async def on_change(self, delta, old, new, model):
        """React to changes in the Juju model."""
        status = None
        db_nsr = self.context['db_nsr']
        vnf_index = self.context['vnf_index']

        nsr_lcm = db_nsr["_admin"]["deploy"]
        nsr_id = nsr_lcm["id"]
        application = self.context['application']

        if delta.entity == "unit":
            # We only care about changes to a unit
            if delta.type == "add" and old is None:
                if new and new.application == application:
                    status = "BUILD"
            elif delta.type == "change":
                if new and new.application == application:
                    if new.agent_status == "idle":
                        if new.workload_status in ("active", "blocked"):
                            status = "ACTIVE"

            elif delta.type == "remove" and new is None:
                if new and new.application == application:
                    status = "DELETING"

        if status:
            nsr_lcm["VCA"][vnf_index]['operational-status'] = status

            # TODO: Clean this up, and make it work with deletes (if we need
            # TODO: to update the database post-delete)
            # Figure out if we're finished configuring
            count = len(nsr_lcm["VCA"])
            active = 0
            for vnf_index in nsr_lcm["VCA"]:
                if nsr_lcm["VCA"][vnf_index]['operational-status'] == "ACTIVE":
                    active += 1
            if active == count:
                db_nsr["config-status"] = "done"
            else:
                db_nsr["config-status"] = "configuring {}/{}".format(active, count)

            try:
                self.context['db'].replace(
                    "nsrs",
                    nsr_id,
                    db_nsr
                )

                # self.context['db'].replace(
                #     "nsr_lcm",
                #     {"id": self.context['nsr_lcm']['id']},
                #     self.context['nsr_lcm']
                # )
            except Exception as e:
                # I've seen this happen when we handle a delete, because the
                # db record is gone by the time we've finished deleting
                # the charms.
                print("Error updating database: ", e)

    pass


def GetJujuApi(config):
    # Quiet logging from the websocket library. If you want to see
    # everything sent over the wire, set this to DEBUG.

    ws_logger = logging.getLogger('websockets.protocol')
    ws_logger.setLevel(logging.INFO)

    api = JujuApi(server=config['host'],
                  port=config['port'],
                  user=config['user'],
                  secret=config['secret'],
                  log=ws_logger,
                  model_name='default'
                  )
    return api


def get_vnf_unique_name(nsr_name, vnfr_name, member_vnf_index):
    """Get the unique VNF name.
    Charm names accepts only a to z and non-consecutive - characters."""
    name = "{}-{}-{}".format(nsr_name, vnfr_name, member_vnf_index)
    new_name = ''
    for c in name:
        if c.isdigit():
            c = chr(97 + int(c))
        elif not c.isalpha():
            c = "-"
        new_name += c
    return re.sub('\-+', '-', new_name.lower())


def get_initial_config(initial_config_primitive, mgmt_ip):
    config = {}
    for primitive in initial_config_primitive:
        if primitive['name'] == 'config':
            for parameter in primitive['parameter']:
                param = parameter['name']
                if parameter['value'] == "<rw_mgmt_ip>":
                    config[param] = mgmt_ip
                else:
                    config[param] = parameter['value']
    return config


async def DeployApplication(vcaconfig, db, db_nsr, vnfd,
                            vnf_index, charm_path):
    """
    Deploy a charm.

    Deploy a VNF configuration charm from a local directory.
    :param dict vcaconfig: The VCA portion of the LCM Configuration
    :param object vnfd: The VNF descriptor
    ...
    :param int vnfd_index: The index of the vnf.

    :Example:

    DeployApplication(...)
    """
    nsr_lcm = db_nsr["_admin"]["deploy"]
    nsr_id = db_nsr["_id"]
    vnf_id = vnfd['id']

    if "proxy" in vnfd["vnf-configuration"]["juju"]:
        use_proxy = vnfd["vnf-configuration"]["juju"]["proxy"]
    else:
        # TBD: We need this to handle a full charm
        use_proxy = True

    application = get_vnf_unique_name(
        db_nsr["name"].lower().strip(),
        vnf_id,
        vnf_index,
    )

    api = GetJujuApi(vcaconfig)

    await api.login()
    if api.authenticated:
        charm = os.path.basename(charm_path)

        # Set the INIT state; further operational status updates
        # will be made by the VCAMonitor
        nsr_lcm["VCA"][vnf_index] = {}
        nsr_lcm["VCA"][vnf_index]['operational-status'] = 'INIT'
        nsr_lcm["VCA"][vnf_index]['application'] = application

        db.replace("nsrs", nsr_id, db_nsr)

        model = await api.get_model()
        context = {
            'application': application,
            'vnf_index': vnf_index,
            'db_nsr': db_nsr,
            'db': db,
        }
        mon = VCAMonitor()
        mon.context = context
        model.add_observer(mon)

        await api.deploy_application(charm,
                                     name=application,
                                     path=charm_path,
                                     )

        # Get and apply the initial config primitive
        cfg = get_initial_config(
            vnfd["vnf-configuration"].get(
                "initial-config-primitive"
            ),
            nsr_lcm['nsr_ip'][vnf_index]
        )

        await api.apply_config(cfg, application)

    await api.logout()


async def RemoveApplication(vcaconfig, db, db_nsr, vnf_index):
    """
    Remove an application from the Juju Controller

    Removed the named application and it's charm from the Juju controller.

    :param object loop: The event loop.
    :param str application_name: The unique name of the application.

    :Example:

    RemoveApplication(loop, "ping_vnf")
    RemoveApplication(loop, "pong_vnf")
    """
    nsr_id = db_nsr["_id"]
    nsr_lcm = db_nsr["_admin"]["deploy"]
    application = nsr_lcm["VCA"][vnf_index]['application']

    api = GetJujuApi(vcaconfig)

    await api.login()
    if api.authenticated:
        model = await api.get_model()
        context = {
            'application': application,
            'vnf_index': vnf_index,
            'db_nsr': db_nsr,
            'db': db,
        }

        mon = VCAMonitor()
        mon.context = context
        model.add_observer(mon)

        print("VCA: Removing application {}".format(application))
        await api.remove_application(application)
        nsr_lcm["VCA"][vnf_index]['application'] = None
        db.replace("nsrs", nsr_id, db_nsr)
    await api.logout()
