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
        self.default_yaml = kwargs.get(
            'default_yaml',
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'default_config.yaml'
            )
        )

        self.setup = kwargs.get('setup', False)
        self.settings_dict = {}

    def run(self):
        """
        Generate Settings dict
        """
        if self.setup is False and not os.path.exists(self.instance_yaml):
            self._CONFIGURE()
        elif self.setup is True:
            self._CONFIGURE()
        else:
            self._READ_SETTINGS()

    def _READ_SETTINGS(self):
        """
        Read Extant Settings or Generate New Ones
        """
        if not os.path.exists(self.instance_yaml):
            logger.error('Not Configured')
            return

        with open(self.instance_yaml, 'r') as stream:
            try:
                self.settings_dict = yaml.load(stream)
            except yaml.YAMLError as exc:
                logger.error('Config YAML read error')
                return

    def _CONFIGURE(self):
        """
        Prompt user for settings as needed for yaml
        """
        with open(self.default_yaml, 'r') as stream:
            try:
                config_dict = yaml.load(stream)
            except yaml.YAMLError as exc:
                logger.error('default YAML read error')
                return

        output_dict = {}

        for j, k in config_dict.iteritems():
            sys.stdout.write('\r')
            new_value = raw_input('%s :' % (j))
            # clean tailing slashes
            if new_value is not None and len(new_value) > 0 and new_value[-1] == '/':
                output_dict[j] = new_value[:-1]
            else:
                output_dict[j] = new_value
            sys.stdout.flush()

        with open(self.instance_yaml, 'w') as outfile:
            outfile.write(
                yaml.dump(
                    output_dict,
                    default_flow_style=False
                )
            )

        self.settings_dict = output_dict
