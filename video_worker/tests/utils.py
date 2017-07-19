"""
Adds util classes and methods for tests.
"""
import os

from video_worker.config import WorkerSetup


TEST_INSTANCE_YAML = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'test_instance_config.yaml'
)

DUMMY_INSTANCE_YAML = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'dummy_instance_config.yaml'
)


def create_worker_setup(kwargs={}):
    """
    Returns a worker setup object for tests.
    """
    kwargs['instance_yaml'] = kwargs.get('instance_yaml', TEST_INSTANCE_YAML)
    kwargs['setup'] = kwargs.get('setup', False)
    return WorkerSetup(**kwargs)
