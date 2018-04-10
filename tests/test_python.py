# A simple test to exercise the libraries' functionality
import asyncio
import functools
import os
import sys
import logging
import unittest
import yaml
from n2vc.vnf import N2VC

NSD_YAML = """
nsd:nsd-catalog:
    nsd:
    -   id: multicharmvdu-ns
        name: multicharmvdu-ns
        short-name: multicharmvdu-ns
        description: NS with 2 VNFs multicharmvdu-vnf connected by datanet and mgmtnet VLs
        version: '1.0'
        logo: osm.png
        constituent-vnfd:
        -   vnfd-id-ref: multicharmvdu-vnf
            member-vnf-index: '1'
        -   vnfd-id-ref: multicharmvdu-vnf
            member-vnf-index: '2'
        vld:
        -   id: mgmtnet
            name: mgmtnet
            short-name: mgmtnet
            type: ELAN
            mgmt-network: 'true'
            vim-network-name: mgmt
            vnfd-connection-point-ref:
            -   vnfd-id-ref: multicharmvdu-vnf
                member-vnf-index-ref: '1'
                vnfd-connection-point-ref: vnf-mgmt
            -   vnfd-id-ref: multicharmvdu-vnf
                member-vnf-index-ref: '2'
                vnfd-connection-point-ref: vnf-mgmt
        -   id: datanet
            name: datanet
            short-name: datanet
            type: ELAN
            vnfd-connection-point-ref:
            -   vnfd-id-ref: multicharmvdu-vnf
                member-vnf-index-ref: '1'
                vnfd-connection-point-ref: vnf-data
            -   vnfd-id-ref: multicharmvdu-vnf
                member-vnf-index-ref: '2'
                vnfd-connection-point-ref: vnf-data
"""

VNFD_YAML = """
vnfd:vnfd-catalog:
    vnfd:
    -   id: multicharmvdu-vnf
        name: multicharmvdu-vnf
        short-name: multicharmvdu-vnf
        version: '1.0'
        description: A VNF consisting of 2 VDUs w/charms connected to an internal VL, and one VDU with cloud-init
        logo: osm.png
        connection-point:
        -   id: vnf-mgmt
            name: vnf-mgmt
            short-name: vnf-mgmt
            type: VPORT
        -   id: vnf-data
            name: vnf-data
            short-name: vnf-data
            type: VPORT
        mgmt-interface:
            cp: vnf-mgmt
        internal-vld:
        -   id: internal
            name: internal
            short-name: internal
            type: ELAN
            internal-connection-point:
            -   id-ref: mgmtVM-internal
            -   id-ref: dataVM-internal
        vdu:
        -   id: mgmtVM
            name: mgmtVM
            image: xenial
            count: '1'
            vm-flavor:
                vcpu-count: '1'
                memory-mb: '1024'
                storage-gb: '10'
            interface:
            -   name: mgmtVM-eth0
                position: '1'
                type: EXTERNAL
                virtual-interface:
                    type: VIRTIO
                external-connection-point-ref: vnf-mgmt
            -   name: mgmtVM-eth1
                position: '2'
                type: INTERNAL
                virtual-interface:
                    type: VIRTIO
                internal-connection-point-ref: mgmtVM-internal
            internal-connection-point:
            -   id: mgmtVM-internal
                name: mgmtVM-internal
                short-name: mgmtVM-internal
                type: VPORT
            cloud-init-file: cloud-config.txt
            vdu-configuration:
                juju:
                    charm: simple
                initial-config-primitive:
                -   seq: '1'
                    name: config
                    parameter:
                    -   name: ssh-hostname
                        value: <rw_mgmt_ip>
                    -   name: ssh-username
                        value: ubuntu
                    -   name: ssh-password
                        value: osm4u
                -   seq: '2'
                    name: touch
                    parameter:
                    -   name: filename
                        value: '/home/ubuntu/first-touch-mgmtVM'
                config-primitive:
                -   name: touch
                    parameter:
                    -   name: filename
                        data-type: STRING
                        default-value: '/home/ubuntu/touched'

        -   id: dataVM
            name: dataVM
            image: xenial
            count: '1'
            vm-flavor:
                vcpu-count: '1'
                memory-mb: '1024'
                storage-gb: '10'
            interface:
            -   name: dataVM-eth0
                position: '1'
                type: INTERNAL
                virtual-interface:
                    type: VIRTIO
                internal-connection-point-ref: dataVM-internal
            -   name: dataVM-xe0
                position: '2'
                type: EXTERNAL
                virtual-interface:
                    type: VIRTIO
                external-connection-point-ref: vnf-data
            internal-connection-point:
            -   id: dataVM-internal
                name: dataVM-internal
                short-name: dataVM-internal
                type: VPORT
            vdu-configuration:
                juju:
                    charm: simple
                initial-config-primitive:
                -   seq: '1'
                    name: config
                    parameter:
                    -   name: ssh-hostname
                        value: <rw_mgmt_ip>
                    -   name: ssh-username
                        value: ubuntu
                    -   name: ssh-password
                        value: osm4u
                -   seq: '2'
                    name: touch
                    parameter:
                    -   name: filename
                        value: '/home/ubuntu/first-touch-dataVM'
                config-primitive:
                -   name: touch
                    parameter:
                    -   name: filename
                        data-type: STRING
                        default-value: '/home/ubuntu/touched'
"""

class PythonTest(unittest.TestCase):
    n2vc = None

    def setUp(self):

        self.log = logging.getLogger()
        self.log.level = logging.DEBUG

        self.loop = asyncio.get_event_loop()

        # self.loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(None)

        # Extract parameters from the environment in order to run our test
        vca_host = os.getenv('VCA_HOST', '127.0.0.1')
        vca_port = os.getenv('VCA_PORT', 17070)
        vca_user = os.getenv('VCA_USER', 'admin')
        vca_charms = os.getenv('VCA_CHARMS', None)
        vca_secret = os.getenv('VCA_SECRET', None)
        self.n2vc = N2VC(
            log=self.log,
            server=vca_host,
            port=vca_port,
            user=vca_user,
            secret=vca_secret,
            artifacts=vca_charms,
        )

    def tearDown(self):
        self.loop.run_until_complete(self.n2vc.logout())

    def get_descriptor(self, descriptor):
        desc = None
        try:
            tmp = yaml.load(descriptor)

            # Remove the envelope
            root = list(tmp.keys())[0]
            if root == "nsd:nsd-catalog":
                desc = tmp['nsd:nsd-catalog']['nsd'][0]
            elif root == "vnfd:vnfd-catalog":
                desc = tmp['vnfd:vnfd-catalog']['vnfd'][0]
        except ValueError:
            assert False
        return desc

    def n2vc_callback(self, model_name, application_name, workload_status, task=None):
        """We pass the vnfd when setting up the callback, so expect it to be
        returned as a tuple."""
        if workload_status and not task:
            self.log.debug("Callback: workload status \"{}\"".format(workload_status))

            if workload_status in ["blocked"]:
                task = asyncio.ensure_future(
                    self.n2vc.ExecutePrimitive(
                        model_name,
                        application_name,
                        "config",
                        None,
                        params={
                            'ssh-hostname': '10.195.8.78',
                            'ssh-username': 'ubuntu',
                            'ssh-password': 'ubuntu'
                        }
                    )
                )
                task.add_done_callback(functools.partial(self.n2vc_callback, None, None, None))
                pass
            elif workload_status in ["active"]:
                self.log.debug("Removing charm")
                task = asyncio.ensure_future(
                    self.n2vc.RemoveCharms(model_name, application_name, self.n2vc_callback)
                )
                task.add_done_callback(functools.partial(self.n2vc_callback, None, None, None))

    def test_deploy_application(self):
        stream_handler = logging.StreamHandler(sys.stdout)
        self.log.addHandler(stream_handler)
        try:
            self.log.info("Log handler installed")
            nsd = self.get_descriptor(NSD_YAML)
            vnfd = self.get_descriptor(VNFD_YAML)

            if nsd and vnfd:

                vca_charms = os.getenv('VCA_CHARMS', None)

                params = {}
                vnf_index = 0

                def deploy():
                    """An inner function to do the deployment of a charm from
                    either a vdu or vnf.
                    """
                    charm_dir = "{}/{}".format(vca_charms, charm)

                    # Setting this to an IP that will fail the initial config.
                    # This will be detected in the callback, which will execute
                    # the "config" primitive with the right IP address.
                    params['rw_mgmt_ip'] = '10.195.8.78'

                    # self.loop.run_until_complete(n.CreateNetworkService(nsd))
                    ns_name = "default"

                    vnf_name = self.n2vc.FormatApplicationName(
                        ns_name,
                        vnfd['name'],
                        str(vnf_index),
                    )

                    self.loop.run_until_complete(
                        self.n2vc.DeployCharms(
                            ns_name,
                            vnf_name,
                            vnfd,
                            charm_dir,
                            params,
                            {},
                            self.n2vc_callback
                        )
                    )

                # Check if the VDUs in this VNF have a charm
                for vdu in vnfd['vdu']:
                    vdu_config = vdu.get('vdu-configuration')
                    if vdu_config:
                        juju = vdu_config['juju']
                        self.assertIsNotNone(juju)

                        charm = juju['charm']
                        self.assertIsNotNone(charm)

                        params['initial-config-primitive'] = vdu_config['initial-config-primitive']

                        deploy()
                        vnf_index += 1

                # Check if this VNF has a charm
                vnf_config = vnfd.get("vnf-configuration")
                if vnf_config:
                    juju = vnf_config['juju']
                    self.assertIsNotNone(juju)

                    charm = juju['charm']
                    self.assertIsNotNone(charm)

                    params['initial-config-primitive'] = vnf_config['initial-config-primitive']

                    deploy()
                    vnf_index += 1

                self.loop.run_forever()

                # self.loop.run_until_complete(n.GetMetrics(vnfd, nsd=nsd))

                # Test actions
                #  ExecutePrimitive(self, nsd, vnfd, vnf_member_index, primitive, callback, *callback_args, **params):

                # self.loop.run_until_complete(n.DestroyNetworkService(nsd))

                # self.loop.run_until_complete(self.n2vc.logout())
        finally:
            self.log.removeHandler(stream_handler)
