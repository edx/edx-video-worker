"""
Generate 3 images for a course video.
"""

from __future__ import absolute_import
import json
import logging
import math
import os
import subprocess
from uuid import uuid4

import requests
from boto.exception import S3ResponseError
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from edx_rest_api_client.client import OAuthAPIClient

from . import generate_apitoken
from video_worker.utils import get_config
from video_worker.utils import build_url
from six.moves import range


IMAGE_COUNT = 3
IMAGE_WIDTH = 1280
IMAGE_HEIGHT = 720
# skip 2 percent of video duration from start to avoid start credits
START_PERCENTAGE = 2.0 / 100
# skip 10 percent of video duration from end to avoid end credits
END_PERCENTAGE = 10.0 / 100

logger = logging.getLogger(__name__)


class VideoImages(object):
    """
    Video Images related functionality.
    """

    def __init__(self, video_object, work_dir, source_file, **kwargs):
        self.video_object = video_object
        self.work_dir = work_dir
        self.source_file = source_file
        self.source_video_file = os.path.join(self.work_dir, self.source_file)
        self.jobid = kwargs.get('jobid', None)
        self.settings = kwargs.get('settings', self.settings_setup())

    def settings_setup(self):
        """
        Initialize settings
        """
        return get_config()

    def create_and_update(self):
        """
        Creat images and update S3 and edxval
        """
        generated_images = self.generate()
        image_keys = self.upload(generated_images)
        self.update_val(image_keys)

    @staticmethod
    def calculate_positions(video_duration):
        """
        Calculate different positions at which images will be taken.

        Arguments:
            video_duration (int): duration of input video

        Returns:
            list of positions
        """
        # Skip predefined duration from start and end of the video
        # and divide remaining duarion into equal distant positions
        start = math.ceil(START_PERCENTAGE * video_duration)
        end = math.ceil(END_PERCENTAGE * video_duration)
        step = math.ceil((video_duration - end - start) / IMAGE_COUNT)
        return [int(start + i * step) for i in range(IMAGE_COUNT)]

    def generate(self):
        """
        Generate video images using ffmpeg.
        """
        if not self.video_object:
            logger.error(
                ': {id} Video Image generation failed: No Video Object'.format(
                )
            )
            return

        generated_images = []
        for position in self.calculate_positions(self.video_object.mezz_duration):
            generated_images.append(
                os.path.join(self.work_dir, '{}.png'.format(uuid4().hex))
            )
            command = ('{ffmpeg} -ss {position} -i {video_file} -y -vf scale={width}:{height}'
                       ' -vsync 2 -vframes 1 {output_file}'.format(
                           ffmpeg=self.settings['ffmpeg_compiled'],
                           position=position,
                           video_file=self.source_video_file,
                           width=IMAGE_WIDTH,
                           height=IMAGE_HEIGHT,
                           output_file=generated_images[-1]))

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=True,
                universal_newlines=True
            )
            stdoutdata, stderrdata = process.communicate()
            logger.info('executing command >> %s', command)
            logger.info('command output >> out=%s -- err=%s', stdoutdata, stderrdata)

        return_images = []
        for image in generated_images:
            if os.path.exists(image):
                return_images.append(image)

        return return_images

    def upload(self, generated_images):
        """
        Upload auto generated images to S3.
        """
        if self.settings['onsite_worker'] is True:
            s3_connection = S3Connection(
                self.settings['edx_access_key_id'],
                self.settings['edx_secret_access_key']
            )
        else:
            s3_connection = S3Connection()

        try:
            bucket = s3_connection.get_bucket(self.settings['aws_video_images_bucket'])
        except S3ResponseError:
            logger.error(': Invalid Storage Bucket for Video Images')
            return

        image_keys = []
        for generated_image in generated_images:
            upload_key = Key(bucket)
            upload_key.key = build_url(
                self.settings['instance_prefix'],
                self.settings['aws_video_images_prefix'],
                os.path.basename(generated_image)
            )
            # image path is stored in edxval without `instance_prefix`
            image_keys.append(
                build_url(
                    self.settings['aws_video_images_prefix'],
                    os.path.basename(generated_image)
                )
            )
            upload_key.set_contents_from_filename(generated_image)
            upload_key.set_acl('public-read')

        return image_keys

    def update_val(self, image_keys):
        """
        Update a course video in edxval database for auto generated images.
        """
        if len(image_keys) > 0:

            for course_id in self.video_object.course_url:
                data = {
                    'course_id': course_id,
                    'edx_video_id': self.video_object.val_id,
                    'generated_images': image_keys
                }

                client = OAuthAPIClient(self.settings['oauth2_provider_url'],
                                        self.settings['oauth2_client_id'],
                                        self.settings['oauth2_client_secret'])

                response = client.request('POST', self.settings['val_video_images_url'], data=json.dumps(data))

                if not response.ok:
                    logger.error(': {id} {message}'.format(
                        id=self.video_object.val_id,
                        message=response.content
                    ))


if __name__ == '__main__':
    vi = VideoImages()
