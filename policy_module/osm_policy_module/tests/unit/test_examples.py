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
