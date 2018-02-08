"""
One off script to force re-encode 422 (satellite encoded) videos for iOS/Android decoded playback

"""

'''
Normal Command
ffmpeg -hide_banner -y -i ${ENCODE_WORKDIR}/UBCSC1SC2017-V007900.mov \
-c:v libx264 -vf scale=640:360 -crf 27 -movflags faststart ${ENCODE_WORKDIR}/UBCSC1SC2017-V007900_MB2.mp4

Should Read
ffmpeg -hide_banner -y -i ${ENCODE_WORKDIR}/UBCSC1SC2017-V007900.mov \
-pix_fmt yuv420p -c:v libx264 -vf scale=640:360 -crf 27 -movflags faststart ${ENCODE_WORKDIR}/UBCSC1SC2017-V007900_MB2.mp4


'''
# import boto
import logging
import os
import sys
import yaml

from boto.s3.connection import S3Connection
from boto.exception import S3ResponseError
from os.path import expanduser

# try:
#     boto.config.add_section('Boto')
# except:
#     pass
#
# boto.config.set('Boto', 'http_socket_timeout', BOTO_TIMEOUT)

logger = logging.getLogger(__name__)
homedir = expanduser("~")


class ForceColorspaceEncode(object):

    def __init__(self, **kwargs):
        self.course_dict = kwargs.get('course_dict', {})
        self.workdir = os.path.join(homedir, 'LEARNER-3956')
        self.instance_yaml = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'instance_config.yaml'
        )
        self.settings = self.setup()

    def setup(self):
        if not os.path.exists(self.instance_yaml):
            print('Not Configured')
            return

        with open(self.instance_yaml, 'r') as stream:
            try:
                settings_dict = yaml.load(stream)
            except yaml.YAMLError:
                print('[SCRIPT] YAML read error')
                return
        if not os.path.exists(self.workdir):
            os.mkdir(self.workdir)

        return settings_dict

    def run_encodes(self):
        for courseid, videoseq in self.course_dict.items():
            x = 100
            while x <= videoseq:
                file = "{course}-V{video}".format(course=courseid, video=str(x).zfill(6))
                print('[SCRIPT] {file}'.format(file=file))
                self.download_file(file)
                self.encode_file(file)
                self.upload_file(file)
                x += 100
                break

    def download_file(self, file):
        """
        'https://s3.amazonaws.com/veda-hotstore/UBCSC1SC2017-V007900.mov'
        :param file:
        :return:
        """

        conn = S3Connection(
            self.settings['veda_access_key_id'],
            self.settings['veda_secret_access_key']
        )
        try:
            bucket = conn.get_bucket(self.settings['veda_s3_hotstore_bucket'])
        except S3ResponseError:
            print('[SCRIPT] Invalid Storage Bucket')
            return

        file_key = '{file}.mov'.format(file=file)
        source_key = bucket.get_key(file_key)

        if source_key is None:
            print('[SCRIPT] S3 Intake Object NOT FOUND')
            return
        print('[SCRIPT] Downloading ...')
        source_key.get_contents_to_filename(os.path.join(self.workdir, file_key))

        if not os.path.exists(os.path.join(self.workdir, self.source_file)):
            print('[SCRIPT] Engine Intake Download')
            return

    def encode_file(self, file):
        """
        """
        pass

    def upload_file(self, file):
        """
        """
        pass


def main():
    encode_instance = ForceColorspaceEncode(
        course_dict={"UBCSC1SC2017": 12300, "UBCSE1SE2017": 12700}
    )
    encode_instance.run_encodes()


if __name__ == '__main__':
    sys.exit(main())
