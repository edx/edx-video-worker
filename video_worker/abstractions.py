"""
Abstractions / A simple way for openVEDA to remember!

AbstractionLayer Object (acts as master abstraction)
    -Video Object
    -[ EncodeObject, EncodeObject ]

"""

import json
import logging
import requests

from reporting import Output
import generate_apitoken
from video_worker.utils import get_config
from global_vars import *
from validate import ValidateVideo


"""Disable insecure warning for requests lib"""
requests.packages.urllib3.disable_warnings()

settings = get_config()

logger = logging.getLogger(__name__)


class Video(object):
    """
    This is a simple video class for easy portability between stages in the workflow
    Includes simple tooling for QA checks and a basic API information importer
    """
    def __init__(self, veda_id=None, **kwargs):

        self.veda_id = veda_id
        self.valid = False
        self.vid_pk = None
        self.class_id = None
        self.val_id = None
        self.mezz_extension = None
        self.mezz_bitrate = None
        self.mezz_title = None
        self.mezz_filesize = None
        self.mezz_resolution = None
        self.mezz_duration = None
        self.mezz_filepath = kwargs.get('mezz_filepath', None)
        # optional
        self.course_url = kwargs.get('course_url', [])

    def activate(self):
        """
        test case
        """
        if self.veda_id is not None and len(settings['veda_api_url']) == 0:
            logger.error('VEDA API Config Incorrect')
            return

        if self.veda_id is None and self.mezz_filepath is None:
            self.mezz_extension = '.mp4'
            self.mezz_title = TEST_VIDEO_FILE
            self.mezz_filepath = os.path.join(TEST_VIDEO_DIR, TEST_VIDEO_FILE)
            self.valid = True
            return

        if self.veda_id:
            """
            Generated Token
            """
            veda_token = generate_apitoken.veda_tokengen()
            if veda_token is None:
                return None

            data = {
                'edx_id': self.veda_id,
            }
            headers = {
                'Authorization': 'Token ' + veda_token,
                'content-type': 'application/json'
            }
            x = requests.get(
                '/'.join((settings['veda_api_url'], 'videos', '')),
                params=data,
                headers=headers
            )

            vid_dict = json.loads(x.text)
            if len(vid_dict['results']) == 0:
                return None

            for v in vid_dict['results']:
                """
                Yeah this is horrible, but it's tied to VEDA's model

                """
                self.vid_pk = v['id']
                self.class_id = v['inst_class']
                self.course_url = v['course_ids']
                self.val_id = v['studio_id']
                self.mezz_extension = v['video_orig_extension']
                self.mezz_bitrate = v['video_orig_bitrate']
                self.mezz_title = v['client_title']
                self.mezz_filesize = v['video_orig_filesize']
                # Do some field cleaning in case of SAR/DAR legacy errors
                mezz_resolution = v['video_orig_resolution'].strip().split(' ')[0]
                self.mezz_resolution = mezz_resolution
                '''Clean from unicode (00:00:00.53)'''
                uni_duration = v['video_orig_duration']
                self.mezz_duration = Output.seconds_from_string(uni_duration)
                self.mezz_filepath = '/'.join((
                    'https://s3.amazonaws.com',
                    settings['veda_s3_hotstore_bucket'],
                    self.veda_id + '.' + self.mezz_extension
                ))
                self.valid = True
        else:
            VV = ValidateVideo(
                filepath=self.mezz_filepath,
                VideoObject=self
            )
            video_dict = VV.get_video_attributes()
            self.mezz_extension = str(os.path.splitext(self.mezz_filepath)[1]).replace('.', '')
            self.mezz_bitrate = 0
            self.mezz_title = self.mezz_filepath.split('/')[-1]
            self.mezz_filesize = video_dict['filesize']
            self.mezz_resolution = video_dict['resolution']
            self.mezz_duration = video_dict['duration']
            self.mezz_filepath = self.mezz_filepath
            self.mezz_bitrate = 'Unparsed'
            self.valid = True


class Encode(object):
    """
    A basic class for easy programatic access to the diff salient variables
    """
    def __init__(self, video_object, profile_name):
        self.ffcommand = ''
        self.VideoObject = video_object
        self.profile_name = profile_name
        self.encode_suffix = None
        self.filetype = None
        self.resolution = None
        self.rate_factor = None
        self.encode_pk = None
        self.output_file = None
        self.upload_filesize = None
        self.endpoint_url = None
        self.encode_library = None

    def pull_data(self):
        """
        Retrieve Active and latest encode data from central VEDA node
        """
        # TODO: Change retrieval to a scheduled/delay process
        if self.VideoObject.veda_id is None:
            self._default_encodes()
            return

        veda_token = generate_apitoken.veda_tokengen()
        if veda_token is None:
            logger.error(
                ': {id} {encode} VEDA Token Generate'.format(
                    id=self.VideoObject.veda_id,
                    encode=self.profile_name
                )
            )
            return

        data = {'product_spec': self.profile_name}

        headers = {
            'Authorization': 'Token ' + veda_token,
            'content-type': 'application/json'
        }
        x = requests.get(
            '/'.join((settings['veda_api_url'], 'encodes')),
            params=data,
            headers=headers
        )
        if x.status_code > 250:
            self._default_encodes()
            return

        enc_dict = json.loads(x.text)

        if len(enc_dict['results']) == 0:
            logger.error(
                ': {id} {encode} VEDA API Encode Mismatch: No Data'.format(
                    id=self.VideoObject.veda_id,
                    encode=self.profile_name
                )
            )
            return

        for e in enc_dict['results']:
            if e['product_spec'] == self.profile_name and e['profile_active'] is True:
                self.resolution = e['encode_resolution']
                self.rate_factor = e['encode_bitdepth']
                self.filetype = e['encode_filetype']
                self.encode_suffix = e['encode_suffix']
                self.encode_pk = e['id']

                if self.encode_suffix is None:
                    # In the case of an API Error
                    self._default_encodes()

    def _default_encodes(self):
        """
        filetype': u'mp4', u'encode_suffix': u'DTH', u'resolution': 720, u'rate_factor'
        """
        encode_data = self._read_encodes()
        self.resolution = encode_data[self.profile_name]['resolution']
        self.rate_factor = encode_data[self.profile_name]['rate_factor']
        self.filetype = encode_data[self.profile_name]['filetype']
        self.encode_suffix = encode_data[self.profile_name]['encode_suffix']
        self.encode_pk = None

    def _read_encodes(self):
        if self.encode_library is None:
            self.encode_library = os.path.join(
                os.path.dirname(os.path.dirname(
                    os.path.abspath(__file__))
                ),
                'default_encode_profiles.json'
            )

        with open(self.encode_library) as data_file:
            data = json.load(data_file)
            return data["ENCODE_PROFILES"]
