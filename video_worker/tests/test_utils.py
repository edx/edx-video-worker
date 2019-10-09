"""
Tests common utils
"""
from __future__ import absolute_import
import os
import six
import tempfile
from unittest import TestCase

import yaml
from ddt import data, ddt, unpack
from mock import patch

from video_worker import utils

TEST_CONFIG = {
    'var1': 123,
    'var2': 999,
    'sub': {
        'sub_var': 'http://example.com'
    }
}

TEST_STATIC_CONFIG = {
    'abc': 999,
    'nested': {
        'nested_url': 'nested.example.com'
    }
}


@ddt
class UtilTests(TestCase):
    """
    Common util tests.
    """
    def setUp(self):
        """
        Tests setup.
        """
        self._orig_environ = dict(os.environ)

        # create a temporary default config file
        _, self.file_path = tempfile.mkstemp(
            suffix='.yml',
            dir=tempfile.tempdir
        )
        with open(self.file_path, 'w') as outfile:
            yaml.dump(TEST_CONFIG, outfile, default_flow_style=False)

        os.environ['VEDA_ENCODE_WORKER_CFG'] = self.file_path

        # create a temporary static config file
        _, self.static_file_path = tempfile.mkstemp(
            suffix='.yml',
            dir=tempfile.tempdir
        )
        with open(self.static_file_path, 'w') as outfile:
            yaml.dump(TEST_STATIC_CONFIG, outfile, default_flow_style=False)

    def tearDown(self):
        """
        Reverse the setup
        """
        # Reset Environment back to original state
        os.environ.clear()
        os.environ.update(self._orig_environ)

        # remove temporary files
        os.remove(self.file_path)
        os.remove(self.static_file_path)

    @data(
        {
            'urls': ('http://api.cielo24/', '/add/job'),
            'params': {},
            'expected_url': 'http://api.cielo24/add/job'
        },
        {
            'urls': ('http://api.cielo24', '/add/job'),
            'params': {'a': 1, 'b': 2},
            'expected_url': 'http://api.cielo24/add/job?a=1&b=2'
        },
        {
            'urls': ('http://api.cielo24/', 'add/job'),
            'params': {'c': 3, 'd': 4},
            'expected_url': 'http://api.cielo24/add/job?c=3&d=4'
        },
        {
            'urls': ('http://api.cielo24', 'add/job'),
            'params': {'p': 100},
            'expected_url': 'http://api.cielo24/add/job?p=100'
        },
        {
            'urls': ('http://api.cielo24', 'add/job', 'media'),
            'params': {'p': 100},
            'expected_url': 'http://api.cielo24/add/job/media?p=100'
        }
    )
    @unpack
    def test_build_url(self, urls, params, expected_url):
        """
        Tests that utils.build_url works as expected.
        """
        url = utils.build_url(
            *urls,
            **params
        )

        generated_url_object = six.moves.urllib.parse.urlparse(url)
        generated_query_params = generated_url_object.query

        generated_query_netloc = generated_url_object.netloc
        generated_query_path = generated_url_object.path

        generated_query_params = six.moves.urllib.parse.parse_qsl(generated_query_params)
        generated_query_params = sorted(generated_query_params)

        expected_url_object = six.moves.urllib.parse.urlparse(expected_url)
        expected_query_params = expected_url_object.query

        expected_query_netloc = expected_url_object.netloc
        expected_query_path = expected_url_object.path

        expected_query_params = six.moves.urllib.parse.parse_qsl(expected_query_params)
        expected_query_params = sorted(expected_query_params)

        self.assertEqual(generated_query_params,
                         expected_query_params)

        self.assertEqual(generated_query_netloc,
                         expected_query_netloc)

        self.assertEqual(generated_query_path,
                         expected_query_path)

    def test_get_config_does_not_exist(self):
        """
        Tests that utils.get_config if file does not exist.
        """
        del os.environ['VEDA_ENCODE_WORKER_CFG']

        with self.assertRaises(IOError):
            utils.get_config(yaml_config_file='does_not_exist')

    def test_get_config_with_default(self):
        """
        Tests that utils.get_config works as expected when reading default config.
        """
        del os.environ['VEDA_ENCODE_WORKER_CFG']

        instance_config = utils.get_config()
        self.assertNotEqual(instance_config, {})

        # read the default config file
        default_yaml_config_file = os.path.join(
            utils.ROOT_DIR,
            utils.DEFAULT_CONFIG_FILE_NAME
        )
        with open(default_yaml_config_file, 'r') as config:
            config_dict = yaml.load(config, Loader=yaml.FullLoader)

        # read the default static config file
        with open(utils.STATIC_CONFIG_FILE_PATH, 'r') as config:
            static_config_dict = yaml.load(config, Loader=yaml.FullLoader)

        self.assertDictEqual(
            instance_config,
            dict(config_dict, **static_config_dict)
        )

    def test_get_config_with_path(self):
        """
        Tests that utils.get_config works as expected when reading config from environment path.
        """
        with patch('video_worker.utils.STATIC_CONFIG_FILE_PATH', self.static_file_path):
            with patch('video_worker.utils.DEFAULT_CONFIG_FILE_NAME', self.file_path):
                instance_config = utils.get_config()
        self.assertDictEqual(instance_config, dict(TEST_CONFIG, **TEST_STATIC_CONFIG))
