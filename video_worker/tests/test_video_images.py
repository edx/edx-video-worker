"""
Video image generation tests.
"""
from __future__ import absolute_import
import os
import tempfile
import unittest

import yaml
from boto.s3.connection import S3Connection
from ddt import data, ddt, unpack
from mock import Mock, patch
from moto import mock_s3_deprecated
from PIL import Image

from .utils import TEST_INSTANCE_YAML
from video_worker import video_images


class MockVideo(object):
    """
    Mock VideoObject
    """
    mezz_duration = 16
    course_url = None
    val_id = None


@ddt
class VideoImagesTest(unittest.TestCase):
    """
    Video images generation test class.
    """
    def setUp(self):
        self.work_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data'
        )
        self.source_file = 'test.mp4'
        with open(TEST_INSTANCE_YAML, 'r') as stream:
            self.settings = yaml.load(stream)

    @patch.object(video_images.VideoImages, 'generate', return_value = ['a/1.png'])
    @patch.object(video_images.VideoImages, 'upload', return_value = ['s3://images/a/1.png'])
    @patch.object(video_images.VideoImages, 'update_val')
    def test_create_and_update(self, mock_update_val, mock_upload, mock_generate):
        """
        Verify that VideoImages.create_and_update method works as expected.
        """
        video_images.VideoImages(
            video_object=MockVideo,
            work_dir=self.work_dir,
            source_file=self.source_file,
            jobid=101,
            settings=self.settings
        ).create_and_update()

        self.assertTrue(mock_generate.called)
        mock_upload.assert_called_with(['a/1.png'])
        mock_update_val.assert_called_with(['s3://images/a/1.png'])

    @data(
        {
            'duration': 10, 'positions': [1, 4, 7],
        },
        {
            'duration': 387, 'positions': [8, 122, 236],
        },
        {
            'duration': 888, 'positions': [18, 279, 540],
        }
    )
    @unpack
    def test_calculate_positions(self, duration, positions):
        """
        Verify that VideoImages.calculate_positions method works as expected.
        """
        self.assertEqual(video_images.VideoImages.calculate_positions(duration), positions)

    def test_generate(self):
        """
        Verify that VideoImages.generate method works as expected.
        """
        images = video_images.VideoImages(
            video_object=MockVideo,
            work_dir=self.work_dir,
            source_file=self.source_file,
            jobid=101,
            settings=self.settings
        ).generate()

        self.assertEqual(len(images), video_images.IMAGE_COUNT)

        for image in images:
            with Image.open(image) as img:
                self.assertEqual(img.size, (video_images.IMAGE_WIDTH, video_images.IMAGE_HEIGHT))

    @data(
        (
            ['course-v1:W3Cx+HTML5.0x+1T2017', 'course-v1:W3Cx+HTML5.0x+1T2018', 'course-v1:W3Cx+HTML5.0x+1T2019'],
            ['video-images/abc.png'],
            True,
            3
        ),
        (
            ['course-v1:W3Cx+HTML5.0x+1T2017', 'course-v1:W3Cx+HTML5.0x+1T2018'],
            ['video-images/abc.png'],
            True,
            2
        ),
        (
            [],
            ['video-images/abc.png'],
            False,
            0
        ),
    )
    @unpack
    @patch('video_worker.video_images.generate_apitoken.val_tokengen', Mock(return_value='val_api_token'))
    def test_update_val(self, course_ids, image_keys, post_called, post_call_count):
        """
        Verify that VideoImages.update_val method works as expected.
        """
        with patch('video_worker.video_images.requests.post', Mock(return_value=Mock(ok=True))) as mock_post:
            MockVideo.course_url = course_ids
            video_images.VideoImages(
                video_object=MockVideo,
                work_dir=self.work_dir,
                source_file=self.source_file,
                jobid=101,
                settings=self.settings
            ).update_val(image_keys)

            self.assertEqual(mock_post.called, post_called)
            self.assertEqual(mock_post.call_count, post_call_count)

    @mock_s3_deprecated
    def test_upload_image_keys(self):
        """
        Verify that VideoImages.upload construct correct s3 keys.
        """
        conn = S3Connection()
        conn.create_bucket(self.settings['aws_video_images_bucket'])

        s3_image_keys = video_images.VideoImages(
            video_object=MockVideo,
            work_dir=self.work_dir,
            source_file=self.source_file,
            jobid=101,
            settings=self.settings
        ).upload(['video_worker/tests/data/edx.jpg'])

        self.assertEqual(s3_image_keys, ['video-images/edx.jpg'])
