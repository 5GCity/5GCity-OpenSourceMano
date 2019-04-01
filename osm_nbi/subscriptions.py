# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module implements a thread that reads from kafka bus implementing all the subscriptions.
It is based on asyncio.
To avoid race conditions it uses same engine class as the main module for database changes
For the moment this module only deletes NS instances when they are terminated with the autoremove flag
"""

import logging
import threading
import asyncio
from http import HTTPStatus
from osm_common import dbmongo, dbmemory, msglocal, msgkafka
from osm_common.dbbase import DbException
from osm_common.msgbase import MsgException
from engine import EngineException

__author__ = "Alfonso Tierno <alfonso.tiernosepulveda@telefonica.com>"


class SubscriptionException(Exception):

    def __init__(self, message, http_code=HTTPStatus.BAD_REQUEST):
        self.http_code = http_code
        Exception.__init__(self, message)


class SubscriptionThread(threading.Thread):

    def __init__(self, config, engine):
        """
        Constructor of class
        :param config: configuration parameters of database and messaging
        :param engine: an instance of Engine class, used for deleting instances
        """
        threading.Thread.__init__(self)

        self.config = config
        self.db = None
        self.msg = None
        self.engine = engine
        self.loop = None
        self.logger = logging.getLogger("nbi.subscriptions")
        self.aiomain_task = None  # asyncio task for receiving kafka bus
        self.internal_session = {  # used for a session to the engine methods
            "_id": "subscription",
            "id": "subscription",
            "project_id": "admin",
            "admin": True
        }

    def run(self):
        """
        Start of the thread
        :return: None
        """
        self.loop = asyncio.new_event_loop()
        try:
            if not self.db:
                if self.config["database"]["driver"] == "mongo":
                    self.db = dbmongo.DbMongo()
                    self.db.db_connect(self.config["database"])
                elif self.config["database"]["driver"] == "memory":
                    self.db = dbmemory.DbMemory()
                    self.db.db_connect(self.config["database"])
                else:
                    raise SubscriptionException("Invalid configuration param '{}' at '[database]':'driver'".format(
                        self.config["database"]["driver"]))
            if not self.msg:
                config_msg = self.config["message"].copy()
                config_msg["loop"] = self.loop
                if config_msg["driver"] == "local":
                    self.msg = msglocal.MsgLocal()
                    self.msg.connect(config_msg)
                elif config_msg["driver"] == "kafka":
                    self.msg = msgkafka.MsgKafka()
                    self.msg.connect(config_msg)
                else:
                    raise SubscriptionException("Invalid configuration param '{}' at '[message]':'driver'".format(
                        config_msg["driver"]))

        except (DbException, MsgException) as e:
            raise SubscriptionException(str(e), http_code=e.http_code)

        self.logger.debug("Starting")
        while True:
            try:
                self.aiomain_task = asyncio.ensure_future(self.msg.aioread("ns", loop=self.loop,
                                                                           callback=self._msg_callback),
                                                          loop=self.loop)
                self.loop.run_until_complete(self.aiomain_task)
            except asyncio.CancelledError:
                break  # if cancelled it should end, breaking loop
            except Exception as e:
                self.logger.exception("Exception '{}' at messaging read loop".format(e), exc_info=True)

        self.logger.debug("Finishing")
        self._stop()
        self.loop.close()

    def _msg_callback(self, topic, command, params):
        """
        Callback to process a received message from kafka
        :param topic:  topic received
        :param command:  command received
        :param params: rest of parameters
        :return: None
        """
        try:
            if topic == "ns":
                if command == "terminated":
                    self.logger.debug("received ns terminated {}".format(params))
                    if params.get("autoremove"):
                        self.engine.del_item(self.internal_session, "nsrs", _id=params["nsr_id"])
                        self.logger.debug("ns={} deleted from database".format(params["nsr_id"]))
                    return
        except (EngineException, DbException, MsgException) as e:
            self.logger.error("Error while processing topic={} command={}: {}".format(topic, command, e))
        except Exception as e:
            self.logger.exception("Exception while processing topic={} command={}: {}".format(topic, command, e),
                                  exc_info=True)

    def _stop(self):
        """
        Close all connections
        :return: None
        """
        try:
            if self.db:
                self.db.db_disconnect()
            if self.msg:
                self.msg.disconnect()
        except (DbException, MsgException) as e:
            raise SubscriptionException(str(e), http_code=e.http_code)

    def terminate(self):
        """
        This is a threading safe method to terminate this thread. Termination is done asynchronous afterwards,
        but not immediately.
        :return: None
        """
        self.loop.call_soon_threadsafe(self.aiomain_task.cancel)
