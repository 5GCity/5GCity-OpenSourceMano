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

import logging
from osm_common import dbmongo, dbmemory, fslocal, msglocal, msgkafka, version as common_version
from osm_common.dbbase import DbException
from osm_common.fsbase import FsException
from osm_common.msgbase import MsgException
from http import HTTPStatus
from base_topic import EngineException, versiontuple
from admin_topics import UserTopic, ProjectTopic, VimAccountTopic, WimAccountTopic, SdnTopic
from descriptor_topics import VnfdTopic, NsdTopic, PduTopic, NstTopic
from instance_topics import NsrTopic, VnfrTopic, NsLcmOpTopic, NsiTopic, NsiLcmOpTopic
from base64 import b64encode
from os import urandom
from threading import Lock

__author__ = "Alfonso Tierno <alfonso.tiernosepulveda@telefonica.com>"
min_common_version = "0.1.16"


class Engine(object):
    map_from_topic_to_class = {
        "vnfds": VnfdTopic,
        "nsds": NsdTopic,
        "nsts": NstTopic,
        "pdus": PduTopic,
        "nsrs": NsrTopic,
        "vnfrs": VnfrTopic,
        "nslcmops": NsLcmOpTopic,
        "vim_accounts": VimAccountTopic,
        "wim_accounts": WimAccountTopic,
        "sdns": SdnTopic,
        "users": UserTopic,
        "projects": ProjectTopic,
        "nsis": NsiTopic,
        "nsilcmops": NsiLcmOpTopic
        # [NEW_TOPIC]: add an entry here
    }

    def __init__(self):
        self.db = None
        self.fs = None
        self.msg = None
        self.config = None
        self.logger = logging.getLogger("nbi.engine")
        self.map_topic = {}
        self.write_lock = None

    def start(self, config):
        """
        Connect to database, filesystem storage, and messaging
        :param config: two level dictionary with configuration. Top level should contain 'database', 'storage',
        :return: None
        """
        self.config = config
        # check right version of common
        if versiontuple(common_version) < versiontuple(min_common_version):
            raise EngineException("Not compatible osm/common version '{}'. Needed '{}' or higher".format(
                common_version, min_common_version))

        try:
            if not self.db:
                if config["database"]["driver"] == "mongo":
                    self.db = dbmongo.DbMongo()
                    self.db.db_connect(config["database"])
                elif config["database"]["driver"] == "memory":
                    self.db = dbmemory.DbMemory()
                    self.db.db_connect(config["database"])
                else:
                    raise EngineException("Invalid configuration param '{}' at '[database]':'driver'".format(
                        config["database"]["driver"]))
            if not self.fs:
                if config["storage"]["driver"] == "local":
                    self.fs = fslocal.FsLocal()
                    self.fs.fs_connect(config["storage"])
                else:
                    raise EngineException("Invalid configuration param '{}' at '[storage]':'driver'".format(
                        config["storage"]["driver"]))
            if not self.msg:
                if config["message"]["driver"] == "local":
                    self.msg = msglocal.MsgLocal()
                    self.msg.connect(config["message"])
                elif config["message"]["driver"] == "kafka":
                    self.msg = msgkafka.MsgKafka()
                    self.msg.connect(config["message"])
                else:
                    raise EngineException("Invalid configuration param '{}' at '[message]':'driver'".format(
                        config["message"]["driver"]))

            self.write_lock = Lock()
            # create one class per topic
            for topic, topic_class in self.map_from_topic_to_class.items():
                self.map_topic[topic] = topic_class(self.db, self.fs, self.msg)
        except (DbException, FsException, MsgException) as e:
            raise EngineException(str(e), http_code=e.http_code)

    def stop(self):
        try:
            if self.db:
                self.db.db_disconnect()
            if self.fs:
                self.fs.fs_disconnect()
            if self.msg:
                self.msg.disconnect()
            self.write_lock = None
        except (DbException, FsException, MsgException) as e:
            raise EngineException(str(e), http_code=e.http_code)

    def new_item(self, rollback, session, topic, indata=None, kwargs=None, headers=None, force=False):
        """
        Creates a new entry into database. For nsds and vnfds it creates an almost empty DISABLED  entry,
        that must be completed with a call to method upload_content
        :param rollback: list to append created items at database in case a rollback must to be done
        :param session: contains the used login username and working project
        :param topic: it can be: users, projects, vim_accounts, sdns, nsrs, nsds, vnfds
        :param indata: data to be inserted
        :param kwargs: used to override the indata descriptor
        :param headers: http request headers
        :param force: If True avoid some dependence checks
        :return: _id: identity of the inserted data.
        """
        if topic not in self.map_topic:
            raise EngineException("Unknown topic {}!!!".format(topic), HTTPStatus.INTERNAL_SERVER_ERROR)
        with self.write_lock:
            return self.map_topic[topic].new(rollback, session, indata, kwargs, headers, force)

    def upload_content(self, session, topic, _id, indata, kwargs, headers, force=False):
        """
        Upload content for an already created entry (_id)
        :param session: contains the used login username and working project
        :param topic: it can be: users, projects, vnfds, nsds,
        :param _id: server id of the item
        :param indata: data to be inserted
        :param kwargs: used to override the indata descriptor
        :param headers: http request headers
        :param force: If True avoid some dependence checks
        :return: _id: identity of the inserted data.
        """
        if topic not in self.map_topic:
            raise EngineException("Unknown topic {}!!!".format(topic), HTTPStatus.INTERNAL_SERVER_ERROR)
        with self.write_lock:
            return self.map_topic[topic].upload_content(session, _id, indata, kwargs, headers, force)

    def get_item_list(self, session, topic, filter_q=None):
        """
        Get a list of items
        :param session: contains the used login username and working project
        :param topic: it can be: users, projects, vnfds, nsds, ...
        :param filter_q: filter of data to be applied
        :return: The list, it can be empty if no one match the filter_q.
        """
        if topic not in self.map_topic:
            raise EngineException("Unknown topic {}!!!".format(topic), HTTPStatus.INTERNAL_SERVER_ERROR)
        return self.map_topic[topic].list(session, filter_q)

    def get_item(self, session, topic, _id):
        """
        Get complete information on an item
        :param session: contains the used login username and working project
        :param topic: it can be: users, projects, vnfds, nsds,
        :param _id: server id of the item
        :return: dictionary, raise exception if not found.
        """
        if topic not in self.map_topic:
            raise EngineException("Unknown topic {}!!!".format(topic), HTTPStatus.INTERNAL_SERVER_ERROR)
        return self.map_topic[topic].show(session, _id)

    def get_file(self, session, topic, _id, path=None, accept_header=None):
        """
        Get descriptor package or artifact file content
        :param session: contains the used login username and working project
        :param topic: it can be: users, projects, vnfds, nsds,
        :param _id: server id of the item
        :param path: artifact path or "$DESCRIPTOR" or None
        :param accept_header: Content of Accept header. Must contain applition/zip or/and text/plain
        :return: opened file plus Accept format or raises an exception
        """
        if topic not in self.map_topic:
            raise EngineException("Unknown topic {}!!!".format(topic), HTTPStatus.INTERNAL_SERVER_ERROR)
        return self.map_topic[topic].get_file(session, _id, path, accept_header)

    def del_item_list(self, session, topic, _filter=None):
        """
        Delete a list of items
        :param session: contains the used login username and working project
        :param topic: it can be: users, projects, vnfds, nsds, ...
        :param _filter: filter of data to be applied
        :return: The deleted list, it can be empty if no one match the _filter.
        """
        if topic not in self.map_topic:
            raise EngineException("Unknown topic {}!!!".format(topic), HTTPStatus.INTERNAL_SERVER_ERROR)
        with self.write_lock:
            return self.map_topic[topic].delete_list(session, _filter)

    def del_item(self, session, topic, _id, force=False):
        """
        Delete item by its internal id
        :param session: contains the used login username and working project
        :param topic: it can be: users, projects, vnfds, nsds, ...
        :param _id: server id of the item
        :param force: indicates if deletion must be forced in case of conflict
        :return: dictionary with deleted item _id. It raises exception if not found.
        """
        if topic not in self.map_topic:
            raise EngineException("Unknown topic {}!!!".format(topic), HTTPStatus.INTERNAL_SERVER_ERROR)
        with self.write_lock:
            return self.map_topic[topic].delete(session, _id, force)

    def edit_item(self, session, topic, _id, indata=None, kwargs=None, force=False):
        """
        Update an existing entry at database
        :param session: contains the used login username and working project
        :param topic: it can be: users, projects, vnfds, nsds, ...
        :param _id: identifier to be updated
        :param indata: data to be inserted
        :param kwargs: used to override the indata descriptor
        :param force: If True avoid some dependence checks
        :return: dictionary, raise exception if not found.
        """
        if topic not in self.map_topic:
            raise EngineException("Unknown topic {}!!!".format(topic), HTTPStatus.INTERNAL_SERVER_ERROR)
        with self.write_lock:
            return self.map_topic[topic].edit(session, _id, indata, kwargs, force)

    def create_admin(self):
        """
        Creates a new user admin/admin into database if database is empty. Useful for initialization
        :return: _id identity of the inserted data, or None
        """
        users = self.db.get_one("users", fail_on_empty=False, fail_on_more=False)
        if users:
            return None
            # raise EngineException("Unauthorized. Database users is not empty", HTTPStatus.UNAUTHORIZED)
        user_desc = {"username": "admin", "password": "admin", "projects": ["admin"]}
        fake_session = {"project_id": "admin", "username": "admin", "admin": True}
        roolback_list = []
        _id = self.map_topic["users"].new(roolback_list, fake_session, user_desc, force=True)
        return _id

    def upgrade_db(self, current_version, target_version):
        if not target_version or current_version == target_version:
            return
        if target_version == '1.0':
            if not current_version:
                # create database version
                serial = urandom(32)
                version_data = {
                    "_id": 'version',               # Always 'version'
                    "version_int": 1000,            # version number
                    "version": '1.0',               # version text
                    "date": "2018-10-25",           # version date
                    "description": "added serial",  # changes in this version
                    'status': 'ENABLED',            # ENABLED, DISABLED (migration in process), ERROR,
                    'serial': b64encode(serial)
                }
                self.db.create("admin", version_data)
                self.db.set_secret_key(serial)
                return
            # TODO add future migrations here

        raise EngineException("Wrong database version '{}'. Expected '{}'"
                              ". It cannot be up/down-grade".format(current_version, target_version),
                              http_code=HTTPStatus.INTERNAL_SERVER_ERROR)

    def init_db(self, target_version='1.0'):
        """
        Init database if empty. If not empty it checks that database version and migrates if needed
        If empty, it creates a new user admin/admin at 'users' and a new entry at 'version'
        :param target_version: check desired database version. Migrate to it if possible or raises exception
        :return: None if ok, exception if error or if the version is different.
        """

        version_data = self.db.get_one("admin", {"_id": "version"}, fail_on_empty=False, fail_on_more=True)
        # check database status is ok
        if version_data and version_data.get("status") != 'ENABLED':
            raise EngineException("Wrong database status '{}'".format(
                version_data["status"]), HTTPStatus.INTERNAL_SERVER_ERROR)

        # check version
        db_version = None if not version_data else version_data.get("version")
        if db_version != target_version:
            self.upgrade_db(db_version, target_version)

        # create user admin if not exist
        self.create_admin()
        return
