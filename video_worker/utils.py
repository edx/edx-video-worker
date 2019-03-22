"""
Common utils.
"""
from datetime import datetime, timedelta
import logging
import os
import time
import urllib
import yaml


log = logging.getLogger(__name__)


DEFAULT_CONFIG_FILE_NAME = 'instance_config.yaml'
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_CONFIG_FILE_PATH = os.path.join(ROOT_DIR, 'static_config.yaml')
DEFAULT_TIMEOUT_SECONDS = 120


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

    # Protect against missing vars
    default_yaml = os.path.join(ROOT_DIR, DEFAULT_CONFIG_FILE_NAME)
    with open(default_yaml, 'r') as config:
        default_dict = yaml.load(config)
    for key, entry in default_dict.items():
        config_dict.setdefault(key, entry)

    return dict(config_dict, **static_config_dict)


class RetryTimeoutError(Exception):
    """Raised when repeated attempts fail to succeed before the specified timeout expires."""
    pass


def retry_on_any_exception(_exc):
    """Retry regardless of the type of exception raised or its data."""
    return True


# copied from https://github.com/edx/edx-analytics-pipeline/blob/master/edx/analytics/tasks/util/retry.py
def retry(should_retry=retry_on_any_exception, base_delay=0.5, timeout=None):
    """
    Retry the function until it succeeds.

    Implements an exponential back-off, sleeping between attempts to allow the remote service to recover. This is often
    used to wrap integrations with external components or services, but could be used for internal purposes as well.
    Note that there are many third-party libraries that implement this simple decorator, but I didn't feel the low
    complexity warranted an entirely new external dependency.

    Arguments:
      should_retry (callable): A function that returns True if the function should be retried given the exception that
        occurred and False if it is fatal and no further attempts should be made. Note that this function is passed the
        exception, so it can read data from it in order to make the decision. For example, it might read the HTTP status
        code off of an HTTP request error.

      base_delay (float): After the first failure, the thread will sleep for this many seconds. After each subsequent
        failure it will double the amount of time it sleeps before retrying. For example: 0.5, 1, 2, 4, 8, 16 etc.

      timeout (float): If this many seconds elapse from the first attempt to the current attempt, abort the process and
        raise a RetryTimeoutError. This allows us to cap the total time spent trying for a successful result.

    Returns:
      A function decorator that uses the above parameters to implement the retry logic around the wrapped function.
    """
    def retry_func_wrapper(func):
        """Decorator that retries the function call when appropriate."""
        def retry_function(*args, **kwargs):
            """The wrapper function that handles errors raised by the decorated function implements the retry logic."""
            max_time = None
            has_valid_timeout = timeout is not None and timeout > 0
            if has_valid_timeout:
                max_time = datetime.utcnow() + timedelta(seconds=timeout)
            attempts = 0
            while True:
                attempts += 1
                try:
                    return func(*args, **kwargs)
                except Exception as exception:  # pylint: disable=broad-except
                    if should_retry(exception):
                        log.warning('Caught retryable exception "%s" in retry handler.  Message: %s', type(exception).__name__, exception)
                        if max_time and datetime.utcnow() > max_time:
                            raise RetryTimeoutError(
                                'Unable to successfully complete call before {} the max timeout time.'.format(
                                    max_time.isoformat()
                                )
                            )
                        sleep_for_seconds = base_delay * (2 ** (attempts - 1))
                        log.info('Sleeping for %f seconds', sleep_for_seconds)
                        time.sleep(sleep_for_seconds)
                        log.info('Retrying')
                    else:
                        raise
        return retry_function
    return retry_func_wrapper
