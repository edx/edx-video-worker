

from boto.s3.connection import S3Connection
import os
import unittest
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from video_worker.config import WorkerSetup

"""
Test for deliverable connection
set to pass if instance_config.yaml is missing

"""


class TestAssetConnection(unittest.TestCase):

    def setUp(self):
        self.WS = WorkerSetup()
        if os.path.exists(self.WS.instance_yaml):
            self.WS.run()
        self.settings = self.WS.settings_dict

    def test_storage_setup(self):
        if not os.path.exists(self.WS.instance_yaml):
            return None

        salient_variables = [
            'aws_deliver_access_key',
            'aws_deliver_secret_key',
            'aws_deliver_bucket'
        ]
        for s in salient_variables:
            self.assertTrue(len(self.settings[s]) > 0)

    def test_delivery_setup(self):
        if not os.path.exists(self.WS.instance_yaml):
            return None

        salient_variables = [
            'aws_access_key',
            'aws_secret_key',
            'aws_storage_bucket'
        ]

        for s in salient_variables:
            self.assertTrue(len(self.settings[s]) > 0)

    def test_storage_connection(self):
        if not os.path.exists(self.WS.instance_yaml):
            return None

        conn = S3Connection(
            self.settings['aws_access_key'],
            self.settings['aws_secret_key']
        )
        try:
            bucket = conn.get_bucket(self.settings['aws_storage_bucket'])
            self.assertTrue(True)
        except:
            self.assertFalse(True)

    def test_delivery_connection(self):
        if not os.path.exists(self.WS.instance_yaml):
            return None

        conn = S3Connection(
            self.settings['aws_deliver_access_key'],
            self.settings['aws_deliver_secret_key']
        )
        try:
            bucket = conn.get_bucket(self.settings['aws_deliver_bucket'])
            self.assertTrue(True)
        except:
            self.assertFalse(True)


def main():
    unittest.main()

if __name__ == '__main__':
    sys.exit(main())
