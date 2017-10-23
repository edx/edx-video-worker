"""
This file tests configuration settings for worker setup.
"""

import unittest
import yaml

from ddt import ddt, data, unpack
from mock import patch

from utils import create_worker_setup, TEST_INSTANCE_YAML


@ddt
class ConfigTest(unittest.TestCase):
    """
    Config test class.
    """
    @data(
        ('/dummy-instance-config-path', 'Not Configured'),
        (TEST_INSTANCE_YAML, '')
    )
    @unpack
    @patch('video_worker.config.logger')
    def test_run(self, instance_yaml, error_message, mock_logger):
        """
        Tests that `_read_settings` method works correctly.
        """
        WS = create_worker_setup({
            'instance_yaml': instance_yaml
        })
        self.assertEqual(WS.settings_dict, {})
        WS.run()

        if error_message:
            self.assertFalse(len(WS.settings_dict))
            mock_logger.error.assert_called_with(error_message)
        else:
            self.assertNotEqual(WS.settings_dict, {})
            self.assertTrue(len(WS.settings_dict))

    @patch('video_worker.config.logger')
    @patch('video_worker.config.yaml.load')
    def test_run_load_error(self, yaml_load, mock_logger):
        """
        Tests that `_read_settings` method raises correct log in case of yaml load error.
        """
        error_message = 'Config YAML read error'
        yaml_load.side_effect = yaml.YAMLError(error_message)
        WS = create_worker_setup()
        self.assertEqual(WS.settings_dict, {})
        WS.run()
        mock_logger.error.assert_called_with(error_message)
        self.assertEqual(WS.settings_dict, {})
