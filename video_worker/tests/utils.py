"""
Adds util classes and methods for tests.
"""

import os


TEST_INSTANCE_YAML = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'data/test_instance_config.yaml'
)

DUMMY_INSTANCE_YAML = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'dummy_instance_config.yaml'
)

# relative path to test config file
TEST_INSTANCE_YAML_FILE = 'video_worker/tests/data/test_instance_config.yaml'
