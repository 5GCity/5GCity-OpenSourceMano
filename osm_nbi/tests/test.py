#! /usr/bin/python3
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

import getopt
import sys
import requests
import json
import logging
import yaml
# import json
# import tarfile
from time import sleep
from random import randint
import os
from sys import stderr

__author__ = "Alfonso Tierno, alfonso.tiernosepulveda@telefonica.com"
__date__ = "$2018-03-01$"
__version__ = "0.3"
version_date = "Oct 2018"


def usage():
    print("Usage: ", sys.argv[0], "[options]")
    print("      Performs system tests over running NBI. It can be used for real OSM test using option '--test-osm'")
    print("      If this is the case env variables 'OSMNBITEST_VIM_NAME' must be supplied to create a VIM if not exist "
          "where deployment is done")
    print("OPTIONS")
    print("      -h|--help: shows this help")
    print("      --insecure: Allows non trusted https NBI server")
    print("      --list: list available tests")
    print("      --manual-check: Deployment tests stop after deployed to allow manual inspection. Only make sense with "
          "'--test-osm'")
    print("      -p|--password PASSWORD: NBI access password. 'admin' by default")
    print("      ---project PROJECT: NBI access project. 'admin' by default")
    print("      --test TEST[,...]: Execute only a test or a comma separated list of tests")
    print("      --params key=val: params to the previous test. key can be vnfd-files, nsd-file, ns-name, ns-config")
    print("      --test-osm: If missing this test is intended for NBI only, no other OSM components are expected. Use "
          "this flag to test the system. LCM and RO components are expected to be up and running")
    print("      --timeout TIMEOUT: General NBI timeout, by default {}s".format(timeout))
    print("      --timeout-deploy TIMEOUT: Timeout used for getting NS deployed, by default {}s".format(timeout_deploy))
    print("      --timeout-configure TIMEOUT: Timeout used for getting NS deployed and configured,"
          " by default {}s".format(timeout_configure))
    print("      -u|--user USERNAME: NBI access username. 'admin' by default")
    print("      --url URL: complete NBI server URL. 'https//localhost:9999/osm' by default")
    print("      -v|--verbose print debug information, can be used several times")
    print("      --no-verbose remove verbosity")
    print("      --version: prints current version")
    print("ENV variables used for real deployment tests with option osm-test.")
    print("      export OSMNBITEST_VIM_NAME=vim-name")
    print("      export OSMNBITEST_VIM_URL=vim-url")
    print("      export OSMNBITEST_VIM_TYPE=vim-type")
    print("      export OSMNBITEST_VIM_TENANT=vim-tenant")
    print("      export OSMNBITEST_VIM_USER=vim-user")
    print("      export OSMNBITEST_VIM_PASSWORD=vim-password")
    print("      export OSMNBITEST_VIM_CONFIG=\"vim-config\"")
    print("      export OSMNBITEST_NS_NAME=\"vim-config\"")
    return


r_header_json = {"Content-type": "application/json"}
headers_json = {"Content-type": "application/json", "Accept": "application/json"}
r_header_yaml = {"Content-type": "application/yaml"}
headers_yaml = {"Content-type": "application/yaml", "Accept": "application/yaml"}
r_header_text = {"Content-type": "text/plain"}
r_header_octect = {"Content-type": "application/octet-stream"}
headers_text = {"Accept": "text/plain,application/yaml"}
r_header_zip = {"Content-type": "application/zip"}
headers_zip = {"Accept": "application/zip,application/yaml"}
headers_zip_yaml = {"Accept": "application/yaml", "Content-type": "application/zip"}
r_headers_yaml_location_vnfd = {"Location": "/vnfpkgm/v1/vnf_packages_content/", "Content-Type": "application/yaml"}
r_headers_yaml_location_nsd = {"Location": "/nsd/v1/ns_descriptors_content/", "Content-Type": "application/yaml"}
r_headers_yaml_location_nst = {"Location": "/nst/v1/netslice_templates_content", "Content-Type": "application/yaml"}
r_headers_yaml_location_nslcmop = {"Location": "nslcm/v1/ns_lcm_op_occs/", "Content-Type": "application/yaml"}

# test ones authorized
test_authorized_list = (
    ("AU1", "Invalid vnfd id", "GET", "/vnfpkgm/v1/vnf_packages/non-existing-id",
     headers_json, None, 404, r_header_json, "json"),
    ("AU2", "Invalid nsd id", "GET", "/nsd/v1/ns_descriptors/non-existing-id",
     headers_yaml, None, 404, r_header_yaml, "yaml"),
    ("AU3", "Invalid nsd id", "DELETE", "/nsd/v1/ns_descriptors_content/non-existing-id",
     headers_yaml, None, 404, r_header_yaml, "yaml"),
)
timeout = 120   # general timeout
timeout_deploy = 60*10        # timeout for NS deploying without charms
timeout_configure = 60*20     # timeout for NS deploying and configuring


class TestException(Exception):
    pass


class TestRest:
    def __init__(self, url_base, header_base=None, verify=False, user="admin", password="admin", project="admin"):
        self.url_base = url_base
        if header_base is None:
            self.header_base = {}
        else:
            self.header_base = header_base.copy()
        self.s = requests.session()
        self.s.headers = self.header_base
        self.verify = verify
        self.token = False
        self.user = user
        self.password = password
        self.project = project
        self.vim_id = None
        # contains ID of tests obtained from Location response header. "" key contains last obtained id
        self.last_id = ""
        self.test_name = None
        self.step = 0   # number of subtest under test
        self.passed_tests = 0
        self.failed_tests = 0

    def set_test_name(self, test_name):
        self.test_name = test_name
        self.step = 0
        self.last_id = ""
        
    def set_header(self, header):
        self.s.headers.update(header)

    def set_tet_name(self, test_name):
        self.test_name = test_name

    def unset_header(self, key):
        if key in self.s.headers:
            del self.s.headers[key]

    def test(self, description, method, url, headers, payload, expected_codes, expected_headers,
             expected_payload, store_file=None, pooling=False):
        """
        Performs an http request and check http code response. Exit if different than allowed. It get the returned id
        that can be used by following test in the URL with {name} where name is the name of the test
        :param description:  description of the test
        :param method: HTTP method: GET,PUT,POST,DELETE,...
        :param url: complete URL or relative URL
        :param headers: request headers to add to the base headers
        :param payload: Can be a dict, transformed to json, a text or a file if starts with '@'
        :param expected_codes: expected response codes, can be int, int tuple or int range
        :param expected_headers: expected response headers, dict with key values
        :param expected_payload: expected payload, 0 if empty, 'yaml', 'json', 'text', 'zip', 'octet-stream'
        :param store_file: filename to store content
        :param pooling: if True do not count neither log this test. Because a pooling is done with many equal requests
        :return: requests response
        """
        r = None
        try:
            if not self.s:
                self.s = requests.session()
            # URL
            if not url:
                url = self.url_base
            elif not url.startswith("http"):
                url = self.url_base + url

            # replace url <> with the last ID
            url = url.replace("<>", self.last_id)
            if payload:
                if isinstance(payload, str):
                    if payload.startswith("@"):
                        mode = "r"
                        file_name = payload[1:]
                        if payload.startswith("@b"):
                            mode = "rb"
                            file_name = payload[2:]
                        with open(file_name, mode) as f:
                            payload = f.read()
                elif isinstance(payload, dict):
                    payload = json.dumps(payload)

            if not pooling:
                test_description = "Test {}{} {} {} {}".format(self.test_name, self.step, description, method, url)
                logger.warning(test_description)
                self.step += 1
            stream = False
            if expected_payload in ("zip", "octet-string") or store_file:
                stream = True
            __retry = 0
            while True:
                try:
                    r = getattr(self.s, method.lower())(url, data=payload, headers=headers, verify=self.verify,
                                                        stream=stream)
                    break
                except requests.exceptions.ConnectionError as e:
                    if __retry == 2:
                        raise
                    logger.error("Exception {}. Retrying".format(e))
                    __retry += 1

            if expected_payload in ("zip", "octet-string") or store_file:
                logger.debug("RX {}".format(r.status_code))
            else:
                logger.debug("RX {}: {}".format(r.status_code, r.text))

            # check response
            if expected_codes:
                if isinstance(expected_codes, int):
                    expected_codes = (expected_codes,)
                if r.status_code not in expected_codes:
                    raise TestException(
                        "Got status {}. Expected {}. {}".format(r.status_code, expected_codes, r.text))

            if expected_headers:
                for header_key, header_val in expected_headers.items():
                    if header_key.lower() not in r.headers:
                        raise TestException("Header {} not present".format(header_key))
                    if header_val and header_val.lower() not in r.headers[header_key]:
                        raise TestException("Header {} does not contain {} but {}".format(header_key, header_val,
                                            r.headers[header_key]))

            if expected_payload is not None:
                if expected_payload == 0 and len(r.content) > 0:
                    raise TestException("Expected empty payload")
                elif expected_payload == "json":
                    try:
                        r.json()
                    except Exception as e:
                        raise TestException("Expected json response payload, but got Exception {}".format(e))
                elif expected_payload == "yaml":
                    try:
                        yaml.safe_load(r.text)
                    except Exception as e:
                        raise TestException("Expected yaml response payload, but got Exception {}".format(e))
                elif expected_payload in ("zip", "octet-string"):
                    if len(r.content) == 0:
                        raise TestException("Expected some response payload, but got empty")
                    # try:
                    #     tar = tarfile.open(None, 'r:gz', fileobj=r.raw)
                    #     for tarinfo in tar:
                    #         tarname = tarinfo.name
                    #         print(tarname)
                    # except Exception as e:
                    #     raise TestException("Expected zip response payload, but got Exception {}".format(e))
                elif expected_payload == "text":
                    if len(r.content) == 0:
                        raise TestException("Expected some response payload, but got empty")
                    # r.text
            if store_file:
                with open(store_file, 'wb') as fd:
                    for chunk in r.iter_content(chunk_size=128):
                        fd.write(chunk)

            location = r.headers.get("Location")
            if location:
                _id = location[location.rfind("/") + 1:]
                if _id:
                    self.last_id = str(_id)
            if not pooling:
                self.passed_tests += 1
            return r
        except TestException as e:
            self.failed_tests += 1
            r_status_code = None
            r_text = None
            if r:
                r_status_code = r.status_code
                r_text = r.text
            logger.error("{} \nRX code{}: {}".format(e, r_status_code, r_text))
            return None
            # exit(1)
        except IOError as e:
            if store_file:
                logger.error("Cannot open file {}: {}".format(store_file, e))
            else:
                logger.error("Exception: {}".format(e), exc_info=True)
            self.failed_tests += 1
            return None
            # exit(1)
        except requests.exceptions.RequestException as e:
            logger.error("Exception: {}".format(e))

    def get_autorization(self):  # user=None, password=None, project=None):
        if self.token:  # and self.user == user and self.password == password and self.project == project:
            return
        # self.user = user
        # self.password = password
        # self.project = project
        r = self.test("Obtain token", "POST", "/admin/v1/tokens", headers_json,
                      {"username": self.user, "password": self.password, "project_id": self.project},
                      (200, 201), r_header_json, "json")
        if not r:
            return
        response = r.json()
        self.token = response["id"]
        self.set_header({"Authorization": "Bearer {}".format(self.token)})

    def remove_authorization(self):
        if self.token:
            self.test("Delete token", "DELETE", "/admin/v1/tokens/{}".format(self.token), headers_json,
                      None, (200, 201, 204), None, None)
        self.token = None
        self.unset_header("Authorization")

    def get_create_vim(self, test_osm):
        if self.vim_id:
            return self.vim_id
        self.get_autorization()
        if test_osm:
            vim_name = os.environ.get("OSMNBITEST_VIM_NAME")
            if not vim_name:
                raise TestException(
                    "Needed to define OSMNBITEST_VIM_XXX variables to create a real VIM for deployment")
        else:
            vim_name = "fakeVim"
        # Get VIM
        r = self.test("Get VIM ID", "GET", "/admin/v1/vim_accounts?name={}".format(vim_name), headers_json,
                      None, 200, r_header_json, "json")
        if not r:
            return
        vims = r.json()
        if vims:
            return vims[0]["_id"]
        # Add VIM
        if test_osm:
            # check needed environ parameters:
            if not os.environ.get("OSMNBITEST_VIM_URL") or not os.environ.get("OSMNBITEST_VIM_TENANT"):
                raise TestException("Env OSMNBITEST_VIM_URL and OSMNBITEST_VIM_TENANT are needed for create a real VIM"
                                    " to deploy on whit the --test-osm option")
            vim_data = "{{schema_version: '1.0', name: '{}', vim_type: {}, vim_url: '{}', vim_tenant_name: '{}', "\
                       "vim_user: {}, vim_password: {}".format(vim_name,
                                                               os.environ.get("OSMNBITEST_VIM_TYPE", "openstack"),
                                                               os.environ.get("OSMNBITEST_VIM_URL"),
                                                               os.environ.get("OSMNBITEST_VIM_TENANT"),
                                                               os.environ.get("OSMNBITEST_VIM_USER"),
                                                               os.environ.get("OSMNBITEST_VIM_PASSWORD"))
            if os.environ.get("OSMNBITEST_VIM_CONFIG"):
                vim_data += " ,config: {}".format(os.environ.get("OSMNBITEST_VIM_CONFIG"))
            vim_data += "}"
        else:
            vim_data = "{schema_version: '1.0', name: fakeVim, vim_type: openstack, vim_url: 'http://10.11.12.13/fake'"\
                       ", vim_tenant_name: 'vimtenant', vim_user: vimuser, vim_password: vimpassword}"
        self.test("Create VIM", "POST", "/admin/v1/vim_accounts", headers_yaml, vim_data,
                  (201), {"Location": "/admin/v1/vim_accounts/", "Content-Type": "application/yaml"}, "yaml")
        return self.last_id

    def print_results(self):
        print("\n\n\n--------------------------------------------")
        print("TEST RESULTS: Total: {}, Passed: {}, Failed: {}".format(self.passed_tests + self.failed_tests,
                                                                       self.passed_tests, self.failed_tests))
        print("--------------------------------------------")

    def wait_until_delete(self, url_op, timeout_delete):
        """
        Make a pooling until topic is not present, because of deleted
        :param url_op:
        :param timeout_delete:
        :return:
        """
        description = "Wait to topic being deleted"
        test_description = "Test {}{} {} {} {}".format(self.test_name, self.step, description, "GET", url_op)
        logger.warning(test_description)
        self.step += 1

        wait = timeout_delete
        while wait >= 0:
            r = self.test(description, "GET", url_op, headers_yaml, None, (200, 404), None, r_header_yaml, "yaml",
                          pooling=True)
            if not r:
                return
            if r.status_code == 404:
                self.passed_tests += 1
                break
            elif r.status_code == 200:
                wait -= 5
                sleep(5)
        else:
            raise TestException("Topic is not deleted after {} seconds".format(timeout_delete))
            self.failed_tests += 1

    def wait_operation_ready(self, ns_nsi, opp_id, timeout, expected_fail=False):
        """
        Wait until nslcmop or nsilcmop finished
        :param ns_nsi: "ns" o "nsi"
        :param opp_id: Id o fthe operation
        :param timeout:
        :param expected_fail:
        :return: None. Updates passed/failed_tests
        """
        if ns_nsi == "ns":
            url_op = "/nslcm/v1/ns_lcm_op_occs/{}".format(opp_id)
        else:
            url_op = "/nsilcm/v1/nsi_lcm_op_occs/{}".format(opp_id)
        description = "Wait to {} lcm operation complete".format(ns_nsi)
        test_description = "Test {}{} {} {} {}".format(self.test_name, self.step, description, "GET", url_op)
        logger.warning(test_description)
        self.step += 1
        wait = timeout
        while wait >= 0:
            r = self.test(description, "GET", url_op, headers_json, None,
                          200, r_header_json, "json", pooling=True)
            if not r:
                return
            nslcmop = r.json()
            if "COMPLETED" in nslcmop["operationState"]:
                if expected_fail:
                    logger.error("NS terminate has success, expecting failing: {}".format(nslcmop["detailed-status"]))
                    self.failed_tests += 1
                else:
                    self.passed_tests += 1
                break
            elif "FAILED" in nslcmop["operationState"]:
                if not expected_fail:
                    logger.error("NS terminate has failed: {}".format(nslcmop["detailed-status"]))
                    self.failed_tests += 1
                else:
                    self.passed_tests += 1
                break

            print(".", end="", file=stderr)
            wait -= 10
            sleep(10)
        else:
            self.failed_tests += 1
            logger.error("NS instantiate is not terminate after {} seconds".format(timeout))
            return
        print("", file=stderr)


class TestNonAuthorized:
    description = "Test invalid URLs. methods and no authorization"

    @staticmethod
    def run(engine, test_osm, manual_check, test_params=None):
        engine.set_test_name("NonAuth")
        engine.remove_authorization()
        test_not_authorized_list = (
            ("Invalid token", "GET", "/admin/v1/users", headers_json, None, 401, r_header_json, "json"),
            ("Invalid URL", "POST", "/admin/v1/nonexist", headers_yaml, None, 405, r_header_yaml, "yaml"),
            ("Invalid version", "DELETE", "/admin/v2/users", headers_yaml, None, 405, r_header_yaml, "yaml"),
        )
        for t in test_not_authorized_list:
            engine.test(*t)


class TestUsersProjects:
    description = "test project and user creation"

    @staticmethod
    def run(engine, test_osm, manual_check, test_params=None):
        engine.set_test_name("UserProject")
        engine.get_autorization()
        engine.test("Create project non admin", "POST", "/admin/v1/projects", headers_json, {"name": "P1"},
                    (201, 204), {"Location": "/admin/v1/projects/", "Content-Type": "application/json"}, "json")
        engine.test("Create project admin", "POST", "/admin/v1/projects", headers_json,
                    {"name": "Padmin", "admin": True}, (201, 204),
                    {"Location": "/admin/v1/projects/", "Content-Type": "application/json"}, "json")
        engine.test("Create project bad format", "POST", "/admin/v1/projects", headers_json, {"name": 1}, 422,
                    r_header_json, "json")
        engine.test("Create user with bad project", "POST", "/admin/v1/users", headers_json,
                    {"username": "U1", "projects": ["P1", "P2", "Padmin"], "password": "pw1"}, 409,
                    r_header_json, "json")
        engine.test("Create user with bad project and force", "POST", "/admin/v1/users?FORCE=True", headers_json,
                    {"username": "U1", "projects": ["P1", "P2", "Padmin"], "password": "pw1"}, 201,
                    {"Location": "/admin/v1/users/", "Content-Type": "application/json"}, "json")
        engine.test("Create user 2", "POST", "/admin/v1/users", headers_json,
                    {"username": "U2", "projects": ["P1"], "password": "pw2"}, 201,
                    {"Location": "/admin/v1/users/", "Content-Type": "application/json"}, "json")
        engine.test("Edit user U1, delete  P2 project", "PATCH", "/admin/v1/users/U1", headers_json,
                    {"projects": {"$'P2'": None}}, 204, None, None)
        res = engine.test("Check user U1, contains the right projects", "GET", "/admin/v1/users/U1",
                          headers_json, None, 200, None, json)
        if res:
            u1 = res.json()
            # print(u1)
            expected_projects = ["P1", "Padmin"]
            if u1["projects"] != expected_projects:
                logger.error("User content projects '{}' different than expected '{}'. Edition has not done"
                             " properly".format(u1["projects"], expected_projects))
                engine.failed_tests += 1

        engine.test("Edit user U1, set Padmin as default project", "PUT", "/admin/v1/users/U1", headers_json,
                    {"projects": {"$'Padmin'": None, "$+[0]": "Padmin"}}, 204, None, None)
        res = engine.test("Check user U1, contains the right projects", "GET", "/admin/v1/users/U1",
                          headers_json, None, 200, None, json)
        if res:
            u1 = res.json()
            # print(u1)
            expected_projects = ["Padmin", "P1"]
            if u1["projects"] != expected_projects:
                logger.error("User content projects '{}' different than expected '{}'. Edition has not done"
                             " properly".format(u1["projects"], expected_projects))
                engine.failed_tests += 1

        engine.test("Edit user U1, change password", "PATCH", "/admin/v1/users/U1", headers_json,
                    {"password": "pw1_new"}, 204, None, None)

        engine.test("Change to project P1 non existing", "POST", "/admin/v1/tokens/", headers_json,
                    {"project_id": "P1"}, 401, r_header_json, "json")

        res = engine.test("Change to user U1 project P1", "POST", "/admin/v1/tokens", headers_json,
                          {"username": "U1", "password": "pw1_new", "project_id": "P1"}, (200, 201),
                          r_header_json, "json")
        if res:
            response = res.json()
            engine.set_header({"Authorization": "Bearer {}".format(response["id"])})

        engine.test("Edit user projects non admin", "PUT", "/admin/v1/users/U1", headers_json,
                    {"projects": {"$'P1'": None}}, 401, r_header_json, "json")
        engine.test("Add new project non admin", "POST", "/admin/v1/projects", headers_json,
                    {"name": "P2"}, 401, r_header_json, "json")
        engine.test("Add new user non admin", "POST", "/admin/v1/users", headers_json,
                    {"username": "U3", "projects": ["P1"], "password": "pw3"}, 401,
                    r_header_json, "json")

        res = engine.test("Change to user U1 project Padmin", "POST", "/admin/v1/tokens", headers_json,
                          {"project_id": "Padmin"}, (200, 201), r_header_json, "json")
        if res:
            response = res.json()
            engine.set_header({"Authorization": "Bearer {}".format(response["id"])})

        engine.test("Add new project admin", "POST", "/admin/v1/projects", headers_json, {"name": "P2"},
                    (201, 204), {"Location": "/admin/v1/projects/", "Content-Type": "application/json"}, "json")
        engine.test("Add new user U3 admin", "POST", "/admin/v1/users",
                    headers_json, {"username": "U3", "projects": ["P2"], "password": "pw3"}, (201, 204),
                    {"Location": "/admin/v1/users/", "Content-Type": "application/json"}, "json")
        engine.test("Edit user projects admin", "PUT", "/admin/v1/users/U3", headers_json,
                    {"projects": ["P2"]}, 204, None, None)

        engine.test("Delete project P2 conflict", "DELETE", "/admin/v1/projects/P2", headers_json, None, 409,
                    r_header_json, "json")
        engine.test("Delete project P2 forcing", "DELETE", "/admin/v1/projects/P2?FORCE=True", headers_json,
                    None, 204, None, None)

        engine.test("Delete user U1. Conflict deleting own user", "DELETE", "/admin/v1/users/U1", headers_json,
                    None, 409, r_header_json, "json")
        engine.test("Delete user U2", "DELETE", "/admin/v1/users/U2", headers_json, None, 204, None, None)
        engine.test("Delete user U3", "DELETE", "/admin/v1/users/U3", headers_json, None, 204, None, None)
        # change to admin
        engine.remove_authorization()   # To force get authorization
        engine.get_autorization()
        engine.test("Delete user U1", "DELETE", "/admin/v1/users/U1", headers_json, None, 204, None, None)
        engine.test("Delete project P1", "DELETE", "/admin/v1/projects/P1", headers_json, None, 204, None, None)
        engine.test("Delete project Padmin", "DELETE", "/admin/v1/projects/Padmin", headers_json, None, 204,
                    None, None)


class TestFakeVim:
    description = "Creates/edit/delete fake VIMs and SDN controllers"

    def __init__(self):
        self.vim = {
            "schema_version": "1.0",
            "schema_type": "No idea",
            "name": "myVim",
            "description": "Descriptor name",
            "vim_type": "openstack",
            "vim_url": "http://localhost:/vim",
            "vim_tenant_name": "vimTenant",
            "vim_user": "user",
            "vim_password": "password",
            "config": {"config_param": 1}
        }
        self.sdn = {
            "name": "sdn-name",
            "description": "sdn-description",
            "dpid": "50:50:52:54:00:94:21:21",
            "ip": "192.168.15.17",
            "port": 8080,
            "type": "opendaylight",
            "version": "3.5.6",
            "user": "user",
            "password": "passwd"
        }
        self.port_mapping = [
            {"compute_node": "compute node 1",
             "ports": [{"pci": "0000:81:00.0", "switch_port": "port-2/1", "switch_mac": "52:54:00:94:21:21"},
                       {"pci": "0000:81:00.1", "switch_port": "port-2/2", "switch_mac": "52:54:00:94:21:22"}
                       ]},
            {"compute_node": "compute node 2",
             "ports": [{"pci": "0000:81:00.0", "switch_port": "port-2/3", "switch_mac": "52:54:00:94:21:23"},
                       {"pci": "0000:81:00.1", "switch_port": "port-2/4", "switch_mac": "52:54:00:94:21:24"}
                       ]}
        ]

    def run(self, engine, test_osm, manual_check, test_params=None):

        vim_bad = self.vim.copy()
        vim_bad.pop("name")

        engine.set_test_name("FakeVim")
        engine.get_autorization()
        engine.test("Create VIM", "POST", "/admin/v1/vim_accounts", headers_json, self.vim, (201, 204),
                    {"Location": "/admin/v1/vim_accounts/", "Content-Type": "application/json"}, "json")
        vim_id = engine.last_id
        engine.test("Create VIM without name, bad schema", "POST", "/admin/v1/vim_accounts", headers_json,
                    vim_bad, 422, None, headers_json)
        engine.test("Create VIM name repeated", "POST", "/admin/v1/vim_accounts", headers_json, self.vim,
                    409, None, headers_json)
        engine.test("Show VIMs", "GET", "/admin/v1/vim_accounts", headers_yaml, None, 200, r_header_yaml,
                    "yaml")
        engine.test("Show VIM", "GET", "/admin/v1/vim_accounts/{}".format(vim_id), headers_yaml, None, 200,
                    r_header_yaml, "yaml")
        if not test_osm:
            # delete with FORCE
            engine.test("Delete VIM", "DELETE", "/admin/v1/vim_accounts/{}?FORCE=True".format(vim_id), headers_yaml,
                        None, 202, None, 0)
            engine.test("Check VIM is deleted", "GET", "/admin/v1/vim_accounts/{}".format(vim_id), headers_yaml, None,
                        404, r_header_yaml, "yaml")
        else:
            # delete and wait until is really deleted
            engine.test("Delete VIM", "DELETE", "/admin/v1/vim_accounts/{}".format(vim_id), headers_yaml, None, 202,
                        None, 0)
            engine.wait_until_delete("/admin/v1/vim_accounts/{}".format(vim_id), timeout)


class TestVIMSDN(TestFakeVim):
    description = "Creates VIM with SDN editing SDN controllers and port_mapping"

    def __init__(self):
        TestFakeVim.__init__(self)
        self.wim = {
            "schema_version": "1.0",
            "schema_type": "No idea",
            "name": "myWim",
            "description": "Descriptor name",
            "wim_type": "odl",
            "wim_url": "http://localhost:/wim",
            "user": "user",
            "password": "password",
            "config": {"config_param": 1}
        }

    def run(self, engine, test_osm, manual_check, test_params=None):
        engine.set_test_name("VimSdn")
        engine.get_autorization()
        # Added SDN
        engine.test("Create SDN", "POST", "/admin/v1/sdns", headers_json, self.sdn, (201, 204),
                    {"Location": "/admin/v1/sdns/", "Content-Type": "application/json"}, "json")
        sdnc_id = engine.last_id
        # sleep(5)
        # Edit SDN
        engine.test("Edit SDN", "PATCH", "/admin/v1/sdns/{}".format(sdnc_id), headers_json, {"name": "new_sdn_name"},
                    204, None, None)
        # sleep(5)
        # VIM with SDN
        self.vim["config"]["sdn-controller"] = sdnc_id
        self.vim["config"]["sdn-port-mapping"] = self.port_mapping
        engine.test("Create VIM", "POST", "/admin/v1/vim_accounts", headers_json, self.vim, (200, 204, 201),
                    {"Location": "/admin/v1/vim_accounts/", "Content-Type": "application/json"}, "json"),

        vim_id = engine.last_id
        self.port_mapping[0]["compute_node"] = "compute node XX"
        engine.test("Edit VIM change port-mapping", "PUT", "/admin/v1/vim_accounts/{}".format(vim_id), headers_json,
                    {"config": {"sdn-port-mapping": self.port_mapping}}, 204, None, None)
        engine.test("Edit VIM remove port-mapping", "PUT", "/admin/v1/vim_accounts/{}".format(vim_id), headers_json,
                    {"config": {"sdn-port-mapping": None}}, 204, None, None)

        engine.test("Create WIM", "POST", "/admin/v1/wim_accounts", headers_json, self.wim, (200, 204, 201),
                    {"Location": "/admin/v1/wim_accounts/", "Content-Type": "application/json"}, "json"),
        wim_id = engine.last_id

        if not test_osm:
            # delete with FORCE
            engine.test("Delete VIM remove port-mapping", "DELETE",
                        "/admin/v1/vim_accounts/{}?FORCE=True".format(vim_id), headers_json, None, 202, None, 0)
            engine.test("Delete SDNC", "DELETE", "/admin/v1/sdns/{}?FORCE=True".format(sdnc_id), headers_json, None,
                        202, None, 0)

            engine.test("Delete WIM", "DELETE",
                        "/admin/v1/wim_accounts/{}?FORCE=True".format(wim_id), headers_json, None, 202, None, 0)
            engine.test("Check VIM is deleted", "GET", "/admin/v1/vim_accounts/{}".format(vim_id), headers_yaml,
                        None, 404, r_header_yaml, "yaml")
            engine.test("Check SDN is deleted", "GET", "/admin/v1/sdns/{}".format(sdnc_id), headers_yaml, None,
                        404, r_header_yaml, "yaml")
            engine.test("Check WIM is deleted", "GET", "/admin/v1/wim_accounts/{}".format(wim_id), headers_yaml,
                        None, 404, r_header_yaml, "yaml")
        else:
            if manual_check:
                input('VIM, SDN, WIM has been deployed. Perform manual check and press enter to resume')
            # delete and wait until is really deleted
            engine.test("Delete VIM remove port-mapping", "DELETE", "/admin/v1/vim_accounts/{}".format(vim_id),
                        headers_json, None, (202, 201, 204), None, 0)
            engine.test("Delete SDN", "DELETE", "/admin/v1/sdns/{}".format(sdnc_id), headers_json, None,
                        (202, 201, 204), None, 0)
            engine.test("Delete VIM", "DELETE", "/admin/v1/wim_accounts/{}".format(wim_id),
                        headers_json, None, (202, 201, 204), None, 0)
            engine.wait_until_delete("/admin/v1/vim_accounts/{}".format(vim_id), timeout)
            engine.wait_until_delete("/admin/v1/sdns/{}".format(sdnc_id), timeout)
            engine.wait_until_delete("/admin/v1/wim_accounts/{}".format(wim_id), timeout)


class TestDeploy:
    description = "Base class for downloading descriptors from ETSI, onboard and deploy in real VIM"

    def __init__(self):
        self.test_name = "DEPLOY"
        self.nsd_id = None
        self.vim_id = None
        self.ns_id = None
        self.vnfds_id = []
        self.descriptor_url = "https://osm-download.etsi.org/ftp/osm-3.0-three/2nd-hackfest/packages/"
        self.vnfd_filenames = ("cirros_vnf.tar.gz",)
        self.nsd_filename = "cirros_2vnf_ns.tar.gz"
        self.descriptor_edit = None
        self.uses_configuration = False
        self.users = {}
        self.passwords = {}
        self.commands = {}
        self.keys = {}
        self.timeout = 120
        self.qforce = ""
        self.ns_params = None

    def create_descriptors(self, engine):
        temp_dir = os.path.dirname(os.path.abspath(__file__)) + "/temp/"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        for vnfd_index, vnfd_filename in enumerate(self.vnfd_filenames):
            if "/" in vnfd_filename:
                vnfd_filename_path = vnfd_filename
                if not os.path.exists(vnfd_filename_path):
                    raise TestException("File '{}' does not exist".format(vnfd_filename_path))
            else:
                vnfd_filename_path = temp_dir + vnfd_filename
                if not os.path.exists(vnfd_filename_path):
                    with open(vnfd_filename_path, "wb") as file:
                        response = requests.get(self.descriptor_url + vnfd_filename)
                        if response.status_code >= 300:
                            raise TestException("Error downloading descriptor from '{}': {}".format(
                                self.descriptor_url + vnfd_filename, response.status_code))
                        file.write(response.content)
            if vnfd_filename_path.endswith(".yaml"):
                headers = headers_yaml
            else:
                headers = headers_zip_yaml
            if randint(0, 1) == 0:
                # vnfd CREATE AND UPLOAD in one step:
                engine.test("Onboard VNFD in one step", "POST",
                            "/vnfpkgm/v1/vnf_packages_content" + self.qforce, headers, "@b" + vnfd_filename_path, 201,
                            r_headers_yaml_location_vnfd,
                            "yaml")
                self.vnfds_id.append(engine.last_id)
            else:
                # vnfd CREATE AND UPLOAD ZIP
                engine.test("Onboard VNFD step 1", "POST", "/vnfpkgm/v1/vnf_packages",
                            headers_json, None, 201,
                            {"Location": "/vnfpkgm/v1/vnf_packages/", "Content-Type": "application/json"}, "json")
                self.vnfds_id.append(engine.last_id)
                engine.test("Onboard VNFD step 2 as ZIP", "PUT",
                            "/vnfpkgm/v1/vnf_packages/<>/package_content" + self.qforce,
                            headers, "@b" + vnfd_filename_path, 204, None, 0)

            if self.descriptor_edit:
                if "vnfd{}".format(vnfd_index) in self.descriptor_edit:
                    # Modify VNFD
                    engine.test("Edit VNFD ", "PATCH",
                                "/vnfpkgm/v1/vnf_packages/{}".format(self.vnfds_id[-1]),
                                headers_yaml, self.descriptor_edit["vnfd{}".format(vnfd_index)], 204, None, None)

        if "/" in self.nsd_filename:
            nsd_filename_path = self.nsd_filename
            if not os.path.exists(nsd_filename_path):
                raise TestException("File '{}' does not exist".format(nsd_filename_path))
        else:
            nsd_filename_path = temp_dir + self.nsd_filename
            if not os.path.exists(nsd_filename_path):
                with open(nsd_filename_path, "wb") as file:
                    response = requests.get(self.descriptor_url + self.nsd_filename)
                    if response.status_code >= 300:
                        raise TestException("Error downloading descriptor from '{}': {}".format(
                            self.descriptor_url + self.nsd_filename, response.status_code))
                    file.write(response.content)
        if nsd_filename_path.endswith(".yaml"):
            headers = headers_yaml
        else:
            headers = headers_zip_yaml

        if randint(0, 1) == 0:
            # nsd CREATE AND UPLOAD in one step:
            engine.test("Onboard NSD in one step", "POST",
                        "/nsd/v1/ns_descriptors_content" + self.qforce, headers, "@b" + nsd_filename_path, 201,
                        r_headers_yaml_location_nsd, yaml)
            self.nsd_id = engine.last_id
        else:
            # nsd CREATE AND UPLOAD ZIP
            engine.test("Onboard NSD step 1", "POST", "/nsd/v1/ns_descriptors",
                        headers_json, None, 201,
                        {"Location": "/nsd/v1/ns_descriptors/", "Content-Type": "application/json"}, "json")
            self.nsd_id = engine.last_id
            engine.test("Onboard NSD step 2 as ZIP", "PUT",
                        "/nsd/v1/ns_descriptors/<>/nsd_content" + self.qforce,
                        headers, "@b" + nsd_filename_path, 204, None, 0)

        if self.descriptor_edit and "nsd" in self.descriptor_edit:
            # Modify NSD
            engine.test("Edit NSD ", "PATCH",
                        "/nsd/v1/ns_descriptors/{}".format(self.nsd_id),
                        headers_yaml, self.descriptor_edit["nsd"], 204, None, None)

    def delete_descriptors(self, engine):
        # delete descriptors
        engine.test("Delete NSSD SOL005", "DELETE",
                    "/nsd/v1/ns_descriptors/{}".format(self.nsd_id),
                    headers_yaml, None, 204, None, 0)
        for vnfd_id in self.vnfds_id:
            engine.test("Delete VNFD SOL005", "DELETE",
                        "/vnfpkgm/v1/vnf_packages/{}".format(vnfd_id), headers_yaml, None, 204, None, 0)

    def instantiate(self, engine, ns_data):
        ns_data_text = yaml.safe_dump(ns_data, default_flow_style=True, width=256)
        # create NS Two steps
        r = engine.test("Create NS step 1", "POST", "/nslcm/v1/ns_instances",
                        headers_yaml, ns_data_text, 201,
                        {"Location": "nslcm/v1/ns_instances/", "Content-Type": "application/yaml"}, "yaml")
        if not r:
            return
        self.ns_id = engine.last_id
        engine.test("Instantiate NS step 2", "POST",
                    "/nslcm/v1/ns_instances/{}/instantiate".format(self.ns_id), headers_yaml, ns_data_text,
                    201, r_headers_yaml_location_nslcmop, "yaml")
        nslcmop_id = engine.last_id

        if test_osm:
            # Wait until status is Ok
            timeout = timeout_configure if self.uses_configuration else timeout_deploy
            engine.wait_operation_ready("ns", nslcmop_id, timeout)

    def terminate(self, engine):
        # remove deployment
        if test_osm:
            engine.test("Terminate NS", "POST", "/nslcm/v1/ns_instances/{}/terminate".format(self.ns_id), headers_yaml,
                        None, 201, r_headers_yaml_location_nslcmop, "yaml")
            nslcmop2_id = engine.last_id
            # Wait until status is Ok
            engine.wait_operation_ready("ns", nslcmop2_id, timeout_deploy)

            engine.test("Delete NS", "DELETE", "/nslcm/v1/ns_instances/{}".format(self.ns_id), headers_yaml, None,
                        204, None, 0)
        else:
            engine.test("Delete NS with FORCE", "DELETE", "/nslcm/v1/ns_instances/{}?FORCE=True".format(self.ns_id),
                        headers_yaml, None, 204, None, 0)

        # check all it is deleted
        engine.test("Check NS is deleted", "GET", "/nslcm/v1/ns_instances/{}".format(self.ns_id), headers_yaml, None,
                    404, None, "yaml")
        r = engine.test("Check NSLCMOPs are deleted", "GET",
                        "/nslcm/v1/ns_lcm_op_occs?nsInstanceId={}".format(self.ns_id), headers_json, None,
                        200, None, "json")
        if not r:
            return
        nslcmops = r.json()
        if not isinstance(nslcmops, list) or nslcmops:
            raise TestException("NS {} deleted but with ns_lcm_op_occ active: {}".format(self.ns_id, nslcmops))

    def test_ns(self, engine, test_osm, commands=None, users=None, passwds=None, keys=None, timeout=0):

        r = engine.test("GET VNFR IDs", "GET",
                        "/nslcm/v1/ns_instances/{}".format(self.ns_id), headers_json, None,
                        200, r_header_json, "json")
        if not r:
            return
        ns_data = r.json()

        vnfr_list = ns_data['constituent-vnfr-ref']
        time = 0
        _commands = commands if commands is not None else self.commands
        _users = users if users is not None else self.users
        _passwds = passwds if passwds is not None else self.passwords
        _keys = keys if keys is not None else self.keys
        _timeout = timeout if timeout != 0 else self.timeout

        for vnfr_id in vnfr_list:
            r = engine.test("Get VNFR to get IP_ADDRESS", "GET",
                            "/nslcm/v1/vnfrs/{}".format(vnfr_id), headers_json, None,
                            200, r_header_json, "json")
            if not r:
                continue
            vnfr_data = r.json()

            vnf_index = str(vnfr_data["member-vnf-index-ref"])
            if not _commands.get(vnf_index):
                continue
            if vnfr_data.get("ip-address"):
                description = "Exec command='{}' at VNFR={} IP={}".format(_commands.get(vnf_index)[0], vnf_index,
                                                                          vnfr_data['ip-address'])
                engine.step += 1
                test_description = "{}{} {}".format(engine.test_name, engine.step, description)
                logger.warning(test_description)
                while _timeout >= time:
                    result, message = self.do_checks([vnfr_data["ip-address"]],
                                                     vnf_index=vnfr_data["member-vnf-index-ref"],
                                                     commands=_commands.get(vnf_index), user=_users.get(vnf_index),
                                                     passwd=_passwds.get(vnf_index), key=_keys.get(vnf_index))
                    if result == 1:
                        engine.passed_tests += 1
                        logger.debug(message)
                        break
                    elif result == 0:
                        time += 20
                        sleep(20)
                    elif result == -1:
                        engine.failed_tests += 1
                        logger.error(message)
                        break
                else:
                    time -= 20
                    engine.failed_tests += 1
                    logger.error(message)
            else:
                engine.failed_tests += 1
                logger.error("VNFR {} has not mgmt address. Check failed".format(vnfr_id))

    def do_checks(self, ip, vnf_index, commands=[], user=None, passwd=None, key=None):
        try:
            import urllib3
            from pssh.clients import ParallelSSHClient
            from pssh.utils import load_private_key
            from ssh2 import exceptions as ssh2Exception
        except ImportError as e:
            logger.critical("Package <pssh> or/and <urllib3> is not installed. Please add them with 'pip3 install "
                            "parallel-ssh urllib3': {}".format(e))
            return -1, "install needed packages 'pip3 install parallel-ssh urllib3'"
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        try:
            p_host = os.environ.get("PROXY_HOST")
            p_user = os.environ.get("PROXY_USER")
            p_password = os.environ.get("PROXY_PASSWD")

            if key:
                pkey = load_private_key(key)
            else:
                pkey = None

            client = ParallelSSHClient(ip, user=user, password=passwd, pkey=pkey, proxy_host=p_host,
                                       proxy_user=p_user, proxy_password=p_password, timeout=10, num_retries=0)
            for cmd in commands:
                output = client.run_command(cmd)
                client.join(output)
                if output[ip[0]].exit_code:
                    return -1, "VNFR {} command '{}' returns error: '{}'".format(ip[0], cmd,
                                                                                 "\n".join(output[ip[0]].stderr))
                else:
                    return 1, "VNFR {} command '{}' successful".format(ip[0], cmd)
        except (ssh2Exception.ChannelFailure, ssh2Exception.SocketDisconnectError, ssh2Exception.SocketTimeout,
                ssh2Exception.SocketRecvError) as e:
            return 0, "Timeout accessing the VNFR {}: {}".format(ip[0], str(e))
        except Exception as e:
            return -1, "ERROR checking the VNFR {}: {}".format(ip[0], str(e))

    def additional_operations(self, engine, test_osm, manual_check):
        pass

    def run(self, engine, test_osm, manual_check, test_params=None):
        engine.set_test_name(self.test_name)
        engine.get_autorization()
        nsname = os.environ.get("OSMNBITEST_NS_NAME", "OSMNBITEST")
        if test_params:
            if "vnfd-files" in test_params:
                self.vnfd_filenames = test_params["vnfd-files"].split(",")
            if "nsd-file" in test_params:
                self.nsd_filename = test_params["nsd-file"]
            if test_params.get("ns-name"):
                nsname = test_params["ns-name"]
        self.create_descriptors(engine)

        # create real VIM if not exist
        self.vim_id = engine.get_create_vim(test_osm)
        ns_data = {"nsDescription": "default description", "nsName": nsname, "nsdId": self.nsd_id,
                   "vimAccountId": self.vim_id}
        if self.ns_params:
            ns_data.update(self.ns_params)
        if test_params and test_params.get("ns-config"):
            if isinstance(test_params["ns-config"], str):
                ns_data.update(yaml.load(test_params["ns-config"]))
            else:
                ns_data.update(test_params["ns-config"])
        self.instantiate(engine, ns_data)

        if manual_check:
            input('NS has been deployed. Perform manual check and press enter to resume')
        if test_osm and self.commands:
            self.test_ns(engine, test_osm)
        self.additional_operations(engine, test_osm, manual_check)
        self.terminate(engine)
        self.delete_descriptors(engine)


class TestDeployHackfestCirros(TestDeploy):
    description = "Load and deploy Hackfest cirros_2vnf_ns example"

    def __init__(self):
        super().__init__()
        self.test_name = "CIRROS"
        self.vnfd_filenames = ("cirros_vnf.tar.gz",)
        self.nsd_filename = "cirros_2vnf_ns.tar.gz"
        self.commands = {'1': ['ls -lrt', ], '2': ['ls -lrt', ]}
        self.users = {'1': "cirros", '2': "cirros"}
        self.passwords = {'1': "cubswin:)", '2': "cubswin:)"}

    def terminate(self, engine):
        # Make a delete in one step, overriding the normal two step of TestDeploy that launched terminate and delete
        if test_osm:
            engine.test("Terminate and delete NS in one step", "DELETE", "/nslcm/v1/ns_instances_content/{}".
                        format(self.ns_id), headers_yaml, None, 202, None, "yaml")

            engine .wait_until_delete("/nslcm/v1/ns_instances/{}".format(self.ns_id), timeout_deploy)
        else:
            engine.test("Delete NS with FORCE", "DELETE", "/nslcm/v1/ns_instances/{}?FORCE=True".format(self.ns_id),
                        headers_yaml, None, 204, None, 0)

        # check all it is deleted
        engine.test("Check NS is deleted", "GET", "/nslcm/v1/ns_instances/{}".format(self.ns_id), headers_yaml, None,
                    404, None, "yaml")
        r = engine.test("Check NSLCMOPs are deleted", "GET",
                        "/nslcm/v1/ns_lcm_op_occs?nsInstanceId={}".format(self.ns_id), headers_json, None,
                        200, None, "json")
        if not r:
            return
        nslcmops = r.json()
        if not isinstance(nslcmops, list) or nslcmops:
            raise TestException("NS {} deleted but with ns_lcm_op_occ active: {}".format(self.ns_id, nslcmops))


class TestDeployHackfest1(TestDeploy):
    description = "Load and deploy Hackfest_1_vnfd example"

    def __init__(self):
        super().__init__()
        self.test_name = "HACKFEST1-"
        self.vnfd_filenames = ("hackfest_1_vnfd.tar.gz",)
        self.nsd_filename = "hackfest_1_nsd.tar.gz"
        # self.commands = {'1': ['ls -lrt', ], '2': ['ls -lrt', ]}
        # self.users = {'1': "cirros", '2': "cirros"}
        # self.passwords = {'1': "cubswin:)", '2': "cubswin:)"}


class TestDeployHackfestCirrosScaling(TestDeploy):
    description = "Load and deploy Hackfest cirros_2vnf_ns example with scaling modifications"

    def __init__(self):
        super().__init__()
        self.test_name = "CIRROS-SCALE"
        self.vnfd_filenames = ("cirros_vnf.tar.gz",)
        self.nsd_filename = "cirros_2vnf_ns.tar.gz"

    def create_descriptors(self, engine):
        super().create_descriptors(engine)
        # Modify VNFD to add scaling and count=2
        self.descriptor_edit = {
            "vnfd0": {
                "vdu": {
                    "$id: 'cirros_vnfd-VM'": {"count": 2}
                },
                "scaling-group-descriptor": [{
                    "name": "scale_cirros",
                    "max-instance-count": 2,
                    "vdu": [{
                        "vdu-id-ref": "cirros_vnfd-VM",
                        "count": 2
                    }]
                }]
            }
        }

    def additional_operations(self, engine, test_osm, manual_check):
        if not test_osm:
            return
        # 2 perform scale out twice
        payload = '{scaleType: SCALE_VNF, scaleVnfData: {scaleVnfType: SCALE_OUT, scaleByStepData: ' \
                  '{scaling-group-descriptor: scale_cirros, member-vnf-index: "1"}}}'
        for i in range(0, 2):
            engine.test("Execute scale action over NS", "POST",
                        "/nslcm/v1/ns_instances/{}/scale".format(self.ns_id), headers_yaml, payload,
                        201, r_headers_yaml_location_nslcmop, "yaml")
            nslcmop2_scale_out = engine.last_id
            engine.wait_operation_ready("ns", nslcmop2_scale_out, timeout_deploy)
            if manual_check:
                input('NS scale out done. Check that two more vdus are there')
            # TODO check automatic

        # 2 perform scale in
        payload = '{scaleType: SCALE_VNF, scaleVnfData: {scaleVnfType: SCALE_IN, scaleByStepData: ' \
                  '{scaling-group-descriptor: scale_cirros, member-vnf-index: "1"}}}'
        for i in range(0, 2):
            engine.test("Execute scale IN action over NS", "POST",
                        "/nslcm/v1/ns_instances/{}/scale".format(self.ns_id), headers_yaml, payload,
                        201, r_headers_yaml_location_nslcmop, "yaml")
            nslcmop2_scale_in = engine.last_id
            engine.wait_operation_ready("ns", nslcmop2_scale_in, timeout_deploy)
            if manual_check:
                input('NS scale in done. Check that two less vdus are there')
            # TODO check automatic

        # perform scale in that must fail as reached limit
        engine.test("Execute scale IN out of limit action over NS", "POST",
                    "/nslcm/v1/ns_instances/{}/scale".format(self.ns_id), headers_yaml, payload,
                    201, r_headers_yaml_location_nslcmop, "yaml")
        nslcmop2_scale_in = engine.last_id
        engine.wait_operation_ready("ns", nslcmop2_scale_in, timeout_deploy, expected_fail=True)


class TestDeployIpMac(TestDeploy):
    description = "Load and deploy descriptor examples setting mac, ip address at descriptor and instantiate params"

    def __init__(self):
        super().__init__()
        self.test_name = "SetIpMac"
        self.vnfd_filenames = ("vnfd_2vdu_set_ip_mac2.yaml", "vnfd_2vdu_set_ip_mac.yaml")
        self.nsd_filename = "scenario_2vdu_set_ip_mac.yaml"
        self.descriptor_url = \
            "https://osm.etsi.org/gitweb/?p=osm/RO.git;a=blob_plain;f=test/RO_tests/v3_2vdu_set_ip_mac/"
        self.commands = {'1': ['ls -lrt', ], '2': ['ls -lrt', ]}
        self.users = {'1': "osm", '2': "osm"}
        self.passwords = {'1': "osm4u", '2': "osm4u"}
        self.timeout = 360

    def run(self, engine, test_osm, manual_check, test_params=None):
        # super().run(engine, test_osm, manual_check, test_params)
        # run again setting IPs with instantiate parameters
        instantiation_params = {
            "vnf": [
                {
                    "member-vnf-index": "1",
                    "internal-vld": [
                        {
                            "name": "internal_vld1",   # net_internal
                            "ip-profile": {
                                "ip-version": "ipv4",
                                "subnet-address": "10.9.8.0/24",
                                "dhcp-params": {"count": 100, "start-address": "10.9.8.100"}
                            },
                            "internal-connection-point": [
                                {
                                    "id-ref": "eth2",
                                    "ip-address": "10.9.8.2",
                                },
                                {
                                    "id-ref": "eth3",
                                    "ip-address": "10.9.8.3",
                                }
                            ]
                        },
                    ],

                    "vdu": [
                        {
                            "id": "VM1",
                            "interface": [
                                # {
                                #     "name": "iface11",
                                #     "floating-ip-required": True,
                                # },
                                {
                                    "name": "iface13",
                                    "mac-address": "52:33:44:55:66:13"
                                },
                            ],
                        },
                        {
                            "id": "VM2",
                            "interface": [
                                {
                                    "name": "iface21",
                                    "ip-address": "10.31.31.22",
                                    "mac-address": "52:33:44:55:66:21"
                                },
                            ],
                        },
                    ]
                },
            ]
        }

        super().run(engine, test_osm, manual_check, test_params={"ns-config": instantiation_params})


class TestDeployHackfest4(TestDeploy):
    description = "Load and deploy Hackfest 4 example."

    def __init__(self):
        super().__init__()
        self.test_name = "HACKFEST4-"
        self.vnfd_filenames = ("hackfest_4_vnfd.tar.gz",)
        self.nsd_filename = "hackfest_4_nsd.tar.gz"
        self.uses_configuration = True
        self.commands = {'1': ['ls -lrt', ], '2': ['ls -lrt', ]}
        self.users = {'1': "ubuntu", '2': "ubuntu"}
        self.passwords = {'1': "osm4u", '2': "osm4u"}
        # Modify VNFD to add scaling
        # self.descriptor_edit = {
        #     "vnfd0": {
        #         'vnf-configuration': {
        #             'config-primitive': [{
        #                 'name': 'touch',
        #                 'parameter': [{
        #                     'name': 'filename',
        #                     'data-type': 'STRING',
        #                     'default-value': '/home/ubuntu/touched'
        #                 }]
        #             }]
        #         },
        #         'scaling-group-descriptor': [{
        #             'name': 'scale_dataVM',
        #             'scaling-policy': [{
        #                 'threshold-time': 0,
        #                 'name': 'auto_cpu_util_above_threshold',
        #                 'scaling-type': 'automatic',
        #                 'scaling-criteria': [{
        #                     'name': 'cpu_util_above_threshold',
        #                     'vnf-monitoring-param-ref': 'all_aaa_cpu_util',
        #                     'scale-out-relational-operation': 'GE',
        #                     'scale-in-threshold': 15,
        #                     'scale-out-threshold': 60,
        #                     'scale-in-relational-operation': 'LE'
        #                 }],
        #                 'cooldown-time': 60
        #             }],
        #             'max-instance-count': 10,
        #             'scaling-config-action': [
        #                 {'vnf-config-primitive-name-ref': 'touch',
        #                  'trigger': 'post-scale-out'},
        #                 {'vnf-config-primitive-name-ref': 'touch',
        #                  'trigger': 'pre-scale-in'}
        #             ],
        #             'vdu': [{
        #                 'vdu-id-ref': 'dataVM',
        #                 'count': 1
        #             }]
        #         }]
        #     }
        # }


class TestDeployHackfest3Charmed(TestDeploy):
    description = "Load and deploy Hackfest 3charmed_ns example"

    def __init__(self):
        super().__init__()
        self.test_name = "HACKFEST3-"
        self.vnfd_filenames = ("hackfest_3charmed_vnfd.tar.gz",)
        self.nsd_filename = "hackfest_3charmed_nsd.tar.gz"
        self.uses_configuration = True
        self.commands = {'1': ['ls -lrt /home/ubuntu/first-touch'], '2': ['ls -lrt /home/ubuntu/first-touch']}
        self.users = {'1': "ubuntu", '2': "ubuntu"}
        self.passwords = {'1': "osm4u", '2': "osm4u"}

    def additional_operations(self, engine, test_osm, manual_check):
        if not test_osm:
            return
        # 1 perform action
        payload = '{member_vnf_index: "2", primitive: touch, primitive_params: { filename: /home/ubuntu/OSMTESTNBI }}'
        engine.test("Exec service primitive over NS", "POST",
                    "/nslcm/v1/ns_instances/{}/action".format(self.ns_id), headers_yaml, payload,
                    201, r_headers_yaml_location_nslcmop, "yaml")
        nslcmop2_action = engine.last_id
        # Wait until status is Ok
        engine.wait_operation_ready("ns", nslcmop2_action, timeout_deploy)
        if manual_check:
            input('NS service primitive has been executed. Check that file /home/ubuntu/OSMTESTNBI is present at '
                  'TODO_PUT_IP')
        if test_osm:
            commands = {'1': [''], '2': ['ls -lrt /home/ubuntu/OSMTESTNBI', ]}
            self.test_ns(engine, test_osm, commands=commands)

        # # 2 perform scale out
        # payload = '{scaleType: SCALE_VNF, scaleVnfData: {scaleVnfType: SCALE_OUT, scaleByStepData: ' \
        #           '{scaling-group-descriptor: scale_dataVM, member-vnf-index: "1"}}}'
        # engine.test("Execute scale action over NS", "POST",
        #             "/nslcm/v1/ns_instances/{}/scale".format(self.ns_id), headers_yaml, payload,
        #             201, r_headers_yaml_location_nslcmop, "yaml")
        # nslcmop2_scale_out = engine.last_id
        # engine.wait_operation_ready("ns", nslcmop2_scale_out, timeout_deploy)
        # if manual_check:
        #     input('NS scale out done. Check that file /home/ubuntu/touched is present and new VM is created')
        # # TODO check automatic
        #
        # # 2 perform scale in
        # payload = '{scaleType: SCALE_VNF, scaleVnfData: {scaleVnfType: SCALE_IN, scaleByStepData: ' \
        #           '{scaling-group-descriptor: scale_dataVM, member-vnf-index: "1"}}}'
        # engine.test("Execute scale action over NS", "POST",
        #             "/nslcm/v1/ns_instances/{}/scale".format(self.ns_id), headers_yaml, payload,
        #             201, r_headers_yaml_location_nslcmop, "yaml")
        # nslcmop2_scale_in = engine.last_id
        # engine.wait_operation_ready("ns", nslcmop2_scale_in, timeout_deploy)
        # if manual_check:
        #     input('NS scale in done. Check that file /home/ubuntu/touched is updated and new VM is deleted')
        # # TODO check automatic


class TestDeployHackfest3Charmed2(TestDeployHackfest3Charmed):
    description = "Load and deploy Hackfest 3charmed_ns example modified version of descriptors to have dots in " \
                  "ids and member-vnf-index."

    def __init__(self):
        super().__init__()
        self.test_name = "HACKFEST3v2-"
        self.qforce = "?FORCE=True"
        self.descriptor_edit = {
            "vnfd0": {
                "vdu": {
                    "$[0]": {
                        "interface": {"$[0]": {"external-connection-point-ref": "pdu-mgmt"}}
                    },
                    "$[1]": None
                },
                "vnf-configuration": None,
                "connection-point": {
                    "$[0]": {
                        "id": "pdu-mgmt",
                        "name": "pdu-mgmt",
                        "short-name": "pdu-mgmt"
                    },
                    "$[1]": None
                },
                "mgmt-interface": {"cp": "pdu-mgmt"},
                "description": "A vnf single vdu to be used as PDU",
                "id": "vdu-as-pdu",
                "internal-vld": {
                    "$[0]": {
                        "id": "pdu_internal",
                        "name": "pdu_internal",
                        "internal-connection-point": {"$[1]": None},
                        "short-name": "pdu_internal",
                        "type": "ELAN"
                    }
                }
            },

            # Modify NSD accordingly
            "nsd": {
                "constituent-vnfd": {
                    "$[0]": {"vnfd-id-ref": "vdu-as-pdu"},
                    "$[1]": None,
                },
                "description": "A nsd to deploy the vnf to act as as PDU",
                "id": "nsd-as-pdu",
                "name": "nsd-as-pdu",
                "short-name": "nsd-as-pdu",
                "vld": {
                    "$[0]": {
                        "id": "mgmt_pdu",
                        "name": "mgmt_pdu",
                        "short-name": "mgmt_pdu",
                        "vnfd-connection-point-ref": {
                            "$[0]": {
                                "vnfd-connection-point-ref": "pdu-mgmt",
                                "vnfd-id-ref": "vdu-as-pdu",
                            },
                            "$[1]": None
                        },
                        "type": "ELAN"
                    },
                    "$[1]": None,
                }
            }
        }


class TestDeployHackfest3Charmed3(TestDeployHackfest3Charmed):
    description = "Load and deploy Hackfest 3charmed_ns example modified version to test scaling and NS parameters"

    def __init__(self):
        super().__init__()
        self.test_name = "HACKFEST3v3-"
        self.commands = {'1': ['ls -lrt /home/ubuntu/first-touch-1'], '2': ['ls -lrt /home/ubuntu/first-touch-2']}
        self.descriptor_edit = {
            "vnfd0": yaml.load(
                """
                scaling-group-descriptor:
                    -   name: "scale_dataVM"
                        max-instance-count: 10
                        scaling-policy:
                        -   name: "auto_cpu_util_above_threshold"
                            scaling-type: "automatic"
                            threshold-time: 0
                            cooldown-time: 60
                            scaling-criteria:
                            -   name: "cpu_util_above_threshold"
                                scale-in-threshold: 15
                                scale-in-relational-operation: "LE"
                                scale-out-threshold: 60
                                scale-out-relational-operation: "GE"
                                vnf-monitoring-param-ref: "monitor1"
                        vdu:
                        -   vdu-id-ref: dataVM
                            count: 1
                        scaling-config-action:
                        -   trigger: post-scale-out
                            vnf-config-primitive-name-ref: touch
                        -   trigger: pre-scale-in
                            vnf-config-primitive-name-ref: touch
                vdu:
                    "$id: dataVM":
                        monitoring-param:
                        -   id: "dataVM_cpu_util"
                            nfvi-metric: "cpu_utilization"

                monitoring-param:
                -   id: "monitor1"
                    name: "monitor1"
                    aggregation-type: AVERAGE
                    vdu-monitoring-param:
                      vdu-ref: "dataVM"
                      vdu-monitoring-param-ref: "dataVM_cpu_util"
                vnf-configuration:
                    initial-config-primitive:
                        "$[1]":
                            parameter:
                                "$[0]":
                                    value: "<touch-filename>"   # default-value: /home/ubuntu/first-touch
                    config-primitive:
                        "$[0]":
                            parameter:
                                "$[0]":
                                    default-value: "<touch-filename2>"
                """)
        }
        self.ns_params = {
            "additionalParamsForVnf": [
                {"member-vnf-index": "1", "additionalParams": {"touch-filename": "/home/ubuntu/first-touch-1",
                                                               "touch-filename2": "/home/ubuntu/second-touch-1"}},
                {"member-vnf-index": "2", "additionalParams": {"touch-filename": "/home/ubuntu/first-touch-2",
                                                               "touch-filename2": "/home/ubuntu/second-touch-2"}},
            ]
        }

    def additional_operations(self, engine, test_osm, manual_check):
        super().additional_operations(engine, test_osm, manual_check)
        if not test_osm:
            return

        # 2 perform scale out
        payload = '{scaleType: SCALE_VNF, scaleVnfData: {scaleVnfType: SCALE_OUT, scaleByStepData: ' \
                  '{scaling-group-descriptor: scale_dataVM, member-vnf-index: "1"}}}'
        engine.test("Execute scale action over NS", "POST",
                    "/nslcm/v1/ns_instances/{}/scale".format(self.ns_id), headers_yaml, payload,
                    201, r_headers_yaml_location_nslcmop, "yaml")
        nslcmop2_scale_out = engine.last_id
        engine.wait_operation_ready("ns", nslcmop2_scale_out, timeout_deploy)
        if manual_check:
            input('NS scale out done. Check that file /home/ubuntu/second-touch-1 is present and new VM is created')
        if test_osm:
            commands = {'1': ['ls -lrt /home/ubuntu/second-touch-1', ]}
            self.test_ns(engine, test_osm, commands=commands)
            # TODO check automatic connection to scaled VM

        # 2 perform scale in
        payload = '{scaleType: SCALE_VNF, scaleVnfData: {scaleVnfType: SCALE_IN, scaleByStepData: ' \
                  '{scaling-group-descriptor: scale_dataVM, member-vnf-index: "1"}}}'
        engine.test("Execute scale action over NS", "POST",
                    "/nslcm/v1/ns_instances/{}/scale".format(self.ns_id), headers_yaml, payload,
                    201, r_headers_yaml_location_nslcmop, "yaml")
        nslcmop2_scale_in = engine.last_id
        engine.wait_operation_ready("ns", nslcmop2_scale_in, timeout_deploy)
        if manual_check:
            input('NS scale in done. Check that file /home/ubuntu/second-touch-1 is updated and new VM is deleted')
        # TODO check automatic


class TestDeploySimpleCharm(TestDeploy):
    description = "Deploy hackfest-4 hackfest_simplecharm example"

    def __init__(self):
        super().__init__()
        self.test_name = "HACKFEST-SIMPLE"
        self.descriptor_url = "https://osm-download.etsi.org/ftp/osm-4.0-four/4th-hackfest/packages/"
        self.vnfd_filenames = ("hackfest_simplecharm_vnf.tar.gz",)
        self.nsd_filename = "hackfest_simplecharm_ns.tar.gz"
        self.uses_configuration = True
        self.commands = {'1': [''], '2': ['ls -lrt /home/ubuntu/first-touch', ]}
        self.users = {'1': "ubuntu", '2': "ubuntu"}
        self.passwords = {'1': "osm4u", '2': "osm4u"}


class TestDeploySimpleCharm2(TestDeploySimpleCharm):
    description = "Deploy hackfest-4 hackfest_simplecharm example changing naming to contain dots on ids and " \
                  "vnf-member-index"

    def __init__(self):
        super().__init__()
        self.test_name = "HACKFEST-SIMPLE2-"
        self.qforce = "?FORCE=True"
        self.descriptor_edit = {
            "vnfd0": {
                "id": "hackfest.simplecharm.vnf"
            },

            "nsd": {
                "id": "hackfest.simplecharm.ns",
                "constituent-vnfd": {
                    "$[0]": {"vnfd-id-ref": "hackfest.simplecharm.vnf", "member-vnf-index": "$1"},
                    "$[1]": {"vnfd-id-ref": "hackfest.simplecharm.vnf", "member-vnf-index": "$2"},
                },
                "vld": {
                    "$[0]": {
                        "vnfd-connection-point-ref": {"$[0]": {"member-vnf-index-ref": "$1",
                                                               "vnfd-id-ref": "hackfest.simplecharm.vnf"},
                                                      "$[1]": {"member-vnf-index-ref": "$2",
                                                               "vnfd-id-ref": "hackfest.simplecharm.vnf"}},
                    },
                    "$[1]": {
                        "vnfd-connection-point-ref": {"$[0]": {"member-vnf-index-ref": "$1",
                                                               "vnfd-id-ref": "hackfest.simplecharm.vnf"},
                                                      "$[1]": {"member-vnf-index-ref": "$2",
                                                               "vnfd-id-ref": "hackfest.simplecharm.vnf"}},
                    },
                }
            }
        }


class TestDeploySingleVdu(TestDeployHackfest3Charmed):
    description = "Generate a single VDU base on editing Hackfest3Charmed descriptors and deploy"

    def __init__(self):
        super().__init__()
        self.test_name = "SingleVDU"
        self.qforce = "?FORCE=True"
        self.descriptor_edit = {
            # Modify VNFD to remove one VDU
            "vnfd0": {
                "vdu": {
                    "$[0]": {
                        "interface": {"$[0]": {"external-connection-point-ref": "pdu-mgmt"}}
                    },
                    "$[1]": None
                },
                "vnf-configuration": None,
                "connection-point": {
                    "$[0]": {
                        "id": "pdu-mgmt",
                        "name": "pdu-mgmt",
                        "short-name": "pdu-mgmt"
                    },
                    "$[1]": None
                },
                "mgmt-interface": {"cp": "pdu-mgmt"},
                "description": "A vnf single vdu to be used as PDU",
                "id": "vdu-as-pdu",
                "internal-vld": {
                    "$[0]": {
                        "id": "pdu_internal",
                        "name": "pdu_internal",
                        "internal-connection-point": {"$[1]": None},
                        "short-name": "pdu_internal",
                        "type": "ELAN"
                    }
                }
            },

            # Modify NSD accordingly
            "nsd": {
                "constituent-vnfd": {
                    "$[0]": {"vnfd-id-ref": "vdu-as-pdu"},
                    "$[1]": None,
                },
                "description": "A nsd to deploy the vnf to act as as PDU",
                "id": "nsd-as-pdu",
                "name": "nsd-as-pdu",
                "short-name": "nsd-as-pdu",
                "vld": {
                    "$[0]": {
                        "id": "mgmt_pdu",
                        "name": "mgmt_pdu",
                        "short-name": "mgmt_pdu",
                        "vnfd-connection-point-ref": {
                            "$[0]": {
                                "vnfd-connection-point-ref": "pdu-mgmt",
                                "vnfd-id-ref": "vdu-as-pdu",
                            },
                            "$[1]": None
                        },
                        "type": "ELAN"
                    },
                    "$[1]": None,
                }
            }
        }


class TestDeployHnfd(TestDeployHackfest3Charmed):
    description = "Generate a HNFD base on editing Hackfest3Charmed descriptors and deploy"

    def __init__(self):
        super().__init__()
        self.test_name = "HNFD"
        self.pduDeploy = TestDeploySingleVdu()
        self.pdu_interface_0 = {}
        self.pdu_interface_1 = {}

        self.pdu_id = None
        # self.vnf_to_pdu = """
        #     vdu:
        #         "$[0]":
        #             pdu-type: PDU-TYPE-1
        #             interface:
        #                 "$[0]":
        #                     name: mgmt-iface
        #                 "$[1]":
        #                     name: pdu-iface-internal
        #     id: hfn1
        #     description: HFND, one PDU + One VDU
        #     name: hfn1
        #     short-name: hfn1
        #
        # """

        self.pdu_descriptor = {
            "name": "my-PDU",
            "type": "PDU-TYPE-1",
            "vim_accounts": "to-override",
            "interfaces": [
                {
                    "name": "mgmt-iface",
                    "mgmt": True,
                    "type": "overlay",
                    "ip-address": "to override",
                    "mac-address": "mac_address",
                    "vim-network-name": "mgmt",
                },
                {
                    "name": "pdu-iface-internal",
                    "mgmt": False,
                    "type": "overlay",
                    "ip-address": "to override",
                    "mac-address": "mac_address",
                    "vim-network-name": "pdu_internal",  # OSMNBITEST-PDU-pdu_internal
                },
            ]
        }
        self.vnfd_filenames = ("hackfest_3charmed_vnfd.tar.gz", "hackfest_3charmed_vnfd.tar.gz")

        self.descriptor_edit = {
            "vnfd0": {
                "id": "hfnd1",
                "name": "hfn1",
                "short-name": "hfn1",
                "vdu": {
                    "$[0]": {
                        "pdu-type": "PDU-TYPE-1",
                        "interface": {
                            "$[0]": {"name": "mgmt-iface"},
                            "$[1]": {"name": "pdu-iface-internal"},
                        }
                    }
                }
            },
            "nsd": {
                "constituent-vnfd": {
                    "$[1]": {"vnfd-id-ref": "hfnd1"}
                },
                "vld": {
                    "$[0]": {"vnfd-connection-point-ref": {"$[1]": {"vnfd-id-ref": "hfnd1"}}},
                    "$[1]": {"vnfd-connection-point-ref": {"$[1]": {"vnfd-id-ref": "hfnd1"}}}
                }
            }
        }

    def create_descriptors(self, engine):
        super().create_descriptors(engine)

        # Create PDU
        self.pdu_descriptor["interfaces"][0].update(self.pdu_interface_0)
        self.pdu_descriptor["interfaces"][1].update(self.pdu_interface_1)
        self.pdu_descriptor["vim_accounts"] = [self.vim_id]
        # TODO get vim-network-name from vnfr.vld.name
        self.pdu_descriptor["interfaces"][1]["vim-network-name"] = "{}-{}-{}".format(
            os.environ.get("OSMNBITEST_NS_NAME", "OSMNBITEST"),
            "PDU", self.pdu_descriptor["interfaces"][1]["vim-network-name"])
        engine.test("Onboard PDU descriptor", "POST", "/pdu/v1/pdu_descriptors",
                    {"Location": "/pdu/v1/pdu_descriptors/", "Content-Type": "application/yaml"}, self.pdu_descriptor,
                    201, r_header_yaml, "yaml")
        self.pdu_id = engine.last_id

    def run(self, engine, test_osm, manual_check, test_params=None):
        engine.get_autorization()
        engine.set_test_name(self.test_name)
        nsname = os.environ.get("OSMNBITEST_NS_NAME", "OSMNBITEST")

        # create real VIM if not exist
        self.vim_id = engine.get_create_vim(test_osm)
        # instantiate PDU
        self.pduDeploy.create_descriptors(engine)
        self.pduDeploy.instantiate(engine, {"nsDescription": "to be used as PDU", "nsName": nsname + "-PDU",
                                            "nsdId": self.pduDeploy.nsd_id, "vimAccountId": self.vim_id})
        if manual_check:
            input('VNF to be used as PDU has been deployed. Perform manual check and press enter to resume')
        if test_osm:
            self.pduDeploy.test_ns(engine, test_osm)

        if test_osm:
            r = engine.test("Get VNFR to obtain IP_ADDRESS", "GET",
                            "/nslcm/v1/vnfrs?nsr-id-ref={}".format(self.pduDeploy.ns_id), headers_json, None,
                            200, r_header_json, "json")
            if not r:
                return
            vnfr_data = r.json()
            # print(vnfr_data)

            self.pdu_interface_0["ip-address"] = vnfr_data[0]["vdur"][0]["interfaces"][0].get("ip-address")
            self.pdu_interface_1["ip-address"] = vnfr_data[0]["vdur"][0]["interfaces"][1].get("ip-address")
            self.pdu_interface_0["mac-address"] = vnfr_data[0]["vdur"][0]["interfaces"][0].get("mac-address")
            self.pdu_interface_1["mac-address"] = vnfr_data[0]["vdur"][0]["interfaces"][1].get("mac-address")
            if not self.pdu_interface_0["ip-address"]:
                raise TestException("Vnfr has not managment ip address")
        else:
            self.pdu_interface_0["ip-address"] = "192.168.10.10"
            self.pdu_interface_1["ip-address"] = "192.168.11.10"
            self.pdu_interface_0["mac-address"] = "52:33:44:55:66:13"
            self.pdu_interface_1["mac-address"] = "52:33:44:55:66:14"

        self.create_descriptors(engine)

        ns_data = {"nsDescription": "default description", "nsName": nsname, "nsdId": self.nsd_id,
                   "vimAccountId": self.vim_id}
        if test_params and test_params.get("ns-config"):
            if isinstance(test_params["ns-config"], str):
                ns_data.update(yaml.load(test_params["ns-config"]))
            else:
                ns_data.update(test_params["ns-config"])

        self.instantiate(engine, ns_data)
        if manual_check:
            input('NS has been deployed. Perform manual check and press enter to resume')
        if test_osm:
            self.test_ns(engine, test_osm)
        self.additional_operations(engine, test_osm, manual_check)
        self.terminate(engine)
        self.pduDeploy.terminate(engine)
        self.delete_descriptors(engine)
        self.pduDeploy.delete_descriptors(engine)

    def delete_descriptors(self, engine):
        super().delete_descriptors(engine)
        # delete pdu
        engine.test("Delete PDU SOL005", "DELETE",
                    "/pdu/v1/pdu_descriptors/{}".format(self.pdu_id),
                    headers_yaml, None, 204, None, 0)


class TestDescriptors:
    description = "Test VNFD, NSD, PDU descriptors CRUD and dependencies"

    def __init__(self):
        self.vnfd_filename = "hackfest_3charmed_vnfd.tar.gz"
        self.nsd_filename = "hackfest_3charmed_nsd.tar.gz"
        self.descriptor_url = "https://osm-download.etsi.org/ftp/osm-3.0-three/2nd-hackfest/packages/"
        self.vnfd_id = None
        self.nsd_id = None
        self.vnfd_empty = """vnfd:vnfd-catalog:
            vnfd:
            -   name: prova
                short-name: prova
                id: prova
        """
        self.vnfd_prova = """vnfd:vnfd-catalog:
            vnfd:
            -   connection-point:
                -   name: cp_0h8m
                    type: VPORT
                id: prova
                name: prova
                short-name: prova
                vdu:
                -   id: vdu_z4bm
                    image: ubuntu
                    interface:
                    -   external-connection-point-ref: cp_0h8m
                        name: eth0
                        virtual-interface:
                        type: VIRTIO
                    name: vdu_z4bm
                version: '1.0'
        """

    def run(self, engine, test_osm, manual_check, test_params=None):
        engine.set_test_name("Descriptors")
        engine.get_autorization()
        temp_dir = os.path.dirname(os.path.abspath(__file__)) + "/temp/"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        # download files
        for filename in (self.vnfd_filename, self.nsd_filename):
            filename_path = temp_dir + filename
            if not os.path.exists(filename_path):
                with open(filename_path, "wb") as file:
                    response = requests.get(self.descriptor_url + filename)
                    if response.status_code >= 300:
                        raise TestException("Error downloading descriptor from '{}': {}".format(
                            self.descriptor_url + filename, response.status_code))
                    file.write(response.content)

        vnfd_filename_path = temp_dir + self.vnfd_filename
        nsd_filename_path = temp_dir + self.nsd_filename

        engine.test("Onboard empty VNFD in one step", "POST", "/vnfpkgm/v1/vnf_packages_content", headers_yaml,
                    self.vnfd_empty, 201, r_headers_yaml_location_vnfd, "yaml")
        self.vnfd_id = engine.last_id

        # test bug 605
        engine.test("Upload invalid VNFD ", "PUT", "/vnfpkgm/v1/vnf_packages/{}/package_content".format(self.vnfd_id),
                    headers_yaml, self.vnfd_prova, 422, r_header_yaml, "yaml")

        engine.test("Upload VNFD {}".format(self.vnfd_filename), "PUT",
                    "/vnfpkgm/v1/vnf_packages/{}/package_content".format(self.vnfd_id), headers_zip_yaml,
                    "@b" + vnfd_filename_path, 204, None, 0)

        queries = ["mgmt-interface.cp=mgmt", "vdu.0.interface.0.external-connection-point-ref=mgmt",
                   "vdu.0.interface.1.internal-connection-point-ref=internal",
                   "internal-vld.0.internal-connection-point.0.id-ref=internal"]
        for query in queries:
            engine.test("Upload invalid VNFD ", "PUT",
                        "/vnfpkgm/v1/vnf_packages/{}/package_content?{}".format(self.vnfd_id, query),
                        headers_zip_yaml, "@b" + vnfd_filename_path, 422, r_header_yaml, "yaml")

        # test bug 605
        engine.test("Upload invalid VNFD ", "PUT", "/vnfpkgm/v1/vnf_packages/{}/package_content".format(self.vnfd_id),
                    headers_yaml, self.vnfd_prova, 422, r_header_yaml, "yaml")

        # get vnfd descriptor
        engine.test("Get VNFD descriptor", "GET", "/vnfpkgm/v1/vnf_packages/{}".format(self.vnfd_id),
                    headers_yaml, None, 200, r_header_yaml, "yaml")

        # get vnfd file descriptor
        engine.test("Get VNFD file descriptor", "GET", "/vnfpkgm/v1/vnf_packages/{}/vnfd".format(self.vnfd_id),
                    headers_text, None, 200, r_header_text, "text", temp_dir+"vnfd-yaml")
        # TODO compare files: diff vnfd-yaml hackfest_3charmed_vnfd/hackfest_3charmed_vnfd.yaml

        # get vnfd zip file package
        engine.test("Get VNFD zip package", "GET",
                    "/vnfpkgm/v1/vnf_packages/{}/package_content".format(self.vnfd_id), headers_zip, None, 200,
                    r_header_zip, "zip", temp_dir+"vnfd-zip")
        # TODO compare files: diff vnfd-zip hackfest_3charmed_vnfd.tar.gz

        # get vnfd artifact
        engine.test("Get VNFD artifact package", "GET",
                    "/vnfpkgm/v1/vnf_packages/{}/artifacts/icons/osm.png".format(self.vnfd_id), headers_zip, None, 200,
                    r_header_octect, "octet-string", temp_dir+"vnfd-icon")
        # TODO compare files: diff vnfd-icon hackfest_3charmed_vnfd/icons/osm.png

        # nsd CREATE AND UPLOAD in one step:
        engine.test("Onboard NSD in one step", "POST", "/nsd/v1/ns_descriptors_content", headers_zip_yaml,
                    "@b" + nsd_filename_path, 201, r_headers_yaml_location_nsd, "yaml")
        self.nsd_id = engine.last_id

        queries = ["vld.0.vnfd-connection-point-ref.0.vnfd-id-ref=hf"]
        for query in queries:
            engine.test("Upload invalid NSD ", "PUT",
                        "/nsd/v1/ns_descriptors/{}/nsd_content?{}".format(self.nsd_id, query),
                        headers_zip_yaml, "@b" + nsd_filename_path, 422, r_header_yaml, "yaml")

        # get nsd descriptor
        engine.test("Get NSD descriptor", "GET", "/nsd/v1/ns_descriptors/{}".format(self.nsd_id), headers_yaml,
                    None, 200, r_header_yaml, "yaml")

        # get nsd file descriptor
        engine.test("Get NSD file descriptor", "GET", "/nsd/v1/ns_descriptors/{}/nsd".format(self.nsd_id), headers_text,
                    None, 200, r_header_text, "text", temp_dir+"nsd-yaml")
        # TODO compare files: diff nsd-yaml hackfest_3charmed_nsd/hackfest_3charmed_nsd.yaml

        # get nsd zip file package
        engine.test("Get NSD zip package", "GET", "/nsd/v1/ns_descriptors/{}/nsd_content".format(self.nsd_id),
                    headers_zip, None, 200, r_header_zip, "zip", temp_dir+"nsd-zip")
        # TODO compare files: diff nsd-zip hackfest_3charmed_nsd.tar.gz

        # get nsd artifact
        engine.test("Get NSD artifact package", "GET",
                    "/nsd/v1/ns_descriptors/{}/artifacts/icons/osm.png".format(self.nsd_id), headers_zip, None, 200,
                    r_header_octect, "octet-string", temp_dir+"nsd-icon")
        # TODO compare files: diff nsd-icon hackfest_3charmed_nsd/icons/osm.png

        # vnfd DELETE
        test_rest.test("Delete VNFD conflict", "DELETE", "/vnfpkgm/v1/vnf_packages/{}".format(self.vnfd_id),
                       headers_yaml, None, 409, None, None)

        test_rest.test("Delete VNFD force", "DELETE", "/vnfpkgm/v1/vnf_packages/{}?FORCE=TRUE".format(self.vnfd_id),
                       headers_yaml, None, 204, None, 0)

        # nsd DELETE
        test_rest.test("Delete NSD", "DELETE", "/nsd/v1/ns_descriptors/{}".format(self.nsd_id), headers_yaml, None, 204,
                       None, 0)


class TestNetSliceTemplates:
    description = "Upload a NST to OSM"

    def __init__(self):
        self.nst_filenames = ("@./cirros_slice/cirros_slice_vld.yaml")

    def run(self, engine, test_osm, manual_check, test_params=None):
        # nst CREATE
        engine.set_test_name("NST")
        engine.get_autorization()
        engine.test("Onboard NST", "POST", "/nst/v1/netslice_templates_content", headers_yaml, self.nst_filenames,
                    201, r_headers_yaml_location_nst, "yaml")
        nst_id = engine.last_id

        # nstd SHOW OSM format
        engine.test("Show NSTD OSM format", "GET", "/nst/v1/netslice_templates/{}".format(nst_id), headers_json, None,
                    200, r_header_json, "json")

        # nstd DELETE
        engine.test("Delete NSTD", "DELETE", "/nst/v1/netslice_templates/{}".format(nst_id), headers_json, None,
                    204, None, 0)


class TestNetSliceInstances:
    description = "Upload a NST to OSM"

    def __init__(self):
        self.vim_id = None
        self.nst_filenames = ("@./cirros_slice/cirros_slice.yaml")

    def run(self, engine, test_osm, manual_check, test_params=None):
        # nst CREATE
        engine.set_test_name("NSI")
        engine.get_autorization()
        engine.test("Onboard NST", "POST", "/nst/v1/netslice_templates_content", headers_yaml, self.nst_filenames, 201,
                    r_headers_yaml_location_nst, "yaml")
        nst_id = engine.last_id

        # nsi CREATE
        self.vim_id = engine.get_create_vim(test_osm)

        ns_data = {"nsiDescription": "default description", "nsiName": "my_slice", "nstId": nst_id,
                   "vimAccountId": self.vim_id}
        ns_data_text = yaml.safe_dump(ns_data, default_flow_style=True, width=256)

        engine.test("Onboard NSI", "POST", "/nsilcm/v1/netslice_instances_content", headers_yaml, ns_data_text, 201,
                    r_headers_yaml_location_nst, "yaml")
        nsi_id = engine.last_id
        
        # TODO: Improve the wait with a polling if NSI was deployed
        wait = 120
        sleep(wait)

        # Check deployment
        engine.test("Wait until NSI is deployed", "GET", "/nsilcm/v1/netslice_instances_content/{}".format(nsi_id),
                    headers_json, None, 200, r_header_json, "json")
 
        # nsi DELETE
        engine.test("Delete NSI", "DELETE", "/nsilcm/v1/netslice_instances_content/{}".format(nsi_id), headers_json,
                    None, 202, r_header_json, "json")
        
        sleep(60)

        # nstd DELETE
        engine.test("Delete NSTD", "DELETE", "/nst/v1/netslice_templates/{}".format(nst_id), headers_json, None,
                    204, None, 0)


if __name__ == "__main__":
    global logger
    test = ""

    # Disable warnings from self-signed certificates.
    requests.packages.urllib3.disable_warnings()
    try:
        logging.basicConfig(format="%(levelname)s %(message)s", level=logging.ERROR)
        logger = logging.getLogger('NBI')
        # load parameters and configuration
        opts, args = getopt.getopt(sys.argv[1:], "hvu:p:",
                                   ["url=", "user=", "password=", "help", "version", "verbose", "no-verbose",
                                    "project=", "insecure", "timeout", "timeout-deploy", "timeout-configure",
                                    "test=", "list", "test-osm", "manual-check", "params=", 'fail-fast'])
        url = "https://localhost:9999/osm"
        user = password = project = "admin"
        test_osm = False
        manual_check = False
        verbose = 0
        verify = True
        fail_fast = False
        test_classes = {
            "NonAuthorized": TestNonAuthorized,
            "FakeVIM": TestFakeVim,
            "TestUsersProjects": TestUsersProjects,
            "VIM-SDN": TestVIMSDN,
            "Deploy-Custom": TestDeploy,
            "Deploy-Hackfest-Cirros": TestDeployHackfestCirros,
            "Deploy-Hackfest-Cirros-Scaling": TestDeployHackfestCirrosScaling,
            "Deploy-Hackfest-3Charmed": TestDeployHackfest3Charmed,
            "Deploy-Hackfest-3Charmed2": TestDeployHackfest3Charmed2,
            "Deploy-Hackfest-3Charmed3": TestDeployHackfest3Charmed3,
            "Deploy-Hackfest-4": TestDeployHackfest4,
            "Deploy-CirrosMacIp": TestDeployIpMac,
            "TestDescriptors": TestDescriptors,
            "TestDeployHackfest1": TestDeployHackfest1,
            # "Deploy-MultiVIM": TestDeployMultiVIM,
            "DeploySingleVdu": TestDeploySingleVdu,
            "DeployHnfd": TestDeployHnfd,
            # "Upload-Slice-Template": TestNetSliceTemplates,
            # "Deploy-Slice-Instance": TestNetSliceInstances,
            "TestDeploySimpleCharm": TestDeploySimpleCharm,
            "TestDeploySimpleCharm2": TestDeploySimpleCharm2,
        }
        test_to_do = []
        test_params = {}

        for o, a in opts:
            # print("parameter:", o, a)
            if o == "--version":
                print("test version " + __version__ + ' ' + version_date)
                exit()
            elif o == "--list":
                for test, test_class in sorted(test_classes.items()):
                    print("{:32} {}".format(test + ":", test_class.description))
                exit()
            elif o in ("-v", "--verbose"):
                verbose += 1
            elif o == "no-verbose":
                verbose = -1
            elif o in ("-h", "--help"):
                usage()
                sys.exit()
            elif o == "--test-osm":
                test_osm = True
            elif o == "--manual-check":
                manual_check = True
            elif o == "--url":
                url = a
            elif o in ("-u", "--user"):
                user = a
            elif o in ("-p", "--password"):
                password = a
            elif o == "--project":
                project = a
            elif o == "--fail-fast":
                fail_fast = True
            elif o == "--test":
                # print("asdfadf", o, a, a.split(","))
                for _test in a.split(","):
                    if _test not in test_classes:
                        print("Invalid test name '{}'. Use option '--list' to show available tests".format(_test),
                              file=sys.stderr)
                        exit(1)
                    test_to_do.append(_test)
            elif o == "--params":
                param_key, _, param_value = a.partition("=")
                text_index = len(test_to_do)
                if text_index not in test_params:
                    test_params[text_index] = {}
                test_params[text_index][param_key] = param_value
            elif o == "--insecure":
                verify = False
            elif o == "--timeout":
                timeout = int(a)
            elif o == "--timeout-deploy":
                timeout_deploy = int(a)
            elif o == "--timeout-configure":
                timeout_configure = int(a)
            else:
                assert False, "Unhandled option"
        if verbose == 0:
            logger.setLevel(logging.WARNING)
        elif verbose > 1:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.ERROR)

        test_rest = TestRest(url, user=user, password=password, project=project)
        # print("tests to do:", test_to_do)
        if test_to_do:
            text_index = 0
            for test in test_to_do:
                if fail_fast and test_rest.failed_tests:
                    break
                text_index += 1
                test_class = test_classes[test]
                test_class().run(test_rest, test_osm, manual_check, test_params.get(text_index))
        else:
            for test, test_class in test_classes.items():
                if fail_fast and test_rest.failed_tests:
                    break
                test_class().run(test_rest, test_osm, manual_check, test_params.get(0))
        test_rest.print_results()
        exit(1 if test_rest.failed_tests else 0)

    except TestException as e:
        logger.error(test + "Test {} Exception: {}".format(test, str(e)))
        exit(1)
    except getopt.GetoptError as e:
        logger.error(e)
        print(e, file=sys.stderr)
        exit(1)
    except Exception as e:
        logger.critical(test + " Exception: " + str(e), exc_info=True)
