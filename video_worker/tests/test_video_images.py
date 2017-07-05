"""
Video image generation tests.
"""
from ddt import ddt, data, unpack
import os
import sys
import unittest
import yaml
from PIL import Image


from video_worker import video_images

MOCK_SETTINGS = {
    'ffmpeg_compiled': 'ffmpeg'
}


class MockVideo(object):
    """
    Mock VideoObject
    """
    mezz_duration = 16


@ddt
class VideoImagesTest(unittest.TestCase):
    """
    Video images generation test class.
    """
    def setUp(self):
        self.work_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'VEDA_TESTFILES'
        )
        self.source_file = 'test.mp4'

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

    @unittest.skipIf(
        'TRAVIS' in os.environ and os.environ['TRAVIS'] == 'true',
        'Skipping this test on Travis CI due to unavailability of required ffmpeg version.'
    )
    def test_generate(self):
        """
        Verify that VideoImages.generate method works as expected.
        """
        images = video_images.VideoImages(
            video_object=MockVideo,
            work_dir=self.work_dir,
            source_file=self.source_file,
            jobid=101,
            settings=MOCK_SETTINGS
        ).generate()

        self.assertEqual(len(images), video_images.IMAGE_COUNT)

        for image in images:
            with Image.open(image) as img:
                self.assertEqual(img.size, (video_images.IMAGE_WIDTH, video_images.IMAGE_HEIGHT))
