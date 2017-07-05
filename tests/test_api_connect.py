
import os
import sys
import unittest
import requests

# for Travis
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from video_worker.config import WorkerSetup
from video_worker.generate_apitoken import val_tokengen, veda_tokengen

"""
This is an API connection test
set to pass if instance_config.yaml is missing

"""
# Disable warning
requests.packages.urllib3.disable_warnings()


class TestAPIConnection(unittest.TestCase):

    def setUp(self):
        self.WS = WorkerSetup()
        if os.path.exists(self.WS.instance_yaml):
            self.WS.run()
        self.settings = self.WS.settings_dict

    def test_val_setup(self):
        if not os.path.exists(self.WS.instance_yaml):
            self.assertTrue(True)
            return None

        salient_variables = [
            'val_api_url',
            'val_client_id',
            'val_password',
            'val_secret_key',
            'val_username',
            'val_token_url',
        ]
        for s in salient_variables:
            self.assertTrue(len(self.WS.settings_dict[s]) > 0)

    def test_veda_setup(self):
        if not os.path.exists(self.WS.instance_yaml):
            self.assertTrue(True)
            return None

        salient_variables = [
            'veda_api_url',
            'veda_auth_url',
            'veda_client_id',
            'veda_secret_key',
            'veda_token_url',
        ]
        for s in salient_variables:
            self.assertTrue(len(self.WS.settings_dict[s]) > 0)

    def test_val_connection(self):
        if not os.path.exists(self.WS.instance_yaml):
            self.assertTrue(True)
            return None

        val_token = val_tokengen()
        self.assertFalse(val_token is None)

        headers = {
            'Authorization': 'Bearer ' + val_token,
            'content-type': 'application/json'
        }
        s = requests.get(self.WS.settings_dict['val_api_url'], headers=headers, timeout=20)

        self.assertFalse(s.status_code == 404)
        self.assertFalse(s.status_code > 299)

    def test_veda_connection(self):
        if not os.path.exists(self.WS.instance_yaml):
            self.assertTrue(True)
            return None

        veda_token = veda_tokengen()
        self.assertFalse(veda_token is None)
        headers = {
            'Authorization': 'Token ' + veda_token,
            'content-type': 'application/json'
        }
        s = requests.get(self.WS.settings_dict['veda_api_url'] + '/', headers=headers, timeout=20)

        self.assertFalse(s.status_code == 404)
        self.assertFalse(s.status_code > 299)


def main():
    unittest.main()


if __name__ == '__main__':
    sys.exit(main())
