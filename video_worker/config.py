"""
This will read a default yaml file and generate a config class
based on variables within

"""

import logging
import os
import sys
import yaml

logger = logging.getLogger(__name__)


class WorkerSetup:

    def __init__(self, **kwargs):
        self.instance_yaml = kwargs.get(
            'instance_yaml',
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'instance_config.yaml'
            )
        )
        self.settings_dict = {}

    def run(self):
        if not os.path.exists(self.instance_yaml):
            logger.error('Not Configured')
            return

        with open(self.instance_yaml, 'r') as stream:
            try:
                self.settings_dict = yaml.load(stream)
            except yaml.YAMLError:
                logger.error('Config YAML read error')
                return
