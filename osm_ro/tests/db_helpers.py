# -*- coding: utf-8 -*-
##
# Copyright 2018 University of Bristol - High Performance Networks Research
# Group
# All Rights Reserved.
#
# Contributors: Anderson Bravalheri, Dimitrios Gkounis, Abubakar Siddique
# Muqaddas, Navdeep Uniyal, Reza Nejabati and Dimitra Simeonidou
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact with: <highperformance-networks@bristol.ac.uk>
#
# Neither the name of the University of Bristol nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# This work has been performed in the context of DCMS UK 5G Testbeds
# & Trials Programme and in the framework of the Metro-Haul project -
# funded by the European Commission under Grant number 761727 through the
# Horizon 2020 and 5G-PPP programmes.
##
import hashlib
import shlex
import unittest
from contextlib import contextmanager
from functools import wraps
from hashlib import md5
from os import environ, pathsep
from subprocess import STDOUT, check_output
from uuid import UUID

from MySQLdb import connect

from ..nfvo_db import nfvo_db

HOST = environ.get('TEST_DB_HOST', 'localhost')
USER = environ.get('TEST_DB_USER', 'mano')
PASSWORD = environ.get('TEST_DB_PASSWORD', 'manopw')
DATABASE = environ.get('TEST_DB_DATABASE', 'mano_db')


def uuid(seed):
    """Generates strings with a UUID format in a repeatable way"""
    return str(UUID(md5(str(seed)).hexdigest()))


def sha1(text):
    """Generates SHA1 hash code from a text string"""
    return hashlib.sha1(text).hexdigest()


def run(*args, **kwargs):
    """Run a command inside a subprocess, raising an exception when it fails

    Arguments:
        *args: you can pass any number of arquments as separated words in the
            shell, or just a single string with the entire command
        **kwargs: proxied to subprocess.check_output (by default
            ``stderr=STDOUT`` and ``universal_newlines=True``
    """
    if len(args) == 1 and isinstance(args[0], str):
        args = shlex.split(args[0])

    opts = dict(stderr=STDOUT, universal_newlines=True)
    opts.update(kwargs)
    return check_output(args, **opts)


# In order to not mess around, enforce user to explicit set the
# test database in a env variable
@unittest.skipUnless(
    environ.get('TEST_DB_HOST'),
    'Test database not available. Please set TEST_DB_HOST env var')
class TestCaseWithDatabase(unittest.TestCase):
    """Connect to the database and provide methods to facilitate isolating the
    database stored inside it between tests.

    In order to avoid connecting, reconnecting, creating tables and destroying
    tables all the time, this class manage the database using class-level
    fixtures. This reduce the cost of performing these actions but not
    guarantees isolation in the DB state between the tests.
    To enforce isolation, please call the ``setup_tables`` and
    ``empty_database`` directly, or write one single test per class.
    """

    host = HOST
    user = USER
    password = PASSWORD
    database = DATABASE

    @classmethod
    def setup_tables(cls):
        """Make sure the database is set up and in the right version, with all the
        required tables.
        """
        dbutils = environ.get('DBUTILS')

        if dbutils:
            environ["PATH"] += pathsep + dbutils

        return run('init_mano_db.sh',
                   '-u', cls.user,
                   '-p', cls.password,
                   '-h', cls.host,
                   '-d', cls.database)

    @classmethod
    def empty_database(cls):
        """Clear the database, so one test does not interfere with the other"""
        # Create a custom connection not attached to the database, so we can
        # destroy and recreate the database itself
        connection = connect(cls.host, cls.user, cls.password)
        cursor = connection.cursor()
        cursor.execute(
            "DROP DATABASE {};".format(
                connection.escape_string(cls.database)))
        cursor.execute(
            "CREATE DATABASE {};".format(
                connection.escape_string(cls.database)))
        cursor.close()
        connection.close()


class TestCaseWithDatabasePerTest(TestCaseWithDatabase):
    """Ensure a connection to the database before and
    drop tables after each test runs
    """

    def setUp(self):
        self.setup_tables()
        self.addCleanup(self.empty_database)

        self.maxDiff = None

        self.db = nfvo_db(self.host, self.user, self.password, self.database)
        self.db.connect()

    def populate(self, seeds=None, **kwargs):
        """Seed the database with initial values"""
        if not seeds:
            seeds = []
        if not isinstance(seeds, (list, tuple)):
            seeds = [seeds]
        if kwargs:
            seeds.append(kwargs)
        self.db.new_rows(seeds)

    def count(self, table):
        """Count number of rows in a table"""
        return self.db.get_rows(
            SELECT='COUNT(*) as count', FROM=table)[0]['count']

    @contextmanager
    def disable_foreign_keys(self):
        """Do the test without checking foreign keys"""
        try:
            cursor = self.db.con.cursor()
            cursor.execute('SET FOREIGN_KEY_CHECKS=0;')
            yield
        finally:
            cursor.execute('SET FOREIGN_KEY_CHECKS=1;')


def disable_foreign_keys(test):
    """Do the test without checking foreign keys.
    To be used together in subclasses of TestCaseWithDatabasePerTest
    """
    @wraps(test)
    def _no_check(self, *args, **kwargs):
        with self.disable_foreign_keys():
            result = test(self, *args, **kwargs)

        return result

    return _no_check
