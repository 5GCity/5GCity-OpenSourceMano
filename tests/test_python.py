import osm_im.vnfd as vnfd_catalog
from pyangbind.lib.serialise import pybindJSONDecoder
import unittest
import yaml

VNFD_YAML = """
vnfd-catalog:
    vnfd:
    -   id: cirros_vnfd
        name: cirros_vnf
        short-name: cirros_vnf
        description: Simple VNF example with a cirros
        vendor: OSM
        version: '1.0'

        # Place the logo as png in icons directory and provide the name here
        logo: cirros-64.png

        # Management interface
        mgmt-interface:
            cp: eth0

        # Atleast one VDU need to be specified
        vdu:
        -   id: cirros_vnfd-VM
            name: cirros_vnfd-VM
            description: cirros_vnfd-VM
            count: 1

            # Flavour of the VM to be instantiated for the VDU
            # flavor below can fit into m1.micro
            vm-flavor:
                vcpu-count: 1
                memory-mb: 256
                storage-gb: 2

            # Image/checksum or image including the full path
            image: 'cirros034'
            #checksum:

            interface:
            # Specify the external interfaces
            # There can be multiple interfaces defined
            -   name: eth0
                type: EXTERNAL
                virtual-interface:
                    type: VIRTIO
                    bandwidth: '0'
                    vpci: 0000:00:0a.0
                external-connection-point-ref: eth0

        connection-point:
            -   name: eth0
                type: VPORT
"""

class PythonTest(unittest.TestCase):


    def test_python_compatibility(self):
        """A simple test to verify Python compatibility.

        This test exercises basic IM interoperability with supported versions
        of Python in order to verify the IM libraries compatibility.

        As of 30 Nov 2017, the IM library fails with Python3. This invokes that
        failing code so that it can be repeatably tested:

        ValueError: '_pybind_generated_by' in __slots__ conflicts with class variable
        """

        try:
            data = yaml.load(VNFD_YAML)

            myvnfd = vnfd_catalog.vnfd()
            pybindJSONDecoder.load_ietf_json(data, None, None, obj=myvnfd)
        except ValueError:
            assert False
