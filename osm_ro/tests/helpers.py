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

import logging
import unittest
from collections import defaultdict

from six import StringIO

from mock import MagicMock, patch

logger = logging.getLogger()


class TestCaseWithLogging(unittest.TestCase):
    """Attach a special handler to the root logger, capturing the logs in a
    internal buffer (caplog property).

    To retrieve the logs, do::

        self.caplog.getvalue()
    """
    def setUp(self):
        super(TestCaseWithLogging, self).setUp()
        self.logger = logging.getLogger()
        self.caplog = StringIO()
        self.log_handler = logging.StreamHandler(self.caplog)
        self.logger.addHandler(self.log_handler)
        self.logger.setLevel(logging.NOTSET)

    def tearDown(self):
        super(TestCaseWithLogging, self).tearDown()
        self.log_handler.close()
        self.logger.removeHandler(self.log_handler)


def mock_imports(modules, preserve=()):
    """Given a list of modules, mock everything, unless listed in the preserve
    argument.
    """
    # Ensure iterable
    if isinstance(modules, str):
        modules = (modules,)
    if isinstance(preserve, str):
        preserve = (preserve,)

    # First expand the list, since children modules needs their parent also
    # mocked most of the time.
    # Example: ['Crypto.PublicKey'] => ['Crypto', 'Crypto.PublicKey']
    all_modules = []
    for name in modules:
        parts = name.split('.')
        compound_name = []
        for part in parts:
            compound_name.append(part)
            all_modules.append('.'.join(compound_name))

    all_modules = set(m for m in all_modules if m not in preserve)
    for module in all_modules:
        logger.info('Mocking module `%s`', module)

    mocks = {module: MagicMock() for module in all_modules}

    return patch.dict('sys.modules', **mocks)


def mock_dict(**kwargs):
    """Create a dict that always respond something.

    Arguments:
        **kwargs: certain items that should be set in the created object
    """
    response = defaultdict(MagicMock)
    for k, v in kwargs.items():
        response[k] = v

    return response


def mock_object(**kwargs):
    """Create an object that always respond something.

    Arguments:
        **kwargs: certain attributes that should be set in the created object
    """
    response = MagicMock()
    for k, v in kwargs.items():
        setattr(response, k, v)

    return response
