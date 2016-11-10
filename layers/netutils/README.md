# Overview

This charm provides basic network utilities that can be run from a Juju-deployed
machine.

# Usage

To deploy the charm:
```bash
$ juju deploy cs:~nfv/netutils
```

To run an action:
```bash
$ juju run-action netutils/0 ping destination=google.com
$ juju run-action netutils/0 traceroute destination=google.com
```

To fetch the output of an action:
```bash
$ juju show-action-output 026b3d4c-0bb2-4818-8d24-9855936cdcdf
results:
  output: |
    traceroute to google.com (216.58.198.78), 30 hops max, 60 byte packets
     1  ec2-79-125-0-86.eu-west-1.compute.amazonaws.com (79.125.0.86)  1.431 ms  1.410 ms  1.380 ms
     2  100.64.2.73 (100.64.2.73)  1.647 ms 100.64.2.103 (100.64.2.103)  1.247 ms 100.64.2.121 (100.64.2.121)  1.224 ms
     3  100.64.0.232 (100.64.0.232)  1.296 ms 100.64.0.184 (100.64.0.184)  1.515 ms 100.64.0.234 (100.64.0.234)  1.079 ms
     4  100.64.16.37 (100.64.16.37)  0.377 ms 100.64.16.49 (100.64.16.49)  0.347 ms 100.64.16.1 (100.64.16.1)  0.340 ms
     5  176.32.107.12 (176.32.107.12)  0.739 ms 176.32.107.4 (176.32.107.4)  0.875 ms  0.748 ms
     6  178.236.0.111 (178.236.0.111)  0.650 ms  0.641 ms  0.645 ms
     7  72.14.215.85 (72.14.215.85)  0.544 ms  1.508 ms  1.498 ms
     8  209.85.252.198 (209.85.252.198)  0.680 ms  0.659 ms  0.618 ms
     9  64.233.174.27 (64.233.174.27)  0.690 ms  0.682 ms  0.634 ms
    10  dub08s02-in-f14.1e100.net (216.58.198.78)  0.568 ms  0.560 ms  0.595 ms
status: completed
timing:
  completed: 2016-06-29 14:50:04 +0000 UTC
  enqueued: 2016-06-29 14:50:03 +0000 UTC
  started: 2016-06-29 14:50:03 +0000 UTC
```
## iperf3

Because iperf3 has a client and server component, the netutils charm can operate
as both. Setting the iperf3 configuration value to True will start iperf3 in
server mode, running as a daemon.
```
$ juju deploy cs:~nfv/netutils client
$ juju deploy cs:~nfv/netutils server iperf3=True
$ juju run-action client/0 iperf host=<ip of server> [...]
```

## Scale out Usage

With great scalability comes great power, but please don't use this to DDoS anyone without their permission.

## Known Limitations and Issues

# Contact Information

## Contributing to the charm

  - The compiled charm can be found [here](https://www.jujucharms.com/u/nfv/netutils).
  - [layer/netutils](https://osm.etsi.org/gitweb/?p=osm/juju-charms.git;a=summary/) contains the source of the layer.
  - Please add any bugs or feature requests to the [bugzilla](https://osm.etsi.org/bugzilla/buglist.cgi?component=Juju-charms&list_id=426&product=OSM&resolution=---).
