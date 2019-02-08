# -*- coding: utf-8 -*-
# pylint: disable=E1101

import unittest

from ..utils import get_arg, inject_args


class TestUtils(unittest.TestCase):
    def test_inject_args_curries_arguments(self):
        fn = inject_args(lambda a=None, b=None: a+b, a=3, b=5)
        self.assertEqual(fn(), 8)

    def test_inject_args_doesnt_add_arg_if_not_needed(self):
        fn = inject_args(lambda: 7, a=1, b=2)
        self.assertEqual(fn(), 7)
        fn = inject_args(lambda a=None: a, b=2)
        self.assertEqual(fn(1), 1)

    def test_inject_args_knows_how_to_handle_arg_order(self):
        fn = inject_args(lambda a=None, b=None: b - a, a=3)
        self.assertEqual(fn(b=4), 1)
        fn = inject_args(lambda b=None, a=None: b - a, a=3)
        self.assertEqual(fn(b=4), 1)

    def test_inject_args_works_as_decorator(self):
        fn = inject_args(x=1)(lambda x=None: x)
        self.assertEqual(fn(), 1)

    def test_get_arg__positional(self):
        def _fn(x, y, z):
            return x + y + z

        x = get_arg('x', _fn, (1, 3, 4), {})
        self.assertEqual(x, 1)
        y = get_arg('y', _fn, (1, 3, 4), {})
        self.assertEqual(y, 3)
        z = get_arg('z', _fn, (1, 3, 4), {})
        self.assertEqual(z, 4)

    def test_get_arg__keyword(self):
        def _fn(x, y, z=5):
            return x + y + z

        z = get_arg('z', _fn, (1, 2), {'z': 3})
        self.assertEqual(z, 3)


if __name__ == '__main__':
    unittest.main()
