"""
Command generation tests.
"""

import os
import unittest

from ddt import ddt, data, unpack
from mock import patch

from video_worker.abstractions import Video, Encode
from video_worker.global_vars import ENCODE_WORK_DIR, TARGET_ASPECT_RATIO, ENFORCE_TARGET_ASPECT
from video_worker.generate_encode import CommandGenerate
from video_worker.tests.utils import TEST_INSTANCE_YAML


@ddt
class CommandGenerateTest(unittest.TestCase):
    """
    Test class for Command Generate.
    """

    def setUp(self):
        """
        Setup for command generate tests.
        """
        self.video = Video(
            veda_id='XXXXXXXX2016-V00TEST'
        )
        self.encode = Encode(
            video_object=self.video,
            profile_name=None
        )
        self.command_generate = CommandGenerate(
            VideoObject=self.video,
            EncodeObject=self.encode
        )

    @data(
        (
            {
                'video_object': None,
                'error_message': 'Command generation: No Video object'
            }
        ),
        (
            {
                'encode_object': None,
                'error_message': 'Command generation: No Encode object'
            }
        ),
        (
            {
                'job_id': 'dummy-job-id',
                'ENFORCE_TARGET_ASPECT': True
            }
        ),
    )
    @patch('video_worker.generate_encode.logger')
    @patch.object(CommandGenerate, '_destination')
    @patch.object(CommandGenerate, '_passes')
    @patch.object(CommandGenerate, '_scalar')
    @patch.object(CommandGenerate, '_codec')
    @patch.object(CommandGenerate, '_call')
    def test_generate(self, mock_data, mock_call, mock_codec, mock_scalar, mock_passes, mock_destination, mock_logger):
        """
        Tests `generate` method works correctly.
        """
        ffcommand = ['dummy-ffcommand-arg']
        job_id = mock_data.get('job_id', None)
        command_generate = CommandGenerate(
            VideoObject=mock_data.get('video_object', self.video),
            EncodeObject=mock_data.get('encode_object', self.encode),
            jobid=job_id
        )

        self.assertEqual(command_generate.ffcommand, [])
        self.assertIsNone(command_generate.workdir)

        command_generate.ffcommand = ffcommand
        result_command = command_generate.generate()

        if mock_data.get('error_message', ''):
            mock_logger.error.assert_called_with(mock_data.get('error_message'))
        else:
            self.assertIsNotNone(command_generate.workdir)
            expected_workdir = os.path.join(ENCODE_WORK_DIR, job_id) if job_id else ENCODE_WORK_DIR
            self.assertEqual(command_generate.workdir, expected_workdir)
            self.assertEqual(result_command, ' '.join(ffcommand))

            if mock_data.get('ENFORCE_TARGET_ASPECT', False):
                self.assertTrue(mock_scalar.called)

            self.assertTrue(mock_call.called)
            self.assertTrue(mock_codec.called)
            self.assertTrue(mock_passes.called)
            self.assertTrue(mock_destination.called)

    @data(
        (
            {
                'veda_id': 'dummy-veda-id',
                'mezz_extension': 'mp4'
            }
        ),
        (
            {
                'mezz_extension': 'mp4'
            }
        ),
        (
            {
                'filetype': 'mp3'
            }
        )
    )
    def test_call(self, mock_data):
        """
        Test that  `_call` method works correctly.
        """
        veda_id = mock_data.get('veda_id', None)
        file_type = mock_data.get('filetype', None)
        mezz_extension = mock_data.get('mezz_extension', '')
        mezz_filepath = mock_data.get('mezz_filepath', 'dummy-mezz-path')

        self.command_generate.workdir = ENCODE_WORK_DIR
        self.command_generate.ffcommand = ['dummy-ffcommand-arg']
        self.command_generate.settings.update({'ffmpeg_compiled': '-ffmpeg_compiled'})
        self.command_generate.VideoObject.veda_id = veda_id
        self.command_generate.VideoObject.mezz_extension = mezz_extension
        self.command_generate.VideoObject.mezz_filepath = mezz_filepath
        self.command_generate.EncodeObject.filetype = file_type

        self.command_generate._call()

        expected_ffcommand = ['dummy-ffcommand-arg', '-ffmpeg_compiled', '-hide_banner', '-y', '-i']
        expected_ffcommand.append('{workdir}/{file_name}{file_extension}'.format(
            workdir=ENCODE_WORK_DIR,
            file_name=veda_id if veda_id else mezz_filepath,
            file_extension='.' + mezz_extension if mezz_extension else ''
        ))

        if file_type != 'mp3':
            expected_ffcommand.append('-c:v')
        else:
            expected_ffcommand.append('-c:a')

        self.assertEqual(self.command_generate.ffcommand, expected_ffcommand)

    @data(
        (
            {
                'filetype': 'mp3'
            }
        ),
        (
            {
                'filetype': 'mp3',
                'ffcommand': ['dummy-ffcommand-arg'],
                'expected_ffcommand': ['dummy-ffcommand-arg', 'libmp3lame']
            }
        ),
        (
            {
                'filetype': 'mp4',
                'ffcommand': ['dummy-ffcommand-arg'],
                'expected_ffcommand': ['dummy-ffcommand-arg', 'libx264']
            }
        ),
        (
            {
                'filetype': 'webm',
                'ffcommand': ['dummy-ffcommand-arg'],
                'expected_ffcommand': ['dummy-ffcommand-arg', 'libvpx']
            }
        )
    )
    def test_codec(self, mock_data):
        """
        Tests that `_codec` mothod works correctly.
        """
        self.command_generate.ffcommand = mock_data.get('ffcommand', None)
        self.command_generate.EncodeObject.filetype = mock_data.get('filetype', None)

        self.command_generate._codec()

        self.assertEqual(self.command_generate.ffcommand, mock_data.get('expected_ffcommand', None))

    @data(
        (
            {
                'ffcommand': None,
                'expected_ffcommand': None
            }
        ),
        (
            {
                'file_type': 'mp3',
                'expected_ffcommand': []
            }
        ),
        (
            {
                'resolution': 480,
                'mezz_bitrate': 'test mezz rate',
                'mezz_resolution': '720x480',
                'expected_ffcommand': []
            }
        ),
        (
            {
                'resolution': 480,
                'mezz_resolution': '720x420',
                'expected_ffcommand': ['-vf', 'scale=853:480']
            }
        ),
        # Add more coverage for _scalar method - See EDUCATOR-1071
    )
    def test_scalar(self, mock_data):
        """
        Tests `_scalar` method works correctly.
        """
        self.command_generate.ffcommand = mock_data.get('ffcommand', [])
        self.command_generate.EncodeObject.filetype = mock_data.get('file_type', 'mp4')
        self.command_generate.EncodeObject.resolution = mock_data.get('resolution', '480')
        self.command_generate.VideoObject.mezz_resolution = mock_data.get('mezz_resolution', 'Unparsed')
        self.command_generate.VideoObject.mezz_bitrate = mock_data.get('mezz_bitrate', 'Unparsed')

        self.command_generate._scalar()

        self.assertEqual(self.command_generate.ffcommand, mock_data.get('expected_ffcommand', []))

    @data(
        (
            'mp3',
            100,
            50,
            ['-b:a', '100k']
        ),
        (
            'mp4',
            100,
            50,
            ['-crf', '100']
        ),
        (
            'webm',
            100,
            50,
            ['-b:v', '50k', '-minrate', '10k', '-maxrate', '62k', '-bufsize', '26k']
        ),
        (
            'webm',
            100,
            200,
            ['-b:v', '100k', '-minrate', '10k', '-maxrate', '125k', '-bufsize', '76k']
        )
    )
    @unpack
    def test_passes(self, file_type, rate_factor, mezz_bitrate, expected_ffcommand):
        """
        Tests that `_passes` works correctly.
        """
        self.command_generate.EncodeObject.filetype = file_type
        self.command_generate.EncodeObject.rate_factor = rate_factor
        self.command_generate.VideoObject.mezz_bitrate = mezz_bitrate

        self.command_generate._passes()

        self.assertEqual(self.command_generate.ffcommand, expected_ffcommand)

    @data(
        {
            'file_type': 'mp4',
            'veda_id': 'dummy-veda-id',
            'expected_ffcommand': ['-movflags', 'faststart']
        },
        {
            'file_type': 'webm',
            'veda_id': 'dummy-veda-id',
            'expected_ffcommand': ['-c:a', 'libvorbis']
        },
        {
            'file_type': 'mp4',
            'veda_id': None,
            'expected_ffcommand': ['-movflags', 'faststart']
        },
    )
    @unpack
    def test_destination(self, file_type, veda_id, expected_ffcommand):
        """
        Tests that `_destination` works correctly.
        """
        encode_suffix = 'dummy-encode-suffix'
        mezz_file_path = 'dummy-mezz-path'
        self.command_generate.workdir = ENCODE_WORK_DIR
        self.command_generate.EncodeObject.encode_suffix = encode_suffix
        self.command_generate.EncodeObject.filetype = file_type
        self.command_generate.VideoObject.veda_id = veda_id
        self.command_generate.VideoObject.mezz_filepath = mezz_file_path

        # Add a correct expected ffcommand path
        expected_ffcommand.append('{workdir}/{veda_id}_{encode_suffix}.{file_type}'.format(
            workdir=ENCODE_WORK_DIR,
            veda_id=veda_id if veda_id else mezz_file_path,
            encode_suffix=encode_suffix,
            file_type=file_type
        ))

        self.command_generate._destination()

        self.assertEqual(self.command_generate.ffcommand, expected_ffcommand)
