"""
Copyright (c) 2015 SONATA-NFV and Paderborn University
ALL RIGHTS RESERVED.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Neither the name of the SONATA-NFV [, ANY ADDITIONAL AFFILIATION]
nor the names of its contributors may be used to endorse or promote
products derived from this software without specific prior written
permission.

This work has been performed in the framework of the SONATA project,
funded by the European Commission under Grant number 671517 through
the Horizon 2020 and 5G-PPP programmes. The authors would like to
acknowledge the contributions of their colleagues of the SONATA
partner consortium (www.sonata-nfv.eu).
"""
"""
This module implements a simple REST API that behaves like SONATA's gatekeeper.

It is only used to support the development of SONATA's SDK tools and to demonstrate
the year 1 version of the emulator until the integration with WP4's orchestrator is done.
"""

import logging
import threading
import dummygatekeeper as dgk


class SonataDummyGatekeeperEndpoint(object):
    """
    Creates and starts a REST API based on Flask in an
    additional thread.

    Can connect this API to data centers defined in an emulator
    topology.
    """

    def __init__(self, listenip, port, deploy_sap=False, docker_management=True):
        self.dcs = {}
        self.ip = listenip
        self.port = port
        dgk.DEPLOY_SAP = deploy_sap
        dgk.USE_DOCKER_MGMT = docker_management
        logging.debug("Created API endpoint %s" % self)

    def __repr__(self):
        return "%s(%s:%d)" % (self.__class__.__name__, self.ip, self.port)

    def connectDatacenter(self, dc):
        self.dcs[dc.label] = dc
        logging.info("Connected DC(%s) to API endpoint %s" % (
            dc, self))

    def start(self):
        thread = threading.Thread(target=self._api_server_thread, args=())
        thread.daemon = True
        thread.start()
        logging.debug("Started API endpoint %s" % self)

    def _api_server_thread(self):
        dgk.start_rest_api(self.ip, self.port, self.dcs)
