"""
This file tests token generation for val and veda APIs.
"""

import json
import unittest

from ddt import ddt, data, unpack
from mock import Mock, patch

from video_worker.generate_apitoken import val_tokengen, veda_tokengen, VEDATokenError
from video_worker.tests.utils import TEST_INSTANCE_YAML_FILE
from video_worker.utils import get_config, RetryTimeoutError


WORKER_SETTINGS = get_config(yaml_config_file=TEST_INSTANCE_YAML_FILE)


@ddt
@patch('video_worker.generate_apitoken.settings', WORKER_SETTINGS)
class GenerateApiTokenTest(unittest.TestCase):
    """
    GenerateApiToken test class.
    """

    @patch('video_worker.generate_apitoken.requests.post')
    def test_veda_tokengen_fail(self, mock_post):
        """
        Tests `veda_tokengen` raises `RetryTimeoutError` on timeout.
        """
        mock_post.return_value = Mock(status_code=400, text='', content={})
        with self.assertRaises(RetryTimeoutError):
            veda_tokengen()

    @patch('video_worker.generate_apitoken.requests.post')
    def test_veda_tokengen_auth_fail(self, mock_post):
        """
        Tests `veda_tokengen` raises `RetryTimeoutError` on timeout.
        """
        access_token = 'dummy-val-token'
        response_data = json.dumps({
            'access_token': access_token
        })
        # Mock request multiple times with different responses.
        mock_post.side_effect = [
            Mock(status_code=200, text=response_data, content=response_data),
            Mock(status_code=400, text='', content={})
        ]
        with self.assertRaises(RetryTimeoutError):
            veda_tokengen()

    @patch('video_worker.generate_apitoken.requests.post')
    def test_veda_tokengen(self, mock_post):
        """
        Tests `veda_tokengen` method works correctly.
        """
        access_token = 'dummy-val-token'
        response_data = json.dumps({
            'access_token': access_token
        })
        mock_post.return_value = Mock(status_code=200, text=response_data, content=response_data)
        response = veda_tokengen()
        response = json.loads(response)
        self.assertEqual(response['access_token'], access_token)

    @patch('video_worker.generate_apitoken.requests.post')
    def test_veda_tokengen_with_retry(self, mock_post):
        """
        Tests `veda_tokengen` method works correctly with retry.
        """
        access_token = 'dummy-val-token'
        response_data = json.dumps({
            'access_token': access_token
        })
        mock_post.side_effect = [
            Mock(side_effect=VEDATokenError('Test')),
            Mock(side_effect=VEDATokenError('Test')),
            Mock(status_code=200, text=response_data, content=response_data),
            Mock(status_code=200, text=response_data, content=response_data),
        ]
        response = veda_tokengen()
        response = json.loads(response)
        self.assertEqual(response['access_token'], access_token)

    @patch('video_worker.generate_apitoken.requests.post')
    @patch('video_worker.generate_apitoken.logger')
    def test_val_tokengen_fail(self, mock_logger, mock_post):
        """
        Tests `val_tokengen` method logs correct error message.
        """
        mock_post.return_value = Mock(status_code=400, text='', content={})
        response = val_tokengen()
        self.assertFalse(response)
        mock_logger.error.assert_called_with('VAL token generation')

    @patch('video_worker.generate_apitoken.requests.post')
    def test_val_tokengen(self, mock_post):
        """
        Tests `val_tokengen` method works correctly.
        """
        access_token = 'dummy-val-token'
        response_data = json.dumps({
            'access_token': access_token
        })
        mock_post.return_value = Mock(status_code=200, text=response_data, content=response_data)
        response = val_tokengen()
        self.assertEqual(response, access_token)
