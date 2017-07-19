"""
This file tests token generation for val and veda APIs.
"""

import json
import unittest

from ddt import ddt, data, unpack
from mock import Mock, patch

from video_worker.generate_apitoken import val_tokengen, veda_tokengen

from utils import create_worker_setup


WS = create_worker_setup()
WS.run()


@ddt
@patch('video_worker.generate_apitoken.settings', WS.settings_dict)
class GenerateApiTokenTest(unittest.TestCase):
    """
    GenerateApiToken test class.
    """

    @patch('video_worker.generate_apitoken.requests.post')
    @patch('video_worker.generate_apitoken.logger')
    def test_veda_tokengen_fail(self, mock_logger, mock_post):
        """
        Tests `veda_tokengen` method logs correct error message.
        """
        mock_post.return_value = Mock(status_code=400, text='', content={})
        response = veda_tokengen()
        self.assertFalse(response)
        mock_logger.error.assert_called_with('VEDA Token Generate')

    @patch('video_worker.generate_apitoken.requests.post')
    @patch('video_worker.generate_apitoken.logger')
    def test_veda_tokengen_auth_fail(self, mock_logger, mock_post):
        """
        Tests `veda_tokengen` method logs correct error message when authorization fails.
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
        response = veda_tokengen()
        self.assertFalse(response)
        mock_logger.error.assert_called_with('VEDA Token Authorization')

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
    @patch('video_worker.generate_apitoken.logger')
    def test_val_tokengen_fail(self, mock_logger, mock_post):
        """
        Tests `val_tokengen` method logs correct error message.
        """
        mock_post.return_value = Mock(status_code=400, text='', content={})
        response = val_tokengen()
        self.assertFalse(response)
        mock_logger.error.assert_called_with('Token Gen Fail: VAL - Check VAL Config')

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
