from mininet.link import Link
from resources import *
from docker import DockerClient
import logging
import threading
import uuid
import time
import ip_handler as IP


class HeatApiStackInvalidException(Exception):
    """
    Exception thrown when a submitted stack is invalid.
    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class OpenstackCompute(object):
    """
    This class is a datacenter specific compute object that tracks all containers that are running in a datacenter,
    as well as networks and configured ports.
    It has some stack dependet logic and can check if a received stack is valid.

    It also handles start and stop of containers.
    """

    def __init__(self):
        self.dc = None
        self.stacks = dict()
        self.computeUnits = dict()
        self.routers = dict()
        self.flavors = dict()
        self._images = dict()
        self.nets = dict()
        self.ports = dict()
        self.compute_nets = dict()
        self.dcli = DockerClient(base_url='unix://var/run/docker.sock')

    @property
    def images(self):
        """
        Updates the known images. Asks the docker daemon for a list of all known images and returns
        the new dictionary.

        :return: Returns the new image dictionary.
        :rtype: ``dict``
        """
        for image in self.dcli.images.list():
            if len(image.tags) > 0:
                for t in image.tags:
                    t = t.replace(":latest", "")  # only use short tag names for OSM compatibility
                    if t not in self._images:
                        self._images[t] = Image(t)
        return self._images

    def add_stack(self, stack):
        """
        Adds a new stack to the compute node.

        :param stack: Stack dictionary.
        :type stack: :class:`heat.resources.stack`
        """
        if not self.check_stack(stack):
            self.clean_broken_stack(stack)
            raise HeatApiStackInvalidException("Stack did not pass validity checks")
        self.stacks[stack.id] = stack

    def clean_broken_stack(self, stack):
        for port in stack.ports.values():
            if port.id in self.ports:
                del self.ports[port.id]
        for server in stack.servers.values():
            if server.id in self.computeUnits:
                del self.computeUnits[server.id]
        for net in stack.nets.values():
            if net.id in self.nets:
                del self.nets[net.id]

    def check_stack(self, stack):
        """
        Checks all dependencies of all servers, ports and routers and their most important parameters.

        :param stack: A reference of the stack that should be checked.
        :type stack: :class:`heat.resources.stack`
        :return: * *True*: If the stack is completely fine.
         * *False*: Else
        :rtype: ``bool``
        """
        everything_ok = True
        for server in stack.servers.values():
            for port_name in server.port_names:
                if port_name not in stack.ports:
                    logging.warning("Server %s of stack %s has a port named %s that is not known." %
                                    (server.name, stack.stack_name, port_name))
                    everything_ok = False
            if server.image is None:
                logging.warning("Server %s holds no image." % (server.name))
                everything_ok = False
            if server.command is None:
                logging.warning("Server %s holds no command." % (server.name))
                everything_ok = False
        for port in stack.ports.values():
            if port.net_name not in stack.nets:
                logging.warning("Port %s of stack %s has a network named %s that is not known." %
                                (port.name, stack.stack_name, port.net_name))
                everything_ok = False
            if port.intf_name is None:
                logging.warning("Port %s has no interface name." % (port.name))
                everything_ok = False
            if port.ip_address is None:
                logging.warning("Port %s has no IP address." % (port.name))
                everything_ok = False
        for router in stack.routers.values():
            for subnet_name in router.subnet_names:
                found = False
                for net in stack.nets.values():
                    if net.subnet_name == subnet_name:
                        found = True
                        break
                if not found:
                    logging.warning("Router %s of stack %s has a network named %s that is not known." %
                                    (router.name, stack.stack_name, subnet_name))
                    everything_ok = False
        return everything_ok

    def add_flavor(self, name, cpu, memory, memory_unit, storage, storage_unit):
        """
        Adds a flavor to the stack.

        :param name: Specifies the name of the flavor.
        :type name: ``str``
        :param cpu:
        :type cpu: ``str``
        :param memory:
        :type memory: ``str``
        :param memory_unit:
        :type memory_unit: ``str``
        :param storage:
        :type storage: ``str``
        :param storage_unit:
        :type storage_unit: ``str``
        """
        flavor = InstanceFlavor(name, cpu, memory, memory_unit, storage, storage_unit)
        self.flavors[flavor.name] = flavor
        return flavor

    def deploy_stack(self, stackid):
        """
        Deploys the stack and starts the emulation.

        :param stackid: An UUID str of the stack
        :type stackid: ``str``
        :return: * *False*: If the Datacenter is None
            * *True*: Else
        :rtype: ``bool``
        """
        if self.dc is None:
            return False

        stack = self.stacks[stackid]
        self.update_compute_dicts(stack)

        # Create the networks first
        for server in stack.servers.values():
            self._start_compute(server)
        return True

    def delete_stack(self, stack_id):
        """
        Delete a stack and all its components.

        :param stack_id: An UUID str of the stack
        :type stack_id: ``str``
        :return: * *False*: If the Datacenter is None
            * *True*: Else
        :rtype: ``bool``
        """
        if self.dc is None:
            return False

        # Stop all servers and their links of this stack
        for server in self.stacks[stack_id].servers.values():
            self.stop_compute(server)
            self.delete_server(server)
        for net in self.stacks[stack_id].nets.values():
            self.delete_network(net.id)
        for port in self.stacks[stack_id].ports.values():
            self.delete_port(port.id)

        del self.stacks[stack_id]
        return True

    def update_stack(self, old_stack_id, new_stack):
        """
        Determines differences within the old and the new stack and deletes, create or changes only parts that
        differ between the two stacks.

        :param old_stack_id: The ID of the old stack.
        :type old_stack_id: ``str``
        :param new_stack: A reference of the new stack.
        :type new_stack: :class:`heat.resources.stack`
        :return: * *True*: if the old stack could be updated to the new stack without any error.
            * *False*: else
        :rtype: ``bool``
        """
        if old_stack_id not in self.stacks:
            return False
        old_stack = self.stacks[old_stack_id]

        # Update Stack IDs
        for server in old_stack.servers.values():
            if server.name in new_stack.servers:
                new_stack.servers[server.name].id = server.id
        for net in old_stack.nets.values():
            if net.name in new_stack.nets:
                new_stack.nets[net.name].id = net.id
                for subnet in new_stack.nets.values():
                    if subnet.subnet_name == net.subnet_name:
                        subnet.subnet_id = net.subnet_id
                        break
        for port in old_stack.ports.values():
            if port.name in new_stack.ports:
                new_stack.ports[port.name].id = port.id
        for router in old_stack.routers.values():
            if router.name in new_stack.routers:
                new_stack.routers[router.name].id = router.id

        # Update the compute dicts to now contain the new_stack components
        self.update_compute_dicts(new_stack)

        self.update_ip_addresses(old_stack, new_stack)

        # Update all interface names - after each port has the correct UUID!!
        for port in new_stack.ports.values():
            port.create_intf_name()

        if not self.check_stack(new_stack):
            return False

        # Remove unnecessary networks
        for net in old_stack.nets.values():
            if not net.name in new_stack.nets:
                self.delete_network(net.id)

        # Remove all unnecessary servers
        for server in old_stack.servers.values():
            if server.name in new_stack.servers:
                if not server.compare_attributes(new_stack.servers[server.name]):
                    self.stop_compute(server)
                else:
                    # Delete unused and changed links
                    for port_name in server.port_names:
                        if port_name in old_stack.ports and port_name in new_stack.ports:
                            if not old_stack.ports.get(port_name) == new_stack.ports.get(port_name):
                                my_links = self.dc.net.links
                                for link in my_links:
                                    if str(link.intf1) == old_stack.ports[port_name].intf_name and \
                                                    str(link.intf1.ip) == \
                                                    old_stack.ports[port_name].ip_address.split('/')[0]:
                                        self._remove_link(server.name, link)

                                        # Add changed link
                                        self._add_link(server.name,
                                                       new_stack.ports[port_name].ip_address,
                                                       new_stack.ports[port_name].intf_name,
                                                       new_stack.ports[port_name].net_name)
                                        break
                        else:
                            my_links = self.dc.net.links
                            for link in my_links:
                                if str(link.intf1) == old_stack.ports[port_name].intf_name and \
                                   str(link.intf1.ip) == old_stack.ports[port_name].ip_address.split('/')[0]:
                                    self._remove_link(server.name, link)
                                    break

                    # Create new links
                    for port_name in new_stack.servers[server.name].port_names:
                        if port_name not in server.port_names:
                            self._add_link(server.name,
                                           new_stack.ports[port_name].ip_address,
                                           new_stack.ports[port_name].intf_name,
                                           new_stack.ports[port_name].net_name)
            else:
                self.stop_compute(server)

        # Start all new servers
        for server in new_stack.servers.values():
            if server.name not in self.dc.containers:
                self._start_compute(server)
            else:
                server.emulator_compute = self.dc.containers.get(server.name)

        del self.stacks[old_stack_id]
        self.stacks[new_stack.id] = new_stack
        return True

    def update_ip_addresses(self, old_stack, new_stack):
        """
        Updates the subnet and the port IP addresses - which should always be in this order!

        :param old_stack: The currently running stack
        :type old_stack: :class:`heat.resources.stack`
        :param new_stack: The new created stack
        :type new_stack: :class:`heat.resources.stack`
        """
        self.update_subnet_cidr(old_stack, new_stack)
        self.update_port_addresses(old_stack, new_stack)

    def update_port_addresses(self, old_stack, new_stack):
        """
        Updates the port IP addresses. First resets all issued addresses. Then get all IP addresses from the old
        stack and sets them to the same ports in the new stack. Finally all new or changed instances will get new
        IP addresses.

        :param old_stack: The currently running stack
        :type old_stack: :class:`heat.resources.stack`
        :param new_stack: The new created stack
        :type new_stack: :class:`heat.resources.stack`
        """
        for net in new_stack.nets.values():
            net.reset_issued_ip_addresses()

        for old_port in old_stack.ports.values():
            for port in new_stack.ports.values():
                if port.compare_attributes(old_port):
                    for net in new_stack.nets.values():
                        if net.name == port.net_name:
                            if net.assign_ip_address(old_port.ip_address, port.name):
                                port.ip_address = old_port.ip_address
                                port.mac_address = old_port.mac_address
                            else:
                                port.ip_address = net.get_new_ip_address(port.name)

        for port in new_stack.ports.values():
            for net in new_stack.nets.values():
                if port.net_name == net.name and not net.is_my_ip(port.ip_address, port.name):
                    port.ip_address = net.get_new_ip_address(port.name)

    def update_subnet_cidr(self, old_stack, new_stack):
        """
        Updates the subnet IP addresses. If the new stack contains subnets from the old stack it will take those
        IP addresses. Otherwise it will create new IP addresses for the subnet.

        :param old_stack: The currently running stack
        :type old_stack: :class:`heat.resources.stack`
        :param new_stack: The new created stack
        :type new_stack: :class:`heat.resources.stack`
        """
        for old_subnet in old_stack.nets.values():
            IP.free_cidr(old_subnet.get_cidr(), old_subnet.subnet_id)

        for subnet in new_stack.nets.values():
            subnet.clear_cidr()
            for old_subnet in old_stack.nets.values():
                if subnet.subnet_name == old_subnet.subnet_name:
                    if IP.assign_cidr(old_subnet.get_cidr(), subnet.subnet_id):
                        subnet.set_cidr(old_subnet.get_cidr())

        for subnet in new_stack.nets.values():
            if IP.is_cidr_issued(subnet.get_cidr()):
                continue

            cird = IP.get_new_cidr(subnet.subnet_id)
            subnet.set_cidr(cird)
        return

    def update_compute_dicts(self, stack):
        """
        Update and add all stack components tho the compute dictionaries.

        :param stack: A stack reference, to get all required components.
        :type stack: :class:`heat.resources.stack`
        """
        for server in stack.servers.values():
            self.computeUnits[server.id] = server
            if isinstance(server.flavor, dict):
                self.add_flavor(server.flavor['flavorName'],
                                server.flavor['vcpu'],
                                server.flavor['ram'], 'MB',
                                server.flavor['storage'], 'GB')
                server.flavor = server.flavor['flavorName']
        for router in stack.routers.values():
            self.routers[router.id] = router
        for net in stack.nets.values():
            self.nets[net.id] = net
        for port in stack.ports.values():
            self.ports[port.id] = port

    def _start_compute(self, server):
        """
        Starts a new compute object (docker container) inside the emulator.
        Should only be called by stack modifications and not directly.

        :param server: Specifies the compute resource.
        :type server: :class:`heat.resources.server`
        """
        logging.debug("Starting new compute resources %s" % server.name)
        network = list()

        for port_name in server.port_names:
            network_dict = dict()
            port = self.find_port_by_name_or_id(port_name)
            if port is not None:
                network_dict['id'] = port.intf_name
                network_dict['ip'] = port.ip_address
                network_dict[network_dict['id']] = self.find_network_by_name_or_id(port.net_name).name
                network.append(network_dict)
        self.compute_nets[server.name] = network
        c = self.dc.startCompute(server.name, image=server.image, command=server.command,
                                 network=network, flavor_name=server.flavor)
        server.emulator_compute = c

        for intf in c.intfs.values():
            for port_name in server.port_names:
                port = self.find_port_by_name_or_id(port_name)
                if port is not None:
                    if intf.name == port.intf_name:
                        # wait up to one second for the intf to come up
                        self.timeout_sleep(intf.isUp, 1)
                        if port.mac_address is not None:
                            intf.setMAC(port.mac_address)
                        else:
                            port.mac_address = intf.MAC()

        # Start the real emulator command now as specified in the dockerfile
        # ENV SON_EMU_CMD
        config = c.dcinfo.get("Config", dict())
        env = config.get("Env", list())
        for env_var in env:
            if "SON_EMU_CMD=" in env_var:
                cmd = str(env_var.split("=")[1])
                server.son_emu_command = cmd
                # execute command in new thread to ensure that GK is not blocked by VNF
                t = threading.Thread(target=c.cmdPrint, args=(cmd,))
                t.daemon = True
                t.start()

    def stop_compute(self, server):
        """
        Determines which links should be removed before removing the server itself.

        :param server: The server that should be removed
        :type server: ``heat.resources.server``
        """
        logging.debug("Stopping container %s with full name %s" % (server.name, server.full_name))
        link_names = list()
        for port_name in server.port_names:
            link_names.append(self.find_port_by_name_or_id(port_name).intf_name)
        my_links = self.dc.net.links
        for link in my_links:
            if str(link.intf1) in link_names:
                # Remove all self created links that connect the server to the main switch
                self._remove_link(server.name, link)

        # Stop the server and the remaining connection to the datacenter switch
        self.dc.stopCompute(server.name)
        # Only now delete all its ports and the server itself
        for port_name in server.port_names:
            self.delete_port(port_name)
        self.delete_server(server)

    def find_server_by_name_or_id(self, name_or_id):
        """
        Tries to find the server by ID and if this does not succeed then tries to find it via name.

        :param name_or_id: UUID or name of the server.
        :type name_or_id: ``str``
        :return: Returns the server reference if it was found or None
        :rtype: :class:`heat.resources.server`
        """
        if name_or_id in self.computeUnits:
            return self.computeUnits[name_or_id]

        for server in self.computeUnits.values():
            if server.name == name_or_id or server.template_name == name_or_id or server.full_name == name_or_id:
                return server
        return None

    def create_server(self, name, stack_operation=False):
        """
        Creates a server with the specified name. Raises an exception when a server with the given name already
        exists!

        :param name: Name of the new server.
        :type name: ``str``
        :param stack_operation: Allows the heat parser to create modules without adapting the current emulation.
        :type stack_operation: ``bool``
        :return: Returns the created server.
        :rtype: :class:`heat.resources.server`
        """
        if self.find_server_by_name_or_id(name) is not None and not stack_operation:
            raise Exception("Server with name %s already exists." % name)
        server = Server(name)
        server.id = str(uuid.uuid4())
        if not stack_operation:
            self.computeUnits[server.id] = server
        return server

    def delete_server(self, server):
        """
        Deletes the given server from the stack dictionary and the computeUnits dictionary.

        :param server: Reference of the server that should be deleted.
        :type server: :class:`heat.resources.server`
        :return: * *False*: If the server name is not in the correct format ('datacentername_stackname_servername') \
                or when no stack with the correct stackname was found.
            * *True*: Else
        :rtype: ``bool``
        """
        if server is None:
            return False
        name_parts = server.name.split('_')
        if len(name_parts) < 3:
            return False

        for stack in self.stacks.values():
            if stack.stack_name == name_parts[1]:
                stack.servers.pop(server.id, None)
        if self.computeUnits.pop(server.id, None) is None:
            return False
        return True

    def find_network_by_name_or_id(self, name_or_id):
        """
        Tries to find the network by ID and if this does not succeed then tries to find it via name.

        :param name_or_id: UUID or name of the network.
        :type name_or_id: ``str``
        :return: Returns the network reference if it was found or None
        :rtype: :class:`heat.resources.net`
        """
        if name_or_id in self.nets:
            return self.nets[name_or_id]
        for net in self.nets.values():
            if net.name == name_or_id:
                return net

        return None

    def create_network(self, name, stack_operation=False):
        """
        Creates a new network with the given name. Raises an exception when a network with the given name already
        exists!

        :param name: Name of the new network.
        :type name: ``str``
        :param stack_operation: Allows the heat parser to create modules without adapting the current emulation.
        :type stack_operation: ``bool``
        :return: :class:`heat.resources.net`
        """
        logging.debug("Creating network with name %s" % name)
        if self.find_network_by_name_or_id(name) is not None and not stack_operation:
            logging.warning("Creating network with name %s failed, as it already exists" % name)
            raise Exception("Network with name %s already exists." % name)
        network = Net(name)
        network.id = str(uuid.uuid4())
        if not stack_operation:
            self.nets[network.id] = network
        return network

    def delete_network(self, name_or_id):
        """
        Deletes the given network.

        :param name_or_id: Name or UUID of the network.
        :type name_or_id: ``str``
        """
        net = self.find_network_by_name_or_id(name_or_id)
        if net is None:
            raise Exception("Network with name or id %s does not exists." % name_or_id)

        for stack in self.stacks.values():
            stack.nets.pop(net.name, None)

        self.nets.pop(net.id, None)

    def create_port(self, name, stack_operation=False):
        """
        Creates a new port with the given name. Raises an exception when a port with the given name already
        exists!

        :param name: Name of the new port.
        :type name: ``str``
        :param stack_operation: Allows the heat parser to create modules without adapting the current emulation.
        :type stack_operation: ``bool``
        :return: Returns the created port.
        :rtype: :class:`heat.resources.port`
        """
        port = self.find_port_by_name_or_id(name)
        if port is not None and not stack_operation:
            logging.warning("Creating port with name %s failed, as it already exists" % name)
            raise Exception("Port with name %s already exists." % name)
        logging.debug("Creating port with name %s" % name)
        port = Port(name)
        if not stack_operation:
            self.ports[port.id] = port
            port.create_intf_name()
        return port

    def find_port_by_name_or_id(self, name_or_id):
        """
        Tries to find the port by ID and if this does not succeed then tries to find it via name.

        :param name_or_id: UUID or name of the network.
        :type name_or_id: ``str``
        :return: Returns the port reference if it was found or None
        :rtype: :class:`heat.resources.port`
        """
        if name_or_id in self.ports:
            return self.ports[name_or_id]
        for port in self.ports.values():
            if port.name == name_or_id or port.template_name == name_or_id:
                return port

        return None

    def delete_port(self, name_or_id):
        """
        Deletes the given port. Raises an exception when the port was not found!

        :param name_or_id:  UUID or name of the port.
        :type name_or_id: ``str``
        """
        port = self.find_port_by_name_or_id(name_or_id)
        if port is None:
            raise Exception("Port with name or id %s does not exists." % name_or_id)

        my_links = self.dc.net.links
        for link in my_links:
            if str(link.intf1) == port.intf_name and \
                            str(link.intf1.ip) == port.ip_address.split('/')[0]:
                self._remove_link(link.intf1.node.name, link)
                break

        self.ports.pop(port.id, None)
        for stack in self.stacks.values():
            stack.ports.pop(port.name, None)

    def _add_link(self, node_name, ip_address, link_name, net_name):
        """
        Adds a new link between datacenter switch and the node with the given name.

        :param node_name: Name of the required node.
        :type node_name: ``str``
        :param ip_address: IP-Address of the node.
        :type ip_address: ``str``
        :param link_name: Link name.
        :type link_name: ``str``
        :param net_name: Network name.
        :type net_name: ``str``
        """
        node = self.dc.net.get(node_name)
        params = {'params1': {'ip': ip_address,
                              'id': link_name,
                              link_name: net_name},
                  'intfName1': link_name,
                  'cls': Link}
        link = self.dc.net.addLink(node, self.dc.switch, **params)
        OpenstackCompute.timeout_sleep(link.intf1.isUp, 1)

    def _remove_link(self, server_name, link):
        """
        Removes a link between server and datacenter switch.

        :param server_name: Specifies the server where the link starts.
        :type server_name: ``str``
        :param link: A reference of the link which should be removed.
        :type link: :class:`mininet.link`
        """
        self.dc.switch.detach(link.intf2)
        del self.dc.switch.intfs[self.dc.switch.ports[link.intf2]]
        del self.dc.switch.ports[link.intf2]
        del self.dc.switch.nameToIntf[link.intf2.name]
        self.dc.net.removeLink(link=link)
        self.dc.net.DCNetwork_graph.remove_edge(server_name, self.dc.switch.name)
        self.dc.net.DCNetwork_graph.remove_edge(self.dc.switch.name, server_name)
        for intf_key in self.dc.net[server_name].intfs.keys():
            if self.dc.net[server_name].intfs[intf_key].link == link:
                self.dc.net[server_name].intfs[intf_key].delete()
                del self.dc.net[server_name].intfs[intf_key]

    @staticmethod
    def timeout_sleep(function, max_sleep):
        """
        This function will execute a function all 0.1 seconds until it successfully returns.
        Will return after `max_sleep` seconds if not successful.

        :param function: The function to execute. Should return true if done.
        :type function: ``function``
        :param max_sleep: Max seconds to sleep. 1 equals 1 second.
        :type max_sleep: ``float``
        """
        current_time = time.time()
        stop_time = current_time + max_sleep
        while not function() and current_time < stop_time:
            current_time = time.time()
            time.sleep(0.1)
