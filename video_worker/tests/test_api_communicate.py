"""
This file tests the workflow of api_communicate.py.
"""

import os
import json
import unittest

from ddt import ddt, data, unpack
from mock import Mock, patch

from video_worker.abstractions import Video
from video_worker.api_communicate import UpdateAPIStatus

from utils import create_worker_setup


WS = create_worker_setup()
WS.run()


@ddt
@patch('video_worker.api_communicate.settings', WS.settings_dict)
class ApiCommunicateTest(unittest.TestCase):
    """
    Api Communicate test class.
    """
    @classmethod
    def setUpClass(cls):
        super(ApiCommunicateTest, cls).setUpClass()
        cls.Video = Video(
            veda_id='XXXXXXXX2016-V00TEST'
        )
        cls.Video.valid = True
        cls.veda_video_status = 'veda status'
        cls.val_video_status = 'val status'

    def setup_api(self, VideoObject=None, **kwargs):
        """
        Setup UpdateAPIStatus Api interface with appropriate arguments.
        """
        communicate_api = UpdateAPIStatus(
            VideoObject=VideoObject,
            veda_video_status=kwargs.get('veda_video_status', None),
            val_video_status=kwargs.get('val_video_status', None),
            send_veda=kwargs.get('send_veda', True),
            send_val=kwargs.get('send_val', True),
        )

        if communicate_api.VideoObject:
            communicate_api.VideoObject.val_id = kwargs.get('val_id', None)
            communicate_api.VideoObject.course_url = kwargs.get('course_url', [])
            communicate_api.VideoObject.valid = kwargs.get('is_video_valid', True)

        communicate_api.veda_token = kwargs.get('veda_token', None)
        communicate_api.val_token = kwargs.get('val_token', None)
        communicate_api.veda_video_dict = kwargs.get('veda_video_dict', None)

        if communicate_api.veda_token:
            communicate_api.veda_headers = {
                'Authorization': 'Token {veda_token}'.format(veda_token=communicate_api.veda_token),
                'content-type': 'application/json'
            }
        return communicate_api

    @data(
        (True, True),
        (False, True),
        (False, False),
        (True, False)
    )
    @unpack
    @patch('video_worker.api_communicate.UpdateAPIStatus.run_val')
    @patch('video_worker.api_communicate.UpdateAPIStatus.run_veda')
    def test_run(self, send_veda, send_val, mock_run_veda, mock_run_val):
        """
        Tests that correct method is called.
        """
        communicate_api = self.setup_api(
            send_veda=send_veda,
            send_val=send_val
        )
        communicate_api.run()
        self.assertEqual(mock_run_veda.called, send_veda)
        self.assertEqual(mock_run_val.called, send_val)

    @data(
        (None, None),
        ('dummy-veda-token', None),
        ('dummy-veda-token', 'dummy-veda-video-status')
    )
    @unpack
    @patch('video_worker.api_communicate.logger')
    @patch('video_worker.api_communicate.UpdateAPIStatus.send_veda_status')
    @patch('video_worker.generate_apitoken.veda_tokengen')
    def test_run_veda(self, veda_token, veda_video_status, mock_veda_tokengen, mock_send_veda_status, mock_logger):
        """
        Test that `run_veda` method works correctly.
        """
        mock_veda_tokengen.return_value = veda_token
        communicate_api = self.setup_api(
            veda_video_status=veda_video_status
        )
        response = communicate_api.run_veda()
        if not veda_token:
            self.assertFalse(response)
            self.assertFalse(mock_send_veda_status.called)
            mock_logger.error.assert_called_with('VEDA API Conn Fail: Invalid Setup/Method')
        elif not veda_video_status:
            self.assertFalse(response)
            self.assertFalse(mock_send_veda_status.called)
        else:
            self.assertTrue(mock_send_veda_status.called)

    @data(None, 'dummy-val-token')
    @patch('video_worker.api_communicate.UpdateAPIStatus.send_val_data')
    @patch('video_worker.generate_apitoken.val_tokengen')
    def test_run_val(self, val_token, mock_val_tokengen, mock_send_val_data):
        """
        Test that `run_val` method works correctly.
        """
        mock_val_tokengen.return_value = val_token
        communicate_api = self.setup_api()
        response = communicate_api.run_val()
        if not val_token:
            self.assertFalse(response)
            self.assertFalse(mock_send_val_data.called)
        else:
            self.assertTrue(mock_send_val_data.called)

    @data(
        (True, 200),
        (True, 400),
        (False, 200),
        (False, 400)
    )
    @unpack
    @patch('video_worker.api_communicate.requests.patch')
    @patch('video_worker.api_communicate.logger')
    def test_send_veda_status(self, is_video_valid, response_status_code, mock_logger, mock_patch):
        """
        Tests `send_veda_status` method works correctly.
        """
        response_data = 'Dummy response data'
        communicate_api = self.setup_api(
            VideoObject=self.Video,
            veda_video_status=self.veda_video_status,
            val_video_status=self.val_video_status,
            veda_video_dict={
                'results': [{
                    'id': 123
                }]
            },
            veda_token='dummy-veda-token',
            is_video_valid=is_video_valid
        )
        response = communicate_api.send_veda_status()

        if not is_video_valid:
            self.assertFalse(mock_patch.called)
            self.assertFalse(response)
        elif response_status_code != 200:
            self.assertTrue(mock_patch.called)
            mock_logger.error.assert_called_with('VEDA API Fail: File GET Failure, no objects')

    @data(
        # Check empty values
        (
            {
                'val_token': None,
                'val_id': None,
                'course_url': []
            },
        ),
        (
            {
                'val_token': 'dummy-val-token',
                'val_id': None,
                'course_url': []
            },
        ),
        (
            {
                'val_token': 'dummy-val-token',
                'val_id': 'dummy-val-id',
                'course_url': []
            },
        ),
        # Check logging with status codes
        (
            {
                'val_token': 'dummy-val-token',
                'val_id': 'dummy-val-id',
                'course_url': ['dummy-course-id'],
                'get_status_code': 400,
                'post_status_code': 200,
                'error_message': 'VAL Communication Fail'
            },
        ),
        (
            {
                'val_token': 'dummy-val-token',
                'val_id': 'dummy-val-id',
                'course_url': ['dummy-course-id'],
                'get_status_code': 404,
                'post_status_code': 300,
                'error_message': 'VAL POST/PUT Fail: VAL'
            },
        ),
        (
            {
                'val_token': 'dummy-val-token',
                'val_id': 'dummy-val-id',
                'course_url': ['dummy-course-id'],
                'get_status_code': 200,
                'post_status_code': 300,
                'error_message': 'VAL POST/PUT Fail'
            },
        ),
        # Success
        (
            {
                'val_token': 'dummy-val-token',
                'val_id': 'dummy-val-id',
                'course_url': ['dummy-course-id']
            },
        )
    )
    @unpack
    @patch('video_worker.api_communicate.requests.put')
    @patch('video_worker.api_communicate.requests.post')
    @patch('video_worker.api_communicate.requests.get')
    @patch('video_worker.api_communicate.logger')
    def test_send_val_data(self, data, mock_logger, mock_get, mock_post, mock_put):
        """
        Tests `send_val_data` method works correctly.
        """
        get_status_code = data.get('get_status_code', 200)
        post_status_code = data.get('post_status_code', 201)
        expected_error_message = data.get('error_message', '')
        response_data = json.dumps({
            'courses': [{
                'dummy-course-id': 'dummy-video-image.jpeg'
            }],
            'encoded_videos': [{
                'url': 'https://testurl.mp4',
                'file_size': 8499040,
                'bitrate': 131,
                'profile': 'override',
            }]
        })

        mock_get.return_value = Mock(status_code=get_status_code, text=response_data, content=response_data)
        mock_post.return_value = Mock(status_code=post_status_code, text=response_data, content=response_data)
        mock_put.return_value = Mock(status_code=post_status_code, text=response_data, content=response_data)
        communicate_api = self.setup_api(
            VideoObject=self.Video,
            val_video_status=self.val_video_status,
            val_token=data.get('val_token', None),
            val_id=data.get('val_id', None),
            course_url=data.get('course_url', []),
        )

        response = communicate_api.send_val_data()

        if not data.get('val_token', None):
            self.assertFalse(mock_get.called)
            self.assertFalse(mock_post.called)
            self.assertFalse(response)

        if expected_error_message:
            self.assertTrue(mock_get.called)
            if get_status_code == 404:
                self.assertFalse(mock_put.called)
                self.assertTrue(mock_post.called)
            if get_status_code == 200:
                self.assertFalse(mock_post.called)
                self.assertTrue(mock_put.called)
            mock_logger.error.assert_called_with(expected_error_message)

    @data(
        (False, 400, ''),
        (True, 400, 'VEDA API Fail: Check VEDA API config'),
        (True, 200, '')
    )
    @unpack
    @patch('video_worker.api_communicate.requests.get')
    @patch('video_worker.api_communicate.logger')
    def test_determine_veda_pk(self, send_video_object, get_status_code, expected_error_message, mock_logger, mock_get):
        """
        Tests `determine_veda_pk` method works correctly.
        """
        response_data = json.dumps({
            'results': [{
                'id': 123
            }]
        })
        mock_get.return_value = Mock(status_code=get_status_code, text=response_data, content=response_data)
        communicate_api = self.setup_api(
            VideoObject=self.Video if send_video_object else None
        )

        response = communicate_api.determine_veda_pk()

        if not send_video_object:
            self.assertFalse(mock_get.called)
            self.assertFalse(response)

        if expected_error_message:
            self.assertTrue(mock_get.called)
            mock_logger.error.assert_called_with(expected_error_message)
        elif get_status_code == 200:
            self.assertTrue(mock_get.called)
            self.assertTrue('results' in response)
