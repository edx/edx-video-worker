"""
This file tests configuration settings for worker setup.
"""

import os
import unittest
import yaml

from ddt import ddt, data, unpack
from mock import Mock, patch, mock_open

from utils import create_worker_setup, TEST_INSTANCE_YAML, DUMMY_INSTANCE_YAML


@ddt
class ConfigTest(unittest.TestCase):
    """
    Config test class.
    """

    @data(
        (True, TEST_INSTANCE_YAML),
        (False, TEST_INSTANCE_YAML),
        (False, '/dummy-instance-config-path'),
        (True, '/dummy-instance-config-path')
    )
    @unpack
    @patch('video_worker.config.WorkerSetup._READ_SETTINGS')
    @patch('video_worker.config.WorkerSetup._CONFIGURE')
    def test_run(self, setup, instance_yaml, mock_configure, mock_read_settings):
        """
        Tests that correct method is called based on worker setup configuration
        """
        WS = create_worker_setup({
            'instance_yaml': instance_yaml,
            'setup': setup
        })
        WS.run()

        instance_yaml_exists = os.path.exists(WS.instance_yaml)
        self.assertEqual(mock_configure.called, setup or not instance_yaml_exists)
        self.assertEqual(mock_read_settings.called, not setup and instance_yaml_exists)

    @data(
        ('/dummy-instance-config-path', 'Not Configured'),
        (TEST_INSTANCE_YAML, '')
    )
    @unpack
    @patch('video_worker.config.logger')
    def test_read_settings(self, instance_yaml, error_message, mock_logger):
        """
        Tests that `_READ_SETTINGS` method works correctly.
        """
        WS = create_worker_setup({
            'instance_yaml': instance_yaml
        })
        self.assertEqual(WS.settings_dict, {})
        WS._READ_SETTINGS()

        if error_message:
            self.assertFalse(len(WS.settings_dict))
            mock_logger.error.assert_called_with(error_message)
        else:
            self.assertNotEqual(WS.settings_dict, {})
            self.assertTrue(len(WS.settings_dict))

    @patch('video_worker.config.raw_input', create=True)
    @patch('video_worker.config.yaml.load')
    def test_configure(self, yaml_load, mock_raw_input):
        """
        Tests that `_CONFIGURE` method works correctly.
        """
        with open(DUMMY_INSTANCE_YAML, 'w+') as file:
            mock_raw_input.return_value = 'dummy-value'
            yaml_load.return_value = {
                'dummy_key': 'dummy-value',
                'empty_value_key': ''
            }
            WS = create_worker_setup({
                'instance_yaml': DUMMY_INSTANCE_YAML
            })
            self.assertEqual(WS.settings_dict, {})

            WS._CONFIGURE()
            self.assertNotEqual(WS.settings_dict, {})
            self.assertTrue(len(WS.settings_dict))

        # Close and delete the file after used
        file.close()
        os.remove(DUMMY_INSTANCE_YAML)

    @patch('video_worker.config.logger')
    @patch('video_worker.config.yaml.load')
    def test_read_settings_load_error(self, yaml_load, mock_logger):
        """
        Tests that `_READ_SETTINGS` method raises correct log in case of yaml load error.
        """
        error_message = 'Config YAML read error'
        yaml_load.side_effect = yaml.YAMLError(error_message)
        WS = create_worker_setup()
        self.assertEqual(WS.settings_dict, {})
        WS._READ_SETTINGS()
        mock_logger.error.assert_called_with(error_message)
        self.assertEqual(WS.settings_dict, {})

    @patch('video_worker.config.logger')
    @patch('video_worker.config.yaml.load')
    def test_configure_load_error(self, yaml_load, mock_logger):
        """
        Tests that `_CONFIGURE` method raises correct log in case of yaml load error.
        """
        error_message = 'default YAML read error'
        yaml_load.side_effect = yaml.YAMLError(error_message)
        WS = create_worker_setup()
        self.assertEqual(WS.settings_dict, {})
        WS._CONFIGURE()
        mock_logger.error.assert_called_with(error_message)
        self.assertEqual(WS.settings_dict, {})
