"""
Common utils.
"""
import os
import urllib
import yaml


DEFAULT_CONFIG_FILE_NAME = 'instance_config.yaml'
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_CONFIG_FILE_PATH = os.path.join(ROOT_DIR, 'static_config.yaml')


def build_url(*urls, **query_params):
    """
    Build a url from specified params.

    Arguments:
        base_url (str): base url
        relative_url (str): endpoint
        query_params (dict): query params

    Returns:
        absolute url
    """
    url = '/'.join(item.strip('/') for item in urls if item)
    if query_params:
        url = '{}?{}'.format(url, urllib.urlencode(query_params))

    return url


def get_config(yaml_config_file=DEFAULT_CONFIG_FILE_NAME):
    """
    Read yaml config file.

    Arguments:
        yaml_config_file (str): yaml config file name

    Returns:
        dict: yaml config
    """
    config_dict = {}

    try:
        yaml_config_file = os.environ['VEDA_ENCODE_WORKER_CFG']
    except KeyError:
        yaml_config_file = os.path.join(
            ROOT_DIR,
            yaml_config_file
        )

    with open(yaml_config_file, 'r') as config:
        config_dict = yaml.load(config)

    # read static config file
    with open(STATIC_CONFIG_FILE_PATH, 'r') as config:
        static_config_dict = yaml.load(config)

    return dict(config_dict, **static_config_dict)
