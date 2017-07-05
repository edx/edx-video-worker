
import os
import sys
import unittest
import yaml

"""
build test

"""


class BuildTest(unittest.TestCase):

    def setUp(self):
        self.default_yaml = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            ),
            'default_config.yaml'
        )

    def test_defaults(self):
        with open(self.default_yaml, 'r') as stream:
            try:
                config_dict = yaml.load(stream)
                self.assertTrue(True)
            except yaml.YAMLError as exc:
                self.assertTrue(False)


def main():
    unittest.main()

if __name__ == '__main__':
    sys.exit(main())
