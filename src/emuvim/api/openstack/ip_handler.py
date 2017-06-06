from resources.net import Net
import threading

lock = threading.Lock()

__issued_ips = dict()
__default_subnet_size = 256
__default_subnet_bitmask = 24
__first_ip = Net.ip_2_int('10.0.0.0')
__last_ip = Net.ip_2_int('10.255.255.255')
__current_ip = __first_ip


def get_new_cidr(uuid):
    """
    Calculates a unused cidr for a subnet.

    :param uuid: The UUID of the subnet - Thus it can store which subnet gets which CIDR
    :type uuid: ``str``
    :return: Returns None if all available CIDR are used. Otherwise returns a valid CIDR.
    :rtype: ``str``
    """
    global lock
    lock.acquire()

    global __current_ip
    while __first_ip <= __current_ip < __last_ip and __current_ip in __issued_ips:
        __current_ip += __default_subnet_size

    if __current_ip >= __last_ip or __current_ip < __first_ip or __current_ip in __issued_ips:
        return None

    __issued_ips[__current_ip] = uuid
    lock.release()

    return Net.int_2_ip(__current_ip) + '/' + str(__default_subnet_bitmask)


def free_cidr(cidr, uuid):
    """
    Frees a issued CIDR thus it can be reused.

    :param cidr: The currently used CIDR.
    :type cidr: ``str``
    :param uuid: The UUID of the Subnet, which uses this CIDR.
    :type uuid: ``str``
    :return: Returns False if the CIDR is None or the UUID did not correspond tho the used CIDR. Else it returns True.
    :rtype: ``bool``
    """
    if cidr is None:
        return False

    global __current_ip
    int_ip = Net.cidr_2_int(cidr)

    global lock
    lock.acquire()

    if int_ip in __issued_ips and __issued_ips[int_ip] == uuid:
        del __issued_ips[int_ip]
        if int_ip < __current_ip:
            __current_ip = int_ip
        lock.release()
        return True
    lock.release()
    return False


def is_cidr_issued(cidr):
    """
    Returns True if the CIDR is used.

    :param cidr: The requested CIDR.
    :type cidr: ``str``
    :return: Returns True if the CIDR is used, else False.
    :rtype: ``bool``
    """
    if cidr is None:
        return False

    int_ip = Net.cidr_2_int(cidr)

    if int_ip in __issued_ips:
        return True
    return False


def is_my_cidr(cidr, uuid):
    """
    Checks if the UUID and the used CIDR are related.

    :param cidr: The issued CIDR.
    :type cidr: ``str``
    :param uuid: The Subnet UUID.
    :type uuid: ``str``
    :return: Returns False if the CIDR is None or if the CIDR is not issued. Else returns True.
    :rtype: ``bool``
    """
    if cidr is None:
        return False

    int_ip = Net.cidr_2_int(cidr)

    if not int_ip in __issued_ips:
        return False

    if __issued_ips[int_ip] == uuid:
        return True
    return False


def assign_cidr(cidr, uuid):
    """
    Allows a subnet to request a specific CIDR.

    :param cidr: The requested CIDR.
    :type cidr: ``str``
    :param uuid: The Subnet UUID.
    :type uuid: ``str``
    :return: Returns False if the CIDR is None or if the CIDR is already issued. Returns True if the CIDR could be
     assigned to the UUID.
    """
    if cidr is None:
        return False

    int_ip = Net.cidr_2_int(cidr)

    if int_ip in __issued_ips:
        return False

    global lock
    lock.acquire()
    __issued_ips[int_ip] = uuid
    lock.release()
    return True
