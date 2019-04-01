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

# import logging
from uuid import uuid4
from hashlib import sha256
from http import HTTPStatus
from validation import user_new_schema, user_edit_schema, project_new_schema, project_edit_schema
from validation import vim_account_new_schema, vim_account_edit_schema, sdn_new_schema, sdn_edit_schema
from validation import wim_account_new_schema, wim_account_edit_schema
from base_topic import BaseTopic, EngineException

__author__ = "Alfonso Tierno <alfonso.tiernosepulveda@telefonica.com>"


class UserTopic(BaseTopic):
    topic = "users"
    topic_msg = "users"
    schema_new = user_new_schema
    schema_edit = user_edit_schema

    def __init__(self, db, fs, msg):
        BaseTopic.__init__(self, db, fs, msg)

    @staticmethod
    def _get_project_filter(session, write=False, show_all=True):
        """
        Generates a filter dictionary for querying database users.
        Current policy is admin can show all, non admin, only its own user.
        :param session: contains "username", if user is "admin" and the working "project_id"
        :param write: if operation is for reading (False) or writing (True)
        :param show_all:  if True it will show public or
        :return:
        """
        if session["admin"]:  # allows all
            return {}
        else:
            return {"username": session["username"]}

    def check_conflict_on_new(self, session, indata, force=False):
        # check username not exists
        if self.db.get_one(self.topic, {"username": indata.get("username")}, fail_on_empty=False, fail_on_more=False):
            raise EngineException("username '{}' exists".format(indata["username"]), HTTPStatus.CONFLICT)
        # check projects
        if not force:
            for p in indata["projects"]:
                if p == "admin":
                    continue
                if not self.db.get_one("projects", {"_id": p}, fail_on_empty=False, fail_on_more=False):
                    raise EngineException("project '{}' does not exists".format(p), HTTPStatus.CONFLICT)

    def check_conflict_on_del(self, session, _id, force=False):
        if _id == session["username"]:
            raise EngineException("You cannot delete your own user", http_code=HTTPStatus.CONFLICT)

    @staticmethod
    def format_on_new(content, project_id=None, make_public=False):
        BaseTopic.format_on_new(content, make_public=False)
        content["_id"] = content["username"]
        salt = uuid4().hex
        content["_admin"]["salt"] = salt
        if content.get("password"):
            content["password"] = sha256(content["password"].encode('utf-8') + salt.encode('utf-8')).hexdigest()

    @staticmethod
    def format_on_edit(final_content, edit_content):
        BaseTopic.format_on_edit(final_content, edit_content)
        if edit_content.get("password"):
            salt = uuid4().hex
            final_content["_admin"]["salt"] = salt
            final_content["password"] = sha256(edit_content["password"].encode('utf-8') +
                                               salt.encode('utf-8')).hexdigest()

    def edit(self, session, _id, indata=None, kwargs=None, force=False, content=None):
        if not session["admin"]:
            raise EngineException("needed admin privileges", http_code=HTTPStatus.UNAUTHORIZED)
        return BaseTopic.edit(self, session, _id, indata=indata, kwargs=kwargs, force=force, content=content)

    def new(self, rollback, session, indata=None, kwargs=None, headers=None, force=False, make_public=False):
        if not session["admin"]:
            raise EngineException("needed admin privileges", http_code=HTTPStatus.UNAUTHORIZED)
        return BaseTopic.new(self, rollback, session, indata=indata, kwargs=kwargs, headers=headers, force=force,
                             make_public=make_public)


class ProjectTopic(BaseTopic):
    topic = "projects"
    topic_msg = "projects"
    schema_new = project_new_schema
    schema_edit = project_edit_schema

    def __init__(self, db, fs, msg):
        BaseTopic.__init__(self, db, fs, msg)

    def check_conflict_on_new(self, session, indata, force=False):
        if not indata.get("name"):
            raise EngineException("missing 'name'")
        # check name not exists
        if self.db.get_one(self.topic, {"name": indata.get("name")}, fail_on_empty=False, fail_on_more=False):
            raise EngineException("name '{}' exists".format(indata["name"]), HTTPStatus.CONFLICT)

    @staticmethod
    def format_on_new(content, project_id=None, make_public=False):
        BaseTopic.format_on_new(content, None)
        content["_id"] = content["name"]

    def check_conflict_on_del(self, session, _id, force=False):
        if _id == session["project_id"]:
            raise EngineException("You cannot delete your own project", http_code=HTTPStatus.CONFLICT)
        if force:
            return
        _filter = {"projects": _id}
        if self.db.get_list("users", _filter):
            raise EngineException("There is some USER that contains this project", http_code=HTTPStatus.CONFLICT)

    def edit(self, session, _id, indata=None, kwargs=None, force=False, content=None):
        if not session["admin"]:
            raise EngineException("needed admin privileges", http_code=HTTPStatus.UNAUTHORIZED)
        return BaseTopic.edit(self, session, _id, indata=indata, kwargs=kwargs, force=force, content=content)

    def new(self, rollback, session, indata=None, kwargs=None, headers=None, force=False, make_public=False):
        if not session["admin"]:
            raise EngineException("needed admin privileges", http_code=HTTPStatus.UNAUTHORIZED)
        return BaseTopic.new(self, rollback, session, indata=indata, kwargs=kwargs, headers=headers, force=force,
                             make_public=make_public)


class VimAccountTopic(BaseTopic):
    topic = "vim_accounts"
    topic_msg = "vim_account"
    schema_new = vim_account_new_schema
    schema_edit = vim_account_edit_schema
    vim_config_encrypted = ("admin_password", "nsx_password", "vcenter_password")

    def __init__(self, db, fs, msg):
        BaseTopic.__init__(self, db, fs, msg)

    def check_conflict_on_new(self, session, indata, force=False):
        self.check_unique_name(session, indata["name"], _id=None)

    def check_conflict_on_edit(self, session, final_content, edit_content, _id, force=False):
        if not force and edit_content.get("name"):
            self.check_unique_name(session, edit_content["name"], _id=_id)

        # encrypt passwords
        schema_version = final_content.get("schema_version")
        if schema_version:
            if edit_content.get("vim_password"):
                final_content["vim_password"] = self.db.encrypt(edit_content["vim_password"],
                                                                schema_version=schema_version, salt=_id)
            if edit_content.get("config"):
                for p in self.vim_config_encrypted:
                    if edit_content["config"].get(p):
                        final_content["config"][p] = self.db.encrypt(edit_content["config"][p],
                                                                     schema_version=schema_version, salt=_id)

    def format_on_new(self, content, project_id=None, make_public=False):
        BaseTopic.format_on_new(content, project_id=project_id, make_public=make_public)
        content["schema_version"] = schema_version = "1.1"

        # encrypt passwords
        if content.get("vim_password"):
            content["vim_password"] = self.db.encrypt(content["vim_password"], schema_version=schema_version,
                                                      salt=content["_id"])
        if content.get("config"):
            for p in self.vim_config_encrypted:
                if content["config"].get(p):
                    content["config"][p] = self.db.encrypt(content["config"][p], schema_version=schema_version,
                                                           salt=content["_id"])

        content["_admin"]["operationalState"] = "PROCESSING"

    def delete(self, session, _id, force=False, dry_run=False):
        """
        Delete item by its internal _id
        :param session: contains the used login username, working project, and admin rights
        :param _id: server internal id
        :param force: indicates if deletion must be forced in case of conflict
        :param dry_run: make checking but do not delete
        :return: dictionary with deleted item _id. It raises EngineException on error: not found, conflict, ...
        """
        # TODO add admin to filter, validate rights
        if dry_run or force:    # delete completely
            return BaseTopic.delete(self, session, _id, force, dry_run)
        else:  # if not, sent to kafka
            v = BaseTopic.delete(self, session, _id, force, dry_run=True)
            self.db.set_one("vim_accounts", {"_id": _id}, {"_admin.to_delete": True})  # TODO change status
            self._send_msg("delete", {"_id": _id})
            return v  # TODO indicate an offline operation to return 202 ACCEPTED


class WimAccountTopic(BaseTopic):
    topic = "wim_accounts"
    topic_msg = "wim_account"
    schema_new = wim_account_new_schema
    schema_edit = wim_account_edit_schema
    wim_config_encrypted = ()

    def __init__(self, db, fs, msg):
        BaseTopic.__init__(self, db, fs, msg)

    def check_conflict_on_new(self, session, indata, force=False):
        self.check_unique_name(session, indata["name"], _id=None)

    def check_conflict_on_edit(self, session, final_content, edit_content, _id, force=False):
        if not force and edit_content.get("name"):
            self.check_unique_name(session, edit_content["name"], _id=_id)

        # encrypt passwords
        schema_version = final_content.get("schema_version")
        if schema_version:
            if edit_content.get("wim_password"):
                final_content["wim_password"] = self.db.encrypt(edit_content["wim_password"],
                                                                schema_version=schema_version, salt=_id)
            if edit_content.get("config"):
                for p in self.wim_config_encrypted:
                    if edit_content["config"].get(p):
                        final_content["config"][p] = self.db.encrypt(edit_content["config"][p],
                                                                     schema_version=schema_version, salt=_id)

    def format_on_new(self, content, project_id=None, make_public=False):
        BaseTopic.format_on_new(content, project_id=project_id, make_public=make_public)
        content["schema_version"] = schema_version = "1.1"

        # encrypt passwords
        if content.get("wim_password"):
            content["wim_password"] = self.db.encrypt(content["wim_password"], schema_version=schema_version,
                                                      salt=content["_id"])
        if content.get("config"):
            for p in self.wim_config_encrypted:
                if content["config"].get(p):
                    content["config"][p] = self.db.encrypt(content["config"][p], schema_version=schema_version,
                                                           salt=content["_id"])

        content["_admin"]["operationalState"] = "PROCESSING"

    def delete(self, session, _id, force=False, dry_run=False):
        """
        Delete item by its internal _id
        :param session: contains the used login username, working project, and admin rights
        :param _id: server internal id
        :param force: indicates if deletion must be forced in case of conflict
        :param dry_run: make checking but do not delete
        :return: dictionary with deleted item _id. It raises EngineException on error: not found, conflict, ...
        """
        # TODO add admin to filter, validate rights
        if dry_run or force:    # delete completely
            return BaseTopic.delete(self, session, _id, force, dry_run)
        else:  # if not, sent to kafka
            v = BaseTopic.delete(self, session, _id, force, dry_run=True)
            self.db.set_one("wim_accounts", {"_id": _id}, {"_admin.to_delete": True})  # TODO change status
            self._send_msg("delete", {"_id": _id})
            return v  # TODO indicate an offline operation to return 202 ACCEPTED


class SdnTopic(BaseTopic):
    topic = "sdns"
    topic_msg = "sdn"
    schema_new = sdn_new_schema
    schema_edit = sdn_edit_schema

    def __init__(self, db, fs, msg):
        BaseTopic.__init__(self, db, fs, msg)

    def check_conflict_on_new(self, session, indata, force=False):
        self.check_unique_name(session, indata["name"], _id=None)

    def check_conflict_on_edit(self, session, final_content, edit_content, _id, force=False):
        if not force and edit_content.get("name"):
            self.check_unique_name(session, edit_content["name"], _id=_id)

        # encrypt passwords
        schema_version = final_content.get("schema_version")
        if schema_version and edit_content.get("password"):
            final_content["password"] = self.db.encrypt(edit_content["password"], schema_version=schema_version,
                                                        salt=_id)

    def format_on_new(self, content, project_id=None, make_public=False):
        BaseTopic.format_on_new(content, project_id=project_id, make_public=make_public)
        content["schema_version"] = schema_version = "1.1"
        # encrypt passwords
        if content.get("password"):
            content["password"] = self.db.encrypt(content["password"], schema_version=schema_version,
                                                  salt=content["_id"])

        content["_admin"]["operationalState"] = "PROCESSING"

    def delete(self, session, _id, force=False, dry_run=False):
        """
        Delete item by its internal _id
        :param session: contains the used login username, working project, and admin rights
        :param _id: server internal id
        :param force: indicates if deletion must be forced in case of conflict
        :param dry_run: make checking but do not delete
        :return: dictionary with deleted item _id. It raises EngineException on error: not found, conflict, ...
        """
        if dry_run or force:  # delete completely
            return BaseTopic.delete(self, session, _id, force, dry_run)
        else:  # if not sent to kafka
            v = BaseTopic.delete(self, session, _id, force, dry_run=True)
            self.db.set_one("sdns", {"_id": _id}, {"_admin.to_delete": True})  # TODO change status
            self._send_msg("delete", {"_id": _id})
            return v   # TODO indicate an offline operation to return 202 ACCEPTED
