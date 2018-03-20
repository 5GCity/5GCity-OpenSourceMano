import json
import os
import unittest

from osm_policy_module.core.agent import PolicyModuleAgent


class PolicyAgentTest(unittest.TestCase):
    def setUp(self):
        self.agent = PolicyModuleAgent()

    def test_get_alarm_configs(self):
        with open(os.path.join(os.path.dirname(__file__), './examples/configure_scaling_full_example.json')) as file:
            example = json.load(file)
            alarm_configs = self.agent._get_alarm_configs(example)
            # TODO Improve assertions
            self.assertEqual(len(alarm_configs), 2)


if __name__ == '__main__':
    unittest.main()
