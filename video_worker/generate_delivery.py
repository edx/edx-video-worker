"""
Gets specified Video and Encode object, and delivers file to endpoint
from VEDA_WORK_DIR, retrieves and checks URL, and passes info to objects

"""

import boto
import boto.s3
from boto.exception import S3ResponseError
from boto.s3.key import Key
import hashlib
import os
import sys
import shutil

from global_vars import MULTI_UPLOAD_BARRIER, ENCODE_WORK_DIR
from reporting import ErrorObject
from video_worker.utils import get_config


settings = get_config()


class Deliverable():

    def __init__(self, VideoObject, encode_profile, output_file, **kwargs):
        self.VideoObject = VideoObject
        self.encode_profile = encode_profile
        self.output_file = output_file
        self.jobid = kwargs.get('jobid', None)
        self.workdir = kwargs.get('workdir', None)
        self.endpoint_url = None
        self.hash_sum = 0
        self.upload_filesize = 0
        self.delivered = False

    def run(self):
        """
        Get file particulars, upload to s3
        """
        if self.workdir is None:
            if self.jobid is None:
                self.workdir = ENCODE_WORK_DIR
            else:
                self.workdir = os.path.join(
                    ENCODE_WORK_DIR,
                    self.jobid
                )

        # file size
        self.upload_filesize = os.stat(
            os.path.join(self.workdir, self.output_file)
        ).st_size
        # hash sum
        self.hash_sum = hashlib.md5(
            open(
                os.path.join(
                    self.workdir,
                    self.output_file
                ), 'rb'
            ).read()
        ).hexdigest()

        if self.upload_filesize < MULTI_UPLOAD_BARRIER:
            # Upload single part
            self.delivered = self._s3_upload()
        else:
            # Upload multipart
            self.delivered = self._boto_multipart()

        if self.delivered is False:
            return None

        self.endpoint_url = '/'.join((
            'https://s3.amazonaws.com',
            settings['veda_deliverable_bucket'],
            self.output_file
        ))
        return True

    def _s3_upload(self):
        """
        Upload single part (under threshold in node_config)
        node_config MULTI_UPLOAD_BARRIER
        """
        try:
            conn = boto.connect_s3(
                settings['veda_access_key_id'],
                settings['veda_secret_access_key']
                )
            delv_bucket = conn.get_bucket(settings['veda_deliverable_bucket'])

        except S3ResponseError:
            ErrorObject().print_error(
                message='Deliverable Fail: s3 Connection Error - Singleton'
            )
            return False

        upload_key = Key(delv_bucket)
        upload_key.key = self.output_file
        upload_key.set_contents_from_filename(
            os.path.join(self.workdir, self.output_file)
        )
        return True

    def _boto_multipart(self):
        """
        Split file into chunks, upload chunks

        NOTE: this should never happen, as your files should be much
        smaller than this, but one never knows
        """
        if not os.path.exists(
            os.path.join(
                self.workdir,
                self.output_file.split('.')[0]
            )
        ):
            os.mkdir(os.path.join(
                self.workdir,
                self.output_file.split('.')[0]
            ))

        os.chdir(
            os.path.join(self.workdir, self.output_file.split('.')[0])
        )

        # Split File into chunks
        split_command = 'split -b10m -a5'  # 5 part names of 5mb
        sys.stdout.write('%s : %s\n' % (self.output_file, 'Generating Multipart'))
        os.system(' '.join((split_command, os.path.join(self.workdir, self.output_file))))
        sys.stdout.flush()

        # Connect to s3
        try:
            c = boto.connect_s3(
                    settings['veda_access_key_id'],
                    settings['veda_secret_access_key']
                )
            b = c.lookup(settings['veda_deliverable_bucket'])
        except S3ResponseError:
            ErrorObject().print_error(
                message='Deliverable Fail: s3 Connection Error - Multipart'
            )
            return False

        if b is None:
            ErrorObject().print_error(
                message='Deliverable Fail: s3 Bucket Connection Error'
            )
            return False

        # Upload and stitch parts
        mp = b.initiate_multipart_upload(self.output_file)

        x = 1
        for fle in sorted(os.listdir(
            os.path.join(
                self.workdir,
                self.output_file.split('.')[0]
            )
        )):
            sys.stdout.write('%s : %s\r' % (fle, 'uploading part'))
            fp = open(fle, 'rb')
            mp.upload_part_from_file(fp, x)
            fp.close()
            sys.stdout.flush()
            x += 1
        sys.stdout.write('\n')
        mp.complete_upload()
        # Clean up multipart
        shutil.rmtree(os.path.join(self.workdir, self.output_file.split('.')[0]))
        return True
