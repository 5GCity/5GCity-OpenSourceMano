# -*- coding: utf-8 -*-
# pylint: disable=E1101
import unittest

from MySQLdb import connect, cursors, DatabaseError, IntegrityError
import mock
from mock import Mock

from ..db_base import retry, with_transaction
from ..nfvo_db import nfvo_db
from .db_helpers import TestCaseWithDatabase


class TestDbDecorators(TestCaseWithDatabase):
    @classmethod
    def setUpClass(cls):
        connection = connect(cls.host, cls.user, cls.password)
        cursor = connection.cursor()
        cursor.execute(
            "CREATE DATABASE IF NOT EXISTS {};".format(
                connection.escape_string(cls.database)))
        cursor.execute("use {};".format(cls.database))
        cursor.execute("""\
            CREATE TABLE IF NOT EXISTS `test_table` (\
                `id` int(11) NOT NULL,
                PRIMARY KEY (`id`)\
            );\
        """)
        cursor.close()
        connection.close()

    @classmethod
    def tearDownClass(cls):
        cls.empty_database()

    def setUp(self):
        self.maxDiff = None
        self.db = nfvo_db(self.host, self.user, self.password, self.database)
        self.db.connect()
        self.addCleanup(lambda: self.db.disconnect())

    def db_run(self, query, cursor=None):
        cursor = cursor or self.db.con.cursor()
        cursor.execute(query)
        return cursor.fetchone()

    def test_retry_inject_attempt(self):
        @retry
        def _fn(db, attempt=None):
            self.assertIsNotNone(attempt)
            self.assertEqual(attempt.number, 1)

        _fn(self.db)

    def test_retry_accept_max_attempts(self):
        success = []
        failures = []

        @retry(max_attempts=5)
        def _fn(db, attempt=None):
            if attempt.count < 4:
                failures.append(attempt.count)
                raise DatabaseError("Emulate DB error", "msg")
            success.append(attempt.count)

        _fn(self.db)
        self.assertEqual(failures, [0, 1, 2, 3])
        self.assertEqual(success, [4])

    def test_retry_reconnect_auctomatically(self):
        success = []
        failures = []

        @retry(max_attempts=3)
        def _fn(db, attempt=None):
            if attempt.count < 2:
                failures.append(attempt.count)
                db.con.close()  # Simulate connection failure
            result = self.db_run('select 1+1, 2+2;')
            success.append(attempt.count)
            return result

        result = _fn(self.db)
        self.assertEqual(failures, [0, 1])
        self.assertEqual(success, [2])
        self.assertEqual(result, (2, 4))

    def test_retry_reraise_non_db_errors(self):
        failures = []

        @retry
        def _fn(db, attempt=None):
            failures.append(attempt.count)
            raise SystemError("Non Correlated Error")

        with self.assertRaises(SystemError):
            _fn(self.db)

        self.assertEqual(failures, [0])

    def test_transaction_rollback(self):
        with self.assertRaises(IntegrityError), \
                 self.db.transaction() as cursor:
            # The first row is created normally
            self.db_run('insert into test_table (id) values (1)', cursor)
            # The second row fails due to repeated id
            self.db_run('insert into test_table (id) values (1)', cursor)
            # The entire transaction will rollback then, and therefore the
            # first operation will be undone

        count = self.db_run('select count(*) FROM test_table')
        self.assertEqual(count, (0,))

    def test_transaction_cursor(self):
        with self.db.transaction(cursors.DictCursor) as cursor:
            count = self.db_run('select count(*) as counter FROM test_table',
                                cursor)

        self.assertEqual(count, {'counter': 0})


if __name__ == '__main__':
    unittest.main()
