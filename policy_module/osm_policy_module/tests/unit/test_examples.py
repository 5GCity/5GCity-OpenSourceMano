# -*- coding: utf-8 -*-

# Copyright 2018 Whitestack, LLC
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Whitestack, LLC

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at

#         http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# For those usages not covered by the Apache License, Version 2.0 please
# contact: bdiaz@whitestack.com or glavado@whitestack.com
##
import json
import unittest

import os

from jsonschema import validate


class ExamplesTest(unittest.TestCase):
    def test_examples_schema(self):
        example_file_path = os.path.join(os.path.dirname(__file__), '../examples/configure_scaling_full_example.json')
        schema_file_path = os.path.join(os.path.dirname(__file__), '../../models/configure_scaling.json')
        with open(example_file_path) as example_file, open(schema_file_path) as schema_file:
            validate(json.load(example_file), json.load(schema_file))


if __name__ == '__main__':
    unittest.main()
