"""
Generate a serial transcode stream from a VEDA instance via Celery.
"""


import boto
import logging
import os
import subprocess
import shutil

from boto.s3.connection import S3Connection
from boto.exception import S3ResponseError
from chunkey import Chunkey

from video_worker.abstractions import Video, Encode
from video_worker.api_communicate import UpdateAPIStatus
from .celeryapp import deliverable_route
from video_worker.generate_encode import CommandGenerate
from video_worker.generate_delivery import Deliverable

from video_worker.global_vars import (
    HOME_DIR,
    ENCODE_WORK_DIR,
    VAL_TRANSCODE_STATUS,
    NODE_TRANSCODE_STATUS,
    BOTO_TIMEOUT
)
from video_worker.reporting import Output
from video_worker.validate import ValidateVideo
from video_worker.video_images import VideoImages
from video_worker.utils import get_config

try:
    boto.config.add_section('Boto')
except:
    pass

boto.config.set('Boto', 'http_socket_timeout', BOTO_TIMEOUT)
server_name = os.environ.get('SERVER_NAME', 'test-worker')
log_format = '[ENCODE_WORKER] ' + server_name + ': %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(format=log_format, level=logging.INFO)
logging.getLogger("requests").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class VideoWorker(object):

    def __init__(self, **kwargs):
        self.settings = None
        self.veda_id = kwargs.get('veda_id', None)
        self.setup = kwargs.get('setup', False)
        self.jobid = kwargs.get('jobid', None)
        self.update_val_status = kwargs.get('update_val_status')
        self.encode_profile = kwargs.get('encode_profile', None)
        self.VideoObject = kwargs.get('VideoObject', None)

        self.instance_yaml = kwargs.get(
            'instance_yaml',
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'instance_config.yaml'
            )
        )
        self.workdir = kwargs.get('workdir', self.determine_workdir())
        self.ffcommand = None
        self.source_file = kwargs.get('source_file', None)
        self.output_file = None
        self.endpoint_url = None
        # Pipeline Steps
        self.encoded = False
        self.delivered = False

    def determine_workdir(self):
        if not os.path.exists(ENCODE_WORK_DIR):
            os.mkdir(ENCODE_WORK_DIR)
        if self.jobid is None:
            return ENCODE_WORK_DIR
        else:
            return os.path.join(ENCODE_WORK_DIR, self.jobid)

    def run(self):
        self.settings = get_config()

        if self.encode_profile is None:
            logger.error('No Encode Profile Specified')
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
            logger.error('{id} : Invalid Video Data'.format(id=self.VideoObject.veda_id))
            return

        if not os.path.exists(self.workdir):
            os.mkdir(self.workdir)

        logger.info('{id} | {encoding} : Ready for Encode'.format(
            id=self.VideoObject.veda_id,
            encoding=self.encode_profile
        ))
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
            logger.error('Invalid Video / Local')
            return

        if self.VideoObject.val_id is not None:
            self._update_api()

        # generate video images command and update S3 and edxval
        # run against 'hls' encode only
        if self.encode_profile == 'hls':
            # Run HLS encode
            self._hls_pipeline()
            # Auto-video Images
            VideoImages(
                video_object=self.VideoObject,
                work_dir=self.workdir,
                source_file=self.source_file,
                jobid=self.jobid,
                settings=self.settings
            ).create_and_update()

        else:
            self._static_pipeline()
        logger.info('{id} | {encoding} : Encode Complete'.format(
            id=self.VideoObject.veda_id,
            encoding=self.encode_profile
        ))
        if self.endpoint_url is not None and self.VideoObject.veda_id is not None:
            # Integrate with main
            veda_id = self.veda_id
            encode_profile = self.encode_profile
            deliverable_route.apply_async(
                (veda_id, encode_profile),
                queue=self.settings['celery_deliver_queue']
            )
        logger.info('{id} | {encoding} : encoded file queued for delivery'.format(
            id=self.VideoObject.veda_id,
            encoding=self.encode_profile
        ))
        # Clean up workdir
        if self.jobid is not None:
            shutil.rmtree(
                self.workdir
            )

    def _static_pipeline(self):
        self._generate_encode()
        if self.ffcommand is None:
            return

        logger.info('ffcommand is written as %s', self.ffcommand)

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
            logger.error(': {id} | {encoding} Local raw video file not found'.format(
                id=self.VideoObject.veda_id,
                encoding=self.encode_profile
            ))
            return

        os.chdir(self.workdir)

        if self.settings['onsite_worker'] is True:
            hls_chunk_instance = Chunkey(
                mezz_file=os.path.join(self.workdir, self.source_file),
                DELIVER_BUCKET=self.settings['edx_s3_endpoint_bucket'],
                clean=False,
                ACCESS_KEY_ID=self.settings['edx_access_key_id'],
                SECRET_ACCESS_KEY=self.settings['edx_secret_access_key']
            )
        else:
            hls_chunk_instance = Chunkey(
                mezz_file=os.path.join(self.workdir, self.source_file),
                DELIVER_BUCKET=self.settings['edx_s3_endpoint_bucket'],
                clean=False,
            )

        if hls_chunk_instance.complete:
            self.endpoint_url = hls_chunk_instance.manifest_url

    def _engine_intake(self):
        """
        Copy file down from AWS S3 storage bucket
        """
        if not self.VideoObject.valid:
            logger.error(': {id} Invalid Video'.format(
                id=self.VideoObject.veda_id,
            ))
            return

        if self.source_file is None:
            if self.settings['onsite_worker'] is True:
                conn = S3Connection(
                    self.settings['veda_access_key_id'],
                    self.settings['veda_secret_access_key']
                )
            else:
                conn = S3Connection()
            try:
                bucket = conn.get_bucket(self.settings['veda_s3_hotstore_bucket'])
            except S3ResponseError:
                logger.error('Invalid hotstore S3 bucket')
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
                logger.error(': {id} S3 Intake object not found'.format(
                    id=self.VideoObject.val_id
                ))
                return

            source_key.get_contents_to_filename(
                os.path.join(self.workdir, self.source_file)
            )

            if not os.path.exists(os.path.join(self.workdir, self.source_file)):
                logger.error(': {id} engine intake download error'.format(
                    id=self.VideoObject.val_id
                ))
            return

        self.VideoObject.valid = ValidateVideo(
            filepath=os.path.join(self.workdir, self.source_file)
        ).valid

    def _update_api(self):
        UpdateAPIStatus(
            val_video_status=VAL_TRANSCODE_STATUS,
            veda_video_status=NODE_TRANSCODE_STATUS,
            send_val=self.update_val_status,
            VideoObject=self.VideoObject,
        ).run()

    def _generate_encode(self):
        """
        Generate the (shell) command / Encode Object
        """
        encoding = Encode(
            video_object=self.VideoObject,
            profile_name=self.encode_profile
        )
        encoding.pull_data()

        if encoding.filetype is None:
            return

        self.ffcommand = CommandGenerate(
            VideoObject=self.VideoObject,
            EncodeObject=encoding,
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
            logger.error(': {id} Encode input file not found'.format(
                id=self.VideoObject.veda_id
            ))
            return

        process = subprocess.Popen(
            self.ffcommand,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
            universal_newlines=True
        )
        Output.status_bar(process=process)

        self.output_file = self.ffcommand.split('/')[-1]
        if not os.path.exists(os.path.join(self.workdir, self.output_file)):
            logger.error(': {id} Encode output file not found'.format(
                id=self.VideoObject.veda_id
            ))

    def _validate_encode(self):
        """
        Validate encode by matching (w/in 5 sec) encode duration,
        as well as standard validation tests
        """
        if self.output_file is None:
            self.encoded = False
            return
        else:
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
