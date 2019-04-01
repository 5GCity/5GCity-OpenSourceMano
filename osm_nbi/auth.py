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
Authenticator is responsible for authenticating the users,
create the tokens unscoped and scoped, retrieve the role
list inside the projects that they are inserted
"""

__author__ = "Eduardo Sousa <esousa@whitestack.com>; Alfonso Tierno <alfonso.tiernosepulveda@telefonica.com>"
__date__ = "$27-jul-2018 23:59:59$"

import cherrypy
import logging
from base64 import standard_b64decode
from copy import deepcopy
from functools import reduce
from hashlib import sha256
from http import HTTPStatus
from random import choice as random_choice
from time import time

from authconn import AuthException
from authconn_keystone import AuthconnKeystone
from osm_common import dbmongo
from osm_common import dbmemory
from osm_common.dbbase import DbException


class Authenticator:
    """
    This class should hold all the mechanisms for User Authentication and
    Authorization. Initially it should support Openstack Keystone as a
    backend through a plugin model where more backends can be added and a
    RBAC model to manage permissions on operations.
    """

    periodin_db_pruning = 60*30  # for the internal backend only. every 30 minutes expired tokens will be pruned

    def __init__(self):
        """
        Authenticator initializer. Setup the initial state of the object,
        while it waits for the config dictionary and database initialization.
        """
        self.backend = None
        self.config = None
        self.db = None
        self.tokens_cache = dict()
        self.next_db_prune_time = 0  # time when next cleaning of expired tokens must be done

        self.logger = logging.getLogger("nbi.authenticator")

    def start(self, config):
        """
        Method to configure the Authenticator object. This method should be called
        after object creation. It is responsible by initializing the selected backend,
        as well as the initialization of the database connection.

        :param config: dictionary containing the relevant parameters for this object.
        """
        self.config = config

        try:
            if not self.db:
                if config["database"]["driver"] == "mongo":
                    self.db = dbmongo.DbMongo()
                    self.db.db_connect(config["database"])
                elif config["database"]["driver"] == "memory":
                    self.db = dbmemory.DbMemory()
                    self.db.db_connect(config["database"])
                else:
                    raise AuthException("Invalid configuration param '{}' at '[database]':'driver'"
                                        .format(config["database"]["driver"]))
            if not self.backend:
                if config["authentication"]["backend"] == "keystone":
                    self.backend = AuthconnKeystone(self.config["authentication"])
                elif config["authentication"]["backend"] == "internal":
                    self._internal_tokens_prune()
                else:
                    raise AuthException("Unknown authentication backend: {}"
                                        .format(config["authentication"]["backend"]))
        except Exception as e:
            raise AuthException(str(e))

    def stop(self):
        try:
            if self.db:
                self.db.db_disconnect()
        except DbException as e:
            raise AuthException(str(e), http_code=e.http_code)

    def init_db(self, target_version='1.1'):
        """
        Check if the database has been initialized, with at least one user. If not, create an adthe required tables
        and insert the predefined mappings between roles and permissions.

        :param target_version: schema version that should be present in the database.
        :return: None if OK, exception if error or version is different.
        """
        pass

    def authorize(self):
        token = None
        user_passwd64 = None
        try:
            # 1. Get token Authorization bearer
            auth = cherrypy.request.headers.get("Authorization")
            if auth:
                auth_list = auth.split(" ")
                if auth_list[0].lower() == "bearer":
                    token = auth_list[-1]
                elif auth_list[0].lower() == "basic":
                    user_passwd64 = auth_list[-1]
            if not token:
                if cherrypy.session.get("Authorization"):
                    # 2. Try using session before request a new token. If not, basic authentication will generate
                    token = cherrypy.session.get("Authorization")
                    if token == "logout":
                        token = None  # force Unauthorized response to insert user password again
                elif user_passwd64 and cherrypy.request.config.get("auth.allow_basic_authentication"):
                    # 3. Get new token from user password
                    user = None
                    passwd = None
                    try:
                        user_passwd = standard_b64decode(user_passwd64).decode()
                        user, _, passwd = user_passwd.partition(":")
                    except Exception:
                        pass
                    outdata = self.new_token(None, {"username": user, "password": passwd})
                    token = outdata["id"]
                    cherrypy.session['Authorization'] = token
            if self.config["authentication"]["backend"] == "internal":
                return self._internal_authorize(token)
            else:
                try:
                    self.backend.validate_token(token)
                    # TODO: check if this can be avoided. Backend may provide enough information
                    return self.tokens_cache[token]
                except AuthException:
                    self.del_token(token)
                    raise
        except AuthException as e:
            if cherrypy.session.get('Authorization'):
                del cherrypy.session['Authorization']
            cherrypy.response.headers["WWW-Authenticate"] = 'Bearer realm="{}"'.format(e)
            raise AuthException(str(e))

    def new_token(self, session, indata, remote):
        if self.config["authentication"]["backend"] == "internal":
            return self._internal_new_token(session, indata, remote)
        else:
            if indata.get("username"):
                token, projects = self.backend.authenticate_with_user_password(
                    indata.get("username"), indata.get("password"))
            elif session:
                token, projects = self.backend.authenticate_with_token(
                    session.get("id"), indata.get("project_id"))
            else:
                raise AuthException("Provide credentials: username/password or Authorization Bearer token",
                                    http_code=HTTPStatus.UNAUTHORIZED)

            if indata.get("project_id"):
                project_id = indata.get("project_id")
                if project_id not in projects:
                    raise AuthException("Project {} not allowed for this user".format(project_id),
                                        http_code=HTTPStatus.UNAUTHORIZED)
            else:
                project_id = projects[0]

            if project_id == "admin":
                session_admin = True
            else:
                session_admin = reduce(lambda x, y: x or (True if y == "admin" else False),
                                       projects, False)

            now = time()
            new_session = {
                "_id": token,
                "id": token,
                "issued_at": now,
                "expires": now + 3600,
                "project_id": project_id,
                "username": indata.get("username") if not session else session.get("username"),
                "remote_port": remote.port,
                "admin": session_admin
            }

            if remote.name:
                new_session["remote_host"] = remote.name
            elif remote.ip:
                new_session["remote_host"] = remote.ip

            # TODO: check if this can be avoided. Backend may provide enough information
            self.tokens_cache[token] = new_session

            return deepcopy(new_session)

    def get_token_list(self, session):
        if self.config["authentication"]["backend"] == "internal":
            return self._internal_get_token_list(session)
        else:
            # TODO: check if this can be avoided. Backend may provide enough information
            return [deepcopy(token) for token in self.tokens_cache.values()
                    if token["username"] == session["username"]]

    def get_token(self, session, token):
        if self.config["authentication"]["backend"] == "internal":
            return self._internal_get_token(session, token)
        else:
            # TODO: check if this can be avoided. Backend may provide enough information
            token_value = self.tokens_cache.get(token)
            if not token_value:
                raise AuthException("token not found", http_code=HTTPStatus.NOT_FOUND)
            if token_value["username"] != session["username"] and not session["admin"]:
                raise AuthException("needed admin privileges", http_code=HTTPStatus.UNAUTHORIZED)
            return token_value

    def del_token(self, token):
        if self.config["authentication"]["backend"] == "internal":
            return self._internal_del_token(token)
        else:
            try:
                self.backend.revoke_token(token)
                del self.tokens_cache[token]
                return "token '{}' deleted".format(token)
            except KeyError:
                raise AuthException("Token '{}' not found".format(token), http_code=HTTPStatus.NOT_FOUND)

    def _internal_authorize(self, token_id):
        try:
            if not token_id:
                raise AuthException("Needed a token or Authorization http header", http_code=HTTPStatus.UNAUTHORIZED)
            # try to get from cache first
            now = time()
            session = self.tokens_cache.get(token_id)
            if session and session["expires"] < now:
                del self.tokens_cache[token_id]
                session = None
            if session:
                return session

            # get from database if not in cache
            session = self.db.get_one("tokens", {"_id": token_id})
            if session["expires"] < now:
                raise AuthException("Expired Token or Authorization http header", http_code=HTTPStatus.UNAUTHORIZED)
            self.tokens_cache[token_id] = session
            return session
        except DbException as e:
            if e.http_code == HTTPStatus.NOT_FOUND:
                raise AuthException("Invalid Token or Authorization http header", http_code=HTTPStatus.UNAUTHORIZED)
            else:
                raise

        except AuthException:
            if self.config["global"].get("test.user_not_authorized"):
                return {"id": "fake-token-id-for-test",
                        "project_id": self.config["global"].get("test.project_not_authorized", "admin"),
                        "username": self.config["global"]["test.user_not_authorized"]}
            else:
                raise

    def _internal_new_token(self, session, indata, remote):
        now = time()
        user_content = None

        # Try using username/password
        if indata.get("username"):
            user_rows = self.db.get_list("users", {"username": indata.get("username")})
            if user_rows:
                user_content = user_rows[0]
                salt = user_content["_admin"]["salt"]
                shadow_password = sha256(indata.get("password", "").encode('utf-8') + salt.encode('utf-8')).hexdigest()
                if shadow_password != user_content["password"]:
                    user_content = None
            if not user_content:
                raise AuthException("Invalid username/password", http_code=HTTPStatus.UNAUTHORIZED)
        elif session:
            user_rows = self.db.get_list("users", {"username": session["username"]})
            if user_rows:
                user_content = user_rows[0]
            else:
                raise AuthException("Invalid token", http_code=HTTPStatus.UNAUTHORIZED)
        else:
            raise AuthException("Provide credentials: username/password or Authorization Bearer token",
                                http_code=HTTPStatus.UNAUTHORIZED)

        token_id = ''.join(random_choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                           for _ in range(0, 32))
        if indata.get("project_id"):
            project_id = indata.get("project_id")
            if project_id not in user_content["projects"]:
                raise AuthException("project {} not allowed for this user"
                                    .format(project_id), http_code=HTTPStatus.UNAUTHORIZED)
        else:
            project_id = user_content["projects"][0]
        if project_id == "admin":
            session_admin = True
        else:
            project = self.db.get_one("projects", {"_id": project_id})
            session_admin = project.get("admin", False)
        new_session = {"issued_at": now, "expires": now + 3600,
                       "_id": token_id, "id": token_id, "project_id": project_id, "username": user_content["username"],
                       "remote_port": remote.port, "admin": session_admin}
        if remote.name:
            new_session["remote_host"] = remote.name
        elif remote.ip:
            new_session["remote_host"] = remote.ip

        self.tokens_cache[token_id] = new_session
        self.db.create("tokens", new_session)
        # check if database must be prune
        self._internal_tokens_prune(now)
        return deepcopy(new_session)

    def _internal_get_token_list(self, session):
        now = time()
        token_list = self.db.get_list("tokens", {"username": session["username"], "expires.gt": now})
        return token_list

    def _internal_get_token(self, session, token_id):
        token_value = self.db.get_one("tokens", {"_id": token_id}, fail_on_empty=False)
        if not token_value:
            raise AuthException("token not found", http_code=HTTPStatus.NOT_FOUND)
        if token_value["username"] != session["username"] and not session["admin"]:
            raise AuthException("needed admin privileges", http_code=HTTPStatus.UNAUTHORIZED)
        return token_value

    def _internal_del_token(self, token_id):
        try:
            self.tokens_cache.pop(token_id, None)
            self.db.del_one("tokens", {"_id": token_id})
            return "token '{}' deleted".format(token_id)
        except DbException as e:
            if e.http_code == HTTPStatus.NOT_FOUND:
                raise AuthException("Token '{}' not found".format(token_id), http_code=HTTPStatus.NOT_FOUND)
            else:
                raise

    def _internal_tokens_prune(self, now=None):
        now = now or time()
        if not self.next_db_prune_time or self.next_db_prune_time >= now:
            self.db.del_list("tokens", {"expires.lt": now})
            self.next_db_prune_time = self.periodin_db_pruning + now
            self.tokens_cache.clear()   # force to reload tokens from database
