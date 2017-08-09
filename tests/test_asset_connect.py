
from boto.exception import S3ResponseError
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

    def test_storage_connection(self):
        if not os.path.exists(self.WS.instance_yaml):
            return None

        conn = S3Connection()
        try:
            bucket = conn.get_bucket(self.settings['veda_s3_hotstore_bucket'])
            self.assertTrue(True)
        except S3ResponseError:
            self.assertFalse(True)

    def test_delivery_connection(self):
        if not os.path.exists(self.WS.instance_yaml):
            return None

        conn = S3Connection()
        try:
            bucket = conn.get_bucket(self.settings['veda_deliverable_bucket'])
            self.assertTrue(True)
        except S3ResponseError:
            self.assertFalse(True)


def main():
    unittest.main()

if __name__ == '__main__':
    sys.exit(main())
