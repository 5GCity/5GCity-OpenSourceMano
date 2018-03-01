# A simple test to exercise the libraries' functionality
import asyncio
import functools
import os
import sys
import logging
import osm_im.vnfd as vnfd_catalog
import osm_im.nsd as nsd_catalog
from pyangbind.lib.serialise import pybindJSONDecoder
import unittest
import yaml
from n2vc.vnf import N2VC

NSD_YAML = """
nsd-catalog:
    nsd:
     -  id: rift_ping_pong_ns
        logo: rift_logo.png
        name: ping_pong_ns
        short-name: ping_pong_ns
        vendor: RIFT.io
        version: '1.1'
        description: RIFT.io sample ping pong network service
        constituent-vnfd:
        -   member-vnf-index: '1'
            vnfd-id-ref: rift_ping_vnf
        -   member-vnf-index: '2'
            vnfd-id-ref: rift_pong_vnf
        initial-service-primitive:
        -   name: start traffic
            parameter:
            -   name: port
                value: 5555
            -   name: ssh-username
                value: fedora
            -   name: ssh-password
                value: fedora
            seq: '1'
            user-defined-script: start_traffic.py
        input-parameter-xpath:
        -   xpath: /nsd:nsd-catalog/nsd:nsd/nsd:vendor
        ip-profiles:
        -   description: Inter VNF Link
            ip-profile-params:
                gateway-address: 31.31.31.210
                ip-version: ipv4
                subnet-address: 31.31.31.0/24
                dhcp-params:
                  count: 200
                  start-address: 31.31.31.2
            name: InterVNFLink
        placement-groups:
        -   member-vnfd:
            -   member-vnf-index-ref: '1'
                vnfd-id-ref: rift_ping_vnf
            -   member-vnf-index-ref: '2'
                vnfd-id-ref: rift_pong_vnf
            name: Orcus
            requirement: Place this VM on the Kuiper belt object Orcus
            strategy: COLOCATION
        -   member-vnfd:
            -   member-vnf-index-ref: '1'
                vnfd-id-ref: rift_ping_vnf
            -   member-vnf-index-ref: '2'
                vnfd-id-ref: rift_pong_vnf
            name: Quaoar
            requirement: Place this VM on the Kuiper belt object Quaoar
            strategy: COLOCATION
        vld:
        -   id: mgmt_vl
            description: Management VL
            name: mgmt_vl
            short-name: mgmt_vl
            vim-network-name: mgmt
            type: ELAN
            vendor: RIFT.io
            version: '1.0'
            mgmt-network: 'true'
            vnfd-connection-point-ref:
            -   member-vnf-index-ref: '1'
                vnfd-connection-point-ref: ping_vnfd/cp0
                vnfd-id-ref: rift_ping_vnf
            -   member-vnf-index-ref: '2'
                vnfd-connection-point-ref: pong_vnfd/cp0
                vnfd-id-ref: rift_pong_vnf
        -   id: ping_pong_vl1
            description: Data VL
            ip-profile-ref: InterVNFLink
            name: data_vl
            short-name: data_vl
            type: ELAN
            vendor: RIFT.io
            version: '1.0'
            vnfd-connection-point-ref:
            -   member-vnf-index-ref: '1'
                vnfd-connection-point-ref: ping_vnfd/cp1
                vnfd-id-ref: rift_ping_vnf
            -   member-vnf-index-ref: '2'
                vnfd-connection-point-ref: pong_vnfd/cp1
                vnfd-id-ref: rift_pong_vnf
"""

VNFD_VCA_YAML = """
vnfd-catalog:
    vnfd:
     -  id: rift_ping_vnf
        name: ping_vnf
        short-name: ping_vnf
        logo: rift_logo.png
        vendor: RIFT.io
        version: '1.1'
        description: This is an example RIFT.ware VNF
        connection-point:
        -   name: ping_vnfd/cp0
            type: VPORT
        -   name: ping_vnfd/cp1
            type: VPORT
        http-endpoint:
        -   path: api/v1/ping/stats
            port: '18888'
        mgmt-interface:
            dashboard-params:
                path: api/v1/ping/stats
                port: '18888'
            port: '18888'
            cp: ping_vnfd/cp0
        placement-groups:
        -   member-vdus:
            -   member-vdu-ref: iovdu_0
            name: Eris
            requirement: Place this VM on the Kuiper belt object Eris
            strategy: COLOCATION
        vdu:
        -   cloud-init-file: ping_cloud_init.cfg
            count: '1'
            interface:
            -   name: eth0
                position: 0
                type: EXTERNAL
                virtual-interface:
                    type: VIRTIO
                external-connection-point-ref: ping_vnfd/cp0
            -   name: eth1
                position: 1
                type: EXTERNAL
                virtual-interface:
                    type: VIRTIO
                external-connection-point-ref: ping_vnfd/cp1
            id: iovdu_0
            image: Fedora-x86_64-20-20131211.1-sda-ping.qcow2
            name: iovdu_0
            vm-flavor:
                memory-mb: '512'
                storage-gb: '4'
                vcpu-count: '1'
        vnf-configuration:
            config-primitive:
            -   name: start
            -   name: stop
            -   name: restart
            -   name: config
                parameter:
                -   data-type: STRING
                    default-value: <rw_mgmt_ip>
                    name: ssh-hostname
                -   data-type: STRING
                    default-value: fedora
                    name: ssh-username
                -   data-type: STRING
                    default-value: fedora
                    name: ssh-password
                -   data-type: STRING
                    name: ssh-private-key
                -   data-type: STRING
                    default-value: ping
                    name: mode
                    read-only: 'true'
            -   name: set-server
                parameter:
                -   data-type: STRING
                    name: server-ip
                -   data-type: INTEGER
                    name: server-port
            -   name: set-rate
                parameter:
                -   data-type: INTEGER
                    default-value: '5'
                    name: rate
            -   name: start-traffic
            -   name: stop-traffic
            initial-config-primitive:
            -   name: config
                parameter:
                -   name: ssh-hostname
                    value: <rw_mgmt_ip>
                -   name: ssh-username
                    value: fedora
                -   name: ssh-password
                    value: fedora
                -   name: mode
                    value: ping
                seq: '1'
            -   name: start
                seq: '2'
            juju:
                charm: pingpong
"""

NSD_DICT = {'name': 'ping_pong_ns', 'short-name': 'ping_pong_ns', 'ip-profiles': [{'ip-profile-params': {'ip-version': 'ipv4', 'dhcp-params': {'count': 200, 'start-address': '31.31.31.2'}, 'subnet-address': '31.31.31.0/24', 'gateway-address': '31.31.31.210'}, 'description': 'Inter VNF Link', 'name': 'InterVNFLink'}], 'logo': 'rift_logo.png', 'description': 'RIFT.io sample ping pong network service', '_admin': {'storage': {'folder': 'd9bc2e64-dfec-4c36-a8bb-c4667e8d7a53', 'tarfile': 'pkg', 'file': 'ping_pong_ns', 'path': '/app/storage/', 'fs': 'local'}, 'created': 1521127984.6414561, 'modified': 1521127984.6414561, 'projects_write': ['admin'], 'projects_read': ['admin']}, 'placement-groups': [{'member-vnfd': [{'member-vnf-index-ref': '1', 'vnfd-id-ref': 'rift_ping_vnf'}, {'member-vnf-index-ref': '2', 'vnfd-id-ref': 'rift_pong_vnf'}], 'name': 'Orcus', 'strategy': 'COLOCATION', 'requirement': 'Place this VM on the Kuiper belt object Orcus'}, {'member-vnfd': [{'member-vnf-index-ref': '1', 'vnfd-id-ref': 'rift_ping_vnf'}, {'member-vnf-index-ref': '2', 'vnfd-id-ref': 'rift_pong_vnf'}], 'name': 'Quaoar', 'strategy': 'COLOCATION', 'requirement': 'Place this VM on the Kuiper belt object Quaoar'}], 'input-parameter-xpath': [{'xpath': '/nsd:nsd-catalog/nsd:nsd/nsd:vendor'}], 'version': '1.1', 'vld': [{'name': 'mgmt', 'short-name': 'mgmt', 'mgmt-network': 'true', 'vim-network-name': 'mgmt', 'version': '1.0', 'vnfd-connection-point-ref': [{'vnfd-connection-point-ref': 'ping_vnfd/cp0', 'member-vnf-index-ref': '1', 'vnfd-id-ref': 'rift_ping_vnf'}, {'vnfd-connection-point-ref': 'pong_vnfd/cp0', 'member-vnf-index-ref': '2', 'vnfd-id-ref': 'rift_pong_vnf'}], 'description': 'Management VL', 'vendor': 'RIFT.io', 'type': 'ELAN', 'id': 'mgmt'}, {'ip-profile-ref': 'InterVNFLink', 'name': 'data_vl', 'short-name': 'data_vl', 'version': '1.0', 'vnfd-connection-point-ref': [{'vnfd-connection-point-ref': 'ping_vnfd/cp1', 'member-vnf-index-ref': '1', 'vnfd-id-ref': 'rift_ping_vnf'}, {'vnfd-connection-point-ref': 'pong_vnfd/cp1', 'member-vnf-index-ref': '2', 'vnfd-id-ref': 'rift_pong_vnf'}], 'description': 'Data VL', 'vendor': 'RIFT.io', 'type': 'ELAN', 'id': 'ping_pong_vl1'}], 'constituent-vnfd': [{'member-vnf-index': '1', 'vnfd-id-ref': 'rift_ping_vnf'}, {'member-vnf-index': '2', 'vnfd-id-ref': 'rift_pong_vnf'}], '_id': 'd9bc2e64-dfec-4c36-a8bb-c4667e8d7a53', 'vendor': 'RIFT.io', 'id': 'rift_ping_pong_ns', 'initial-service-primitive': [{'parameter': [{'name': 'port', 'value': 5555}, {'name': 'ssh-username', 'value': 'fedora'}, {'name': 'ssh-password', 'value': 'fedora'}], 'name': 'start traffic', 'seq': '1', 'user-defined-script': 'start_traffic.py'}]}


VNFD_PING_DICT = {'name': 'ping_vnf', 'short-name': 'ping_vnf', 'mgmt-interface': {'port': '18888', 'cp': 'ping_vnfd/cp0', 'dashboard-params': {'port': '18888', 'path': 'api/v1/ping/stats'}}, 'description': 'This is an example RIFT.ware VNF', 'connection-point': [{'type': 'VPORT', 'name': 'ping_vnfd/cp0'}, {'type': 'VPORT', 'name': 'ping_vnfd/cp1'}], '_admin': {'storage': {'folder': '9ad8de93-cfcc-4da9-9795-d7dc5fec184e', 'fs': 'local', 'file': 'ping_vnf', 'path': '/app/storage/', 'tarfile': 'pkg'}, 'created': 1521127972.1878572, 'modified': 1521127972.1878572, 'projects_write': ['admin'], 'projects_read': ['admin']}, 'vnf-configuration': {'initial-config-primitive': [{'parameter': [{'name': 'ssh-hostname', 'value': '<rw_mgmt_ip>'}, {'name': 'ssh-username', 'value': 'ubuntu'}, {'name': 'ssh-password', 'value': 'ubuntu'}, {'name': 'mode', 'value': 'ping'}], 'name': 'config', 'seq': '1'}, {'name': 'start', 'seq': '2'}], 'juju': {'charm': 'pingpong'}, 'config-primitive': [{'name': 'start'}, {'name': 'stop'}, {'name': 'restart'}, {'parameter': [{'data-type': 'STRING', 'name': 'ssh-hostname', 'default-value': '<rw_mgmt_ip>'}, {'data-type': 'STRING', 'name': 'ssh-username', 'default-value': 'ubuntu'}, {'data-type': 'STRING', 'name': 'ssh-password', 'default-value': 'ubuntu'}, {'data-type': 'STRING', 'name': 'ssh-private-key'}, {'data-type': 'STRING', 'name': 'mode', 'read-only': 'true', 'default-value': 'ping'}], 'name': 'config'}, {'parameter': [{'data-type': 'STRING', 'name': 'server-ip'}, {'data-type': 'INTEGER', 'name': 'server-port'}], 'name': 'set-server'}, {'parameter': [{'data-type': 'INTEGER', 'name': 'rate', 'default-value': '5'}], 'name': 'set-rate'}, {'name': 'start-traffic'}, {'name': 'stop-traffic'}]}, 'placement-groups': [{'member-vdus': [{'member-vdu-ref': 'iovdu_0'}], 'name': 'Eris', 'strategy': 'COLOCATION', 'requirement': 'Place this VM on the Kuiper belt object Eris'}], 'http-endpoint': [{'port': '18888', 'path': 'api/v1/ping/stats'}], 'version': '1.1', 'logo': 'rift_logo.png', 'vdu': [{'vm-flavor': {'vcpu-count': '1', 'storage-gb': '20', 'memory-mb': '2048'}, 'count': '1', 'interface': [{'type': 'EXTERNAL', 'name': 'eth0', 'position': 0, 'virtual-interface': {'type': 'VIRTIO'}, 'external-connection-point-ref': 'ping_vnfd/cp0'}, {'type': 'EXTERNAL', 'name': 'eth1', 'position': 1, 'virtual-interface': {'type': 'VIRTIO'}, 'external-connection-point-ref': 'ping_vnfd/cp1'}], 'name': 'iovdu_0', 'image': 'xenial', 'id': 'iovdu_0', 'cloud-init-file': 'ping_cloud_init.cfg'}], '_id': '9ad8de93-cfcc-4da9-9795-d7dc5fec184e', 'vendor': 'RIFT.io', 'id': 'rift_ping_vnf'}

VNFD_PONG_DICT = {'name': 'pong_vnf', 'short-name': 'pong_vnf', 'mgmt-interface': {'port': '18888', 'cp': 'pong_vnfd/cp0', 'dashboard-params': {'port': '18888', 'path': 'api/v1/pong/stats'}}, 'description': 'This is an example RIFT.ware VNF', 'connection-point': [{'type': 'VPORT', 'name': 'pong_vnfd/cp0'}, {'type': 'VPORT', 'name': 'pong_vnfd/cp1'}], '_admin': {'storage': {'folder': '9ad8de93-cfcc-4da9-9795-d7dc5fec184e', 'fs': 'local', 'file': 'pong_vnf', 'path': '/app/storage/', 'tarfile': 'pkg'}, 'created': 1521127972.1878572, 'modified': 1521127972.1878572, 'projects_write': ['admin'], 'projects_read': ['admin']}, 'vnf-configuration': {'initial-config-primitive': [{'parameter': [{'name': 'ssh-hostname', 'value': '<rw_mgmt_ip>'}, {'name': 'ssh-username', 'value': 'ubuntu'}, {'name': 'ssh-password', 'value': 'ubuntu'}, {'name': 'mode', 'value': 'pong'}], 'name': 'config', 'seq': '1'}, {'name': 'start', 'seq': '2'}], 'juju': {'charm': 'pingpong'}, 'config-primitive': [{'name': 'start'}, {'name': 'stop'}, {'name': 'restart'}, {'parameter': [{'data-type': 'STRING', 'name': 'ssh-hostname', 'default-value': '<rw_mgmt_ip>'}, {'data-type': 'STRING', 'name': 'ssh-username', 'default-value': 'ubuntu'}, {'data-type': 'STRING', 'name': 'ssh-password', 'default-value': 'ubuntu'}, {'data-type': 'STRING', 'name': 'ssh-private-key'}, {'data-type': 'STRING', 'name': 'mode', 'read-only': 'true', 'default-value': 'pong'}], 'name': 'config'}, {'parameter': [{'data-type': 'STRING', 'name': 'server-ip'}, {'data-type': 'INTEGER', 'name': 'server-port'}], 'name': 'set-server'}, {'parameter': [{'data-type': 'INTEGER', 'name': 'rate', 'default-value': '5'}], 'name': 'set-rate'}, {'name': 'start-traffic'}, {'name': 'stop-traffic'}]}, 'placement-groups': [{'member-vdus': [{'member-vdu-ref': 'iovdu_0'}], 'name': 'Eris', 'strategy': 'COLOCATION', 'requirement': 'Place this VM on the Kuiper belt object Eris'}], 'http-endpoint': [{'port': '18888', 'path': 'api/v1/pong/stats'}], 'version': '1.1', 'logo': 'rift_logo.png', 'vdu': [{'vm-flavor': {'vcpu-count': '1', 'storage-gb': '20', 'memory-mb': '2048'}, 'count': '1', 'interface': [{'type': 'EXTERNAL', 'name': 'eth0', 'position': 0, 'virtual-interface': {'type': 'VIRTIO'}, 'external-connection-point-ref': 'ping_vnfd/cp0'}, {'type': 'EXTERNAL', 'name': 'eth1', 'position': 1, 'virtual-interface': {'type': 'VIRTIO'}, 'external-connection-point-ref': 'ping_vnfd/cp1'}], 'name': 'iovdu_0', 'image': 'xenial', 'id': 'iovdu_0', 'cloud-init-file': 'pong_cloud_init.cfg'}], '_id': '9ad8de93-cfcc-4da9-9795-d7dc5fec184e', 'vendor': 'RIFT.io', 'id': 'rift_pong_vnf'}


class PythonTest(unittest.TestCase):
    n2vc = None

    def setUp(self):

        self.log = logging.getLogger()
        self.log.level = logging.DEBUG

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)

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

    def get_vnf_descriptor(self, descriptor):
        vnfd = vnfd_catalog.vnfd()
        try:
            data = yaml.load(descriptor)
            pybindJSONDecoder.load_ietf_json(data, None, None, obj=vnfd)
        except ValueError:
            assert False
        return vnfd

    def get_ns_descriptor(self, descriptor):
        nsd = nsd_catalog.nsd()
        try:
            data = yaml.load(descriptor)
            pybindJSONDecoder.load_ietf_json(data, None, None, obj=nsd)
        except ValueError:
            assert False
        return nsd

    # def test_descriptor(self):
    #     """Test loading and parsing a descriptor."""
    #     nsd = self.get_ns_descriptor(NSD_YAML)
    #     vnfd = self.get_vnf_descriptor(VNFD_VCA_YAML)
    #     if vnfd and nsd:
    #         pass

    # def test_yang_to_dict(self):
    #     # Test the conversion of the native object returned by pybind to a dict
    #     # Extract parameters from the environment in order to run our test
    #
    #     nsd = self.get_ns_descriptor(NSD_YAML)
    #     new = yang_to_dict(nsd)
    #     self.assertEqual(NSD_DICT, new)

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
                    self.n2vc.RemoveCharms(model_name, application_name, self.n2vc_callback, model_name, application_name)
                )
                task.add_done_callback(functools.partial(self.n2vc_callback, None, None, None))
        elif task:
            if task.done():
                self.loop.stop()

    def test_deploy_application(self):
        stream_handler = logging.StreamHandler(sys.stdout)
        self.log.addHandler(stream_handler)
        try:
            self.log.info("Log handler installed")
            nsd = NSD_DICT
            vnfd_ping = VNFD_PING_DICT
            vnfd_pong = VNFD_PONG_DICT
            if nsd and vnfd_ping and vnfd_pong:
                vca_charms = os.getenv('VCA_CHARMS', None)

                config = vnfd_ping['vnf-configuration']
                self.assertIsNotNone(config)

                juju = config['juju']
                self.assertIsNotNone(juju)

                charm = juju['charm']
                self.assertIsNotNone(charm)

                charm_dir = "{}/{}".format(vca_charms, charm)
                # n.callback_status = self.callback_status

                # Setting this to an IP that will fail the initial config.
                # This will be detected in the callback, which will execute
                # the "config" primitive with the right IP address.
                params = {
                    'rw_mgmt_ip': '127.0.0.1'
                }

                # self.loop.run_until_complete(n.CreateNetworkService(nsd))
                # task = asyncio.ensure_future(n.DeployCharms(vnfd, nsd=nsd, artifacts=charm_dir))
                # task = asyncio.ensure_future(n.DeployCharms(vnfd, nsd=nsd, artifacts=charm_dir))
                ns_name = "default"

                ping_vnf_name = self.n2vc.FormatApplicationName(ns_name, vnfd_ping['name'])
                pong_vnf_name = self.n2vc.FormatApplicationName(ns_name, vnfd_pong['name'])

                self.loop.run_until_complete(self.n2vc.DeployCharms(ns_name, ping_vnf_name, vnfd_ping, charm_dir, params, {}, self.n2vc_callback))
                self.loop.run_until_complete(self.n2vc.DeployCharms(ns_name, pong_vnf_name, vnfd_pong, charm_dir, params, {}, self.n2vc_callback))
                self.loop.run_forever()

                # self.loop.run_until_complete(n.GetMetrics(vnfd, nsd=nsd))
                # Test actions
                #  ExecutePrimitive(self, nsd, vnfd, vnf_member_index, primitive, callback, *callback_args, **params):

                # self.loop.run_until_complete(n.DestroyNetworkService(nsd))

                # self.loop.run_until_complete(self.n2vc.logout())
        finally:
            self.log.removeHandler(stream_handler)

    # def test_deploy_application(self):
    #
    #     nsd = self.get_ns_descriptor(NSD_YAML)
    #     vnfd = self.get_vnf_descriptor(VNFD_VCA_YAML)
    #     if nsd and vnfd:
    #         # 1) Test that we're parsing the data correctly
    #         for vnfd_yang in vnfd.vnfd_catalog.vnfd.itervalues():
    #             vnfd_rec = vnfd_yang.get()
    #             # Each vnfd may have a charm
    #             # print(vnfd)
    #             config = vnfd_rec.get('vnf-configuration')
    #             self.assertIsNotNone(config)
    #
    #             juju = config.get('juju')
    #             self.assertIsNotNone(juju)
    #
    #             charm = juju.get('charm')
    #             self.assertIsNotNone(charm)
    #
    #         # 2) Exercise the data by deploying the charms
    #
    #         # Extract parameters from the environment in order to run our test
    #         vca_host = os.getenv('VCA_HOST', '127.0.0.1')
    #         vca_port = os.getenv('VCA_PORT', 17070)
    #         vca_user = os.getenv('VCA_USER', 'admin')
    #         vca_charms = os.getenv('VCA_CHARMS', None)
    #         vca_secret = os.getenv('VCA_SECRET', None)
    #         # n = N2VC(
    #         #     server='10.195.8.254',
    #         #     port=17070,
    #         #     user='admin',
    #         #     secret='74e7aa0cc9cb294de3af294bd76b4604'
    #         # )
    #         n = N2VC(
    #             server=vca_host,
    #             port=vca_port,
    #             user=vca_user,
    #             secret=vca_secret,
    #             artifacts=vca_charms,
    #         )
    #
    #         n.callback_status = self.callback_status
    #
    #         self.loop.run_until_complete(n.CreateNetworkService(nsd))
    #         self.loop.run_until_complete(n.DeployCharms(vnfd, nsd=nsd))
    #         # self.loop.run_until_complete(n.GetMetrics(vnfd, nsd=nsd))
    #
    #         # self.loop.run_until_complete(n.RemoveCharms(nsd, vnfd))
    #         self.loop.run_until_complete(n.DestroyNetworkService(nsd))
    #
    #         self.loop.run_until_complete(n.logout())
    #         n = None

    def callback_status(self, nsd, vnfd, workload_status):
        """An example callback.

        This is an example of how a client using N2VC can receive periodic
        updates on the status of a vnfd
        """
        # print(nsd)
        # print(vnfd)
        print("Workload status: {}".format(workload_status))

    def test_deploy_multivdu_application(self):
        """Deploy a multi-vdu vnf that uses multiple charms."""
        pass

    def test_remove_application(self):
        pass

    def test_get_metrics(self):
        pass
