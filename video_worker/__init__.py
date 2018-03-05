"""
Generate a serial transcode stream from a VEDA instance via Celery.
"""

import boto
import logging
import nose
import os
import subprocess
import shutil

from boto.s3.connection import S3Connection
from boto.exception import S3ResponseError
from chunkey import Chunkey

from video_worker.abstractions import Video, Encode
from video_worker.api_communicate import UpdateAPIStatus
from celeryapp import deliverable_route
from video_worker.generate_encode import CommandGenerate
from video_worker.generate_delivery import Deliverable
from video_worker.global_vars import ENCODE_WORK_DIR, VAL_TRANSCODE_STATUS, NODE_TRANSCODE_STATUS
from video_worker.reporting import Output
from video_worker.validate import ValidateVideo
from video_worker.video_images import VideoImages
from video_worker.utils import get_config

try:
    boto.config.add_section('Boto')
except:
    pass

boto.config.set('Boto', 'http_socket_timeout', '10')

logging.basicConfig()
logger = logging.getLogger(__name__)


class VideoWorker(object):

    def __init__(self, **kwargs):
        self.settings = None
        self.veda_id = kwargs.get('veda_id', None)
        self.setup = kwargs.get('setup', False)
        self.jobid = kwargs.get('jobid', None)
        self.encode_profile = kwargs.get('encode_profile', None)
        self.VideoObject = kwargs.get('VideoObject', None)

        # Working Dir Config
        self.workdir = kwargs.get('workdir', None)
        if self.workdir is None:
            if self.jobid is None:
                self.workdir = ENCODE_WORK_DIR
            else:
                self.workdir = os.path.join(ENCODE_WORK_DIR, self.jobid)

            if not os.path.exists(ENCODE_WORK_DIR):
                os.mkdir(ENCODE_WORK_DIR)

        self.ffcommand = None
        self.source_file = kwargs.get('source_file', None)
        self.output_file = None
        self.endpoint_url = None
        # Pipeline Steps
        self.encoded = False
        self.delivered = False

    def test(self):
        """
        Run tests
        """
        current_dir = os.getcwd()

        test_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'tests'
        )
        os.chdir(test_dir)
        test_bool = nose.run()

        # Return to previous state
        os.chdir(current_dir)
        return test_bool

    def run(self):
        self.settings = get_config()

        if self.encode_profile is None:
            logger.error('[VIDEO_WORKER] No Encode Profile Specified')
            return

        self.VideoObject = Video(
            veda_id=self.veda_id,
        )
        if self.source_file is not None:
            self.VideoObject.mezz_filepath = os.path.join(
                self.workdir,
                self.source_file
            )

        self.VideoObject.activate()
        if not self.VideoObject.valid:
            logger.error('[VIDEO_WORKER] Invalid Video / VEDA Data')
            return

        if not os.path.exists(self.workdir):
            os.mkdir(self.workdir)

        # Pipeline Steps :
        #   I. Intake
        #     Ib. Validate Mezz
        #   II. change status in APIs
        #   III. Generate Encode Command
        #   IV. Execute Encodes
        #     IVa. Validate Products
        #   (*)V. Deliver Encodes (sftp and others?), retrieve URLs
        #   (*)VI. Change Status in APIs, add URLs
        #   VII. Clean Directory

        self._engine_intake()

        if not self.VideoObject.valid:
            logger.error('[VIDEO_WORKER] Invalid Video / Local')
            return

        if self.VideoObject.val_id is not None:
            self._update_api()

        # generate video images command and update S3 and edxval
        # run against 'hls' encode only
        if self.encode_profile == 'hls':
            VideoImages(
                video_object=self.VideoObject,
                work_dir=self.workdir,
                source_file=self.source_file,
                jobid=self.jobid,
                settings=self.settings
            ).create_and_update()
            # Run HLS encode
            self._hls_pipeline()
        else:
            self._static_pipeline()

        if self.endpoint_url is not None and self.VideoObject.veda_id is not None:
            # Integrate with main
            veda_id = self.veda_id
            encode_profile = self.encode_profile
            deliverable_route.apply_async(
                (veda_id, encode_profile),
                queue=self.settings['celery_deliver_queue']
            )
        # Clean up workdir
        if self.jobid is not None:
            shutil.rmtree(
                self.workdir
            )

    def _static_pipeline(self):
        self._generate_encode()
        if self.ffcommand is None:
            return

        self._execute_encode()

        if self.encode_profile == 'audio_mp3':
            self.encoded = True
        else:
            self._validate_encode()

        if self.encoded and self.VideoObject.veda_id is not None:
            self._deliver_file()

    def _hls_pipeline(self):
        """
        Activate HLS, use hls lib to upload
        """
        if not os.path.exists(os.path.join(self.workdir, self.source_file)):
            logger.error('[VIDEO_WORKER] Source File (local) NOT FOUND - HLS')
            return

        os.chdir(self.workdir)

        V1 = Chunkey(
            mezz_file=os.path.join(self.workdir, self.source_file),
            DELIVER_BUCKET=self.settings['edx_s3_endpoint_bucket'],
            ACCESS_KEY_ID=self.settings['edx_access_key_id'],
            SECRET_ACCESS_KEY=self.settings['edx_secret_access_key'],
            clean=False
        )

        if V1.complete:
            self.endpoint_url = V1.manifest_url

    def _engine_intake(self):
        """
        Copy file down from AWS S3 storage bucket
        """
        if not self.VideoObject.valid:
            logger.error('[VIDEO_WORKER] Invalid Video')
            return

        if self.source_file is None:
            conn = S3Connection(
                self.settings['veda_access_key_id'],
                self.settings['veda_secret_access_key']
            )
            try:
                bucket = conn.get_bucket(self.settings['veda_s3_hotstore_bucket'])
            except S3ResponseError:
                logger.error('[VIDEO_WORKER] Invalid Storage Bucket')
                return

            if self.VideoObject.mezz_extension is not None and len(self.VideoObject.mezz_extension) > 0:
                self.source_file = '.'.join((
                    self.VideoObject.veda_id,
                    self.VideoObject.mezz_extension
                ))
            else:
                self.source_file = self.VideoObject.veda_id
            source_key = bucket.get_key(self.source_file)

            if source_key is None:
                logger.error('[VIDEO_WORKER] S3 Intake Object NOT FOUND')
                return

            source_key.get_contents_to_filename(
                os.path.join(self.workdir, self.source_file)
            )

            if not os.path.exists(os.path.join(self.workdir, self.source_file)):
                logger.error('[VIDEO_WORKER] Engine Intake Download')

            return

        self.VideoObject.valid = ValidateVideo(
            filepath=os.path.join(self.workdir, self.source_file)
        ).valid

    def _update_api(self):
        UpdateAPIStatus(
            val_video_status=VAL_TRANSCODE_STATUS,
            veda_video_status=NODE_TRANSCODE_STATUS,
            VideoObject=self.VideoObject,
        ).run()

    def _generate_encode(self):
        """
        Generate the (shell) command / Encode Object
        """
        E = Encode(
            video_object=self.VideoObject,
            profile_name=self.encode_profile
        )
        E.pull_data()

        if E.filetype is None:
            return

        self.ffcommand = CommandGenerate(
            VideoObject=self.VideoObject,
            EncodeObject=E,
            jobid=self.jobid,
            workdir=self.workdir,
            settings=self.settings
        ).generate()

    def _execute_encode(self):
        """
        if this is just a filepath, this should just work
        --no need to move the source--
        """
        if not os.path.exists(os.path.join(self.workdir, self.source_file)):
            logger.error('[VIDEO_WORKER] Source File (local) NOT FOUND - Input')
            return
        process = subprocess.Popen(
            self.ffcommand,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
            universal_newlines=True
        )
        print '%s : %s' % (self.VideoObject.veda_id, self.encode_profile)
        Output.status_bar(process=process)
        # to be polite
        print
        self.output_file = self.ffcommand.split('/')[-1]
        if not os.path.exists(
                os.path.join(self.workdir, self.output_file)
        ):
            logger.error('[VIDEO_WORKER] Source File (local) NOT FOUND - Output')

    def _validate_encode(self):
        """
        Validate encode by matching (w/in 5 sec) encode duration,
        as well as standard validation tests
        """
        self.encoded = ValidateVideo(
            filepath=os.path.join(self.workdir, self.output_file),
            product_file=True,
            VideoObject=self.VideoObject
        ).valid

    def _deliver_file(self):
        """
        Deliver Here
        """
        if not os.path.exists(
                os.path.join(self.workdir, self.output_file)
        ):
            return

        D1 = Deliverable(
            VideoObject=self.VideoObject,
            encode_profile=self.encode_profile,
            output_file=self.output_file,
            jobid=self.jobid,
            workdir=self.workdir
        )
        D1.run()
        self.delivered = D1.delivered
        self.endpoint_url = D1.endpoint_url
