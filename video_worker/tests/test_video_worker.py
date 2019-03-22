"""
This file tests the working of Video Worker.
"""

import os
import unittest

from ddt import ddt, data, unpack
from boto.exception import S3ResponseError
from mock import Mock, patch

from video_worker import VideoWorker, logger as video_worker_logger, deliverable_route
from video_worker.abstractions import Video
from video_worker.global_vars import ENCODE_WORK_DIR
from video_worker.utils import get_config

worker_settings = get_config()


@ddt
class VideoWorkerTest(unittest.TestCase):
    """
    Test class for Video Worker.
    """

    def setUp(self):
        super(VideoWorkerTest, self).setUp()
        self.VW = VideoWorker(**{
            'workdir': '/dummy-work-dir'
        })

        # Provide dummy values for Video Worker.
        self.VW.VideoObject = Video(
            veda_id='XXXXXXXX2016-V00TEST'
        )
        self.VW.VideoObject.valid = True
        self.VW.output_file = 'dummy-outfile'
        self.VW.source_file = 'dummy-sourcefile'

    @data(
        {},
        {
            'jobid': 'dummy-job-id',
            'workdir': '',
        },
        {
            'jobid': 'dummy-job-id',
            'workdir': '',
        },
        {
            'jobid': 'dummy-job-id',
            'workdir': '/dummy-work-dir',
        }
    )
    def test_video_worker(self, data):
        """
        Tests video worker object is created with correct values.
        """
        VW = VideoWorker(**data)

        # Verify that workdir has correct value
        job_id = data.get('jobid', None)
        expected_workdir = data.get(
            'workdir',
            os.path.join(ENCODE_WORK_DIR, job_id) if job_id else ENCODE_WORK_DIR
        )
        self.assertEqual(VW.workdir, expected_workdir)

    @data(
        (
            {
                'error_message': 'No Encode Profile Specified'
            }
        ),
        (
            {
                'is_valid': False,
                'encode_profile': 'static-pipeline',
                'error_message': 'dummy-veda-id : Invalid Video Data'
            }
        ),
        (
            {
                'is_valid_engine_intake': False,
                'encode_profile': 'static-pipeline',
                'error_message': 'Invalid Video / Local'
            }
        ),
        (
            {
                'encode_profile': 'static-pipeline',
                'path_exists': False
            }
        ),
        # Success
        (
            {
                'encode_profile': 'hls'
            }
        ),
        (
            {
                'encode_profile': 'static-pipeline'
            }
        )
    )
    @patch.object(VideoWorker, '_static_pipeline')
    @patch.object(VideoWorker, '_hls_pipeline')
    @patch.object(VideoWorker, '_update_api')
    @patch('video_worker.video_images.VideoImages.settings_setup')
    @patch('video_worker.video_images.VideoImages.create_and_update')
    @patch.object(deliverable_route, 'apply_async')
    @patch.object(video_worker_logger, 'error')
    @patch('shutil.rmtree')
    @patch('os.path.exists')
    @patch('os.mkdir')
    def test_run(self, mock_data, mock_mkdir, mock_exists, mock_rmtree, mock_logger, celeryapp_sync_mock,
                 vide_images_create_and_update_mock, video_images_setup_mock, mock_update_api, mock_hls_pipeline,
                 mock_static_pipeline):
        """
        Test that `run` method works correctly.
        """
        is_valid = mock_data.get('is_valid', True)
        is_valid_engine_intake = mock_data.get('is_valid_engine_intake', True)
        error_message = mock_data.get('error_message', '')
        encoded_profile = mock_data.get('encode_profile', None)
        path_exists = mock_data.get('path_exists', True)

        self.VW.settings = worker_settings
        self.VW.encode_profile = encoded_profile
        self.VW.VideoObject.valid = is_valid
        self.VW.jobid = 'dummy-jobid'
        self.VW.endpoint_url = '/dummy-endpoint-url'

        # First 2 calls to os.path.exists will be called in WS.run() so we need to make sure our TEST_INSTANCE_YAML
        # file path is check correctly.
        mock_exists.side_effect = [True, True, path_exists] if path_exists else [True, path_exists]

        video_images_setup_mock.return_value = worker_settings

        def change_video_valid(self):
            """
            Changes Video.valid to True when validate() is called.
            """
            self.valid = True
            self.val_id = 'dummy-val-id'
            self.veda_id = 'dummy-veda-id'

        def change_video_invalid(self):
            """
            Changes Video.valid to False when validate() is called.
            """
            self.valid = False
            self.val_id = 'dummy-val-id'
            self.veda_id = 'dummy-veda-id'

        def change_video_valid_intake(self):
            """
            Changes VM.VideoObject.valid to False.
            """
            self.VideoObject.valid = True

        def change_video_invalid_intake(self):
            """
            Changes VM.VideoObject.valid to True.
            """
            self.VideoObject.valid = False

        change_video_func = change_video_valid if is_valid else change_video_invalid
        change_video_func_intake = change_video_valid_intake if is_valid_engine_intake else change_video_invalid_intake

        with patch('video_worker.abstractions.Video.activate', new=change_video_func):
            with patch.object(VideoWorker, '_engine_intake', new=change_video_func_intake):
                # Call VideoWorker run method.
                self.VW.run()

        if error_message:
            mock_logger.assert_called_with(error_message)
        else:
            self.assertTrue(mock_update_api.called)
            self.assertTrue(celeryapp_sync_mock.called)
            self.assertTrue(mock_rmtree.called)

            if encoded_profile == 'hls':
                self.assertTrue(mock_hls_pipeline.called)
                self.assertFalse(mock_static_pipeline.called)

                self.assertTrue(vide_images_create_and_update_mock.called)
                self.assertTrue(video_images_setup_mock.called)
            else:
                self.assertTrue(mock_static_pipeline.called)
                self.assertFalse(mock_hls_pipeline.called)

    @patch('os.path.exists')
    @patch.object(video_worker_logger, 'error')
    def test_hls_pipeline_error(self, mock_logger, mock_exists):
        """
        Test that `hls_pipeline` logs correct error when path does not exist.
        """
        mock_exists.return_value = False

        self.assertIsNone(self.VW.endpoint_url)

        self.VW._hls_pipeline()

        self.assertIsNone(self.VW.endpoint_url)
        mock_logger.assert_called_with(': XXXXXXXX2016-V00TEST | None Local raw video file not found')

    @data(
        (
            {
                'generate_encode_mock_called': True
            }
        ),
        (
            {
                'ffcommand': 'dummy-ffcommand',
                'generate_encode_mock_called': True,
                'validate_encode_mock_called': True,
                'execute_encode_mock_called': True
            }
        ),
        (
            {
                'ffcommand': 'dummy-ffcommand',
                'is_encoded': True,
                'generate_encode_mock_called': True,
                'validate_encode_mock_called': True,
                'execute_encode_mock_called': True,
                'deliver_file_mock_called': True
            }
        ),
    )
    @patch.object(VideoWorker, '_deliver_file')
    @patch.object(VideoWorker, '_validate_encode')
    @patch.object(VideoWorker, '_execute_encode')
    @patch.object(VideoWorker, '_generate_encode')
    def test_static_pipeline(self, mock_data, generate_encode_mock,
                             execute_encode_mock, validate_encode_mock, deliver_file_mock):
        """
        Test that `_static_pipeline` works correctly.
        """
        self.VW.ffcommand = mock_data.get('ffcommand', None)
        self.VW.encoded = mock_data.get('is_encoded', False)

        self.VW._static_pipeline()

        self.assertEqual(generate_encode_mock.called, mock_data.get('generate_encode_mock_called', False))
        self.assertEqual(execute_encode_mock.called, mock_data.get('execute_encode_mock_called', False))
        self.assertEqual(validate_encode_mock.called, mock_data.get('validate_encode_mock_called', False))
        self.assertEqual(deliver_file_mock.called, mock_data.get('deliver_file_mock_called', False))

    @patch('os.path.exists')
    @patch('os.chdir')
    def test_hls_pipeline(self, mock_chdir, mock_exists):
        """
        Tests `_hls_pipeline` works correctly.
        """
        # Mock `os.chdir` to procced ahead in the test.
        # Mock to return path exists
        mock_exists.return_value = True

        def change_chunkey(self, **kwarg):
            """
            Change values of Chunkey when __init__ is called.
            """
            self.complete = True
            self.manifest_url = '/dummy-manifest-url'

        # Add dummy s3 bucket info to settings.
        worker_settings.update({
            'edx_s3_endpoint_bucket': 'dummy-edx_s3_endpoint_bucket',
            'edx_access_key_id': 'dummy-edx_access_key_id',
            'edx_secret_access_key': 'dummy-edx_secret_access_key',
        })
        self.VW.settings = worker_settings

        self.assertIsNone(self.VW.endpoint_url)

        with patch('chunkey.Chunkey.__init__', new=change_chunkey) as mock_chunkey:
            self.VW._hls_pipeline()

        self.assertIsNotNone(self.VW.endpoint_url)
        self.assertEqual(self.VW.endpoint_url, '/dummy-manifest-url')

    @data(
        (
            {
                'valid_video': False,
                'error_message': ': XXXXXXXX2016-V00TEST Invalid Video'
            }
        ),
        (
            {
                'source_file': None,
                'mock_get_bucket': False,
                'error_message': 'Invalid hotstore S3 bucket'
            }
        ),
        (
            {
                'source_file': None,
                'mock_get_bucket_key': True,
                'error_message': ': None S3 Intake object not found'
            }
        ),
        (
            {
                'source_file': None,
                'path_exists': False,
                'error_message': ': None engine intake download error'
            }
        ),
        # Success
        (
            {
                'source_file': 'dummy-source-file.mp4',
                'validate_valid': False
            }
        ),
        (
            {
                'source_file': 'dummy-source-file.mp4',
                'validate_valid': True
            }
        )
    )
    @patch('boto.s3.connection.S3Connection.__init__')
    @patch('boto.s3.connection.S3Connection.get_bucket')
    @patch.object(video_worker_logger, 'error')
    @patch('os.path.exists')
    @patch('video_worker.validate.ValidateVideo.validate')
    def test_engine_intake(self, data, mock_valid, mock_exists, mock_logger, mock_get_bucket, mock_conn):
        """
        Test that `_engine_intake` method works correctly.
        """
        # Setup test data.
        self.VW.VideoObject.valid = data.get('valid_video', self.VW.VideoObject.valid)
        self.VW.VideoObject.mezz_extension = '.mp4'
        self.VW.source_file = data.get('source_file', self.VW.source_file)

        # Mock s3 bucket and key
        bucket = Mock(get_key=Mock(return_value=Mock()))

        # `bucket.get_key` returns None.
        if data.get('mock_get_bucket_key', False):
            bucket = Mock(get_key=Mock(return_value=None))

        mock_exists.return_value = data.get('path_exists', True)
        mock_conn.return_value = None
        mock_get_bucket.return_value = bucket
        mock_valid.return_value = data.get('validate_valid', False)

        # Throw S3ResponseError on `s3connection.get_bucket`
        if not data.get('mock_get_bucket', True):
            mock_get_bucket.side_effect = S3ResponseError(403, 'Forbidden', 'Dummy S3ResponseError.')

        # Add dummy s3 bucket info to settings.
        worker_settings.update({
            'aws_storage_bucket': 'dummy-aws_storage_bucket',
        })
        self.VW.settings = worker_settings

        self.VW._engine_intake()

        if data.get('error_message', ''):
            mock_logger.assert_called_with(data.get('error_message'))
        else:
            self.assertEqual(self.VW.VideoObject.valid, data.get('validate_valid', False))

    @patch('video_worker.api_communicate.UpdateAPIStatus.run')
    def test_update_api(self, mock_run):
        """
        Tests `_update_api` method works correctly.
        """
        self.assertFalse(mock_run.called)
        self.VW._update_api()
        self.assertTrue(mock_run.called)

    @data(
        ('', ''),
        ('video/mp4', 'dummy-ffcommand')
    )
    @unpack
    @patch('video_worker.generate_encode.CommandGenerate.generate')
    def test_generate_encode(self, filetype, ffcommand, ffcommand_generate_mock):
        """
        Test that `_generate_encode` works correctly.
        """
        ffcommand_generate_mock.return_value = ffcommand

        def no_change_encode(self):
            """
            Does not change value of Encode's filetype when mock is called.
            """
            pass

        def change_encode(self):
            """
            Changes value of Encode's filetype when mock is called.
            """
            self.filetype = 'video/mp4'

        pull_data_change_function = change_encode if filetype else no_change_encode
        with patch('video_worker.abstractions.Encode.pull_data', new=pull_data_change_function) as pull_data_mock:
            self.VW._generate_encode()

        if filetype and ffcommand:
            self.assertIsNotNone(self.VW.ffcommand)
            self.assertEqual(self.VW.ffcommand, ffcommand)
        else:
            self.assertIsNone(self.VW.ffcommand)

    @data(
        (
            {
                'error_message': ': XXXXXXXX2016-V00TEST Encode input file not found'
            }
        ),
        (
            {
                'path_exists': [True, False],
                'error_message': ': XXXXXXXX2016-V00TEST Encode output file not found'
            }
        ),
        (
            {
                'path_exists': [True, True]
            }
        )
    )
    @patch('os.path.exists')
    @patch.object(video_worker_logger, 'error')
    def test_execute_encode(self, mock_data, mock_logger, mock_exists):
        """
        Test that `_execute_encode` method worrks correctly.
        """
        expected_output_file = 'dummy-outfile'
        self.VW.ffcommand = '/dummy/test/path/ffcommand-outfile'
        mock_exists.side_effect = mock_data.get('path_exists', [False, False])

        self.assertEqual(self.VW.output_file, expected_output_file)

        self.VW._execute_encode()

        if mock_data.get('error_message', ''):
            mock_logger.assert_called_with(mock_data.get('error_message', ''))

        expected_output_file = 'ffcommand-outfile' if len(mock_data.get('path_exists', [])) else expected_output_file
        self.assertEqual(self.VW.output_file, expected_output_file)

    @data(True, False)
    @patch('video_worker.validate.ValidateVideo.validate')
    def test_validate_encode(self, is_valid, mock_valid):
        """
        Tests `_validate_encode` method works correctly.
        """
        mock_valid.return_value = is_valid
        self.assertFalse(self.VW.encoded)

        self.VW._validate_encode()
        self.assertEqual(self.VW.encoded, is_valid)

    @patch('os.path.exists')
    def test_deliver_file_not_exist(self, mock_exists):
        """
        Tests that `_deliver_file` does not do any thing if output_file does not exist.
        """
        mock_exists.return_value = False

        self.assertFalse(self.VW.delivered)
        self.assertIsNone(self.VW.endpoint_url)
        self.VW._deliver_file()

        self.assertTrue(mock_exists.called)
        self.assertFalse(self.VW.delivered)
        self.assertIsNone(self.VW.endpoint_url)

    @patch('os.path.exists')
    def test_deliver_file(self, mock_exists):
        """
        Tests `_deliver_file` works correctly.
        """

        def change_deliverable(self):
            """
            Change values of Deliverable when D1.run() is called in `deliver_file`.
            """
            self.delivered = True
            self.endpoint_url = '/dummy-endpoint-url'

        # Mock os.path.exists so that we can proceed to Deliverable without actually creating the path.
        mock_exists.return_value = True

        self.assertFalse(self.VW.delivered)
        self.assertIsNone(self.VW.endpoint_url)

        with patch('video_worker.generate_delivery.Deliverable.run', new=change_deliverable) as mock_deliverable_run:
            self.VW._deliver_file()

        self.assertTrue(self.VW.delivered)
        self.assertIsNotNone(self.VW.endpoint_url)
        self.assertEqual(self.VW.endpoint_url, '/dummy-endpoint-url')
